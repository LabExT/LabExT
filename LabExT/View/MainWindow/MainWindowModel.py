#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import TYPE_CHECKING

from tkinter import BooleanVar, StringVar

from LabExT.Model.ExperimentHandler import ExperimentHandler
from LabExT.View.Controls.ControlPanel import ControlCommand

if TYPE_CHECKING:
    from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
else:
    EditMeasurementWizardController = None

class MainWindowModel:
    """
    The model class for the Main window.
    Contains all data, and functions to manipulate said data.
    """
    application_title = 'The Laboratory Tool'

    def __init__(self, controller, root, experiment_manager):
        self.root = root
        self.controller = controller
        self.view = None
        self.experiment_manager = experiment_manager
        self.chiptable_settings_path = 'experiment_chip_settings.json'
        self.savetable_settings_path = 'experiment_save_settings.json'
        self.axis_settings_path = 'mainwindow_axis_settings.json'
        self.currently_plotted_meas_name = None

        # do not let the user set the experiment settings manually
        self.allow_change_chip_params = BooleanVar(self.root, False)
        self.allow_change_save_params = BooleanVar(self.root, False)

        # from the old viewmodel file
        self.logger = logging.getLogger()
        self.logger.debug('Initialise MainWindowViewModel with tkinter: %s experiment_manager: %s',
                          root,
                          self.experiment_manager)

        self.app_width = self.root.winfo_screenwidth()
        self.app_height = self.root.winfo_screenheight()

        self.logger.debug('Screen size: %sx%s', self.app_width, self.app_height)

        # definitions for button commands
        self.commands = list()
        start_button = ControlCommand(
            self.controller.start, self.root, name='Run (F5)')
        self.commands.append(start_button)
        stop_button = ControlCommand(
            self.controller.stop, self.root, name='Abort (Escape)', can_execute=False)
        self.commands.append(stop_button)

        self.experiment = None
        self.chip_parameters = None
        self.save_parameters = None
        self.selec_plot_data = None
        self.last_opened_new_meas_wizard_controller: EditMeasurementWizardController = None

        self.load_exp_parameters()

        # handler to run experiments asynchronously
        self.experiment_handler = ExperimentHandler()
        self.experiment_handler.current_experiment = self.experiment
        # listen if the experiment is finished
        self.experiment_handler.experiment_finished.append(self.on_experiment_finished)

        # initialise execution control variables
        self.var_mm_pause = BooleanVar(self.root)
        self.var_mm_pause.trace("w", self.exctrl_vars_changed)
        self.var_mm_pause_reason = StringVar(self.root)
        self.var_auto_move = BooleanVar(self.root)
        self.var_auto_move.trace("w", self.exctrl_vars_changed)
        self.var_auto_move_reason = StringVar(self.root)
        self.var_sfp_ena = BooleanVar(self.root)
        self.var_sfp_ena.trace("w", self.exctrl_vars_changed)
        self.var_sfp_ena_reason = StringVar(self.root)
        self.var_imeas_wait_time_str = StringVar(self.root, "0.0")
        self.var_imeas_wait_time_str.trace("w", self.exctrl_vars_changed)

        # status of various sub-modules
        self.status_mover_connected_stages = BooleanVar(self.root)
        self.status_mover_connected_stages.trace("w", self.submodule_status_updated)
        self.status_mover_can_move_to_device = BooleanVar(self.root)
        self.status_mover_can_move_to_device.trace("w", self.submodule_status_updated)
        self.status_sfp_initialized = BooleanVar(self.root)
        self.status_sfp_initialized.trace("w", self.submodule_status_updated)

        # for testing across threads
        self.allow_GUI_changes = True  # set to False to not invoke TK callbacks

    def load_exp_parameters(self):
        """
        Loads all experiment parameters and saves them within the model.
        """
        if self.experiment_manager.exp:
            self.experiment = self.experiment_manager.exp
            self.chip_parameters = self.experiment_manager.exp.chip_parameters
            self.save_parameters = self.experiment_manager.exp.save_parameters
            self.selec_plot_data = self.experiment.selec_plot_collection

    def on_experiment_start(self):
        """
        Upon start of the experiment alters which buttons are pressable.
        """
        if not self.allow_GUI_changes:
            return

        # change control button states
        self.commands[0].can_execute = False  # disable the start button
        self.commands[1].can_execute = True  # enable the stop button
        # disable change in experiment parameters
        self.allow_change_chip_params.set(False)
        self.allow_change_save_params.set(False)

    def on_experiment_finished(self):
        """Called when an experiment is finished. Resets control
        buttons.
        """
        if not self.allow_GUI_changes:
            return

        self.logger.debug('Experiment finished, resetting controls...')
        self.commands[0].can_execute = True  # enable the start button
        self.commands[1].can_execute = False  # disable the stop button
        # enable change in save file parameters
        if not self.experiment_manager.chip:
            self.allow_change_chip_params.set(True)
        self.allow_change_save_params.set(True)

    def exctrl_vars_changed(self, *args):
        """
        Called by Tkinter once any execution control variables changed.

        Parameters
        ----------
        *args
            Tkinter arguments, not needed.
        """
        if not self.allow_GUI_changes:
            return

        # save udpates of control variables to log
        self.logger.debug('State of manual mode is: %s', self.var_mm_pause.get())
        self.logger.debug('State of auto move is: %s', self.var_auto_move.get())
        self.logger.debug('State of SFP enable is: %s', self.var_sfp_ena.get())
        self.logger.debug('Inter-measurement wait time is: %s', self.var_imeas_wait_time_str.get())

        # propagate change to experiment
        self.experiment_manager.exp.exctrl_pause_after_device = self.var_mm_pause.get()
        self.experiment_manager.exp.exctrl_auto_move_stages = self.var_auto_move.get()
        self.experiment_manager.exp.exctrl_enable_sfp = self.var_sfp_ena.get()

        # allow wait time changes only if manual mode is not activated
        if self.var_mm_pause.get():
            self.view.frame.control_panel.exctrl_wait_time.config(state='disabled')
            self.view.frame.control_panel.wait_time_lbl.config(state='disabled')
        else:
            self.view.frame.control_panel.exctrl_wait_time.config(state='normal')
            self.view.frame.control_panel.wait_time_lbl.config(state='normal')

        # convert wait time to float and check for positive-ness
        try:
            imeas_wait_time = float(self.var_imeas_wait_time_str.get())
        except ValueError:
            # text does not convert to float, so we skip updating the variable
            return

        if imeas_wait_time < 0.0:
            self.logger.info('Inter-measurement wait time cannot be negative. Setting to 0.0')
            imeas_wait_time = 0.0
            self.var_imeas_wait_time_str.set("0.0")

        self.experiment_manager.exp.exctrl_inter_measurement_wait_time = imeas_wait_time

    def submodule_status_updated(self, *args):
        """
        Callback on any status change of the submodules
        """

        if not self.allow_GUI_changes:
            return

        # this variable should track Mover.mover_enabled
        has_connected_stages = bool(self.status_mover_connected_stages.get())
        # this variable should track Mover.trafo_enabled
        can_move_to_device = bool(self.status_mover_can_move_to_device.get())
        # this variable should track PeakSearcher.initialized
        sfp_init = bool(self.status_sfp_initialized.get())

        if not has_connected_stages:
            reason = "No connected stages"
            self.var_mm_pause.set(True)
            self.var_mm_pause_reason.set(reason)
            # self._main_window.exctrl_mm_pause.config(state='disabled')
            self.var_auto_move.set(False)
            self.var_auto_move_reason.set(reason)
            self.view.frame.control_panel.exctrl_auto_move.config(state='disabled')
            self.var_sfp_ena.set(False)
            self.var_sfp_ena_reason.set(reason)
            self.view.frame.control_panel.exctrl_sfp_ena.config(state='disabled')
        else:
            if not can_move_to_device:
                self.var_mm_pause.set(True)
                self.var_mm_pause_reason.set("Mover is not fully calibrated")
                # self._main_window.exctrl_mm_pause.config(state='disabled')
                self.var_auto_move.set(False)
                self.var_auto_move_reason.set("Mover is not fully calibrated")
                self.view.frame.control_panel.exctrl_auto_move.config(state='disabled')
            else:
                # self.var_mm_pause.set(X)  # no change
                self.var_mm_pause_reason.set("")
                # self._main_window.exctrl_mm_pause.config(state='normal')
                # self.var_auto_move.set(X)  # no change
                self.var_auto_move_reason.set("")
                self.view.frame.control_panel.exctrl_auto_move.config(state='normal')
            if not sfp_init:
                self.var_sfp_ena.set(False)
                self.var_sfp_ena_reason.set("Search-for-peak not initialized")
                self.view.frame.control_panel.exctrl_sfp_ena.config(state='disabled')
            else:
                # self.var_sfp_ena.set(X)  # no change
                self.var_sfp_ena_reason.set("")
                self.view.frame.control_panel.exctrl_sfp_ena.config(state='normal')
