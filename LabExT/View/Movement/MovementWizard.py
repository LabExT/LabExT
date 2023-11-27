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
from LabExT.Movement.PathPlanning import SingleModeFiber, StagePolygon

from LabExT.Utils import run_with_wait_window, try_to_lift_window
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Controls.Wizard import Step, Wizard
from LabExT.View.Controls.ParameterTable import ParameterTable

from LabExT.Measurements.MeasAPI.Measparam import MeasParamAuto

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

    def __init__(self, master, mover, experiment_manager=None):
        """
        Constructor for new Stage Wizard.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        experiment_manager : ExperimentManager = None
            Optional instance of the current experiment manager
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

        self.experiment_manager = experiment_manager

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
                self.mover.reset_calibrations()
            else:
                return False

        self.stage_assignment_step.update_polygon_cfg()
        for stage, assignment in self.stage_assignment_step.assignment.items():
            orientation, port = assignment

            polygon_cls, polygon_cls_cfg = self.stage_assignment_step.polygon_cfg.get(stage, (
                self.stage_assignment_step.DEFAULT_POLYGON,
                self.stage_assignment_step.DEFAULT_POLYGON.get_default_parameters()))
            stage_polygon = polygon_cls(
                orientation, parameters=polygon_cls_cfg)

            try:
                run_with_wait_window(
                    self,
                    f"Connecting to stage {stage}",
                    lambda: self.mover.add_stage_calibration(
                        stage=stage,
                        orientation=orientation,
                        port=port,
                        stage_polygon=stage_polygon))
            except (ValueError, MoverError, StageError) as e:
                self.mover.reset_calibrations()
                messagebox.showerror(
                    "Error",
                    f"Connecting to stages failed: {e}",
                    parent=self)
                return False

        if not self.experiment_manager:
            messagebox.showinfo(
                "Stage Setup completed.",
                f"Successfully connected to {len(self.stage_assignment_step.assignment)} stage(s).",
                parent=self)
        else:
            if messagebox.askyesnocancel(
                "Stage Setup completed.",
                f"Successfully connected to {len(self.stage_assignment_step.assignment)} stage(s)."
                "Do you want to calibrate the stages now?",
                    parent=self):
                self.destroy()

                self.experiment_manager.main_window.open_stage_calibration()

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

                self.mover.dump_settings()

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
    """
    Wizard to calibrate stages.
    """

    def __init__(
        self,
        master,
        mover,
        chip=None,
        experiment_manager=None
    ) -> None:
        """
        Constructor for new Mover Wizard.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        chip : Chip = None
            Optional instance of the current chip.
            Required for coordinate pairing step.
        experiment_manager : ExperimentManager = None
            Optional instance of the current experiment manager
        """
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip
        self.experiment_manager = experiment_manager

        if len(self.mover.calibrations) == 0:
            raise RuntimeError(
                "Calibration not possible without connected stages.")

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

        self.calibrate_axes_step = AxesCalibrationStep(self, self.mover)
        self.coordinate_pairing_step = CoordinatePairingStep(
            self, self.mover, self.chip)

        self.calibrate_axes_step.next_step = self.coordinate_pairing_step
        self.coordinate_pairing_step.previous_step = self.calibrate_axes_step

        self.current_step = self.calibrate_axes_step

    def finish(self):
        """
        Callback when user wants to finish the calibration.
        """
        try:
            self.mover.dump_calibrations()
        except Exception as err:
            messagebox.showerror(
                "Error",
                f"Could not store calibration settings to disk: {err}",
                parent=self)
            return False

        return True


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
            Label(
                frame,
                text="No stage classes found!",
                foreground="#FF3333").pack(
                side=TOP,
                fill=X)

        for stage_name, stage_cls in self.mover.stage_classes.items():
            stage_driver_frame = Frame(frame)
            stage_driver_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                stage_driver_frame,
                text=f"[{stage_cls.__name__}] {stage_cls.description}"
            ).pack(side=LEFT, fill=X)

            stage_driver_load = Button(
                stage_driver_frame,
                text="Load Driver",
                state=NORMAL if stage_cls.driver_specifiable else DISABLED,
                command=partial(
                    stage_cls.load_driver,
                    parent=self.wizard))
            stage_driver_load.pack(side=RIGHT)

            stage_driver_status = Label(
                stage_driver_frame,
                text="Loaded" if stage_cls.driver_loaded else "Not Loaded",
                foreground='#4BB543' if stage_cls.driver_loaded else "#FF3333",
            )
            stage_driver_status.pack(side=RIGHT, padx=10)


class StageAssignmentStep(Step):
    """
    Wizard Step to assign and connect stages.
    """

    POLYGON_OPTIONS = {
        pg.__name__: pg for pg in StagePolygon.find_polygon_classes()}

    ASSIGNMENT_MENU_PLACEHOLDER = "-- unused --"

    DEFAULT_POLYGON = SingleModeFiber
    DEFAULT_ASSIGNMENT = (
        ASSIGNMENT_MENU_PLACEHOLDER,
        DevicePort.INPUT)

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
            c.stage: (o, p)
            for (o, p), c in self.mover.calibrations.items()}
        self.polygon_cfg = {
            c.stage: (c.stage_polygon.__class__, c.stage_polygon.parameters)
            for c in self.mover.calibrations.values()}

        self.orientation_vars, self.port_vars, self.polygon_vars = self._build_assignment_variables()
        self._stage_polygon_parameter_tables = {}

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
                 s.__class__.description,
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

            polygon_menu = OptionMenu(
                available_stage_frame,
                self.polygon_vars[avail_stage],
                *(list(self.POLYGON_OPTIONS.keys()))
            )
            polygon_menu.pack(side=RIGHT, padx=5)

            polygon_menu.config(state=DISABLED if self.orientation_vars[avail_stage].get(
            ) == self.ASSIGNMENT_MENU_PLACEHOLDER else NORMAL)

            Label(
                available_stage_frame, text="Stage type:"
            ).pack(side=RIGHT, fill=X, padx=5)

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

            # Enable configuration if orientation is selected
            if self.orientation_vars[avail_stage].get(
            ) != self.ASSIGNMENT_MENU_PLACEHOLDER:
                polygon_cfg_frame = Frame(stage_assignment_frame)
                polygon_cfg_frame.pack(side=TOP, fill=X)

                polygon_cls, polygon_cls_cfg = self.polygon_cfg.get(
                    avail_stage, (self.DEFAULT_POLYGON, self.DEFAULT_POLYGON.get_default_parameters()))
                polygon_params = {
                    l: MeasParamAuto(
                        value=v) for l,
                    v in polygon_cls_cfg.items()}

                polygon_cfg_table = ParameterTable(polygon_cfg_frame)
                polygon_cfg_table.title = f"Configure Polygon: {polygon_cls.__name__}"
                polygon_cfg_table.parameter_source = polygon_params
                polygon_cfg_table.pack(
                    side=TOP, fill=X, expand=0, padx=2, pady=2)

                self._stage_polygon_parameter_tables[avail_stage] = polygon_cfg_table

    def on_reload(self) -> None:
        """
        Callback, when wizard step gets reloaded.

        Checks if there is an assignment and if no stage, orientation or port was used twice.
        """
        if not self.assignment:
            self.finish_step_enabled = False
            self.wizard.set_error("Please assign at least one to proceed.")
            return

        orientations, ports = zip(*self.assignment.values())
        double_orientations = len(orientations) != len(set(orientations))
        ports_orientations = len(ports) != len(set(ports))
        if double_orientations or ports_orientations:
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
        polygon_cls_name = self.polygon_vars[stage].get()
        polygon_cls = self.POLYGON_OPTIONS[polygon_cls_name]

        if orientation == self.ASSIGNMENT_MENU_PLACEHOLDER:
            self.assignment.pop(stage, None)
            self.wizard.__reload__()
            return

        if stage in self._stage_polygon_parameter_tables:
            settings = {}
            self._stage_polygon_parameter_tables[stage].serialize_to_dict(settings)
            polygon_cls_cfg = settings['data']
        else:
            polygon_cls_cfg = polygon_cls.get_default_parameters()

        self.polygon_cfg[stage] = (polygon_cls, polygon_cls_cfg)
        self.assignment[stage] = (
            Orientation[orientation.upper()],
            DevicePort[port.upper()])

        self.wizard.__reload__()

    def update_polygon_cfg(self) -> None:
        """
        Updates polygon configuration by reading values from table.
        """
        for stage, polygon_cfg_table in self._stage_polygon_parameter_tables.items():
            polygon_cls_name = self.polygon_vars[stage].get()
            polygon_cls = self.POLYGON_OPTIONS[polygon_cls_name]

            settings = {}
            polygon_cfg_table.serialize_to_dict(settings)
            self.polygon_cfg[stage] = (polygon_cls, settings['data'])

    def _build_assignment_variables(self) -> tuple:
        """
        Builds and returns Tkinter variables for orrientation and port selection.
        """
        orientation_vars = {}
        port_vars = {}
        polygon_vars = {}

        for stage in self.mover.available_stages:
            orientation, port = self.assignment.get(
                stage, self.DEFAULT_ASSIGNMENT)
            polygon_cls, _ = self.polygon_cfg.get(
                stage, (self.DEFAULT_POLYGON, {}))

            port_var = StringVar(self.wizard, port)
            port_var.trace(
                W, lambda *_, stage=stage: self.change_assignment(stage))

            orientation_var = StringVar(self.wizard, orientation)
            orientation_var.trace(
                W, lambda *_, stage=stage: self.change_assignment(stage))

            polygon_var = StringVar(self.wizard, polygon_cls.__name__)
            polygon_var.trace(
                W, lambda *_, stage=stage: self.change_assignment(stage))

            orientation_vars[stage] = orientation_var
            port_vars[stage] = port_var
            polygon_vars[stage] = polygon_var

        return orientation_vars, port_vars, polygon_vars


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
            on_next=self.on_next,
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

    def on_next(self) -> bool:
        """
        Callback, when user finishes axes calibration.
        Stores rotation to file.
        """
        try:
            self.mover.dump_axes_rotations()
        except Exception as err:
            messagebox.showerror(
                "Error",
                f"Failed to store axes rotation to file: {err}",
                parent=self.wizard)
            return False

        return True

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
        chip : Chip
            Instance of the current chip.
        """
        super().__init__(
            wizard,
            self.build,
            finish_step_enabled=True,
            on_reload=self.on_reload,
            title="Stage Configuration")
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip

        self._use_input_stage_var = BooleanVar(
            self.wizard, self.mover.has_input_calibration)
        self._use_output_stage_var = BooleanVar(
            self.wizard, self.mover.has_output_calibration)
        self._full_calibration_new_pairing_button = None

        self._coordinate_pairing_table = None
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

        # Render frame to for current chip
        chip_frame = CustomFrame(frame)
        chip_frame.title = "Imported Chip"
        chip_frame.pack(side=TOP, fill=X, pady=5)

        Label(
            chip_frame,
            text="The calibration is calculated using several coordinate pairs consisting of chip and stage coordinates. \n"
            "The following chip is used for calibration:").pack(
            side=TOP,
            fill=X)

        if self.chip:
            Label(
                chip_frame,
                text=f"{self.chip.name} (imported from {self.chip.path})",
                foreground='#4BB543'
            ).pack(side=LEFT, fill=X)
        else:
            Label(
                chip_frame,
                text="No Chip imported!",
                foreground='#FF3333'
            ).pack(side=LEFT, fill=X)

            Button(
                chip_frame,
                text="Import Chip",
                command=self._on_chip_import
            ).pack(side=RIGHT)

        # Render table with all defined pairings
        pairings_frame = CustomFrame(frame)
        pairings_frame.title = "Defined Pairings"
        pairings_frame.pack(side=TOP, fill=X, pady=5)

        pairings_table_frame = Frame(pairings_frame)
        pairings_table_frame.pack(side=TOP, fill=X, expand=False)

        self._coordinate_pairing_table = CustomTable(
            parent=pairings_table_frame,
            selectmode='extended',
            columns=(
                'ID',
                'Stage',
                'Stage Cooridnate',
                'Device',
                'Chip Coordinate'),
            rows=[(
                str(idx),
                str(p.calibration),
                str(p.stage_coordinate),
                str(p.device.short_str),
                str(p.chip_coordinate)
            ) for idx, p in enumerate(self.pairings)])

        Button(
            pairings_frame,
            text="Remove selected pairings",
            state=DISABLED if len(self.pairings) == 0 else NORMAL,
            command=self._remove_pairings
        ).pack(side=LEFT)

        Button(
            pairings_frame,
            text="Reset all pairings",
            state=DISABLED if len(self.pairings) == 0 else NORMAL,
            command=self._reset_all_pairings
        ).pack(side=RIGHT)

        # Render frame to show current calibration state
        calibration_summary_frame = CustomFrame(frame)
        calibration_summary_frame.pack(side=TOP, fill=X, pady=5)

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

            if calibration._kabsch_rotation.is_valid:
                rad, deg, per = calibration._kabsch_rotation.get_z_plane_angles()
                Label(
                    stage_calibration_frame,
                    text="Angle between XY Plane: "
                    "{:.2f} rad - {:.2f}° - {:.2f}%".format(rad, deg, per)
                ).grid(row=2, column=1, padx=2, pady=2, sticky=W)

        # FRAME FOR NEW PAIRING
        new_pairing_frame = CustomFrame(frame)
        new_pairing_frame.title = "Create New Pairing"
        new_pairing_frame.pack(side=TOP, fill=X, pady=5)

        if self.mover.has_input_calibration:
            Checkbutton(
                new_pairing_frame,
                text="Use Input-Stage for Pairing",
                state=NORMAL if self.chip else DISABLED,
                variable=self._use_input_stage_var
            ).pack(side=LEFT)
        if self.mover.has_output_calibration:
            Checkbutton(
                new_pairing_frame,
                text="Use Output-Stage for Pairing",
                state=NORMAL if self.chip else DISABLED,
                variable=self._use_output_stage_var
            ).pack(side=LEFT)

        self._full_calibration_new_pairing_button = Button(
            new_pairing_frame,
            text="New Pairing...",
            state=NORMAL if self.chip else DISABLED,
            command=self._new_coordinate_pairing)
        self._full_calibration_new_pairing_button.pack(side=RIGHT)

    def on_reload(self):
        """
        Callback, when wizard step gets reloaded.
        Checks, if the all transformations are vald.
        """
        if not self.chip:
            self.next_step_enabled = False
            self.finish_step_enabled = False
            self.wizard.set_error("Please import a chip to calibrate stages.")
            return

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

    def _reset_all_pairings(self):
        """
        Resets all pairings if the user confirms before.
        """
        if len(self.pairings) == 0:
            return

        if not messagebox.askokcancel(
            "Reset all pairings",
            f"Are you sure to delete all {len(self.pairings)} coordinate pairs? "
            "This step cannot be undone.",
                parent=self.wizard):
            return

        for calibration in self.mover.calibrations.values():
            calibration.reset_single_point_offset()
            calibration.reset_kabsch_rotation()

        self.pairings = []

        self.wizard.__reload__()

    def _remove_pairings(self):
        """
        Removes all selected pairings.
        """
        if len(self.pairings) == 0:
            return

        blacklisted_pairings = self._get_selected_pairings()
        if len(blacklisted_pairings) == 0:
            messagebox.showerror(
                "No pairings selected",
                "No pairings were selected for deletion.",
                parent=self.wizard)
            return

        whitelisted_pairings = [
            p for p in self.pairings if p not in blacklisted_pairings]

        # Reset all
        for calibration in self.mover.calibrations.values():
            calibration.reset_single_point_offset()
            calibration.reset_kabsch_rotation()

        self.pairings = []

        # Calc new transformations
        self._save_coordinate_pairing(whitelisted_pairings)
        self.wizard.__reload__()

    def _get_selected_pairings(self) -> List[CoordinatePairing]:
        """
        Returns a list of selected pairings in table.
        """
        if not self._coordinate_pairing_table:
            return []

        selected_pairings = []
        checked_iids = self._coordinate_pairing_table._tree.selection()
        for iid in checked_iids:
            pairing_idx = self._coordinate_pairing_table._tree.set(iid, 0)
            try:
                selected_pairings.append(
                    self.pairings[int(pairing_idx)])
            except (IndexError, ValueError):
                continue

        return selected_pairings

    def _new_coordinate_pairing(self):
        """
        Creates a window to create a coordinate pairing.
        """
        if self._check_for_exisiting_coordinate_window():
            return

        with_input_stage = self._use_input_stage_var.get()
        with_output_stage = self._use_output_stage_var.get()

        if not with_input_stage and not with_output_stage:
            messagebox.showwarning(
                "No Stages selected",
                "No stages have been selected with which to create a coordinate pairing. "
                "At least one stage must be selected.",
                parent=self.wizard)
            return

        try:
            self._coordinate_pairing_window = CoordinatePairingsWindow(
                self.wizard,
                self.mover,
                self.chip,
                experiment_manager=self.wizard.experiment_manager,
                on_finish=self._save_coordinate_pairing,
                with_input_stage=with_input_stage,
                with_output_stage=with_output_stage)
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

    def _on_chip_import(self) -> None:
        """
        Callback, when user wants to import a chip
        """
        if not self.wizard.experiment_manager:
            return

        self.wizard.experiment_manager.main_window.open_import_chip()
        self.chip = self.wizard.experiment_manager.chip

        self.wizard.__reload__()
