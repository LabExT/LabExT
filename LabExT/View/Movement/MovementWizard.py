#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from functools import partial
from tkinter import W, Label, Button, messagebox, StringVar, OptionMenu, Frame, Button, Label, DoubleVar, Entry, DISABLED, NORMAL, LEFT, RIGHT, TOP, X
from typing import Type

from LabExT.Utils import run_with_wait_window
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Controls.Wizard import Step, Wizard

from LabExT.Movement.Calibration import DevicePort, Orientation
from LabExT.Movement.Stage import Stage, StageError
from LabExT.Movement.MoverNew import MoverError, MoverNew, Stage


class StageWizard(Wizard):
    """
    Wizard to load stage drivers and connect to stages.
    """

    def __init__(self, master, mover):
        """
        Constructor for new Stage Wizard.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        """
        super().__init__(
            master,
            width=1100,
            height=800,
            on_finish=self.finish,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish Setup",
        )
        self.title("Configure Mover")
        self.mover: Type[MoverNew] = mover

        self.load_driver_step = StageDriverStep(self, self.mover)
        self.stage_assignment_step = StageAssignmentStep(self, self.mover)

        self.load_driver_step.next_step = self.stage_assignment_step
        self.stage_assignment_step.previous_step = self.load_driver_step

        self.current_step = self.load_driver_step

    def finish(self) -> bool:
        """
        Creates calibrations and connect to stages.
        """
        if self.mover.has_connected_stages:
            if messagebox.askokcancel(
                "Proceed?",
                "You have already created stages. If you continue, they will be reset, including the calibrations. Proceed?",
                    parent=self):
                self.mover.reset()
            else:
                return False

        for stage, assignment in self.stage_assignment_step.assignment.items():
            try:
                calibration = self.mover.add_stage_calibration(
                    stage, *assignment)
                run_with_wait_window(
                    self,
                    f"Connecting to stage {stage}",
                    lambda: calibration.connect_to_stage())
            except (ValueError, MoverError, StageError) as e:
                self.mover.reset()
                messagebox.showerror(
                    "Error",
                    f"Connecting to stages failed: {e}",
                    parent=self)

        messagebox.showinfo(
            "Stage Setup completed.",
            f"Successfully connected to {len(self.stage_assignment_step.assignment)} stage(s).",
            parent=self)

        return True


class MoverWizard(Wizard):
    """
    Wizard to configure the mover
    """

    def __init__(self, master, mover):
        """
        Constructor for new Mover Wizard.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        """
        self.mover: Type[MoverNew] = mover

        if not self.mover.has_connected_stages:
            raise RuntimeError("No connected stages. Cannot configure mover.")

        super().__init__(
            master,
            width=1100,
            height=800,
            on_finish=self.finish,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Save",
            with_sidebar=False
        )
        self.title("Configure Mover")

        self.configure_mover_step = ConfigureMoverStep(self, self.mover)
        self.current_step = self.configure_mover_step

    def finish(self):
        speed_xy = self._get_safe_value(
            self.configure_mover_step.xy_speed_var,
            float,
            self.mover.DEFAULT_SPEED_XY)
        speed_z = self._get_safe_value(
            self.configure_mover_step.z_speed_var,
            float,
            self.mover.DEFAULT_SPEED_Z)
        acceleration_xy = self._get_safe_value(
            self.configure_mover_step.xy_acceleration_var,
            float,
            self.mover.DEFAULT_ACCELERATION_XY)

        if self._warn_user_about_zero_speed(
                speed_xy) and self._warn_user_about_zero_speed(speed_z):
            try:
                self.mover.speed_xy = speed_xy
                self.mover.speed_z = speed_z
                self.mover.acceleration_xy = acceleration_xy

                messagebox.showinfo(
                    "Mover Setup completed.",
                    f"Successfully configured mover.",
                    parent=self)

                return True
            except Exception as e:
                messagebox.showerror(
                    message=f"Could not setup stages. Reason: {e}",
                    parent=self)

        return False

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


class StageDriverStep(Step):
    """
    Wizard Step to load stage drivers.
    """

    def __init__(self, wizard, mover) -> None:
        """
        Constructor for new Wizard step for loading drivers.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        """
        super().__init__(
            wizard,
            self.build,
            title="Driver Settings")
        self.mover: Type[MoverNew] = mover

    def build(self, frame: Type[CustomFrame]) -> None:
        """
        Builds step to load stage drivers.

        Parameters
        ----------
        frame : CustomFrame
            Instance of a customized Tkinter frame.
        """
        frame.title = "Load Stage Drivers"

        Label(
            frame,
            text="Below you can see all Stage classes available in LabExT.\nSo that all stages can be found correctly in the following step, make sure that the drivers for each class are loaded."
        ).pack(side=TOP, fill=X)

        if not self.mover.stage_classes:
            Label(frame, text="No stage classes found!").pack(side=TOP, fill=X)

        for stage_cls in self.mover.stage_classes:
            stage_driver_frame = Frame(frame)
            stage_driver_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                stage_driver_frame,
                text=f"[{stage_cls.__name__}] {stage_cls.meta.description}"
            ).pack(side=LEFT, fill=X)

            stage_driver_load = Button(
                stage_driver_frame,
                text="Load Driver",
                state=NORMAL if stage_cls.meta.driver_specifiable else DISABLED,
                command=partial(
                    self.load_driver,
                    stage_cls))
            stage_driver_load.pack(side=RIGHT)

            stage_driver_status = Label(
                stage_driver_frame,
                text="Loaded" if stage_cls.driver_loaded else "Not Loaded",
                foreground='#4BB543' if stage_cls.driver_loaded else "#FF3333",
            )
            stage_driver_status.pack(side=RIGHT, padx=10)

    def load_driver(self, stage_class: Stage) -> None:
        """
        Callback to invoke a stage classes driver loading method.

        Parameters
        ----------
        stage_class : Stage
            Class of a stage.
        """
        if not stage_class.load_driver(self.wizard):
            return

        self.mover.reload_stage_classes()
        self.mover.reload_stages()
        self.wizard.__reload__()


