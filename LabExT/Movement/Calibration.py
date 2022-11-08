#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from __future__ import annotations
import logging

from typing import TYPE_CHECKING, Type, Union
from functools import wraps
from contextlib import contextmanager
from time import sleep

import numpy as np

from LabExT.Movement.config import DevicePort, Orientation, State, Axis, Direction, CoordinateSystem
from LabExT.Movement.Transformations import StageCoordinate, ChipCoordinate, CoordinatePairing, SinglePointOffset, AxesRotation, KabschRotation
from LabExT.Movement.Stage import StageError
from LabExT.Movement.PathPlanning import StagePolygon, SingleModeFiber

if TYPE_CHECKING:
    from LabExT.Movement.Stage import Stage
    from LabExT.Movement.MoverNew import MoverNew
    from LabExT.Wafer.Chip import Chip


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
            if calibration.coordinate_system == CoordinateSystem.UNKNOWN:
                raise CalibrationError(
                    "Function {} needs a cooridnate system to operate in. Please use the context to set the system.".format(
                        func.__name__))

            if calibration.coordinate_system == CoordinateSystem.CHIP and calibration.state < chip_coordinate_system:
                raise CalibrationError(
                    "Function {} needs at least a calibration state of {} to operate in chip coordinate system".format(
                        func.__name__, chip_coordinate_system))

            if calibration.coordinate_system == CoordinateSystem.STAGE and calibration.state < stage_coordinate_system:
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

    _logger = logging.getLogger()

    @classmethod
    def load(
        cls,
        mover: Type[MoverNew],
        stage: Type[Stage],
        calibration_data: dict,
        chip: Type[Chip] = None
    ) -> Type[Calibration]:
        """
        Creates a new calibration based on calibration data.

        Parameters
        ----------
        mover : Mover
            Instance of mover associated with this calibration.
        stage : Stage
            Instance of a stage
        calibration_data : dict
            Dumped calibration data

        Returns
        -------
        Calibration
            Instance of calibration
        """
        try:
            orientation = Orientation[calibration_data["orientation"]]
            device_port = DevicePort[calibration_data["device_port"]]
        except KeyError as err:
            raise CalibrationError(
                f"The parameter is not defined: {err}. "
                "Make sure to pass a valid orientation and device port.")

        axes_rotation = None
        if "axes_rotation" in calibration_data:
            axes_rotation = AxesRotation.load(
                calibration_data["axes_rotation"])

        single_point_offset = None
        if "single_point_offset" in calibration_data:
            if axes_rotation is not None and chip is not None:
                single_point_offset = SinglePointOffset.load(
                    calibration_data["single_point_offset"], chip=chip, axes_rotation=axes_rotation)
            else:
                cls._logger.debug(
                    "Cannot set single point offset when axes rotation or chip is not defined")

        kabsch_rotation = None
        if "kabsch_rotation" in calibration_data:
            if axes_rotation is not None and chip is not None:
                kabsch_rotation = KabschRotation.load(
                    calibration_data["kabsch_rotation"], chip=chip, axes_rotation=axes_rotation)
            else:
                cls._logger.debug(
                    "Cannot set kabsch rotation when axes rotation or chip is not defined")

        return cls(
            mover,
            stage,
            orientation,
            device_port,
            axes_rotation,
            single_point_offset,
            kabsch_rotation)

    def __init__(
        self,
        mover: Type[MoverNew],
        stage: Type[Stage],
        orientation: Orientation,
        device_port: DevicePort,
        axes_rotation: Type[AxesRotation] = None,
        single_point_offset: Type[SinglePointOffset] = None,
        kabsch_rotation: Type[KabschRotation] = None
    ) -> None:
        self.mover = mover
        self.stage: Type[Stage] = stage

        self.stage_polygon: Type[StagePolygon] = SingleModeFiber(orientation)

        self._orientation = orientation
        self._device_port = device_port

        self._coordinate_system = CoordinateSystem.UNKNOWN

        self._axes_rotation = axes_rotation
        if axes_rotation is None:
            self._axes_rotation = AxesRotation()

        self._single_point_offset = single_point_offset
        if single_point_offset is None:
            self._single_point_offset = SinglePointOffset(self._axes_rotation)

        self._kabsch_rotation = kabsch_rotation
        if kabsch_rotation is None:
            self._kabsch_rotation = KabschRotation(self._axes_rotation)

        assert self._single_point_offset.axes_rotation == self._axes_rotation, "Axes rotation for single point offset must be the same than for the calibration."
        assert self._kabsch_rotation.axes_rotation == self._axes_rotation, "Axes rotation for kabsch rotation must be the same than for the calibration"

        self._state = State.UNINITIALIZED
        self.determine_state(skip_connection=False)
        self.mover.update_main_model()

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
    def coordinate_system(self) -> CoordinateSystem:
        """
        Returns the current coordinate system
        """
        return self._coordinate_system

    @property
    def is_chip_coordinate_system_set(self) -> bool:
        """
        Returns True if chip coordinate system is set.
        """
        return self.coordinate_system == CoordinateSystem.CHIP

    @property
    def is_stage_coordinate_system_set(self) -> bool:
        """
        Returns True if stage coordinate system is set.
        """
        return self.coordinate_system == CoordinateSystem.STAGE

    def set_coordinate_system(
        self,
        system: CoordinateSystem
    ) -> None:
        """
        Sets the current coordinate system

        Raises
        ------
        ValueError
            If the requested system is not supported.
        """
        if not isinstance(system, CoordinateSystem):
            raise ValueError(
                f"Requested coordinate system {system} for {self} is invalid.")

        self._logger.debug(
            f"Set coordinate system for {self} to {system}")

        self._coordinate_system = system

    @contextmanager
    def perform_in_system(self, system: CoordinateSystem):
        """
        Context manager to execute a block of instructions in requested coordinates.

        Resets the system at the end.
        """
        prior_coordinate_system = self.coordinate_system

        self.set_coordinate_system(system)
        try:
            yield
        finally:
            self.set_coordinate_system(prior_coordinate_system)

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
            self.mover.update_main_model()

    def disconnect_to_stage(self) -> None:
        """
        Closes the connection to the stage.
        """
        try:
            self.stage.disconnect()
        finally:
            self.determine_state(skip_connection=False)
            self.mover.update_main_model()

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
            self.mover.update_main_model()

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
            self.mover.update_main_model()

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
            self.mover.update_main_model()

    def reset_single_point_offset(self) -> None:
        """
        Resets the single point offset transformation
        """
        self._single_point_offset.initialize()
        self.determine_state(skip_connection=True)
        self.mover.update_main_model()

    def reset_kabsch_rotation(self) -> None:
        """
        Resets the kabsch rotation
        """
        self._kabsch_rotation.initialize()
        self.determine_state(skip_connection=True)
        self.mover.update_main_model()

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

        if self.is_stage_coordinate_system_set:
            return stage_position
        elif self.is_chip_coordinate_system_set:
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
        RuntimeError
            If coordinate system is unsupported.
        """
        if self.is_stage_coordinate_system_set:
            stage_offset = offset
        elif self.is_chip_coordinate_system_set:
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
        RuntimeError
            If coordinate system is unsupported.
        """
        if self.is_stage_coordinate_system_set:
            stage_coordinate = coordinate
        elif self.is_chip_coordinate_system_set:
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

        with self.perform_in_system(CoordinateSystem.CHIP):
            self.move_relative(ChipCoordinate.from_numpy(wiggle_difference))
            sleep(wait_time)
            self.move_relative(ChipCoordinate.from_numpy(-wiggle_difference))

        self.stage.set_speed_xy(current_speed_xy)
        self.stage.set_speed_z(current_speed_z)

    def dump(self) -> dict:
        """
        Returns a dict of all calibration properties.
        """
        calibration_dump = {
            "orientation": self.orientation.value,
            "device_port": self._device_port.value}

        if self._axes_rotation.is_valid:
            calibration_dump["axes_rotation"] = self._axes_rotation.dump()

        if self._single_point_offset.is_valid:
            calibration_dump["single_point_offset"] = self._single_point_offset.dump(
            )

        if self._kabsch_rotation.is_valid:
            calibration_dump["kabsch_rotation"] = self._kabsch_rotation.dump()

        return calibration_dump
