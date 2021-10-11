#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
from tkinter import messagebox, TclError

from LabExT.Experiments.ToDo import ToDo
from LabExT.Utils import get_visa_address, get_configuration_file_path
from LabExT.View.Controls.InstrumentSelector import InstrumentRole
from LabExT.View.EditMeasurementWizard.EditMeasurementWizardModel import EditMeasurementWizardModel
from LabExT.View.EditMeasurementWizard.EditMeasurementWizardView import EditMeasurementWizardView


class EditMeasurementWizardController:
    """
    Controller Class for the EditMeasurementWizard. Gets instanceiated and used from the main window.
    Sets up model and view classes, contains controll logic, callback functions for the EditMeasurementWizard
    """

    def __init__(self, parent, experiment_manager):
        self.root = parent
        self.experiment_manager = experiment_manager
        self._experiment = self.experiment_manager.exp

        self.logger = logging.getLogger()

        self.model = EditMeasurementWizardModel(self.experiment_manager)
        self.view = EditMeasurementWizardView(self.model, self, self.root, self.experiment_manager)

        # set the proper reference in the model class
        self.model.set_view(self.view)

        # setup the main window
        self.view.setup_main_window()

        # start the GUI
        self.stage_start(0)

    def stage_start(self, stage_number):
        """
        start stage with given number, takes care of GUI changes
        """
        # disable all frames before
        for stage_idx in range(0, stage_number):
            section_frame = self.view.section_frames[stage_idx]
            if section_frame is not None:
                # disable all content in frame
                section_frame.enabled = False
                # relink continue button to restart own stage
                section_frame.continue_button.config(text="Back", command=self._start_stage_wrapper(stage_idx))

        # remove selected and all future step frames from GUI
        for stage_idx in range(stage_number, len(self.view.section_frames)):
            section_frame = self.view.section_frames[stage_idx]
            if section_frame is not None:
                section_frame.grid_remove()

        # call GUI setup function of step
        if stage_number == 0:
            if self.model.chip_available:
                self.view.s0_chip_device_selection_setup()
            else:
                self.view.s0_adhoc_device_selection_setup()
        elif stage_number == 1:
            self.view.s1_measurement_selection_setup()
        elif stage_number == 2:
            self.view.s2_instrument_selection_setup()
        elif stage_number == 3:
            self.view.s3_measurement_parameter_setup()
        elif stage_number == 4:
            self.view.s4_final_save_buttons()
        else:
            raise ValueError("Unknown stage with number {:d}".format(stage_number))

        # call business logic after setup of stage
        self.stage_start_logic(stage_number=stage_number)

    def stage_start_logic(self, stage_number):
        """
        takes care of business logic when starting a new stage
        """
        # first, load any settings there might already be saved
        self.deserialize_settings()

        if stage_number == 0:
            # if available: define a pre-selected device from savefilemore
            if self.model.chip_available:
                # chip-based device
                if self.model.saved_s0_device_id is not None:
                    # this fails silently if device ID is not available in table
                    self.view.s0_device_table.set_selected_device(self.model.saved_s0_device_id)
                    # fill info-string to user since table does not autoscroll
                    dev = self.view.s0_device_table.get_selected_device()
                    if dev is not None:
                        self.view.s0_selected_device_info['text'] = "Pre-selected device: " + str(dev.short_str())
                    else:
                        msg = 'Device ID loaded from settings file ({:d}) is not available ' + \
                              'in the current chip. Not setting a default.'
                        self.logger.info(msg.format(self.model.saved_s0_device_id))
            else:
                # ad hoc device
                self.view.s0_adhoc_frame.deserialize(self.model.adhoc_device_save_file_name)
        elif stage_number == 1:
            # if available: define a pre-selected measurement from save file
            if self.model.saved_s1_measurement_name is not None:
                if self.model.saved_s1_measurement_name in self._experiment.measurement_list:
                    self.view.s1_meas_name.set(self.model.saved_s1_measurement_name)
                else:
                    msg = 'Measurement name loaded from settings file ({:s}) is not available ' + \
                          'in the current experiment. Not setting a default.'
                    self.logger.info(msg.format(self.model.saved_s1_measurement_name))
            if self.model.saved_s1_measurement_nr is not None:
                self.view.s1_meas_nr.set(self.model.saved_s1_measurement_nr)
        elif stage_number == 2:
            # if available: define instrument selection
            self.view.s2_instrument_selector.deserialize(self.model.instrument_settings_file_name)
        elif stage_number == 3:
            # if available: define measurement parameters from savefile
            # save the parameters to measurement
            self.model.s1_measurement.parameters = self.view.s3_measurement_param_table.to_meas_param()
            if self.model.s1_measurement is not None:
                self.view.s3_measurement_param_table.deserialize(self.model.s1_measurement.settings_path)
        elif stage_number == 4:
            # there is nothing to load or save for the save button stage
            pass
        else:
            raise ValueError("Unknown stage with number {:d}".format(stage_number))

    def stage_completed(self, stage_number):
        """
        Wraps stage_completed_logic to disable / enable continue button.
        """
        self.view.section_frames[stage_number].continue_button['state'] = 'disabled'
        self.stage_completed_logic(stage_number=stage_number)
        try:
            self.view.section_frames[stage_number].continue_button['state'] = 'normal'
        except TclError:
            # this is expected since the button has been destroyed if the user closes the window
            pass

    def stage_completed_logic(self, stage_number):
        """
        Called when the user presses the "Continue" button of a stage. Takes care of business logic.
        """
        if stage_number == 0:
            if self.model.chip_available:
                # chip based device, save id to file
                self.model.s0_device = self.view.s0_device_table.get_selected_device()
                if self.model.s0_device is None:
                    self.show_error("No device selected",
                                    "No device selected. Please select a device to continue.")
                    return
                self.view.s0_selected_device_info['text'] = "Selected device: " + str(self.model.s0_device.short_str())
            else:
                # adhoc device, serialize
                try:
                    self.model.s0_device = self.view.s0_adhoc_frame.get_custom_device()
                except ValueError as err:
                    self.show_error('Value Error', 'Invalid data was entered: ' + str(err))
                    return
                self.view.s0_adhoc_frame.serialize(self.model.adhoc_device_save_file_name)

        elif stage_number == 1:
            # initialize given measurement
            selected_meas_name = self.view.s1_meas_name.get()
            if selected_meas_name == self.view.default_text:
                self.show_error("No measurement selected",
                                "No measurement selected. Please select a valid Measurement to continue.")
                return
            self.model.s1_measurement = self._experiment.create_measurement_object(selected_meas_name)
            # find available instruments for given measurement
            available_instruments = dict()
            for role_name in self.model.s1_measurement.get_wanted_instrument():
                io_set = get_visa_address(role_name)

                available_instruments.update({role_name: InstrumentRole(self.view.wizard_window, io_set)})
            self.model.s1_available_instruments = available_instruments

        elif stage_number == 2:
            # get the chosen experiment descriptor dicts for each role and save it to the measurement
            for role_name, role_instrs in self.model.s1_available_instruments.items():
                self.model.s1_measurement.selected_instruments.update({role_name: role_instrs.choice})
            # initialize the instruments
            try:
                # we now do that in the controller
                # first we start the progress bar
                self.model.s1_measurement.init_instruments()
            except Exception as e:
                self.show_error("Instrument initialization error",
                                "Could not initialize instruments. Reason: " + repr(e))
                return
            # finally, save the instrument choices to file
            self.view.s2_instrument_selector.serialize(self.model.instrument_settings_file_name)

        elif stage_number == 3:
            try:
                self.view.s3_measurement_param_table.check_parameter_validity()
            except ValueError as e:
                self.show_error('Value Error', 'Invalid data was entered:\n' + str(e))
                return
            # we serialize the user settings to file for future use
            if self.model.s1_measurement is not None:
                self.view.s3_measurement_param_table.serialize(self.model.s1_measurement.settings_path)
            else:
                msg = "Measurement is not defined. Cannot serialize measurement parameters."
                self.logger.warning(msg)

        elif stage_number == 4:
            # save device reference and new measurement to the experiment's to_do_list and close wizard
            self._experiment.to_do_list.append(ToDo(self.model.s0_device, self.model.s1_measurement))
            self._experiment.update()
            self.view.scrollable_frame.unbound_mouse_wheel()
            self.view.wizard_window.destroy()
            return

        else:
            raise ValueError("Unknown stage with number {:d}".format(stage_number))

        # save user settings to file
        self.serialize_settings()

        # launch next stage
        self.stage_start(stage_number + 1)

    def _start_stage_wrapper(self, idx):
        """
        Due to Python's internal name resolution, we have to create a lambda object within
        a separate function and return it, otherwise idx gets evaluated at time of the call of
        the lambda function instead at the time of defining it.
        """
        return lambda: self.stage_start(idx)

    def show_error(self, title, message):
        self.logger.error(message)
        messagebox.showerror(title=title, message=message, parent=self.view.wizard_window)

    def serialize_settings(self):
        """Saves user entries from s0 and s1 to file."""

        # load old settings if available
        settings_path = get_configuration_file_path(self.model.settings_file_name)
        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as json_file:
                data = json.loads(json_file.read())
        else:
            data = {}

        # read current parameters to save dict
        if self.model.s0_device is not None:
            data['device_id'] = self.model.s0_device._id
        if self.model.s1_measurement is not None:
            data['measurement_name'] = self.model.s1_measurement.name

        # store save dict to file
        with open(settings_path, 'w') as json_file:
            json_file.write(json.dumps(data))

    def deserialize_settings(self):
        """Loads user entries from s0 and s1."""

        # load settings if available
        settings_path = get_configuration_file_path(self.model.settings_file_name)
        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as json_file:
                data = json.loads(json_file.read())

            # read current parameters to save dict
            if 'device_id' in data:
                self.model.saved_s0_device_id = data['device_id']
            if 'measurement_name' in data:
                self.model.saved_s1_measurement_name = data['measurement_name']
