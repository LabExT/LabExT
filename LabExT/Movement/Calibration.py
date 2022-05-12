#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import Type, Union
from functools import wraps
from contextlib import contextmanager

from LabExT.Movement.config import DevicePort, Orientation, State
from LabExT.Movement.Transformations import StageCoordinate, ChipCoordinate, SinglePointOffset, AxesRotation, KabschRotation
from LabExT.Movement.Stage import StageError


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
        self.stage = stage

        self._state = State.CONNECTED if stage.connected else State.UNINITIALIZED
        self._orientation = orientation
        self._device_port = device_port

        self._corrdinate_system = None

        self._axes_rotation: Type[AxesRotation] = None
        self._single_point_offset: Type[SinglePointOffset] = None
        self._kabsch_rotation: Type[KabschRotation] = None

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
        return self._corrdinate_system

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
