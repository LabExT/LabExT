#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from contextlib import contextmanager
from time import sleep
from bidict import bidict, ValueDuplicationError, KeyDuplicationError, OnDup, RAISE
from typing import Dict, Type, List
from functools import wraps
from LabExT.Movement.PathPlanning import PathPlanning
from LabExT.Movement.Transformations import ChipCoordinate

from LabExT.Movement.config import Orientation, DevicePort
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.Stage import Stage
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

    def __init__(self, experiment_manager):
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager.
        """
        self.experiment_manager = experiment_manager

        self._stage_classes: List[Stage] = []
        self._available_stages: List[Type[Stage]] = []

        # Mover state
        self._calibrations = bidict()
        self._port_by_orientation = bidict()
        self._speed_xy = None
        self._speed_z = None
        self._acceleration_xy = None
        self._z_lift = None

        self.stages_lifted = False

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
    def calibrations(self):
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
    def z_lift(self):
        """
        Returns the set value of how much the stage moves up
        :return: how much the stage moves up [um]
        """
        return self._z_lift

    @z_lift.setter
    def z_lift(self, lift):
        """
        Sets the value of how much the stage moves up
        :param height: how much the stage moves up [um]
        """
        lift = float(lift)
        assert lift >= 0.0, "Lift distance must be non-negative."
        self._z_lift = lift

    @contextmanager
    def perform_in_chip_coordinates(self):
        """
        Context manager to execute a block of instructions in chip coordinates 
        for all defined calibrations.
        """
        for calibration in self.calibrations.values():
            calibration.coordinate_system = ChipCoordinate
        
        try:
            yield
        finally:
            for calibration in self.calibrations.values():
                calibration.coordinate_system = None


    @assert_connected_stages
    def move_absolute(
        self,
        movement_commands: Dict[Orientation, Type[ChipCoordinate]],
        chip: Type[Chip] = None
    ) -> None:
        """
        Moves the stages absolutely in the chip coordinate system.

        If a PathPlanning instance is passed, it is used to calculate a collision-free path.

        Parameters
        ----------
        movement_commands : Dict[Orientation, Type[ChipCoordinate]]
            A mapping between orientation and target chip coordinate.
            For example, if the mapping `Orientation.LEFT: ChipCoordinate(1,2,3)` exists, the left stage is moved to the chip co-ordinate x=1, y=2, z=3
        path_planning : PathPlanning
            PathPlanning instance for waypoint calculation.

        Raises
        ------
        MoverError
            If an orientation has been given a target, but no stage exists for this orientation.
        """
        for target_orient in movement_commands.keys():
            if not target_orient in self._port_by_orientation.keys():
                raise MoverError(f"No {target_orient} stage configured, but target coordinate for {target_orient} passed.")


        with self.perform_in_chip_coordinates():

            # left_cali = movement_commands[Orientation.LEFT]

            # PathPlanning({

            # })

            planning = PathPlanning(
                start_goal_coordinates={
                    o: (self._get_calibration(orientation=o).get_position(), target) for o, target in movement_commands.items()
                },
                chip=chip)

            for waypoints in planning.waypoints():
                for orientation, waypoint in waypoints.items():
                    waypoint.z = self.z_lift
                    self._get_calibration(orientation=orientation).move_absolute(waypoint)
        
        # with self.perform_in_chip_coordinates():
        #     for orient, target in movement_commands.items():
        #         self._get_calibration(orientation=orient).move_absolute(target)


    def move_to_device(self, chip: Type[Chip], device_id: int):
        """
        Moves stages to device.
        """
        device = chip._devices.get(device_id)
        if device is None:
            raise MoverError

        self.lower_or_lift_stages()

        movement_commands = {}
        if self.input_calibration:
            movement_commands[self.input_calibration.orientation] = device.input_coordinate
        if self.output_calibration:
            movement_commands[self.output_calibration.orientation] = device.output_coordinate
        
        self.move_absolute(movement_commands, chip=chip)

        self.lower_or_lift_stages()


    def lower_or_lift_stages(self):
        """
        Lifts or lowers input and output stage (if defined) by the configured z_lift value.

        Performs movement in chip coordinates.

        Performs NO safe movement.
        """
        stage_offset = ChipCoordinate(0,0,-self.z_lift if self.stages_lifted else self.z_lift)
        with self.perform_in_chip_coordinates():
            if self.input_calibration:
                self.input_calibration.move_absolute(
                    coordinate=self.input_calibration.get_position() + stage_offset,
                    wait_for_stopping=True)

            if self.output_calibration:
                self.output_calibration.move_absolute(
                    coordinate=self.output_calibration.get_position() + stage_offset,
                    wait_for_stopping=True)

        self.stages_lifted = not self.stages_lifted

    #
    #   Helpers
    #

    def _get_calibration(self, port=None, orientation=None, default=None) -> Type[Calibration]:
        """
        Get safely calibration by port and orientation.
        """
        orientation = orientation or self._port_by_orientation.inverse.get(
            port)
        port = port or self._port_by_orientation.get(orientation)
        return self.calibrations.get((orientation, port), default)