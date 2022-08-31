#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from logging import getLogger
from functools import partial
from itertools import product
from tkinter import W, Label, Button, messagebox, StringVar, OptionMenu, Frame, Button, Label, DoubleVar, Entry, BooleanVar, Checkbutton, DISABLED, NORMAL, LEFT, RIGHT, TOP, X
from typing import Type, List
from bidict import bidict

from LabExT.Utils import run_with_wait_window, try_to_lift_window
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Controls.Wizard import Step, Wizard

from LabExT.Movement.config import Orientation, DevicePort, Axis, Direction
from LabExT.Movement.Stage import Stage, StageError
from LabExT.Movement.MoverNew import MoverError, MoverNew, Stage
from LabExT.Movement.Transformations import CoordinatePairing
from LabExT.Movement.Calibration import Calibration
from LabExT.Wafer.Chip import Chip


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
                return False

        try:
            self.mover.set_default_settings()
        except Exception as err:
            messagebox.showerror(
                "Error",
                f"Failed to set default setting: {err}",
                parent=self)
            return False

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
        z_lift = self._get_safe_value(
            self.configure_mover_step.z_lift_var,
            float,
            self.mover.DEFAULT_Z_LIFT)

        if self._warn_user_about_zero_speed(
                speed_xy) and self._warn_user_about_zero_speed(speed_z):
            try:
                self.mover.speed_xy = speed_xy
                self.mover.speed_z = speed_z
                self.mover.acceleration_xy = acceleration_xy
                self.mover.z_lift = z_lift

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


class CalibrationWizard(Wizard):
    def __init__(self, master, mover, chip):
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip

        if len(self.mover.calibrations) == 0:
            raise RuntimeError(
                "Calibration not possible without connected stages.")

        if self.chip is None:
            raise RuntimeError("Calibration not possible without loaded chip.")

        super().__init__(
            master,
            width=1100,
            height=800,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish Setup",
        )
        self.title("Configure Mover")

        self.calibrate_axes_step = AxesCalibrationStep(self, self.mover)
        self.coordinate_pairing_step = CoordinatePairingStep(
            self, self.mover, self.chip)

        self.calibrate_axes_step.next_step = self.coordinate_pairing_step
        self.coordinate_pairing_step.previous_step = self.calibrate_axes_step

        self.current_step = self.calibrate_axes_step


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
        self.z_lift_var = DoubleVar(
            self.wizard,
            self.mover.z_lift if self.mover._z_lift else self.mover.DEFAULT_Z_LIFT)

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

        self._build_entry_with_label(
            stage_properties_frame,
            self.z_lift_var,
            label="Z channel up-movement during xy movement:",
            unit="[um]")

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


