#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from __future__ import annotations
import inspect

from typing import TYPE_CHECKING, Type, Union
from functools import wraps
from contextlib import contextmanager
from time import sleep
from importlib import import_module

import numpy as np

from tkinter import messagebox

from LabExT.Movement.config import DevicePort, Orientation, State, Axis, Direction
from LabExT.Movement.Transformations import StageCoordinate, ChipCoordinate, CoordinatePairing, SinglePointOffset, AxesRotation, KabschRotation
from LabExT.Movement.Stage import StageError
from LabExT.Movement.PathPlanning import StagePolygon, SingleModeFiber

if TYPE_CHECKING:
    from LabExT.Movement.Stage import Stage
    from LabExT.Movement.MoverNew import MoverNew


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
        def wrap(calibration: Type["Calibration"], *args, **kwargs):
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

    @classmethod
    def from_file_format(
            cls,
            mover,
            calibration_settings: dict) -> Type[Calibration]:
        """
        Creates a calibration from settings.
        """
        stages_module = import_module(calibration_settings["stage_module"])
        stage_cls = getattr(stages_module, calibration_settings["stage_cls"])
        stage = stage_cls(address=calibration_settings["stage_address"])

        if calibration_settings["axes_rotation"]:
            axes_rotation = AxesRotation.from_storable_format(
                calibration_settings["axes_rotation"])

            if calibration_settings["single_point_offset"]:
                single_point_offset = SinglePointOffset.from_storable_format(
                    axes_rotation, calibration_settings["single_point_offset"])
            else:
                single_point_offset = None

            if calibration_settings["kabsch_rotation"]:
                kabsch_rotation = KabschRotation.from_storable_format(
                    calibration_settings["kabsch_rotation"])
            else:
                kabsch_rotation = None
        else:
            axes_rotation = None

        return cls(
            mover,
            stage,
            orientation=Orientation[calibration_settings["orientation"]],
            device_port=DevicePort[calibration_settings["device_port"]],
            axes_rotation=axes_rotation,
            single_point_offset=single_point_offset,
            kabsch_rotation=kabsch_rotation)

    def __init__(
        self,
        mover,
        stage,
        orientation: Orientation,
        device_port: DevicePort,
        axes_rotation: Type[AxesRotation] = None,
        single_point_offset: Type[SinglePointOffset] = None,
        kabsch_rotation: Type[KabschRotation] = None
    ) -> None:
        self.mover: Type[MoverNew] = mover
        self.stage: Type[Stage] = stage

        self.stage_polygon: Type[StagePolygon] = SingleModeFiber(orientation)

        self._state = State.CONNECTED if stage.connected else State.UNINITIALIZED
        self._orientation = orientation
        self._device_port = device_port

        self._coordinate_system = None

        self._axes_rotation = axes_rotation if axes_rotation else AxesRotation()
        self._single_point_offset = single_point_offset if single_point_offset else SinglePointOffset(
            self._axes_rotation)
        self._kabsch_rotation = kabsch_rotation if kabsch_rotation else KabschRotation(self._axes_rotation)

    #
    #   Representation
    #

    def __str__(self) -> str:
        return "{} Stage ({})".format(str(self.orientation), str(self.stage))

    @property
    def short_str(self) -> str:
        return "{} Stage ({})".format(
            str(self.orientation), str(self._device_port))

    def to_file_format(self) -> dict:
        """
        Returns the calibration into file format.
        """
        return {
            "stage_module": inspect.getmodule(
                self.stage).__name__,
            "stage_cls": self.stage.__class__.__name__,
            "stage_address": self.stage.address,
            "orientation": self.orientation.name,
            "device_port": self._device_port.name,
            "axes_rotation": self._axes_rotation.to_storable_format(),
            "single_point_offset": self._single_point_offset.to_storable_format(),
            "kabsch_rotation": self._kabsch_rotation.to_storable_format()}
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

    #
    #   Position method
    #

    @assert_minimum_state_for_coordinate_system(
        stage_coordinate_system=State.CONNECTED,
        chip_coordinate_system=State.SINGLE_POINT_FIXED)
    def get_position(
            self) -> Union[Type[StageCoordinate], Type[ChipCoordinate]]:
        """
        Method to read out the current position of the stage.
        This method can display the position in stage and chip coordinates,
        depending on the context in which this method is used.

        Returns
        -------
        position: StageCoordinate | ChipCoordinate
            Position of the stage in chip or stage coordinates.

        Raises
        ------
        CalibrationError
            If the state of calibration is lower than the required one.
        RuntimeError
            If coordinate system is unsupported.
        """
        stage_position = StageCoordinate.from_list(self.stage.get_position())

        if self.coordinate_system == StageCoordinate:
            return stage_position
        elif self.coordinate_system == ChipCoordinate:
            if self.state == State.FULLY_CALIBRATED:
                return self._kabsch_rotation.stage_to_chip(stage_position)
            elif self.state == State.SINGLE_POINT_FIXED:
                return self._single_point_offset.stage_to_chip(stage_position)
            else:
                raise CalibrationError(
                    "Insufficient calibration state to return the position in chip coordinates.")
        else:
            RuntimeError(
                f"Unsupported coordinate system {self.coordinate_system} to return the stage position")

    #
    #   Movement methods
    #

    @assert_minimum_state_for_coordinate_system(
        stage_coordinate_system=State.CONNECTED,
        chip_coordinate_system=State.COORDINATE_SYSTEM_FIXED)
    def move_relative(self,
                      offset: Union[Type[StageCoordinate],
                                    Type[ChipCoordinate]],
                      wait_for_stopping: bool = True) -> None:
        """
        Moves the stage relative in its coordinate system.
        The offset can be passed a stage or chip coordinate,
        depending on the context in which this method is used.

        Parameters
        ----------
        offset: StageCoordinate | ChipCoordinate
            Relative offset in stage or chip coordinates.

        Raises
        ------
        CalibrationError
            If the state of calibration is lower than the required one.
        TypeError
            If the passed offset does not have the correct type.
        RuntimeError
            If coordinate system is unsupported.
        """
        if not isinstance(offset, self.coordinate_system):
            raise TypeError(
                f"Given offset is in {type(offset)}. Need offset in {self.coordinate_system} to move the stage relative in this system.")

        if self.coordinate_system == StageCoordinate:
            stage_offset = offset
        elif self.coordinate_system == ChipCoordinate:
            stage_offset = self._axes_rotation.chip_to_stage(offset)
        else:
            RuntimeError(
                f"Unsupported coordinate system {self.coordinate_system} to move the stage relatively.")

        self.stage.move_relative(
            x=stage_offset.x,
            y=stage_offset.y,
            z=stage_offset.z,
            wait_for_stopping=wait_for_stopping)

    @assert_minimum_state_for_coordinate_system(
        stage_coordinate_system=State.CONNECTED,
        chip_coordinate_system=State.SINGLE_POINT_FIXED)
    def move_absolute(self,
                      coordinate: Union[Type[StageCoordinate],
                                        Type[ChipCoordinate]],
                      wait_for_stopping: bool = True) -> None:
        """
        Moves the stage absolute to the given coordinate.
        The coordinate can be passed in stage or chip coordinates,
        depending on the coordinate system in which this method is called.

        Parameters
        ----------
        coordinate: StageCoordinate | ChipCoordinate
            Coordinate offset in stage or chip coordinates.

        Raises
        ------
        CalibrationError
            If the state of calibration is lower than the required one.
        TypeError
            If the passed offset does not have the correct type.
        RuntimeError
            If coordinate system is unsupported.
        """
        if not isinstance(coordinate, self.coordinate_system):
            raise TypeError(
                f"Given coordinate is in {type(coordinate)}. Need coordinate in {self.coordinate_system} to move the stage absolute in this system.")

        if self.coordinate_system == StageCoordinate:
            stage_coordinate = coordinate
        elif self.coordinate_system == ChipCoordinate:
            if self.state == State.FULLY_CALIBRATED:
                stage_coordinate = self._kabsch_rotation.chip_to_stage(
                    coordinate)
            elif self.state == State.SINGLE_POINT_FIXED:
                stage_coordinate = self._single_point_offset.chip_to_stage(
                    coordinate)
            else:
                raise CalibrationError(
                    "Insufficient calibration state to move the stage absolutely.")
        else:
            RuntimeError(
                f"Unsupported coordinate system {self.coordinate_system} to move the stage absolutely.")

        if self._allow_movement(coordinate, stage_coordinate):
            self.stage.move_absolute(
                x=stage_coordinate.x,
                y=stage_coordinate.y,
                z=stage_coordinate.z,
                wait_for_stopping=wait_for_stopping)

    def wiggle_axis(
            self,
            wiggle_axis: Axis,
            wiggle_distance: float = 1e3,
            wiggle_speed: float = 1e3,
            wait_time: float = 2) -> None:
        """
        Wiggles an axis of the stage.
        Moves the axis first in a positive direction then in a negative direction.
        This method can be used to check the axis rotation.
        This method is executed in chip coordinates.

        Parameters
        ----------
        wiggle_axis: Axis
            Axis to be wiggled.
        wiggle_distance: float = 1e3
            Specifies how much the axis should be moved in one direction [um].
        wiggle_speed: float = 1e3
            Specifies how fast the axis should be moved in one direction [um/s].
        wait_time: float = 2
            Specifies how long to wait between positive and negative movement [s].
        """
        current_speed_xy = self.stage.get_speed_xy()
        current_speed_z = self.stage.get_speed_z()

        self.stage.set_speed_xy(wiggle_speed)
        self.stage.set_speed_z(wiggle_speed)

        wiggle_difference = np.array(
            [wiggle_distance if wiggle_axis == axis else 0 for axis in Axis])
        with self.perform_in_chip_coordinates():
            self.move_relative(ChipCoordinate.from_numpy(wiggle_difference))
            sleep(wait_time)
            self.move_relative(ChipCoordinate.from_numpy(-wiggle_difference))

        self.stage.set_speed_xy(current_speed_xy)
        self.stage.set_speed_z(current_speed_z)

    def _allow_movement(self, chip_target, stage_target):
        stage_position = StageCoordinate.from_list(self.stage.get_position())

        if self.state == State.FULLY_CALIBRATED:
            chip_position = self._kabsch_rotation.stage_to_chip(stage_position)
        elif self.state == State.SINGLE_POINT_FIXED:
            chip_position = self._single_point_offset.stage_to_chip(
                stage_position)
        else:
            chip_position = None

        return messagebox.askyesno(
            title="Confirm Movement",
            message=f"Chip-Coordinates: \n -Current: {chip_position} \n -Target: {chip_target} \n -Delta: {chip_position - chip_target} \n\n" \
                f"Stage-Coordinates \n -Current: {stage_position} \n -Target: {stage_target} \n -Delta: {stage_position - stage_target}"
        )