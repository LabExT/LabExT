#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from enum import Enum, auto

from LabExT.Movement.Transformations import SinglePointFixation
from LabExT.Movement.Stage import StageError


class Orientation(Enum):
    """
    Enumerate different state orientations.
    """
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()

    def __str__(self) -> str:
        return self.name.capitalize()


class DevicePort(Enum):
    """Enumerate different device ports."""
    INPUT = auto()
    OUTPUT = auto()

    def __str__(self) -> str:
        return self.name.capitalize()


class State(Enum):
    """
    Enumerate different calibration states.
    """
    UNINITIALIZED = 0
    CONNECTED = 1
    COORDINATE_SYSTEM_FIXED = 2
    SINGLE_POINT_FIXED = 3
    FULLY_CALIBRATED = 4

    def __str__(self) -> str:
        return self.name.replace('_', ' ').capitalize()


class Calibration:
    """
    Represents a calibration of one stage.
    """

    def __init__(self, mover, stage, orientation, device_port) -> None:
        self.mover = mover
        self.stage = stage

        self._state = State.CONNECTED if stage.connected else State.UNINITIALIZED
        self._orientation = orientation
        self._device_port = device_port

        self._axes_rotation = None
        self._single_point_fixation = None

    #
    #   Representation
    #

    def __str__(self) -> str:
        return "{} Stage ({})".format(str(self.orientation), str(self.stage))

    @property
    def short_str(self) -> str:
        return "{} Stage ({})".format(
            str(self.orientation), str(self._device_port))

    #
    #   Properties
    #

    @property
    def state(self) -> State:
        """
        Returns the current calibration state.
        """
        return self._state

    @property
    def orientation(self) -> Orientation:
        """
        Returns the orientation of the stage: Left, Right, Top or Bottom
        """
        return self._orientation

    @property
    def is_input_stage(self):
        """
        Returns True if the stage will move to the input of a device.
        """
        return self._device_port == DevicePort.INPUT

    @property
    def is_output_stage(self):
        """
        Returns True if the stage will move to the output of a device.
        """
        return self._device_port == DevicePort.OUTPUT

    #
    #   Calibration Setup Methods
    #

    def connect_to_stage(self) -> bool:
        """
        Opens a connections to the stage.
        """
        try:
            if self.stage.connect():
                self._state = State.CONNECTED
                return True
        except StageError as e:
            self._state = State.UNINITIALIZED
            raise e

        return False

    def fix_coordinate_system(self, axes_rotation: Type[AxesRotation]) -> bool:
        if not axes_rotation.is_valid:
            raise CalibrationError(
                "The given axis assignment does not define a valid 90 degree rotation. ")

        self._axes_rotation = axes_rotation
        self._state = State.COORDINATE_SYSTEM_FIXED

        return True

    def fix_single_point(
            self,
            single_point_fixation: Type[SinglePointFixation]):
        if not single_point_fixation.is_valid:
            raise CalibrationError(
                "The given fixation is no valid. ")

        self._single_point_fixation = single_point_fixation
        self._state = State.SINGLE_POINT_FIXED

        return True

    #
    #   Movement Methods
    #

    def wiggle_axis(
            self,
            axis: Axis,
            axes_rotation: Type[AxesRotation],
            wiggle_distance=1e3,
            wiggle_speed=1e3):
        """
        Wiggles the requested axis positioner in order to enable the user to test the correct direction and axis mapping.
        """
        x_stage, y_stage, z_stage = axes_rotation.chip_to_stage(np.array([
            wiggle_distance if axis == Axis.X else 0,
            wiggle_distance if axis == Axis.Y else 0,
            wiggle_distance if axis == Axis.Z else 0
        ]))

        current_speed_xy = self.stage.get_speed_xy()
        current_speed_z = self.stage.get_speed_z()

        self.stage.set_speed_xy(wiggle_speed)
        self.stage.set_speed_z(wiggle_speed)

        self.stage.move_relative(x_stage, y_stage, z_stage)
        time.sleep(2)
        self.stage.move_relative(-x_stage, -y_stage, -z_stage)

        self.stage.set_speed_xy(current_speed_xy)
        self.stage.set_speed_z(current_speed_z)
