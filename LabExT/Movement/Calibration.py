#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time
from typing import Type
import numpy as np

from enum import Enum, auto
from LabExT.Movement.Stage import StageError


class CalibrationError(RuntimeError):
    pass

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


class Axis(Enum):
    """Enumerate different channels. Each channel represents one axis."""
    X = 0
    Y = 1
    Z = 2

    def __str__(self) -> str:
        return "{}-Axis".format(self.name)


class Direction(Enum):
    """
    Enumerate different axis directions.
    """
    POSITIVE = 1
    NEGATIVE = -1

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


class AxesRotation:
    """
    Assigns a stage axis (X,Y,Z) to the positive chip axes (X,Y,Z) with associated direction.
    If the assignment is well defined, a rotation matrix is calculated, which rotates the given chip coordinate perpendicular to the stage coordinate.
    The rotation matrix (3x3) is therefore a signed permutation matrix of the coordinate axes of the chip.

    Each row of the matrix represents a chip axis. Each column of the matrix represents a stage axis.

    (i,j) = 1 iff positive Chip-Axis i is used for positive Stage-Axis j, where i,j in [X,Y,Z]
    (i,j) = -1 iff negative Chip-Axis i is used for negatitve Stage-Axis j, where i,j in [X,Y,Z]
    """
    def __init__(self) -> None:
        self._n = len(Axis) # 3, if we not inventing a new dimension
        self._matrix = np.identity(len(Axis)) # 3x3 identity matrix

    def update(self, chip_axis: Axis, stage_axis: Axis, direction: Direction):
        """
        Updates the axes rotation matrix.
        Resets all mappings for given chip axis and sets entry for (stage_axis, chip_axis) with given direction.
        """
        if not (isinstance(chip_axis, Axis) and isinstance(stage_axis, Axis)):
            raise ValueError("Unknown axes given for calibration.")

        if not isinstance(direction, Direction):
            raise ValueError("Unknown direction given for calibration.")

        self._matrix[:,chip_axis.value] = np.eye(1,3,stage_axis.value) * direction.value

    @property
    def is_valid(self):
        """
        Checks if given matrix is a permutation matrix.

        A matrix is a permutation matrix if the sum of each row and column is exactly 1.
        """
        abs_matrix = np.absolute(self._matrix)
        return (abs_matrix.sum(axis=0) == 1).all() and (abs_matrix.sum(axis=1) == 1).all()


    def chip_to_stage(self, chip_coordinate):
        """
        Rotates the chip cooridnate (x,y,z) according to the axes calibration.

        Raises CalibrationError error if matrix is not valid.
        """
        if not self.is_valid:
            raise CalibrationError("The current axis assignment does not define a valid 90 degree rotation. ")

        return self._matrix.dot(np.array(chip_coordinate))



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
            raise CalibrationError("The given axis assignment does not define a valid 90 degree rotation. ")
        
        self._axes_rotation = axes_rotation
        self._state = State.COORDINATE_SYSTEM_FIXED

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
