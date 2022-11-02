#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import numpy as np

from contextlib import contextmanager
from time import sleep, time
from bidict import bidict, ValueDuplicationError, KeyDuplicationError, OnDup, RAISE
from typing import Dict, Tuple, Type, List, Set
from functools import wraps
from os.path import exists
from datetime import datetime

from LabExT.Movement.config import CLOCKWISE_ORDERING, State, Orientation, DevicePort
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.Stage import Stage
from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.PathPlanning import PathPlanning

from LabExT.Utils import get_configuration_file_path
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

        self._stage_classes: List[Stage] = []
        self._available_stages: List[Type[Stage]] = []

        # Mover state
        self._calibrations = bidict()
        self._port_by_orientation = bidict()
        self._speed_xy = None
        self._speed_z = None
        self._acceleration_xy = None
        self._z_lift = None

        # Keeps track of lifted stages
        self._lifted_stages: Set[Calibration] = set()

        self.reload_stages()
        self.reload_stage_classes()

    def reset(self):
        """
        Resets Mover state.
        """
        self._calibrations = bidict()
        self._port_by_orientation = bidict()
        self._speed_xy = None
        self._speed_z = None
        self._acceleration_xy = None

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

        for calibration in self.calibrations.values():
            calibration.reset_single_point_offset()
            calibration.reset_kabsch_rotation()

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

    #
    #   Reload properties
    #

    def reload_stages(self) -> None:
        """
        Loads all available stages.
        """
        self._available_stages = Stage.find_available_stages()

    def reload_stage_classes(self) -> None:
        """
        Loads all Stage classes.
        """
        self._stage_classes = Stage.find_stage_classes()

    #
    #   Properties
    #

    @property
    def stage_classes(self) -> List[Stage]:
        """
        Returns a list of all Stage classes.
        Read-only.
        """
        return self._stage_classes

    @property
    def available_stages(self) -> List[Type[Stage]]:
        """
        Returns a list of stages available to the computer (all possible connection types)
        For example: For SmarAct Stages, this function returns all USB-connected stages.
        Read-only.
        """
        return self._available_stages

    @property
    def calibrations(
            self) -> Dict[Tuple[Orientation, DevicePort], Type[Calibration]]:
        """
        Returns a mapping: Calibration -> (orientation, device_port) instance
        Read-only. Use add_stage_calibration to register a new stage.
        """

        return self._calibrations

    @property
    def active_stages(self) -> List[Type[Stage]]:
        """
        Returns a list of all active stages. A stage is called active if it has been assigned
        to an orientation and device port
        """
        return [c.stage for c in self._calibrations.values()]

    @property
    def connected_stages(self) -> List[Type[Stage]]:
        """
        Returns a list of all connected stages.
        """
        return [s for s in self.active_stages if s.connected]

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
                   State.FULLY_CALIBRATED for c in self.calibrations.values())

    @property
    def can_move_relatively(self) -> bool:
        """
        Returns True if mover can move relatively in chip coordinates.
        """
        if not self.calibrations:
            return False

        return all(
            c.state >= State.COORDINATE_SYSTEM_FIXED for c in self.calibrations.values())

    @property
    def left_calibration(self) -> Type[Calibration]: return self._get_calibration(
        orientation=Orientation.LEFT)

    @property
    def right_calibration(self) -> Type[Calibration]: return self._get_calibration(
        orientation=Orientation.RIGHT)

    @property
    def top_calibration(self) -> Type[Calibration]: return self._get_calibration(
        orientation=Orientation.TOP)

    @property
    def bottom_calibration(self) -> Type[Calibration]: return self._get_calibration(
        orientation=Orientation.BOTTOM)

    @property
    def input_calibration(self) -> Type[Calibration]: return self._get_calibration(
        port=DevicePort.INPUT)

    @property
    def output_calibration(self) -> Type[Calibration]: return self._get_calibration(
        port=DevicePort.OUTPUT)

    #
    #   Add new stage
    #

    def add_stage_calibration(
            self,
            stage: Type[Stage],
            orientation: Orientation,
            port: DevicePort) -> Type[Calibration]:
        """
        Creates a new Calibration instance for a stage.
        Adds this instance to the list of connected stages.

        Raises ValueError, if orientation or device port is invalid.
        Raises MoverError, if Stage has been used before.

        Returns new calibration instance.
        """
        if not isinstance(port, DevicePort):
            raise ValueError("{} is an invalid port".format(port))

        if not isinstance(orientation, Orientation):
            raise ValueError(
                "{} is an invalid orientation".format(orientation))

        try:
            self._port_by_orientation.put(
                orientation, port, OnDup(key=RAISE))
        except ValueDuplicationError:
            raise MoverError(
                "A stage has already been assigned for the {} port.".format(port))
        except KeyDuplicationError:
            raise MoverError(
                "A stage has already been assigned for {}.".format(orientation))

        calibration = Calibration(self, stage, orientation, port)

        if stage in self.active_stages:
            del self._port_by_orientation[orientation]
            raise MoverError(
                "Stage {} has already an assignment.".format(stage))

        self._calibrations.put(
            (orientation, port), calibration, OnDup(
                key=RAISE))
        return calibration

    def restore_stage_calibration(
        self,
        stage: Type[Stage],
        calibration_data: dict
    ) -> Type[Calibration]:
        """
        Restores a calibration for given stage and calibration data.
        """
        if stage in self.active_stages:
            raise MoverError(
                "Stage {} has already an assignment.".format(stage))

        calibration = Calibration.load(
            self, stage, calibration_data, self._chip)

        self._port_by_orientation.put(
            calibration._orientation,
            calibration._device_port,
            OnDup(
                key=RAISE))

        self._calibrations.put(
            (calibration._orientation,
             calibration._device_port),
            calibration,
            OnDup(
                key=RAISE))

        return calibration

    #
    #   Stage Settings Methods
    #

    @assert_connected_stages
    def set_default_settings(self) -> None:
        """
        Set mover default settings
        """
        self.speed_xy = self.DEFAULT_SPEED_XY
        self.speed_z = self.DEFAULT_SPEED_Z
        self.acceleration_xy = self.DEFAULT_ACCELERATION_XY
        self.z_lift = self.DEFAULT_Z_LIFT

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

    @assert_connected_stages
    def move_absolute(
        self,
        movement_commands: Dict[Orientation, Type[ChipCoordinate]],
        chip: Type[Chip],
        wait_for_stopping: bool = True,
        wait_timeout: float = 2.0
    ) -> None:
        """
        Moves the stages absolutely in the chip coordinate system.

        A collision-free trajectory is calculated.

        Parameters
        ----------
        movement_commands : Dict[Orientation, Type[ChipCoordinate]]
            A mapping between orientation and target chip coordinate.
            For example, if the mapping `Orientation.LEFT: ChipCoordinate(1,2,3)` exists, the left stage is moved to the chip co-ordinate x=1, y=2, z=3
        wait_for_stopping: bool = True
            Whether each stage should have completed its movement before the next one moves.

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

        path_planning = PathPlanning(chip)

        # Set up Path Planning
        for orientation, target in movement_commands.items():
            calibration = self._get_calibration(orientation=orientation)
            if calibration is None:
                raise MoverError(
                    f"No {orientation} stage configured, but target coordinate for {orientation} passed.")

            current_stage_level = None
            if calibration in self._lifted_stages:
                current_stage_level = self.z_lift

            path_planning.set_stage_target(
                calibration, target, z_level=current_stage_level)

        # Move stages on safe trajectory
        for calibration_waypoints in path_planning.trajectory():
            for calibration, waypoint in calibration_waypoints.items():
                with calibration.perform_in_chip_coordinates():
                    calibration.move_absolute(waypoint, wait_for_stopping)

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

    @assert_connected_stages
    def move_relative(
        self,
        movement_commands: Dict[Orientation, Type[ChipCoordinate]],
        ordering: List[Orientation] = CLOCKWISE_ORDERING,
        wait_for_stopping: bool = True
    ) -> None:
        """
        Moves the stages relatively in the chip coordinate system.
        Note: There is no collision-free algorithm, the stages are moved
        based on the given ordering (default clockwise).
        Parameters
        ----------
        movement_commands : Dict[Orientation, Type[ChipCoordinate]]
            A mapping between orientation and requested offset in chip coordinates.
            For example, if the mapping `Orientation.LEFT: ChipCoordinate(1,2,3)` exists, the left stage is moved relatively
            with an offset of x=1, y=2, z=3.
        wait_for_stopping: bool = True
            Whether each stage should have completed its movement before the next one moves.
        Raises
        ------
        MoverError
            If an orientation has been given a target, but no stage exists for this orientation.
            If Mover cannot move relatively.
        """
        if not self.can_move_relatively:
            raise MoverError(
                f"Cannot perform relative movement, not all active stages are calibrated correctly."
                "Note for each stage the coordinate system must be fixed.")

        if not movement_commands:
            return

        # Makes sure that a calibration exists for each movement command.
        resolved_calibrations = {}
        for orientation in movement_commands:
            calibration = self._get_calibration(orientation=orientation)
            if calibration is None:
                raise MoverError(
                    f"No {orientation} stage configured, but offset for {orientation} passed.")

            resolved_calibrations[orientation] = calibration

        # Move stages w.r.t the ordering.
        for orientation in ordering:
            if orientation not in movement_commands:
                continue

            calibration = resolved_calibrations[orientation]
            requested_target = movement_commands[orientation]

            with calibration.perform_in_chip_coordinates():
                calibration.move_relative(requested_target, wait_for_stopping)

    @contextmanager
    def lift_stages(self):
        """
        Lifts the stages to the configured value before the block is executed and lowers the stages again after the block.

        Performs movement in chip coordinates.
        Performs NO safe movement (i.e no Path planning)
        """

        def _toggle_stage_lift():
            """
            Moves all stages to z lift level.
            Moves up if stages_are_lifted is false and vice versa.
            """
            for calibration in self.calibrations.values():
                _is_lifted = calibration in self._lifted_stages
                target_z = self.z_lift if not _is_lifted else 0
                with calibration.perform_in_chip_coordinates():
                    stage_start_pos = calibration.get_position()
                    target_coordinate = ChipCoordinate(
                        x=stage_start_pos.x, y=stage_start_pos.y, z=target_z)
                    try:
                        calibration.move_absolute(
                            target_coordinate, wait_for_stopping=True)
                    finally:
                        stage_end_pos = calibration.get_position()
                        lift_delta = stage_end_pos - stage_start_pos

                        if not np.isclose(
                                lift_delta.to_numpy(),
                                np.array([0, 0, target_z]),
                                rtol=1e-05,
                                atol=1e-08).all():
                            self.logger.error(
                                f"{calibration} didn't not move properly to {target_z} while lifting/lowering stage.")
                        
                        if _is_lifted:
                            self._lifted_stages.remove(calibration)
                        else:
                            self._lifted_stages.add(calibration)

        _toggle_stage_lift()
        try:
            yield
        finally:
            _toggle_stage_lift()

    @assert_connected_stages
    def move_to_device(self, chip: Type[Chip], device: Type[Device]):
        """
        Moves stages to device.

        Parameters
        ----------
        chip: Chip
            Instance of a imported chip.
        device: Device
            Device to which the stages should move.

        Raises
        ------
        MoverError
            If no device was found for the given ID.
        """
        # Set up movement commands
        # A movement command orders a calibration to move to a certain
        # coordinate (here device port coordinates)
        movement_commands = {}
        if self.input_calibration:
            movement_commands[self.input_calibration.orientation] = device.input_coordinate
        if self.output_calibration:
            movement_commands[self.output_calibration.orientation] = device.output_coordinate

        with self.lift_stages():
            self.move_absolute(movement_commands, chip=chip)

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

        with open(self.CALIBRATIONS_SETTINGS_FILE, "w+") as fp:
            json.dump({
                "chip_name": _chip_name,
                "last_updated_at": datetime.now().isoformat(),
                "calibrations": [
                    c.dump() for c in self.calibrations.values()]
            }, fp)

    def dump_settings(self) -> None:
        """
        Stores mover settings to file.
        """
        with open(self.MOVER_SETTINGS_FILE, "w+") as fp:
            json.dump({
                "speed_xy": self._speed_xy,
                "speed_z": self._speed_z,
                "acceleration_xy": self._acceleration_xy,
                "z_lift": self._z_lift
            }, fp)

    def has_chip_stored_calibration(self, chip: Type[Chip]) -> bool:
        """
        Checks if for given chip exists a stored calibration.
        """
        if chip is None or chip.name is None:
            return False

        if not exists(self.CALIBRATIONS_SETTINGS_FILE):
            return False

        with open(self.CALIBRATIONS_SETTINGS_FILE, "r") as fp:
            try:
                calibration_settings = json.load(fp)
            except json.JSONDecodeError:
                return False
            _chip_name = calibration_settings.get("chip_name")
            _calibrations = calibration_settings.get("calibrations", [])
            return _chip_name == chip.name and len(_calibrations) > 0

    @property
    def calibration_settings_file(self) -> str:
        """
        Returns the calibration settings file.
        """
        return self.CALIBRATIONS_SETTINGS_FILE

    #
    #   Helpers
    #

    def _get_calibration(
            self,
            port=None,
            orientation=None,
            default=None) -> Type[Calibration]:
        """
        Get safely calibration by port and orientation.
        """
        orientation = orientation or self._port_by_orientation.inverse.get(
            port)
        port = port or self._port_by_orientation.get(orientation)
        return self.calibrations.get((orientation, port), default)
