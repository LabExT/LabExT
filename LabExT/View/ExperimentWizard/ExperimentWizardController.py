#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import itertools
import logging
from tkinter import messagebox, TclError

from LabExT.Experiments.ToDo import ToDo
from LabExT.Model.WizardQuitException import WizardQuitException
from LabExT.View.ExperimentWizard.Components.CustomDeviceWindow import CustomDeviceWindow
from LabExT.View.ExperimentWizard.Components.DeviceWindow import DeviceWindow
from LabExT.View.ExperimentWizard.Components.InstrumentWindow import InstrumentWindow
from LabExT.View.ExperimentWizard.Components.MeasurementWindow import MeasurementWindow
from LabExT.View.ExperimentWizard.ExperimentWizardModel import ExperimentWizardModel
from LabExT.View.ExperimentWizard.ExperimentWizardView import ExperimentWizardView
from LabExT.View.SettingsWindow import SettingsWindow


class ExperimentWizardController:
    """Guides the user through the different steps in order to start
    a new experiment.
    """

    def __init__(self, parent, experiment_manager):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter window parent.
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self._root = parent
        self.experiment_manager = experiment_manager

        self.logger = logging.getLogger()
        self.logger.debug('Initialised ExperimentWizard with parent:%s experiment_manager:%s', parent,
                          experiment_manager)

        # minimize main window to not clutter everything
        self._root.wm_state('iconic')

        # initialize model
        self.model = ExperimentWizardModel(self)

        # initialize view
        self.view = ExperimentWizardView(self.model, self, self._root)

        mover = self.experiment_manager.mover
        self.logger.debug('Mover is: %s', mover)

        chip = self.experiment_manager.chip
        self.logger.debug('Chip is: %s', chip)

        # temporary todos to be copied to the experiment manager are stored here:
        self._temporary_created_ToDos = []

    def close_wizard(self):
        """Called when user presses on 'x'. Asks if user wants to quit
        and restores old experiment.
        """
        m = messagebox.askyesno('Quit', 'Do you want to quit the ExperimentWizard?')
        if m:
            self.logger.debug('User aborted ExperimentWizard. Resetting to old experiment...')
            self.view.main_window.destroy()
            # open main window again
            self._root.state('normal')

    def finish_wizard(self):
        """ Executed on user click on final "continue" button in the Wizard """
        # copy all temporarily created ToDos to the experiment To Do list and tell it to update the GUI
        self.experiment_manager.exp.to_do_list.extend(self._temporary_created_ToDos)
        self.experiment_manager.exp.update()
        # close wizard window
        self.view.main_window.destroy()
        self._root.state('normal')

    def start_wizard(self):
        """Starts the experiment wizard workflow and creates the
        to_do_list for the experiment at the end.
        """

        # clear measurement and device selections from last wizard run
        self.experiment_manager.exp.device_list.clear()
        self.experiment_manager.exp.selected_measurements.clear()

        # ask the user if want to import chip file
        if not self.experiment_manager.chip:
            m = messagebox.askyesno(
                'No chip',
                'You have not imported a chip. Would you like to proceed by defining a DUT ad-hoc?')
            if not m:
                self.finish_wizard()
                return

        self.display_next_window()

    def user_aborted(self):
        self.logger.debug('Wizard aborted by user')
        self.view.main_window.destroy()
        self._root.state('normal')

    def display_next_window(self):
        self._update_labels()
        self.model.current_step += 1

        if self.model.current_step == 1:
            try:
                # only open device window if there is a chip
                if self.experiment_manager.chip:
                    self.view.new_toplevel(DeviceWindow, self.experiment_manager, self.display_next_window)
                # let the user set own device
                else:
                    self.logger.debug('User has not set chip file. Opening personal device window...')
                    self.view.new_toplevel(CustomDeviceWindow, self.experiment_manager, self.display_next_window)
            except WizardQuitException:
                self.user_aborted()

        elif self.model.current_step == 2:
            try:
                self.view.new_toplevel(MeasurementWindow, self.experiment_manager, self.display_next_window)
            except WizardQuitException:
                self.user_aborted()

        elif self.model.current_step == 3:
            try:
                self.view.new_toplevel(InstrumentWindow, self.experiment_manager, self.display_next_window)
            except WizardQuitException:
                self.user_aborted()

        elif self.model.current_step == 4:
            if self.experiment_manager.exp.selected_measurements:
                self.view.new_toplevel(SettingsWindow, self.experiment_manager, self.finalize)
            else:
                # this should really never happen
                msg = 'ERROR!! No active measurements. Cannot show measurement settings window.' + \
                      'This should never happen, as this is at the end of ExperimentWizard!'
                messagebox.showerror("CRITICAL", msg)
                self.logger.critical(msg)

    def finalize(self):
        self._update_labels()
        self.model.current_step += 1
        # were done, create all ToDos in a local list
        self._temporary_created_ToDos.extend([
            ToDo(dev, meas) for dev, meas in itertools.product(
                self.experiment_manager.exp.device_list,
                self.experiment_manager.exp.selected_measurements)
        ])
        self.logger.debug('Created to_do_list: %s', self._temporary_created_ToDos)

        # clear selection lists from this wizard run
        self.experiment_manager.exp.device_list.clear()
        self.experiment_manager.exp.selected_measurements.clear()

        # allow the user to press the button to continue
        self.view.main_window.helper_window.continue_button.config(state='normal')

    def _update_labels(self):
        """Sets the current instruction color to green and the next
        instruction to yellow.
        """
        try:
            self.view.labels[self.model.current_step].config(bg='lime')
            self.view.labels[self.model.current_step + 1].config(bg='#f0ff00')
        except TclError as e:
            # this happens if the window is already closed but this functions gets called one last time.
            # -> ignore color change and carry on
            self.logger.debug("Could not update labels: " + str(e))
