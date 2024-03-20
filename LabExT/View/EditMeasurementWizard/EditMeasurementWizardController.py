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

from typing import TYPE_CHECKING, List

from LabExT.Experiments.ToDo import ToDo
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.InstrumentSelector import InstrumentRole
from LabExT.View.EditMeasurementWizard.EditMeasurementWizardModel import EditMeasurementWizardModel
from LabExT.View.EditMeasurementWizard.EditMeasurementWizardView import EditMeasurementWizardView
from LabExT.View.EditMeasurementWizard.WizardEntry.Factory import wizard_entry_controller_factory
from LabExT.View.EditMeasurementWizard.WizardEntry.FinishedError import WizardFinishedError

if TYPE_CHECKING:
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController
else:
    ExperimentManager = None
    WizardEntryController = None


class EditMeasurementWizardController:
    """
    Controller Class for the EditMeasurementWizard. Gets instantiated and used from the main window.
    Sets up model and view classes, contains control logic, callback functions for the EditMeasurementWizard
    """

    def __init__(self, parent, experiment_manager: ExperimentManager):
        self.root = parent
        self.experiment_manager = experiment_manager
        self._experiment = self.experiment_manager.exp

        self.logger = logging.getLogger()

        self.model = EditMeasurementWizardModel(self.experiment_manager)
        self.view = EditMeasurementWizardView(
            self.model, self, self.root, self.experiment_manager)
        self.entry_controllers: List[WizardEntryController] = []

        # set the proper reference in the model class
        self.model.set_view(self.view)

        # set up the main window
        self.view.setup_main_window()

        # start the GUI
        self.stage_start(0)

    def escape_event(self, stage_nr: int):
        """This method is called by the WizardEntryViews if the user hits escape.

        Ideally this would be done with an event system, where this
        controller inherits from the (theoretical) EscapeEventListener
        interface and adds itself to the event-creating WizardEntries.
        However, this is out of scope for this update. Maybe in the 
        future though :-)
        """
        if stage_nr == 0:
            self.view.wizard_window.destroy()
        else:
            self.stage_start(stage_nr - 1)

    def stage_start(self, stage_number):
        """
        start stage with given number, takes care of GUI changes
        """
        # make sure to remove trailing stages if escape
        # or back-button was pressed
        for controller in self.entry_controllers[stage_number:]:
            self.logger.debug(
                f"Removing controller {controller} from EditMeasurementWizard")
            controller.remove()
        self.entry_controllers = self.entry_controllers[:stage_number]
        # disable all frames before
        for controller in self.entry_controllers[:stage_number]:
            self.logger.debug(
                f"Disabling controller {controller} in EditMeasurementWizard")
            controller.disable()

        # adding new wizard entry
        self.entry_controllers.append(wizard_entry_controller_factory(
            stage_number, self.model.chip_available, self.view._wizard_frame, self))

        # call business logic after setup of stage
        self.stage_start_logic(stage_number=stage_number)
        return

    def stage_start_logic(self, stage_number: int):
        """
        takes care of business logic when starting a new stage
        """
        # first, load settings from disk
        self.deserialize_settings()

        # then, populate entries
        self.entry_controllers[stage_number].deserialize(
            self.model.settings[stage_number])

        return

    def stage_completed(self, stage_number: int):
        """
        Wraps stage_completed_logic to disable / enable continue button.
        """
        self.entry_controllers[stage_number].allow_interaction(False)
        self.stage_completed_logic(stage_number=stage_number)
        try:
            self.entry_controllers[stage_number].allow_interaction(True)
        except TclError:
            # this is expected since the button has been destroyed if the user closes the window
            pass

    def stage_completed_logic(self, stage_number: int):
        """
        Called when the user presses the "Continue" button of a stage. Takes care of business logic.
        """
        try:
            self.model.results[stage_number] = self.entry_controllers[stage_number].results(
            )
        except ValueError as v:
            self.show_error("Can't continue", str(v))
            return
        except WizardFinishedError:
            return

        # save settings
        self.entry_controllers[stage_number].serialize(
            self.model.settings[stage_number])
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
        messagebox.showerror(title=title, message=message,
                             parent=self.view.wizard_window)

    def serialize_settings(self):
        """Saves user entries to disk."""

        # load old settings if available
        settings_path = get_configuration_file_path(
            self.model.settings_file_name)

        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as json_file:
                settings = json.loads(json_file.read())
                try:
                    settings = {int(k): v for k, v in settings.items()}
                except ValueError:
                    self._update_cache_files()
        else:
            settings = {}

        # read current parameters to save dict
        settings.update(self.model.settings)

        # store save dict to file
        with open(settings_path, 'w') as json_file:
            json_file.write(json.dumps(settings, indent=4))

    def deserialize_settings(self):
        """Loads user entries from disk."""

        # load settings if available
        settings_path = get_configuration_file_path(
            self.model.settings_file_name)
        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as json_file:
                # read from file and convert keys to int
                data = json.loads(json_file.read())
                try:
                    data = {int(k): v for k, v in data.items()}
                except ValueError:
                    self._update_cache_files()
                    data = dict()

            # read current parameters to save dict
            self.model.settings.update(data)

    def _update_cache_files(self) -> None:
        """This function is needed to update the cache into the new format.

        It deletes all cache files starting with `EditMeasurementWizard`.
        """
        cache_dir = os.path.dirname(
            get_configuration_file_path(self.model.settings_file_name))
        cache_files = [f for f in os.listdir(
            cache_dir) if f.startswith("EditMeasurementWizard")]
        for file in cache_files:
            os.remove(os.path.join(cache_dir, file))

    def register_keyboard_shortcut(self, keys: str, action) -> None:
        if keys != "<F1>":
            self.view.register_keyboard_shortcut(keys, action)
