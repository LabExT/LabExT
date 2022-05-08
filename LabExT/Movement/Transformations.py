#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, NamedTuple, Type
from abc import ABC, abstractmethod, abstractproperty
from functools import wraps
import numpy as np
from scipy.spatial.transform import Rotation

from LabExT.Movement.config import Axis, Direction

if TYPE_CHECKING:
    from LabExT.Movement.Calibration import Calibration
    from LabExT.Wafer.Chip import Chip


class Coordinate(ABC):
    """
    Abstract base class of a coordinate with X, Y and Z values.

    The base class cannot be initialised directly.
    """
    @classmethod
    def from_list(cls, list: list) -> Type[Coordinate]:
        """
        Returns a new coordinate, created from a list.
        """
        return cls(*list[:3])

    @classmethod
    def from_numpy(cls, array: np.ndarray) -> Type[Coordinate]:
        """
        Returns a new coordinate created from a one-dimensional numpy array.
        """
        if array.ndim != 1:
            raise ValueError("The given array is not a 1D-Array.")

        return cls(*array.tolist()[:3])

    @abstractmethod
    def __init__(self, x=0, y=0, z=0) -> None:
        """
        Constructor.
        """
        self.x = x
        self.y = y
        self.z = z

        self.type: Coordinate = type(self)

    def __str__(self) -> str:
        """
        Prints coordinate rounded to 2 digits
        """
        return "[{:.2f}, {:.2f}, {:.2f}]".format(self.x, self.y, self.z)

    def __add__(self, other) -> Type[Coordinate]:
        """
        Adds two coordinates.
        Returns a new coordinate of the same type.

        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, self.type):
            raise TypeError(
                "Invalid types: {} and {} cannot be added.".format(
                    self.type, type(other)))

        return self.type.from_numpy(self.to_numpy() + other.to_numpy())

    def __sub__(self, other) -> Type[Coordinate]:
        """
        Subtracts two coordinates.
        Returns a new coordinate of the same type.

        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, self.type):
            raise TypeError(
                "Invalid types: {} and {} cannot be added.".format(
                    self.type, type(other)))

        return self.type.from_numpy(self.to_numpy() - other.to_numpy())

    def __eq__(self, o: object) -> bool:
        """
        Compares two coordinates.

        Two coordinates are equal, if they are of the same type and all
        values are equal.
        """
        if not isinstance(o, self.type):
            return False

        return o.x == self.x and o.y == self.y and o.z == self.z

    def __mul__(self, scalar) -> Type[Coordinate]:
        """
        Multiplies the coordinate by a scalar.
        Returns a new coordinate of the same type.
        """
        return self.type.from_numpy(self.to_numpy() * scalar)

    def to_list(self) -> list:
        """
        Returns the coordinate as a list.
        """
        return [self.x, self.y, self.z]

    def to_numpy(self) -> np.ndarray:
        """
        Returns the coordinate as a numpy array.
        """
        return np.array(self.to_list())


class StageCoordinate(Coordinate):
    """
    A Coordinate in the coordinate system of a stage.
    """

    def __init__(self, x=0, y=0, z=0) -> None:
        super().__init__(x, y, z)


class ChipCoordinate(Coordinate):
    """
    A Coordinate in the cooridnate system of a chip.
    """

    def __init__(self, x=0, y=0, z=0) -> None:
        super().__init__(x, y, z)


class CoordinatePairing(NamedTuple):
    calibration: Type[Calibration]
    stage_coordinate: Type[StageCoordinate]
    device: Type[Chip]
    chip_coordinate: Type[ChipCoordinate]


class Transformation(ABC):
    """
    Abstract interface for transformations.

    The base class cannot be initialised directly.
    """

    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractproperty
    def is_valid(self) -> bool:
        """
        Returns True if the transformation is valid.
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initializes the transformation.
        """
        pass

    @abstractmethod
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a coordinate in chip space to stage space.
        """
        pass

    @abstractmethod
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a coordinate in stage space to chip space.
        """
        pass


class TransformationError(RuntimeError):
    pass


def assert_valid_transformation(func):
    """
    Decorator to assert that a transformation is valid.

    Raises
    ------
    TransformationError
        If transformation is not valid.
    """
    @wraps(func)
    def warp(transformation, *args, **kwargs):
        if not transformation.is_valid:
            raise TransformationError(
                "Cannot transform with invalid transformation.")

        return func(transformation, *args, **kwargs)
    return warp


