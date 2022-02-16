#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from functools import partial
from tkinter import DoubleVar, Label, Button, Entry, ttk, messagebox, StringVar, OptionMenu, Frame, Button, Label, DISABLED, NORMAL, VERTICAL, W, LEFT, RIGHT, TOP, X
from typing import Tuple, Type

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Controls.Wizard import Wizard

from LabExT.Movement.Calibration import DevicePort, Orientation


class MovementWizardView(Wizard):
    """
    Implements a Wizard for set up the stages.
    """

    ASSIGNMENT_MENU_PLACEHOLDER = "-- unused --"

    def __init__(self, parent, controller, mover):
        super().__init__(
            parent,
            width=800,
            height=600,
            on_finish=self._save,
            cancel_button_label="Cancel and Close",
            finish_button_label="Finish and Save"
        )
        self.title("Stage Setup Wizard")

        self.controller = controller
        self.experiment_manager = controller.experiment_manager
        self.mover = mover

        # -- 1. STEP: LOAD DRIVERS
        self.load_driver_step = self.add_step(self._driver_step_builder,
                                              title="Driver Settings")

        # -- 2. STEP: STAGE ASSIGNMENT
        self.assign_stages_step = self.add_step(
            self._stage_assignment_step_builder,
            title="Stage Connection",
            on_reload=self._check_stage_assignment)
        # Step variables and state
        self._current_stage_assignment = {}
        self.stage_port_var = {}
        self.stage_orientation_var = {}
        for stage in self.mover.available_stages:
            self.stage_port_var.update(
                {stage: StringVar(self.parent, DevicePort.INPUT)})
            self.stage_port_var[stage].trace(
                W, lambda *_, stage=stage: self._on_stage_assignment(stage))

            self.stage_orientation_var.update(
                {stage: StringVar(self.parent, self.ASSIGNMENT_MENU_PLACEHOLDER)})
            self.stage_orientation_var[stage].trace(
                W, lambda *_, stage=stage: self._on_stage_assignment(stage))

        # -- 3. STEP: STAGE CONFIGURATION
        self.configure_stages_step = self.add_step(
            self._configuration_step_builder,
            title="Stage Configuration",
            finish_step_enabled=True)
        # Step variables and state
        self.xy_speed_var = DoubleVar(self.parent, self.mover.DEFAULT_SPEED_XY)
        self.z_speed_var = DoubleVar(self.parent, self.mover.DEFAULT_SPEED_Z)
        self.xy_acceleration_var = DoubleVar(
            self.parent, self.mover.DEFAULT_ACCELERATION_XY)

        # Connect Steps
        self.load_driver_step.next_step = self.assign_stages_step
        self.assign_stages_step.previous_step = self.load_driver_step
        self.assign_stages_step.next_step = self.configure_stages_step
        self.configure_stages_step.previous_step = self.assign_stages_step

        # Start Wizard by setting the current step
        self.current_step = self.load_driver_step

    #
    #   Step Builder
    #

    def _driver_step_builder(self, frame: Type[CustomFrame]):
        """
        Builds step to load stage drivers.
        """
        frame.title = "Load Stage Drivers"

        step_description = Label(
            frame,
            text="Below you can see all Stage classes available in LabExT.\nSo that all stages can be found correctly in the following step, make sure that the drivers for each class are loaded."
        )
        step_description.pack(side=TOP, fill=X)

        ttk.Separator(
            frame, orient=VERTICAL
        ).pack(side=TOP, fill=X, pady=10)

        if not self.mover.stage_classes:
            Label(frame, text="No stage classes found!").pack(side=TOP, fill=X)

        for stage_class in self.mover.stage_classes:
            stage_driver_frame = Frame(frame)
            stage_driver_frame.pack(side=TOP, fill=X, pady=2)

            stage_driver_label = Label(
                stage_driver_frame,
                text="[{}] {}".format(
                    stage_class.__name__,
                    stage_class.meta.description))
            stage_driver_label.pack(side=LEFT, fill=X)

            stage_driver_load = Button(
                stage_driver_frame,
                text="Load Driver",
                state=NORMAL if stage_class.meta.driver_specifiable else DISABLED,
                command=partial(
                    self.controller.load_driver,
                    stage_class))
            stage_driver_load.pack(side=RIGHT)

            stage_driver_status = Label(
                stage_driver_frame,
                text="Loaded" if stage_class.driver_loaded else "Not Loaded",
                foreground='#4BB543' if stage_class.driver_loaded else "#FF3333",
            )
            stage_driver_status.pack(side=RIGHT, padx=10)

        ttk.Separator(
            frame, orient=VERTICAL
        ).pack(side=TOP, fill=X, pady=10)

        reload_stage_classes_button = Button(
            frame,
            text="Reload Stage classes",
            command=self.controller.reload_stage_classes
        )
        reload_stage_classes_button.pack(side=TOP, anchor="e")

    def _stage_assignment_step_builder(self, frame: Type[CustomFrame]):
        """
        Builds stage to assign stages.
        """
        frame.title = "Manage Stage Connections"

        step_description = Label(
            frame,
            text="Below you can see all the stages found by LabExT.\nIf stages are missing, go back one step and check if all drivers are loaded."
        )
        step_description.pack(side=TOP, fill=X)

        available_stages_frame = CustomFrame(frame)
        available_stages_frame.title = "Available Stages"
        available_stages_frame.pack(side=TOP, fill=X)

        CustomTable(
            parent=available_stages_frame,
            selectmode='none',
            columns=(
                'ID', 'Description', 'Stage Class', 'Address', 'Connected'
            ),
            rows=[
                (idx,
                 s.__class__.meta.description,
                 s.__class__.__name__,
                 s.address_string,
                 s.connected)
                for idx, s in enumerate(self.mover.available_stages)])

        stage_assignment_frame = CustomFrame(frame)
        stage_assignment_frame.title = "Assign Stages"
        stage_assignment_frame.pack(side=TOP, fill=X)

        for available_stage in self.mover.available_stages:
            available_stage_frame = Frame(stage_assignment_frame)
            available_stage_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                available_stage_frame, text=str(available_stage), anchor="w"
            ).pack(side=LEFT, fill=X, padx=(0, 10))

            # Set up menu for port selection
            stage_port_menu = OptionMenu(
                available_stage_frame,
                self.stage_port_var[available_stage],
                *(list(DevicePort))
            )
            stage_port_menu.pack(side=RIGHT, padx=5)
            stage_port_menu.config(state=DISABLED if self.stage_orientation_var[available_stage].get(
            ) == self.ASSIGNMENT_MENU_PLACEHOLDER else NORMAL)

            Label(
                available_stage_frame, text="Device Port:"
            ).pack(side=RIGHT, fill=X, padx=5)

            # Set up menu for orientation selection
            OptionMenu(
                available_stage_frame,
                self.stage_orientation_var[available_stage],
                *([self.ASSIGNMENT_MENU_PLACEHOLDER] + list(Orientation))
            ).pack(side=RIGHT, padx=5)

            Label(
                available_stage_frame, text="Stage Orientation:"
            ).pack(side=RIGHT, fill=X, padx=5)

    def _configuration_step_builder(self, frame: Type[CustomFrame]):
        """
        Builds step to configure stages.
        """
        frame.title = "Configure Assigned Stages"

        step_description = Label(
            frame,
            text="Configure the selected stages.\nThese settings are applied globally to all selected stages."
        )
        step_description.pack(side=TOP, fill=X)

        stage_properties_frame = CustomFrame(frame)
        stage_properties_frame.title = "Speed and Acceleration Settings"
        stage_properties_frame.pack(side=TOP, fill=X)

        Label(
            stage_properties_frame,
            anchor="w",
            text="Speed Hint: A value of 0 (default) deactivates the speed control feature. The stage will move as fast as possible!"
        ).pack(side=TOP, fill=X)
        Label(
            stage_properties_frame,
            anchor="w",
            text="Acceleration Hint: A value of 0 (default) deactivates the acceleration control feature."
        ).pack(side=TOP, fill=X)

        ttk.Separator(
            stage_properties_frame,
            orient=VERTICAL
        ).pack(side=TOP, fill=X, pady=10)

        self._build_entry_with_label(
            stage_properties_frame,
            self.xy_speed_var,
            label="Movement speed xy direction (valid range: {}...{:.0e}um/s):".format(
                self.mover.SPEED_LOWER_BOUND,
                self.mover.SPEED_UPPER_BOUND),
            unit="[um/s]")

        self._build_entry_with_label(
            stage_properties_frame,
            self.z_speed_var,
            label="Movement speed z direction (valid range: {}...{:.0e}um/s):".format(
                self.mover.SPEED_LOWER_BOUND,
                self.mover.SPEED_UPPER_BOUND),
            unit="[um/s]")

        self._build_entry_with_label(
            stage_properties_frame,
            self.xy_acceleration_var,
            label="Movement acceleration xy direction (valid range: {}...{:.0e}um/s^2):".format(
                self.mover.ACCELERATION_LOWER_BOUND,
                self.mover.ACCELERATION_UPPER_BOUND),
            unit="[um/s^2]")
    #
    #   Callbacks
    #

    def _save(self):
        """
        Callback, when user hits "Save" button.
        """
        speed_xy = self._get_safe_value(
            self.xy_speed_var, float, self.mover.DEFAULT_SPEED_XY)
        speed_z = self._get_safe_value(
            self.z_speed_var, float, self.mover.DEFAULT_SPEED_Z)
        acceleration_xy = self._get_safe_value(
            self.xy_acceleration_var, float, self.mover.DEFAULT_ACCELERATION_XY)

        if self._warn_user_about_zero_speed(
                speed_xy) and self._warn_user_about_zero_speed(speed_z):
            try:
                self.controller.save(
                    stage_assignment=self._current_stage_assignment,
                    speed_xy=speed_xy,
                    speed_z=speed_z,
                    acceleration_xy=acceleration_xy
                )
                messagebox.showinfo(message="Successfully connected to {} stages.".format(
                    len(self._current_stage_assignment)))
                return True
            except Exception as e:
                messagebox.showerror(
                    message="Could not setup stages. Reason: {}".format(e))
                self.current_step = self.configure_stages_step
                return False

    def _on_stage_assignment(self, stage):
        """
        Callback, when user changes a stage assignment.
        Updates internal wizard state and reloads contents.
        """
        port = self.stage_port_var.get(stage, StringVar()).get()
        orientation = self.stage_orientation_var.get(stage, StringVar).get()

        if orientation == self.ASSIGNMENT_MENU_PLACEHOLDER:
            self._current_stage_assignment.pop(stage, None)
            self.__reload__()
            return

        self._current_stage_assignment[stage] = (
            Orientation[orientation.upper()], DevicePort[port.upper()])
        self.__reload__()

    def _check_stage_assignment(self):
        """
        Callback, when stage assignment steps reload.
        Check if current wizard state is valid.
        """
        valid, error = self._is_assignment_valid()
        self.current_step.next_step_enabled = valid
        self.set_error(error)

    #
    #   Frame Helpers
    #

    def _build_entry_with_label(
            self,
            parent,
            var: Type[DoubleVar],
            label: str = None,
            unit: str = None) -> None:
        """
        Builds an tkinter entry with label and unit.
        """
        entry_frame = Frame(parent)
        entry_frame.pack(side=TOP, fill=X, pady=2)

        Label(entry_frame, text=label).pack(side=LEFT)
        Label(entry_frame, text=unit).pack(side=RIGHT)
        entry = Entry(entry_frame, textvariable=var)
        entry.pack(side=RIGHT, padx=10)

    #
    #   Helpers
    #

    def _warn_user_about_zero_speed(self, speed) -> bool:
        """
        Warns user when settings speed to zero.

        Returns True if speed is not zero or user wants to set speed to zero.
        """
        if speed == 0.0:
            return messagebox.askokcancel(
                message="Setting speed to 0 will turn the speed control OFF! \n"
                "The stage will now move as fast as possible. Set a different speed if "
                "this is not intended. Do you want still to proceed?")

        return True

    def _is_assignment_valid(self) -> Tuple[bool, str]:
        """
        Returns a decision whether a the current mapping is valid.
        Checks for duplicate orientations and/or ports.
        """
        if not self._current_stage_assignment:
            return (False, "Please assign at least one to proceed.")

        if any(map(lambda l: len(l) != len(set(l)), zip(
                *self._current_stage_assignment.values()))):
            return (
                False,
                "Please do not assign a orientation or device port twice.")

        return (True, "")

    def _get_safe_value(
            self,
            var: Type[DoubleVar],
            to_type: type,
            default=None):
        """
        Returns the value of a tkinter entry and cast it to a specified type.

        If casting or retrieving fails, it returns a default value.
        """
        try:
            return to_type(var.get())
        except (ValueError, TypeError):
            return default