class StageAssignmentStep(Step):
    """
    Wizard Step to assign and connect stages.
    """

    ASSIGNMENT_MENU_PLACEHOLDER = "-- unused --"

    def __init__(self, wizard, mover) -> None:
        """
        Constructor for new Wizard step for assigning stages.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        """
        super().__init__(
            wizard,
            self.build,
            on_reload=self.on_reload,
            title="Stage Connection")
        self.mover: Type[MoverNew] = mover

        self.assignment = {
            c.stage: (
                o,
                p) for (
                o,
                p),
            c in self.mover.calibrations.items()}
        self.orientation_vars, self.port_vars = self._build_assignment_variables()

    def build(self, frame: Type[CustomFrame]) -> None:
        """
        Builds step to assign stages.

        Parameters
        ----------
        frame : CustomFrame
            Instance of a customized Tkinter frame.
        """
        frame.title = "Manage Stage Connections"

        Label(
            frame,
            text="Below you can see all the stages found by LabExT.\nIf stages are missing, go back one step and check if all drivers are loaded."
        ).pack(side=TOP, fill=X)

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

        for avail_stage in self.mover.available_stages:
            available_stage_frame = Frame(stage_assignment_frame)
            available_stage_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                available_stage_frame, text=str(avail_stage), anchor="w"
            ).pack(side=LEFT, fill=X, padx=(0, 10))

            port_menu = OptionMenu(
                available_stage_frame,
                self.port_vars[avail_stage],
                *(list(DevicePort))
            )
            port_menu.pack(side=RIGHT, padx=5)

            port_menu.config(state=DISABLED if self.orientation_vars[avail_stage].get(
            ) == self.ASSIGNMENT_MENU_PLACEHOLDER else NORMAL)

            Label(
                available_stage_frame, text="Device Port:"
            ).pack(side=RIGHT, fill=X, padx=5)

            OptionMenu(
                available_stage_frame,
                self.orientation_vars[avail_stage],
                *([self.ASSIGNMENT_MENU_PLACEHOLDER] + list(Orientation))
            ).pack(side=RIGHT, padx=5)

            Label(
                available_stage_frame, text="Stage Orientation:"
            ).pack(side=RIGHT, fill=X, padx=5)

    def on_reload(self) -> None:
        """
        Callback, when wizard step gets reloaded.

        Checks if there is an assignment and if no stage, orientation or port was used twice.
        """
        if not self.assignment:
            self.finish_step_enabled = False
            self.wizard.set_error("Please assign at least one to proceed.")
            return

        if any(map(lambda l: len(l) != len(set(l)),
               zip(*self.assignment.values()))):
            self.finish_step_enabled = False
            self.wizard.set_error(
                "Please do not assign a orientation or device port twice.")
            return

        self.finish_step_enabled = True
        self.wizard.set_error("")

    def change_assignment(self, stage: Stage) -> None:
        """
        Callback, when user changes a stage assignment.
        Updates internal wizard state and reloads contents.
        """
        port = self.port_vars[stage].get()
        orientation = self.orientation_vars[stage].get()

        if orientation == self.ASSIGNMENT_MENU_PLACEHOLDER:
            self.assignment.pop(stage, None)
            self.wizard.__reload__()
            return

        self.assignment[stage] = (
            Orientation[orientation.upper()], DevicePort[port.upper()])
        self.wizard.__reload__()

    def _build_assignment_variables(self) -> tuple:
        """
        Builds and returns Tkinter variables for orrientation and port selection.
        """
        orientation_vars = {}
        port_vars = {}

        for stage in self.mover.available_stages:
            orientation, port = self.assignment.get(
                stage, (self.ASSIGNMENT_MENU_PLACEHOLDER, DevicePort.INPUT))

            port_var = StringVar(self.wizard, port)
            port_var.trace(
                W, lambda *_, stage=stage: self.change_assignment(stage))

            orientation_var = StringVar(self.wizard, orientation)
            orientation_var.trace(
                W, lambda *_, stage=stage: self.change_assignment(stage))

            orientation_vars[stage] = orientation_var
            port_vars[stage] = port_var

        return orientation_vars, port_vars


class ConfigureMoverStep(Step):
    def __init__(self, wizard, mover) -> None:
        super().__init__(
            wizard,
            self.build,
            finish_step_enabled=True,
            title="Stage Configuration")
        self.mover: Type[MoverNew] = mover

        self.xy_speed_var = DoubleVar(
            self.wizard,
            self.mover.speed_xy if self.mover._speed_xy else self.mover.DEFAULT_SPEED_XY)
        self.z_speed_var = DoubleVar(
            self.wizard,
            self.mover.speed_z if self.mover._speed_z else self.mover.DEFAULT_SPEED_Z)
        self.xy_acceleration_var = DoubleVar(
            self.wizard,
            self.mover.acceleration_xy if self.mover._acceleration_xy else self.mover.DEFAULT_ACCELERATION_XY)

    def build(self, frame: Type[CustomFrame]):
        """
        Builds step to configure stages.
        """
        frame.title = "Configure Assigned Stages"

        Label(
            frame,
            text="Configure the selected stages.\nThese settings are applied globally to all selected stages."
        ).pack(side=TOP, fill=X)

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
