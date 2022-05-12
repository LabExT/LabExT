#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Type, Union
from functools import wraps
from contextlib import contextmanager

from LabExT.Movement.config import DevicePort, Orientation, State, Axis, Direction
from LabExT.Movement.Transformations import StageCoordinate, ChipCoordinate, CoordinatePairing, SinglePointOffset, AxesRotation, KabschRotation
from LabExT.Movement.Stage import StageError


if TYPE_CHECKING:
    from LabExT.Movement.Stage import Stage


class CalibrationError(RuntimeError):
    pass


def assert_minimum_state_for_coordinate_system(
    chip_coordinate_system=None,
    stage_coordinate_system=None
):
    """
    Decorator to require a minimum calibration state to perform the given function in the given coordinate system.

    Parameters
    ----------
    chip_coordinate_system : State
        Minimum state to execute the method in the chip coordinate system.
    stage_coordinate_system : State
        Minimum state to execute the method in the stage coordinate system.
    """
    def assert_state(func):
        @wraps(func)
        def wrap(calibration: Type[Calibration], *args, **kwargs):
            if calibration.coordinate_system is None:
                raise CalibrationError(
                    "Function {} needs a cooridnate system to operate in. Please use the context to set the system.".format(
                        func.__name__))

            if calibration.coordinate_system == ChipCoordinate and calibration.state < chip_coordinate_system:
                raise CalibrationError(
                    "Function {} needs at least a calibration state of {} to operate in chip coordinate system".format(
                        func.__name__, chip_coordinate_system))

            if calibration.coordinate_system == StageCoordinate and calibration.state < stage_coordinate_system:
                raise CalibrationError(
                    "Function {} needs at least a calibration state of {} to operate in stage coordinate system".format(
                        func.__name__, stage_coordinate_system))

            return func(calibration, *args, **kwargs)
        return wrap
    return assert_state


class Calibration:
    """
    Represents a calibration of one stage.
    """

    def __init__(self, mover, stage, orientation, device_port) -> None:
        self.mover = mover
        self.stage: Type[Stage] = stage

        self._state = State.CONNECTED if stage.connected else State.UNINITIALIZED
        self._orientation = orientation
        self._device_port = device_port

        self._coordinate_system = None

        self._axes_rotation: Type[AxesRotation] = AxesRotation()
        self._single_point_offset: Type[SinglePointOffset] = SinglePointOffset(self._axes_rotation)
        self._kabsch_rotation: Type[KabschRotation] = KabschRotation()

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
    #   Coordinate System Control
    #

    @property
    def coordinate_system(
            self) -> Union[None, StageCoordinate, ChipCoordinate]:
        """
        Returns the current coordinate system
        """
        return self._coordinate_system

    @coordinate_system.setter
    def coordinate_system(self, system) -> None:
        """
        Sets the current coordinate system

        If None, the system will be reset.

        Parameters
        ----------
        system : Coordinate
            Coordinate system to be stored, either chip or stage system.

        Raises
        ------
        ValueError
            If the requested system is not supported.
        CalibrationError
            If a coordinate system is already set.
        """
        if system is None:
            self._coordinate_system = None
            return

        if system not in [ChipCoordinate, StageCoordinate]:
            raise ValueError(
                f"The requested coordinate system {system} is not supported.")

        if self._coordinate_system is not None:
            raise CalibrationError("A coordinate system is already set.")

        self._coordinate_system = system

    @contextmanager
    def perform_in_chip_coordinates(self):
        """
        Context manager to execute a block of instructions in chip coordinates.

        Sets the coordinate system to chip system first and resets the system at the end.
        """
        self.coordinate_system = ChipCoordinate
        try:
            yield
        finally:
            self.coordinate_system = None

    @contextmanager
    def perform_in_stage_coordinates(self):
        """
        Context manager to execute a block of instructions in stage coordinates.

        Sets the coordinate system to stage system first and resets the system at the end.
        """
        self.coordinate_system = StageCoordinate
        try:
            yield
        finally:
            self.coordinate_system = None

    #
    #   Calibration Setup Methods
    #

    def connect_to_stage(self) -> None:
        """
        Opens a connection to the stage.
        """
        try:
            self.stage.connect()
        finally:
            self.determine_state(skip_connection=False)

    def disconnect_to_stage(self) -> None:
        """
        Closes the connection to the stage.
        """
        try:
            self.stage.disconnect()
        finally:
            self.determine_state(skip_connection=False)

    def update_axes_rotation(
            self,
            chip_axis: Axis,
            direction: Direction,
            stage_axis: Axis) -> None:
        """
        Updates the axis rotation of the calibration.
        After the update, the state of the calibration is recalculated.

        Parameters
        ----------
        chip_axis: Axis
            Chip Axis which is to be assigned a Stage Axis.
            The value of the enum defines which column of the rotation matrix is to be changed.
        direction: Direction
            Defines the direction of the assigned stage axis.
        stage_axis: Axis
            Stage Axis which is to be assigned to the Chip Axis.
            The value of the enum defines which row of the rotation matrix is to be changed.
        """
        try:
            self._axes_rotation.update(chip_axis, direction, stage_axis)
        finally:
            self.determine_state(skip_connection=True)

    def update_single_point_offset(
            self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the single point offset transformation of the calibration.
        After the update, the state of the calibration is recalculated.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate
        """
        try:
            self._single_point_offset.update(pairing)
        finally:
            self.determine_state(skip_connection=True)

    def update_kabsch_rotation(self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the kabsch transformation of the calibration.
        After the update, the state of the calibration is recalculated.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate
        """
        try:
            self._kabsch_rotation.update(pairing)
        finally:
            self.determine_state(skip_connection=True)

    def determine_state(self, skip_connection=False) -> None:
        """
        Determines the status of the calibration independently of the status variables of the instance.
        1. Checks whether the stage responds. If yes, status is at least CONNECTED.
        2. Checks if axis rotation is valid. If Yes, status is at least COORDINATE SYSTEM FIXED.
        3. Checks if single point fixation is valid. If Yes, status is at least SINGLE POINT FIXED.
        4. Checks if full calibration is valid. If Yes, status is FULLY CALIBRATED.
        """
        # Reset state
        self._state = State.UNINITIALIZED

        # 1. Check if stage responds
        if self.stage is None:
            return

        if not skip_connection:
            try:
                if not self.stage.connected or self.stage.get_status() is None:
                    return
                self._state = State.CONNECTED
            except StageError:
                return
        else:
            self._state = State.CONNECTED

        # 2. Check if axis rotation is valid
        if not self._axes_rotation or not self._axes_rotation.is_valid:
            return
        self._state = State.COORDINATE_SYSTEM_FIXED

        # 3. Check if single point fixation is valid
        if not self._single_point_offset or not self._single_point_offset.is_valid:
            return
        self._state = State.SINGLE_POINT_FIXED

        # 4. Check if Full Calibration is valid
        if not self._kabsch_rotation or not self._kabsch_rotation.is_valid:
            return

        self._state = State.FULLY_CALIBRATED
