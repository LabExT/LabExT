#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import os
import logging

from time import sleep, time
from os.path import dirname, join
from typing import Dict, Type, List
from functools import wraps
from datetime import datetime
from contextlib import contextmanager

from LabExT.Movement.config import State, DevicePort, CoordinateSystem
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.Stage import Stage
from LabExT.Movement.Transformations import ChipCoordinate, AxesRotation
from LabExT.Movement.PathPlanning import PathPlanning, CollisionAvoidancePlanning, SingleStagePlanning, StagePolygon

from LabExT.Utils import get_configuration_file_path
from LabExT.PluginLoader import PluginAPI
from LabExT.Wafer.Chip import Chip
from LabExT.Wafer.Device import Device


def assert_connected_stages(func):
    """
    Use this decorator to assert that the mover has at least one connected stage,
    when calling methods, which require connected stages.
    """

    @wraps(func)
    def wrapper(mover, *args, **kwargs):
        if not mover.has_connected_stages:
            raise MoverError(
                "Function {} needs at least one connected stage. Please use the connection functions beforehand".format(
                    func.__name__))

        return func(mover, *args, **kwargs)
    return wrapper


class MoverError(RuntimeError):
    pass


class MoverNew:
    """
    Entrypoint for all movement in LabExT.
    """

    # For range constants: See SmarAct Control Guide for more details.
    # Both ranges are inclusive, e.g speed in [SPEED_LOWER_BOUND,
    # SPEED_UPPER_BOUND]
    SPEED_LOWER_BOUND = 0
    SPEED_UPPER_BOUND = 1e5

    ACCELERATION_LOWER_BOUND = 0
    ACCELERATION_UPPER_BOUND = 1e7

    # Reasonable default values
    DEFAULT_SPEED_XY = 200.0
    DEFAULT_SPEED_Z = 20.0
    DEFAULT_ACCELERATION_XY = 0.0
    DEFAULT_Z_LIFT = 20.0

    # Settings files
    MOVER_SETTINGS_FILE = get_configuration_file_path(
        config_file_path_in_settings_dir="mover_settings.json")
    AXES_ROTATIONS_FILE = get_configuration_file_path(
        config_file_path_in_settings_dir="mover_axes_rotations.json")
    CALIBRATIONS_SETTINGS_FILE = get_configuration_file_path(
        config_file_path_in_settings_dir="mover_calibrations.json")

    def __init__(
        self,
        experiment_manager=None,
        chip=None
    ) -> None:
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager = None
            Current instance of ExperimentManager.
        chip : Chip = None
            Current instance of imported chip.
        """
        self.logger = logging.getLogger()

        self.experiment_manager = experiment_manager
        self._chip: Type[Chip] = chip

        # Mover API
        self.stage_api = PluginAPI(
            base_class=Stage, core_search_path=join(
                dirname(__file__), 'Stages'))
        self.polygon_api = PluginAPI(
            base_class=StagePolygon,
            core_search_path=dirname(__file__))

        # Mover calibrations
        self._calibrations: List[Type[Calibration]] = []
        self.__port_assigned_calibrations: Dict[DevicePort, Type[Calibration]] = {
            port: None for port in DevicePort}

        # Mover settings
        self._speed_xy = self.DEFAULT_SPEED_XY
        self._speed_z = self.DEFAULT_SPEED_Z
        self._acceleration_xy = self.DEFAULT_ACCELERATION_XY
        self._z_lift = self.DEFAULT_Z_LIFT

    def reset(self):
        """
        Resets complete mover stage.
        """
        self.reset_calibrations()

        self._speed_xy = self.DEFAULT_SPEED_XY
        self._speed_z = self.DEFAULT_SPEED_Z
        self._acceleration_xy = self.DEFAULT_ACCELERATION_XY
        self._z_lift = self.DEFAULT_Z_LIFT

    def reset_calibrations(self):
        """
        Resets all calibrations
        """
        for s in self.connected_stages:
            s.disconnect()

        self._calibrations = []
        self.__port_assigned_calibrations = {port: None for port in DevicePort}

    #
    #   Set chip
    #

    def set_chip(self, chip: Type[Chip]) -> None:
        """
        Sets the the current chip.
        This method will reset single point offset and kabsch rotation.
        """
        if self._chip == chip:
            return

        # Reset chip sensitive transformations
        for calibration in self.calibrations:
            calibration.reset_single_point_offset()
            calibration.reset_kabsch_rotation()

        # Store updates calibrations to disk
        self.dump_calibrations()

        # Set new chip
        self._chip = chip

    def update_main_model(self) -> None:
        """
        Update main model
        """
        if not self.experiment_manager:
            return

        _main_window = self.experiment_manager.main_window
        if not _main_window:
            return

        _main_window.model.status_mover_connected_stages.set(
            self.has_connected_stages)
        _main_window.model.status_mover_can_move_to_device.set(
            self.can_move_absolutely)

        _main_window.refresh_context_menu()

    def import_api_classes(self) -> None:
        """
        Import all mover api classes
        """
        search_paths = []
        if self.experiment_manager:
            search_paths = self.experiment_manager.addon_settings['addon_search_directories']

        self.stage_api.import_classes(search_paths)
        self.polygon_api.import_classes(search_paths)

    #
    #   Properties
    #

    @property
    def calibrations(self) -> List[Type[Calibration]]:
        """
        Returns a list of all calibrations
        Read-only. Use register_stage_calibration to register a new stage.
        """
        return self._calibrations

    @property
    def active_stages(self) -> List[Type[Stage]]:
        """
        Returns a list of all active stages. A stage is called active if it has been assigned
        to an orientation and device port
        """
        return [c.stage for c in self.calibrations]

    @property
    def connected_stages(self) -> List[Type[Stage]]:
        """
        Returns a list of all connected stages.
        """
        return [s for s in self.active_stages if s.connected]

    @property
    def state(self) -> State:
        """
        Returns the mover state, which is the lowest state of all calibrations
        """
        if not self.calibrations:
            return State.UNINITIALIZED

        return min(c.state for c in self.calibrations)

    @property
    def has_connected_stages(self) -> bool:
        """
        Returns True if any of the connected stage is connected (opened a connection to the stage).
        """
        return len(self.connected_stages) > 0

    @property
    def can_move_absolutely(self) -> bool:
        """
        Returns True if mover can move absolutely in chip coordinates.
        """
        if not self.calibrations:
            return False

        return all(c.state == State.SINGLE_POINT_FIXED or c.state ==
                   State.FULLY_CALIBRATED for c in self.calibrations)

    @property
    def can_move_relatively(self) -> bool:
        """
        Returns True if mover can move relatively in chip coordinates.
        """
        if not self.calibrations:
            return False

        return all(
            c.state >= State.COORDINATE_SYSTEM_FIXED for c in self.calibrations)

    @property
    def can_move_to_device(self) -> bool:
        """
        Returns True if mover can move to device.
        """
        port_assigned_calibrations = [
            c for c in self.__port_assigned_calibrations.values() if c is not None]

        return all(
            c.state >= State.SINGLE_POINT_FIXED for c in port_assigned_calibrations)

    @property
    def input_calibration(self) -> Type[Calibration]:
        """
        Returns the calibration assigned to the input port of a device.
        """
        return self.get_port_assigned_calibration(DevicePort.INPUT)

    @property
    def output_calibration(self) -> Type[Calibration]:
        """
        Returns the calibration assigned to the output port of a device.
        """
        return self.get_port_assigned_calibration(DevicePort.OUTPUT)

    @property
    def has_input_calibration(self) -> bool:
        """
        Returns True if input calibration is defined.
        """
        return self.input_calibration is not None

    @property
    def has_output_calibration(self) -> bool:
        """
        Returns True if output calibration is defined.
        """
        return self.output_calibration is not None

    def get_available_stages(self) -> list:
        """
        Returns a list of tuple of available stages.
        A tuple consists of available stage class paired with an available stage address.
        """
        available_stages = []
        for stage_cls in self.stage_api.imported_classes.values():
            try:
                available_stages += [(stage_cls, address)
                                     for address in stage_cls.find_stage_addresses()]
            except Exception as e:
                self.logger.error(
                    f"Failed to discover stages for {stage_cls}: {e}")

        return available_stages

    def get_port_assigned_calibration(
        self,
        device_port: DevicePort
    ) -> Type[Calibration]:
        """
        Returns calibration assigned to given device port.
        """
        return self.__port_assigned_calibrations.get(device_port)

    #
    #   Add new stage
    #

    def register_stage_calibration(
        self,
        calibration: Type[Calibration]
    ) -> None:
        """
        Registers a new stage calibration.
        """
        # Each new calibration needs stage
        if calibration.stage is None:
            raise ValueError(
                "Cannot register calibration without associated stage.")

        # Check that no stage is used twice
        if calibration.stage in self.active_stages:
            raise MoverError(
                f"The stage '{calibration.stage}' has already been registered.")

        # Check if calibration is used for Move-To-Device
        if calibration.is_automatic_movement_enabled:
            assigned_port = calibration.device_port
            if self.get_port_assigned_calibration(assigned_port):
                raise MoverError(
                    f"A Stage has already been assigned for device port {assigned_port}")

            self.logger.info(
                f"Set {calibration} for automatic movement to {assigned_port} device port.")
            self.__port_assigned_calibrations[assigned_port] = calibration

        # Add calibration to mover
        self._calibrations.append(calibration)

        # Stage successfully as stage registered
        calibration.connect_to_stage()
        # Setting stage settings
        calibration.stage.set_speed_xy(self._speed_xy)
        calibration.stage.set_speed_z(self._speed_z)
        calibration.stage.set_acceleration_xy(self._acceleration_xy)

    def deregister_stage_calibration(
        self,
        calibration: Type[Calibration]
    ) -> None:
        """
        Deregisters a new stage calibration.
        """
        if calibration not in self.calibrations:
            raise MoverError(
                f"Stage calibration '{calibration}' was not registered.")

        # Reset port assignment
        self.__port_assigned_calibrations = {
            p: None if c == calibration else c for p,
            c in self.__port_assigned_calibrations.items()}

        self._calibrations.remove(calibration)

    def restore_stage_calibration(
        self,
        stage: Type[Stage],
        calibration_data: dict
    ) -> None:
        """
        Restores a calibration for given stage and calibration data.
        """
        calibration = Calibration.load(
            self, stage, calibration_data, self._chip)

        self.register_stage_calibration(calibration)

    #
    #   Coordinate System Control
    #

    @contextmanager
    def set_stages_coordinate_system(self, system: CoordinateSystem):
        """
        Sets the coordinate system of all connected stages to the requested one.
        """
        prior_coordinate_systems = {
            c: c.coordinate_system for c in self.calibrations}

        for calibration in self.calibrations:
            calibration.set_coordinate_system(system)

        try:
            yield
        finally:
            for calibration, prior_coordinate_system in prior_coordinate_systems.items():
                calibration.set_coordinate_system(prior_coordinate_system)

    #
    #   Stage Settings Methods
    #

    @property
    @assert_connected_stages
    def speed_xy(self) -> float:
        """
        Returns the XY speed of all connected stages.
        If a stage has a different speed than stored in the Mover object (self._speed_xy), it will be changed to the stored one.
        """
        if any(s.get_speed_xy() != self._speed_xy for s in self.connected_stages):
            self.speed_xy = self._speed_xy

        return self._speed_xy

    @speed_xy.setter
    @assert_connected_stages
    def speed_xy(self, umps: float):
        """
        Sets the XY speed for all connected stages to umps.
        Throws MoverError if a change of a stage fails. Stores the speed internally in the Mover object.
        """
        if umps < self.SPEED_LOWER_BOUND or umps > self.SPEED_UPPER_BOUND:
            raise ValueError("Speed for xy is out of valid range.")

        try:
            for stage in self.connected_stages:
                stage.set_speed_xy(umps)
        except RuntimeError as exec:
            raise MoverError("Setting xy speed failed: {}".format(exec))

        self._speed_xy = umps

    @property
    @assert_connected_stages
    def speed_z(self) -> float:
        """
        Returns the Z speed of all connected stages.
        If a stage has a different speed than stored in the Mover object (self._speed_z), it will be changed to the stored one.
        """
        if any(s.get_speed_z() != self._speed_z for s in self.connected_stages):
            self.speed_z = self._speed_z

        return self._speed_z

    @speed_z.setter
    @assert_connected_stages
    def speed_z(self, umps: float):
        """
        Sets the Z speed for all connected stages to umps.
        Throws MoverError if a change of a stage fails. Stores the speed internally in the Mover object.
        """
        if umps < self.SPEED_LOWER_BOUND or umps > self.SPEED_UPPER_BOUND:
            raise ValueError("Speed for z is out of valid range.")

        try:
            for stage in self.connected_stages:
                stage.set_speed_z(umps)
        except RuntimeError as exec:
            raise MoverError("Setting z speed failed: {}".format(exec))

        self._speed_z = umps

    @property
    @assert_connected_stages
    def acceleration_xy(self) -> float:
        """
        Returns the XY acceleration of all connected stages.
        If a stage has a different acceleration than stored in the Mover object (self._acceleration_xy), it will be changed to the stored one.
        """
        if any(s.get_acceleration_xy() !=
               self._acceleration_xy for s in self.connected_stages):
            self.acceleration_xy = self._acceleration_xy

        return self._acceleration_xy

    @acceleration_xy.setter
    @assert_connected_stages
    def acceleration_xy(self, umps2: float):
        """
        Sets the XY acceleration for all connected stages to umps.
        Throws MoverError if a change of a stage fails. Stores the acceleration internally in the Mover object.
        """
        if umps2 < self.ACCELERATION_LOWER_BOUND or umps2 > self.ACCELERATION_UPPER_BOUND:
            raise ValueError("Acceleration for xy is out of valid range.")

        try:
            for stage in self.connected_stages:
                stage.set_acceleration_xy(umps2)
        except RuntimeError as exec:
            raise MoverError("Acceleration xy speed failed: {}".format(exec))

        self._acceleration_xy = umps2

    @property
    def z_lift(self) -> float:
        """
        Returns the set value of how much the stage moves up
        Always positive.
        """
        return self._z_lift

    @z_lift.setter
    def z_lift(self, lift: float) -> None:
        """
        Sets the value of how much the stage moves up

        Parameters
        ----------
        lift : float
            How much the stage moves up [um]

        Raises
        ------
        ValueError
            If lift is negative.
        """
        if lift < 0:
            raise ValueError("Lift distance must be non-negative.")

        self._z_lift = lift

    #
    #   Movement Methods
    #

    def get_path_planning_strategy(self) -> Type[PathPlanning]:
        """
        Returns a PathPlanning based on number of stages
        """
        if len(self.connected_stages) == 1:
            return SingleStagePlanning(
                max_lift_correction=100,
                correction_tolerance=10)
        else:
            return CollisionAvoidancePlanning(
                chip=self._chip,
                abort_local_minimum=3)

    @assert_connected_stages
    def move_absolute(
        self,
        movement_commands: Dict[Type[Calibration], Type[ChipCoordinate]],
        with_lifted_stages: bool = False,
        wait_for_stopping: bool = True,
        wait_timeout: float = 2.0
    ) -> None:
        """
        Moves the stages absolutely in the chip coordinate system.

        A collision-free trajectory is calculated.

        Parameters
        ----------
        movement_commands : Dict[Type[Calibration], Type[ChipCoordinate]]
            A mapping between calibration and target chip coordinate.
        wait_for_stopping: bool = True
            Whether each stage should have completed its movement before the next one moves.
        with_lifted_stages: bool = False
            Indicates whether the stages should be lifted before movement.

        Raises
        ------
        MoverError
            If an orientation has been given a target, but no stage exists for this orientation.
        LocalMinimumError
            If the path-finding algorithm makes no progress
             i.e. does not converge to the target coordinate.
        """
        if not movement_commands:
            return

        with self.set_stages_coordinate_system(CoordinateSystem.CHIP):
            path_planning = self.get_path_planning_strategy()

            # Set up Path Planning
            for calibration, target in movement_commands.items():
                if with_lifted_stages:
                    calibration.lift_stage(self.z_lift)

                target.z = calibration.get_position().z
                path_planning.set_stage_target(calibration, target)

            # Move stages on safe trajectory
            for calibration_waypoints in path_planning.trajectory():
                for calibration, waypoint in calibration_waypoints.items():
                    calibration.move_absolute(
                        coordinate=waypoint.coordinate, wait_for_stopping=(
                            wait_for_stopping or waypoint.wait_for_stopping))

                # Wait for all stages to stop if stages move simultaneously.
                if not wait_for_stopping:
                    busy_spinning_start = time()
                    while True:
                        sleep(0.05)

                        if time() - busy_spinning_start >= wait_timeout:
                            raise RuntimeError(
                                f"Stages did not stop after {wait_timeout} seconds. Abort.")

                        if all(c.stage.is_stopped
                               for c in calibration_waypoints.keys()):
                            break

            # Movement complete and lower stages (if requested)
            # Lift stages if requested
            if with_lifted_stages:
                for c in movement_commands.keys():
                    c.lower_stage(self.z_lift)

    @assert_connected_stages
    def move_relative(
        self,
        movement_commands: Dict[Type[Calibration], Type[ChipCoordinate]],
        wait_for_stopping: bool = True
    ) -> None:
        """
        Moves the stages relatively in the chip coordinate system.
        Note: There is no collision-free algorithm.

        Parameters
        ----------
        movement_commands : Dict[Type[Calibration], Type[ChipCoordinate]]
            A mapping between calibration and requested offset in chip coordinates.
        wait_for_stopping: bool = True
            Whether each stage should have completed its movement before the next one moves.
        Raises
        ------
        MoverError
            If Mover cannot move relatively.
        """
        if not self.can_move_relatively:
            raise MoverError(
                f"Cannot perform relative movement, not all active stages are calibrated correctly."
                "Note for each stage the coordinate system must be fixed.")

        if not movement_commands:
            return

        for calibration, offset in movement_commands.items():
            with calibration.perform_in_system(CoordinateSystem.CHIP):
                calibration.move_relative(offset, wait_for_stopping)

    @assert_connected_stages
    def move_to_device(self, target_device: Type[Device]):
        """
        Moves stages to device.

        Moves stages absolute to coordinate with path planning and lifted stages.

        Parameters
        ----------
        target_device: Device
            Device to which the stages should move.
        """
        if not self.can_move_to_device:
            raise MoverError(
                "Cannot move to device: Either no port assigned stages were added or they cannot move absolutely.")

        assert target_device in self._chip.devices.values(
        ), "Target device must be a device of the currently imported chip."

        movement_commands = {}
        if self.has_input_calibration:
            movement_commands[self.input_calibration] = target_device.input_coordinate

        if self.has_output_calibration:
            movement_commands[self.output_calibration] = target_device.output_coordinate

        self.move_absolute(
            movement_commands,
            with_lifted_stages=True)

    #
    #   Load and store mover settings
    #

    def dump_calibrations(self) -> None:
        """
        Stores current calibrations to file.
        """
        _chip_name = None
        if self._chip:
            _chip_name = self._chip.name

        with open(self.CALIBRATIONS_SETTINGS_FILE, "w") as fp:
            json.dump({
                "chip_name": _chip_name,
                "last_updated_at": datetime.now().isoformat(),
                "calibrations": [
                    c.dump() for c in self.calibrations]
            }, fp, indent=2)

    def dump_axes_rotations(self) -> None:
        """
        Stores all axes rotations of calibrations to file.
        """
        with open(self.AXES_ROTATIONS_FILE, "w") as fp:
            json.dump({
                c.stage.identifier: c.dump(
                    axes_rotation=True,
                    single_point_offset=False,
                    kabsch_rotation=False,
                    stage_polygon=False) for c in self.calibrations}, fp)

    def dump_settings(self) -> None:
        """
        Stores mover settings to file.
        """
        with open(self.MOVER_SETTINGS_FILE, "w") as fp:
            json.dump({
                "speed_xy": self._speed_xy,
                "speed_z": self._speed_z,
                "acceleration_xy": self._acceleration_xy,
                "z_lift": self._z_lift
            }, fp)

    def load_settings(self) -> None:
        """
        Loads mover settings from file if available.

        Updates internal state of stage speed, lift and acceleration.
        Sets these properties for all connected stages.
        """
        if not os.path.exists(self.MOVER_SETTINGS_FILE):
            return

        try:
            with open(self.MOVER_SETTINGS_FILE) as fp:
                mover_settings = json.load(fp)
        except (OSError, json.decoder.JSONDecodeError) as err:
            self.logger.error(
                f"Failed to load/decode settings file {self.MOVER_SETTINGS_FILE}: {err}")
            return

        self._speed_xy = mover_settings.get("speed_xy", self.DEFAULT_SPEED_XY)
        self._speed_z = mover_settings.get("speed_z", self.DEFAULT_SPEED_Z)
        self._acceleration_xy = mover_settings.get(
            "acceleration_xy", self.DEFAULT_ACCELERATION_XY)
        self._z_lift = mover_settings.get("z_lift", self.DEFAULT_SPEED_Z)

        self.logger.debug(
            f"Restored mover settings: xy-speed = {self._speed_xy}; z-speed = {self._speed_z}; "
            f"xy-acceleration = {self._acceleration_xy}; z-lift = {self.z_lift}")

    def load_stored_axes_rotation_for_stage(
        self,
        stage: Type[Stage]
    ) -> Type[AxesRotation]:
        """
        Returns a restored AxesRotation from file if available.

        If not available, returns a default identity rotation.
        """
        try:
            with open(self.AXES_ROTATIONS_FILE, "r") as fp:
                saved_axes_rotations = json.load(fp)
        except (OSError, json.decoder.JSONDecodeError) as err:
            self.logger.error(
                f"Failed to load/decode axes rotation file {self.AXES_ROTATIONS_FILE}: {err}")
            return AxesRotation()

        if stage.identifier not in saved_axes_rotations:
            return AxesRotation()

        self.logger.debug(
            f"Found saved axes rotation for {stage.identifier} in {self.AXES_ROTATIONS_FILE}. "
            "Restoring it.")

        try:
            return AxesRotation.load(
                mapping=saved_axes_rotations[stage.identifier]["axes_rotation"])
        except Exception as err:
            self.logger.error(
                f"Failed to restore axes rotation for {stage.identifier} from {self.AXES_ROTATIONS_FILE}: {err}")
            return AxesRotation()

    def load_stored_calibrations_for_chip(
        self,
        chip: Type[Chip]
    ) -> dict:
        """
        Returns restored calibrations from file if available.

        If not available, returns an empty dict.
        """
        if chip is None or chip.name is None:
            return {}

        try:
            with open(self.CALIBRATIONS_SETTINGS_FILE, "r") as fp:
                calibration_settings = json.load(fp)
                chip_name = calibration_settings.get("chip_name")
                calibrations = calibration_settings.get("calibrations", [])
                if chip_name == chip.name and len(calibrations) > 0:
                    return calibration_settings
                else:
                    return {}
        except (OSError, json.decoder.JSONDecodeError) as err:
            self.logger.error(
                f"Failed to load/decode calibration file {self.AXES_ROTATIONS_FILE}: {err}")
            return {}