class AxesRotation(Transformation):
    """
    Defines a transformation to rotate a chip coordinate to a stage coordinate.
    This allows relative movements in the chip coordinate system for all stages.

    Functionality:
    If correctly defined, a 3x3 signed permutation matrix is defined.
    - Chip-to-Stage: Given a chip coordinate, this is multiplied on the right by the matrix to obtain a stage coordinate.
    - Stage-to-Chip: Given a stage coordinate, this is multiplied on the right by the inverse matrix to obtain a chip coordinate.
    """

    def __init__(self) -> None:
        self.initialize()

    def initialize(self) -> None:
        """
        Initalises the transformation by defining an identity matrix as a rotation matrix
        and defining the associated mapping.
        """
        self.matrix = np.identity(len(Axis))
        self.mapping = {
            Axis.X: (Direction.POSITIVE, Axis.X),
            Axis.Y: (Direction.POSITIVE, Axis.Y),
            Axis.Z: (Direction.POSITIVE, Axis.Z),
        }

    def update(
            self,
            chip_axis: Axis,
            direction: Direction,
            stage_axis: Axis) -> None:
        """
        Updates the axes rotation matrix.
        Replaces the column vector of given chip with signed (direction) i-th unit vector (i is stage)

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

        Raises
        ------
        ValueError
           If stage_axis, chip_axis or direction is not an instance of the required enum.
        """
        if not (isinstance(chip_axis, Axis) and isinstance(stage_axis, Axis)):
            raise ValueError("Unknown axes given for calibration.")

        if not isinstance(direction, Direction):
            raise ValueError("Unknown direction given for calibration.")

        self.mapping[chip_axis] = (direction, stage_axis)

        # Replacing column of chip with signed (direction) i-th unit vector (i
        # is stage)
        self.matrix[:, chip_axis.value] = np.eye(
            1, 3, stage_axis.value) * direction.value

    @property
    def is_valid(self) -> bool:
        """
        Checks if given matrix is a permutation matrix.
        A matrix is a permutation matrix if the sum of each row and column is exactly 1.
        """
        abs_matrix = np.absolute(self.matrix)
        return (
            abs_matrix.sum(
                axis=0) == 1).all() and (
            abs_matrix.sum(
                axis=1) == 1).all()

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Rotates the chip coordinate according to the axes rotation.
        i.e axes_rotation.dot(chip_coordinate)

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the current rotation is not a permutation matrix.
        """
        return StageCoordinate.from_numpy(
            self.matrix.dot(chip_coordinate.to_numpy()))

    @assert_valid_transformation
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Rotates the stage coordinate according to the inverse axes rotation.
        i.e np.linalg.inv(axes_rotation).dot(chip_coordinate)

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the current rotation is not a permutation matrix.
        """
        return ChipCoordinate.from_numpy(
            np.linalg.inv(self.matrix).dot(stage_coordinate.to_numpy()))