class AxesCalibrationStep(Step):
    """
    Wizard Step to calibrate stage axes.
    """

    STAGE_AXIS_OPTIONS = bidict({o: " ".join(map(str, o))
                                for o in product(Direction, Axis)})

    def __init__(self, wizard, mover) -> None:
        """
        Constructor for new Wizard step for calibrating stage axes.

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
            title="Stage Axes Calibration")
        self.mover: Type[MoverNew] = mover
        self.logger = getLogger()

        self.axes_mapping_vars = self._build_axes_mapping_vars()

    def _build_axes_mapping_vars(self):
        """
        Builds and returns Tkinter variables for axes calibration.
        """
        vars = {}
        for calibration in self.mover.calibrations.values():
            # Get current mapping
            _current_mapping = {}
            if calibration._axes_rotation and calibration._axes_rotation.is_valid:
                _current_mapping = calibration._axes_rotation.mapping

            for chip_axis in Axis:
                _current_value = _current_mapping.get(
                    chip_axis, (Direction.POSITIVE, chip_axis))
                str_var = StringVar(self.wizard, _current_value)
                str_var.trace(
                    W,
                    lambda *_,
                    calibration=calibration,
                    chip_axis=chip_axis: self.calibrate_axis(
                        calibration,
                        chip_axis))
                vars.setdefault(calibration, {})[chip_axis] = str_var

        return vars

    def build(self, frame: Type[CustomFrame]):
        """
        Builds step to calibrate axes.

        Parameters
        ----------
        frame : CustomFrame
            Instance of a customized Tkinter frame.
        """
        frame.title = "Fix Coordinate System"

        Label(
            frame,
            text="In order for each stage to move relative to the chip coordinates, the direction of each axis of each stage must be defined. \n Postive Y-Axis: North of chip, Positive X-Axis: East of chip, Positive Z-Axis: Lift stage"
        ).pack(side=TOP, fill=X)

        for calibration in self.mover.calibrations.values():
            stage_calibration_frame = CustomFrame(frame)
            stage_calibration_frame.title = str(calibration)
            stage_calibration_frame.pack(side=TOP, fill=X, pady=2)

            for chip_axis in Axis:
                chip_axis_frame = Frame(stage_calibration_frame)
                chip_axis_frame.pack(side=TOP, fill=X)

                Label(
                    chip_axis_frame,
                    text="Positive {}-Chip-axis points to ".format(chip_axis.name)
                ).pack(side=LEFT)

                OptionMenu(
                    chip_axis_frame,
                    self.axes_mapping_vars[calibration][chip_axis],
                    *self.STAGE_AXIS_OPTIONS.values(),
                ).pack(side=LEFT)

                Label(chip_axis_frame, text="of Stage").pack(side=LEFT)

                wiggle_button = Button(
                    chip_axis_frame,
                    text="Wiggle {}-Axis".format(
                        chip_axis.name),
                    command=lambda axis=chip_axis,
                    calibration=calibration: self.wiggle_axis(
                        calibration,
                        axis),
                    state=NORMAL if calibration._axes_rotation.is_valid else DISABLED)
                wiggle_button.pack(side=RIGHT)

    def on_reload(self) -> None:
        """
        Callback, when coordinate system fixation step gets reloaded.
        Checks, if the current assignment is valid.
        """
        if all(c._axes_rotation.is_valid for c in self.mover.calibrations.values()):
            self.next_step_enabled = True
            self.wizard.set_error("")
        else:
            self.next_step_enabled = False
            self.wizard.set_error("Please do not assign a stage axis twice.")

    def calibrate_axis(self, calibration: Type[Calibration], chip_axis: Axis):
        """
        Callback, when user wants to change the axis rotation of a calibration.
        """
        axis_var = self.axes_mapping_vars[calibration][chip_axis]
        direction, stage_axis = self.STAGE_AXIS_OPTIONS.inverse[axis_var.get()]

        calibration.update_axes_rotation(chip_axis, direction, stage_axis)
        self.wizard.__reload__()

    def wiggle_axis(self, calibration: Type[Calibration], chip_axis: Axis):
        """
        Callback, when user wants to wiggle an axis.

        Parameters
        ----------
        calibration: Calibration
            Instance of a calibration
        chip_axis: Axis
            Requested chip axis to wiggle
        """
        if not self._confirm_wiggle(chip_axis):
            return

        try:
            run_with_wait_window(
                self.wizard,
                f"Wiggle {chip_axis} of {calibration}",
                lambda: calibration.wiggle_axis(chip_axis))
        except RuntimeError as e:
            self.logger.log(f"Wiggling {chip_axis} failed: {e}")
            messagebox.showerror(
                "Error"
                f"Wiggling {chip_axis} failed: {e}",
                parent=self.wizard)

    def _confirm_wiggle(self, axis) -> bool:
        """
        Confirms with user if wiggeling is allowed.
        """
        message = 'By proceeding this button will move the stage along the {} direction. \n\n'.format(axis) \
                  + 'Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n' \
                  + 'For correct operation the stage should: \n' \
                  + 'First: Move in positive {}-Chip-Axis direction \n'.format(axis) \
                  + 'Second: Move in negative {}-Chip-Axis direction \n\n'.format(axis) \
                  + 'If not, please check your assignments.\n Do you want to proceed with wiggling?'

        return messagebox.askokcancel("Warning", message, parent=self.wizard)


class CoordinatePairingStep(Step):
    """
    Wizard Step to fully calibrate stages.
    """

    def __init__(self, wizard, mover, chip) -> None:
        """
        Constructor for new Wizard step for fully calibrate stages.

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
            finish_step_enabled=True,
            on_reload=self.on_reload,
            title="Stage Configuration")
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip

        self._use_input_stage_var = BooleanVar(self.wizard, True)
        self._use_output_stage_var = BooleanVar(self.wizard, True)
        self._full_calibration_new_pairing_button = None

        self._coordinate_pairing_window = None

        self.pairings = self._build_pairings()

    def _build_pairings(self) -> list:
        """
        Returns a list of current pairings.
        """
        pairings = []
        for calibration in self.mover.calibrations.values():
            _kabsch_rotation = calibration._kabsch_rotation
            if _kabsch_rotation and _kabsch_rotation.is_valid:
                pairings += _kabsch_rotation.pairings

            _single_point_offset = calibration._single_point_offset
            if _single_point_offset and _single_point_offset.is_valid:
                if _single_point_offset.pairing not in pairings:
                    pairings.append(_single_point_offset.pairing)

        return pairings

    def build(self, frame: Type[CustomFrame]):
        """
        Builds step to fully calibrate axes.

        Parameters
        ----------
        frame : CustomFrame
            Instance of a customized Tkinter frame.
        """
        frame.title = "Calibrate Stage to enable absolute movement"

        Label(
            frame,
            text="To move the stages absolutely in chip coordinates, define at least 3 stage-chip-coordinate pairings to calculate the rotation. \n" +
            "Note: After the first coordinate pairing, the stages can be moved approximatively absolute in chip coordinates.").pack(
            side=TOP,
            fill=X)

        # Render table with all defined pairings
        pairings_frame = CustomFrame(frame)
        pairings_frame.title = "Defined Pairings"
        pairings_frame.pack(side=TOP, fill=X)

        pairings_table_frame = Frame(pairings_frame)
        pairings_table_frame.pack(side=TOP, fill=X, expand=False)

        CustomTable(
            parent=pairings_table_frame,
            selectmode='none',
            columns=(
                'ID',
                'Stage',
                'Stage Cooridnate',
                'Device',
                'Chip Coordinate'),
            rows=[
                (idx,
                 ) + p for idx,
                p in enumerate(
                    self.pairings)])

        # Render frame to show current calibration state
        calibration_summary_frame = CustomFrame(frame)
        calibration_summary_frame.pack(side=TOP, fill=X)

        for calibration in self.mover.calibrations.values():
            stage_calibration_frame = CustomFrame(calibration_summary_frame)
            stage_calibration_frame.title = str(calibration)
            stage_calibration_frame.pack(side=TOP, fill=X, pady=2)

            # SINGLE POINT STATE
            Label(
                stage_calibration_frame,
                text="Single Point Fixation:"
            ).grid(row=0, column=0, padx=2, pady=2, sticky=W)
            Label(
                stage_calibration_frame,
                text=calibration._single_point_offset,
                foreground='#4BB543' if calibration._single_point_offset.is_valid else "#FF3333",
            ).grid(
                row=0,
                column=1,
                padx=2,
                pady=2,
                sticky=W)

            # GLOBAL STATE
            Label(
                stage_calibration_frame,
                text="Global Transformation:"
            ).grid(row=1, column=0, padx=2, pady=2, sticky=W)
            Label(
                stage_calibration_frame,
                text=calibration._kabsch_rotation,
                foreground='#4BB543' if calibration._kabsch_rotation.is_valid else "#FF3333",
            ).grid(
                row=1,
                column=1,
                padx=2,
                pady=2,
                sticky=W)

        # FRAME FOR NEW PAIRING
        new_pairing_frame = CustomFrame(frame)
        new_pairing_frame.title = "Create New Pairing"
        new_pairing_frame.pack(side=TOP, fill=X, pady=5)

        Checkbutton(
            new_pairing_frame,
            text="Use Input-Stage for Pairing",
            variable=self._use_input_stage_var
        ).pack(side=LEFT)
        Checkbutton(
            new_pairing_frame,
            text="Use Output-Stage for Pairing",
            variable=self._use_output_stage_var
        ).pack(side=LEFT)

        self._full_calibration_new_pairing_button = Button(
            new_pairing_frame,
            text="New Pairing...",
            command=self._new_coordinate_pairing)
        self._full_calibration_new_pairing_button.pack(side=RIGHT)

    def on_reload(self):
        """
        Callback, when wizard step gets reloaded.
        Checks, if the all transformations are vald.
        """
        if not all(
                c._single_point_offset.is_valid for c in self.mover.calibrations.values()):
            self.next_step_enabled = False
            self.finish_step_enabled = False
            self.wizard.set_error("Please fix for each stage a single point.")
            return

        if not all(
                c._kabsch_rotation.is_valid for c in self.mover.calibrations.values()):
            self.next_step_enabled = False
            self.finish_step_enabled = True
            self.wizard.set_error(
                "Please define for each stage at least three points to calibrate the stages globally.")
            return

        self.finish_step_enabled = True
        self.next_step_enabled = True
        self.wizard.set_error("")

    def _new_coordinate_pairing(self):
        """
        Creates a window to create a coordinate pairing.
        """
        if self._check_for_exisiting_coordinate_window():
            return

        try:
            self._coordinate_pairing_window = CoordinatePairingsWindow(
                self.wizard,
                self.mover,
                self.chip,
                on_finish=self._save_coordinate_pairing,
                with_input_stage=self._use_input_stage_var.get(),
                with_output_stage=self._use_output_stage_var.get())
        except Exception as e:
            messagebox.showerror(
                "Error",
                "Could not initiate a new coordinate pairing: {}".format(e),
                parent=self.wizard)

    def _save_coordinate_pairing(self, pairings: List[CoordinatePairing]):
        """
        Delegates the list of pairings to the responsible calibrations.
        """
        for p in pairings:
            if not p.calibration._single_point_offset.is_valid:
                p.calibration.update_single_point_offset(p)

            p.calibration.update_kabsch_rotation(p)
            self.pairings.append(p)

        self.wizard.__reload__()

    def _check_for_exisiting_coordinate_window(self) -> bool:
        """
        Ensures that only one window exists to create a new coordinate pair.
        Returns True if there is a exsiting window.
        """
        if self._coordinate_pairing_window is None or not try_to_lift_window(
                self._coordinate_pairing_window):
            return False

        if not messagebox.askyesno(
            "New Coordinate-Pairing",
            "You have an incomplete creation of a coordinate pair. Click Yes if you want to continue it or No if you want to create the new one.",
                parent=self._coordinate_pairing_window):
            self._coordinate_pairing_window.cancel()
            self._coordinate_pairing_window = None
            return False

        return True
