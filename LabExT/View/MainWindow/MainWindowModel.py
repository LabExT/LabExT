#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import BooleanVar, StringVar

from LabExT.Model.ExperimentHandler import ExperimentHandler
from LabExT.Utils import DeprecatedException
from LabExT.View.Controls.ControlPanel import ControlCommand


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
        stop_button = ControlCommand(
            self.controller.stop, self.root, name='Abort (Escape)', can_execute=False)
        finish_button = ControlCommand(
            self.finish, self.root, name='Finish', can_execute=False)
        self.commands.append(start_button)
        self.commands.append(stop_button)
        self.commands.append(finish_button)

        self.experiment = None
        self.chip_parameters = None
        self.save_parameters = None
        self.live_plot_data = None
        self.selec_plot_data = None

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

        # status of various sub-modules
        self.status_mover_driver_enabled = BooleanVar(self.root)
        self.status_mover_driver_enabled.trace("w", self.submodule_status_updated)
        self.status_transformation_enabled = BooleanVar(self.root)
        self.status_transformation_enabled.trace("w", self.submodule_status_updated)
        self.status_sfp_initialized = BooleanVar(self.root)
        self.status_sfp_initialized.trace("w", self.submodule_status_updated)

    def load_exp_parameters(self):
        """
        Loads all experiment parameters and saves them within the model.
        """
        if self.experiment_manager.exp:
            self.experiment = self.experiment_manager.exp
            self.chip_parameters = self.experiment_manager.exp.chip_parameters
            self.save_parameters = self.experiment_manager.exp.save_parameters
            self.live_plot_data = self.experiment.live_plot_collection
            self.selec_plot_data = self.experiment.selec_plot_collection

    def experiment_changed(self, ex):
        raise DeprecatedException("Experiment object must not be recreated!")

    def settings(self):
        raise DeprecationWarning("Open Settings window is deprecated. Do not use!")

    def finish(self):
        raise DeprecationWarning("Finish button function is deprecated. Do not use!")

    def on_experiment_start(self):
        """
        Upon start of the experiment alters which buttons are pressable.
        """
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
        self.logger.debug('Experiment finished, resetting controls...')
        self.commands[0].can_execute = True  # enable the start button
        self.commands[1].can_execute = False  # disable the stop button
        # enable change in save file parameters
        self.allow_change_save_params.set(True)

    def exctrl_vars_changed(self, *args):
        """
        Called by Tkinter once any execution control variables changed.

        Parameters
        ----------
        *args
            Tkinter arguments, not needed.
        """
        self.logger.debug('State of manual mode is: %s', self.var_mm_pause.get())
        self.logger.debug('State of auto move is: %s', self.var_auto_move.get())
        self.logger.debug('State of SFP enable is: %s', self.var_sfp_ena.get())

        # propagate change to experiment
        self.experiment_manager.exp.exctrl_pause_after_device = self.var_mm_pause.get()
        self.experiment_manager.exp.exctrl_auto_move_stages = self.var_auto_move.get()
        self.experiment_manager.exp.exctrl_enable_sfp = self.var_sfp_ena.get()

    def submodule_status_updated(self, *args):
        """
        Callback on any status change of the submodules
        """

        # this variable should track Mover.mover_enabled
        mover_ena = bool(self.status_mover_driver_enabled.get())
        # this variable should track Mover.trafo_enabled
        trafo_ena = bool(self.status_transformation_enabled.get())
        # this variable should track PeakSearcher.initialized
        sfp_init = bool(self.status_sfp_initialized.get())

        if not mover_ena:
            reason = "Stage driver not loaded"
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
            if not trafo_ena:
                self.var_mm_pause.set(True)
                self.var_mm_pause_reason.set('Transformation not calibrated')
                # self._main_window.exctrl_mm_pause.config(state='disabled')
                self.var_auto_move.set(False)
                self.var_auto_move_reason.set('Transformation not calibrated')
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