class SinglePointOffset(Transformation):
    """
    Transformation to convert chip coordinates into stage coordinates and vice versa.

    The transformation requires a correct stage-axis rotation (90 degrees) beforehand, meaning that stage and chip axes are identical after the rotation.

    Functionality:
    - Input is a single stage-chip coordinate pair.
    - The chip coordinate is rotated by the axis rotation to then calculate an offset between the rotated chip coordinate and the stage coordinate. This offset is stored.
    - Stage-To-Chip: The offset is added to the given stage coordinate. The sum is then rotated to a chip coordinate.
    - Chip-To-Stage: The give chip coordinate is rotated into the stage coordinate system and then the offset is subtracted.

    Note: The transformation assumes that the stage and chip axes are parallel. This is not the case in reality, so this transformation is only an approximation.
    """

    def __init__(self, axes_rotation: Type[AxesRotation]) -> None:
        self.axes_rotation: Type[AxesRotation] = axes_rotation
        self.initialize()

    def initialize(self):
        """
        Initalises the transformation by unsetting all coordinates and offsets.
        """
        self.pairing = None
        self.stage_offset: Type[StageCoordinate] = None

    def __str__(self) -> str:
        if self.stage_offset is None:
            return "No single point fixed"

        return "Stage-Coordinate {} fixed with Chip-Coordinate {}".format(
            self.pairing.stage_coordinate, self.pairing.chip_coordinate)

    @property
    def is_valid(self):
        """
        Returns True if single point transformation is defined, i.e. a offset is defined.
        """
        return self.stage_offset is not None and self.axes_rotation.is_valid

    def update(self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the offset based on a coordinate pairing.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate

        Raises
        ------
        ValueError
           If pairing is incomplete, i.e. stage coordinate or chip coordinate is missing.
        """
        if pairing.chip_coordinate is None or pairing.stage_coordinate is None:
            raise ValueError("Incomplete Pairing")

        self.pairing = pairing
        self.stage_offset = self.axes_rotation.chip_to_stage(
            pairing.chip_coordinate) - pairing.stage_coordinate

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a chip coordinate into a stage coordinate.
        Rotates the given chip coordinate to a stage cooridnate and subtracts the stage offset.

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the offset is not defined.
        """
        return self.axes_rotation.chip_to_stage(
            chip_coordinate) - self.stage_offset

    @assert_valid_transformation
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a stage coordinate into a chip coordinate.
        Adds the stage offset to the given stage coordinate and rotates the result to a chip coordinate.

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the offset is not defined.
        """
        return self.axes_rotation.stage_to_chip(
            stage_coordinate + self.stage_offset)


class KabschRotation(Transformation):
    """
    Estimate a rotation to optimally align two sets of vectors.
    Find a rotation to align a set of stage coordinates with a set of chip coordinates.
    For more information see Kabsch Algorithm.
    We require 3 points for a 3D transformation.
    More points are possible and may increase the accuracy.
    """

    MIN_POINTS = 3

    def __init__(self) -> None:
        self.initialize()

    def initialize(self) -> None:
        """
        Initalises the transformation by unsetting all coordinates and offsets.
        """
        self.pairings = []

        self.chip_coordinates = np.empty((0, 3), float)
        self.stage_coordinates = np.empty((0, 3), float)

        self.chip_offset = None
        self.stage_offset = None

        self.rotation = None
        self._rmsd = None

    def __str__(self) -> str:
        if not self.is_valid:
            return "No valid rotation defined ({}/{} Points set)".format(
                len(self.pairings), self.MIN_POINTS)

        return "Rotation defined with {} Points (RMSD: {})".format(
            len(self.pairings), self.rmsd)

    @property
    def is_valid(self) -> bool:
        """
        Returns True if Kabsch transformation is defined, i.e. if more than 3 pairings are defined.
        """
        return len(self.pairings) >= self.MIN_POINTS

    @property
    def rmsd(self):
        """
        Returns RMSD of rotation.
        """
        return self._rmsd if self.is_valid else None

    def update(self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the transformation by adding a new pairing.
        Add the stage coordinate and chip coordinates to a matrix and recalculates the rotation.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate

        Raises
        ------
        ValueError
           If the pairing is not well defined or a pairing for the chip has already been set.
        """
        if not isinstance(pairing, CoordinatePairing) or not all(pairing):
            raise ValueError(
                "Use a complete CoordinatePairing object to update the rotation. ")

        if any(p.device == pairing.device for p in self.pairings):
            raise ValueError(
                "A pairing with this device has already been saved.")

        self.pairings.append(pairing)

        self.chip_coordinates = np.append(
            self.chip_coordinates,
            [pairing.chip_coordinate.to_numpy()],
            axis=0)
        self.stage_coordinates = np.append(
            self.stage_coordinates,
            [pairing.stage_coordinate.to_numpy()],
            axis=0)

        # Calculate mean for each set
        self.chip_offset = ChipCoordinate.from_numpy(
            self.chip_coordinates.mean(axis=0))
        self.stage_offset = StageCoordinate.from_numpy(
            self.stage_coordinates.mean(axis=0))

        # Create Rotation with centered vectors
        self.rotation, self._rmsd = Rotation.align_vectors(
            (self.chip_coordinates - self.chip_offset.to_numpy()),
            (self.stage_coordinates - self.stage_offset.to_numpy()))

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a chip coordinate into a stage coordinate.
        Centres the given chip coordinate by substracting the chip offset
        and applies inverse rotation, then adds the stage offset.

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid.
        """
        centered_chip_coordinate = chip_coordinate - self.chip_offset

        return StageCoordinate.from_numpy(
            self.rotation.apply(centered_chip_coordinate.to_numpy(),
                                inverse=True)) + self.stage_offset

    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a stage coordinate into a chip coordinate.
        Centres the given stage coordinate by substracting the stage offset
        and applies rotation, then adds the chip offset.

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid.
        """
        centered_stage_coordinate = stage_coordinate - self.stage_offset

        return ChipCoordinate.from_numpy(self.rotation.apply(
            centered_stage_coordinate.to_numpy())) + self.chip_offset
