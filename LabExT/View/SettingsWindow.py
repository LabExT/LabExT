#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, DISABLED, Button, BooleanVar, messagebox, Label

from LabExT.View.Controls.AdhocDeviceFrame import AdhocDeviceFrame
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentRole
from LabExT.View.Controls.InstrumentSelector import InstrumentSelector
from LabExT.View.Controls.ParameterTable import ParameterTable, ConfigParameter
from LabExT.View.Controls.ScrollableFrame import ScrollableFrame


class SettingsWindow(ScrollableFrame):
    """Frame that contains all settings from all active measurements.
    User can set new values or reset to old values.
    """

    def __init__(self,
                 parent,
                 experiment_manager,
                 edit_meas_list=None,
                 device_list=None,
                 force_noload=False,
                 callback=None):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Containing window.
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager.
        edit_meas_list : List[Measurement] (optional)
            If given, open the settings window only for the measurements in the list, not all in exp_manager
        device_list : List[Device] (optional)
            If given, shows some information for all given devices in text form, not to change anything.
        force_noload : bool (optional, default False)
            If set to True, will not load anything from saved settings files.
        """
        super(SettingsWindow, self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()
        self.logger.debug('SettingsWindow initialised with parent: %s experiment_manager: %s',
                          parent, experiment_manager)

        self._root = parent
        self._experiment_manager = experiment_manager
        if edit_meas_list is None:
            # edit all open measurements in experiment_manager
            self._edit_meas_list = self._experiment_manager.exp.selected_measurements
        else:
            # store the given measurements
            self._edit_meas_list = edit_meas_list
        if device_list is not None:
            self._device_list = device_list
        else:
            self._device_list = []

        self.force_noload = force_noload
        self.callback = callback
        self._root.title = 'Settings'

        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # place hint
        hint = "Any changes you make to the measurement settings will immediately be saved!"
        top_hint = Label(parent, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # configure scrollable frame part
        self.grid(row=1, column=0, sticky='nswe')  # place window in root element
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._content_frame = self.get_content_frame()
        self._content_frame.columnconfigure(0, weight=1)

        self._children = []
        self.__setup__()  # setup the main window content

    def __on_close__(self):
        """Called by the ok button. Saves the entered values to the
        .json file of the corresponding measurement. Then proceeds to
        close the window.
        """
        self.logger.debug('Trying to close SettingsWindow.')
        # iterate through all elements in window
        for child in self._children:
            self.logger.debug('Current child: %s', child)
            if isinstance(child, ParameterTable):
                self.logger.debug('Child is ParameterTable with title: %s', child.title)
                # get name of measurement corresponding to the parameter table
                measurement_name = child.title.replace('Parameters ', '')
                self.logger.debug('Trying to find corresponding measurement...')
                # get the corresponding measurement object in experiment
                for m in self._experiment_manager.exp.selected_measurements:
                    self.logger.debug('Current measurement: %s', m)
                    if m.name == measurement_name:
                        self._meas = m
                        self.logger.debug('Found corresponding measurement!')
                        break
                else:
                    continue
                # save values in .json file
                if child.serialize(self._meas.settings_path):
                    self.logger.info('Saving parameters of measurement {:s} to file.'.format(measurement_name))
        # here we write the paramters to the model

        self._root.destroy()
        if self.callback is not None:
            self.callback()

    def __setup__(self):
        """Sets up the frame by iterating through current measurements.
        """
        self.logger.debug('Start setup of SettingsWindow.')
        # generate adhoc device frames to show device infos
        for dev_idx, device in enumerate(self._device_list):
            dev_frame = AdhocDeviceFrame(self._content_frame)
            dev_frame.grid(row=dev_idx, column=0, padx=5, pady=5)
            dev_frame.load_existing_device(device)
            dev_frame.enabled = False
            dev_frame.title = "Information about Device"

        # generate measurement setting frames
        for meas_idx, measurement in enumerate(self._edit_meas_list):
            counter = 0

            # new frame for every measurement
            meas_frame = CustomFrame(self._content_frame, padx=5, pady=5)
            meas_frame.title = measurement.get_name_with_id()
            meas_frame.grid(row=meas_idx + len(self._device_list), column=0)
            self._children.append(meas_frame)
            meas_frame.columnconfigure(0, weight=1)

            self.logger.debug('Created new frame with title: %s',meas_frame.title)

            # add instruments and their names addresses
            for (inst_type, inst_name), inst_reference in measurement.instruments.items():
                self._instrument_measurement_table = InstrumentSelector(meas_frame)
                # user cannot change instrument addresses anymore, they
                # were already initialised
                self._instrument_measurement_table.title = inst_type
                self._instrument_measurement_table.grid(
                    row=counter,
                    column=0,
                    columnspan=2,
                    padx=5,
                    pady=5,
                    sticky='w')
                # add instrument to gui
                self._children.append(self._instrument_measurement_table)

                instrument_list = dict()
                instrument_list.update(
                    {inst_type: InstrumentRole(self._root, [inst_reference.instrument_config_descriptor])}
                )

                self.logger.debug('Set chosen instruments to %s', instrument_list)

                self._instrument_measurement_table.instrument_source = instrument_list
                self._instrument_measurement_table.can_execute(DISABLED)

                # display settings of instrument
                counter += 1
                data_dict = {}
                t = ParameterTable(self._instrument_measurement_table, customwidth=40)
                # convert settings from normal dictionary to configparam dictionary
                try:
                    inst_parameter = inst_reference.get_instrument_parameter()
                except Exception as exc:
                    messagebox.showinfo('Instrument Error',
                                        'Cannot get instrument parameters: ' + repr(exc))
                    self.logger.exception('Error occured during fetching of instrument parameters: ' + repr(exc))
                    inst_parameter = {}

                for k, v in inst_parameter.items():
                    data_dict[k] = ConfigParameter(self._root, value=v)

                t.grid(row=counter, column=0, sticky='w')
                t.title = 'Instrument Settings'
                self._var = BooleanVar()
                t.enabled = self._var
                t.parameter_source = data_dict

                self._var.set(False)

                counter += 1

            # display measurement parameters
            self._parameter_measurement_table = ParameterTable(meas_frame, store_callback=measurement.store_new_param)
            self._parameter_measurement_table.grid(
                row=counter, column=0, padx=5, pady=5, sticky='w')
            self._children.append(self._parameter_measurement_table)
            self._parameter_measurement_table.title = 'Parameters ' + measurement.name
            self._parameter_measurement_table.parameter_source = measurement.parameters
            # here we need to manage the final update, the writeback to measurement

            if not self.force_noload:
                if self._parameter_measurement_table.deserialize(measurement.settings_path):
                    self.logger.info("Loading measurement's {:s} parameter from file.".format(measurement.name))
            counter += 1

            self._reset_button = Button(self._content_frame, text='Reset Values', command=self.reset_values, width=10)
            self._reset_button.grid(row=100, column=0, padx=5, pady=5, sticky='w')
            self._children.append(self._reset_button)

            self._ok_button = Button(self._content_frame, text='OK', command=self.__on_close__, width=10)
            self._ok_button.grid(row=100, column=0, padx=5, pady=5, sticky='e')
            self._children.append(self._ok_button)

    def reset_values(self):
        """Called when user presses on reset button. Repaints the frame
        and loads old settings from .json files.
        """
        self.logger.debug('User reset values in SettingsWindow.')
        for child in self._children:
            child.destroy()
        self.__setup__()
