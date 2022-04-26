#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import NamedTuple, Type
import numpy as np


class Transformation(ABC):
    """
    Abstract interface for transformations.
    """

    @abstractmethod
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def is_valid(self):
        """
        Returns True if the transformation is valid.
        """
        pass

    @abstractmethod
    def chip_to_stage(self, chip_coordinate):
        """
        Transforms a coordinate in chip space to stage space.
        """
        pass

    @abstractmethod
    def stage_to_chip(self, stage_coordinate):
        """
        Transforms a coordinate in stage space to chip space.
        """
        pass


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
    calibration: object
    stage_coordinate: list
    device: object
    chip_coordinate: list


class SinglePointFixation(Transformation):
    """
    Performs a translation based on a fixed single point.
    """

    def __init__(self) -> None:
        self._chip_coordinate = None
        self._stage_coordinate = None
        self._offset = None

    def __str__(self) -> str:
        if self._offset is None:
            return "No single point fixed"

        return "Stage-Coordinate {} fixed with Chip-Coordinate {}".format(
            self._stage_coordinate, self._chip_coordinate)

    @property
    def is_valid(self):
        """
        Returns True if single point transformation is defined.
        """
        return self._offset is not None

    def update(self, pairing: Type[CoordinatePairing]):
        """
        Updates the offset based on a coordinate pairing.
        """
        if pairing.chip_coordinate is None or pairing.stage_coordinate is None:
            raise ValueError("Incomplete Pairing")

        self._chip_coordinate = np.array(pairing.chip_coordinate)
        self._stage_coordinate = np.array(pairing.stage_coordinate)

        self._offset = self._stage_coordinate - self._chip_coordinate

    def chip_to_stage(self, chip_coordinate):
        """
        Translates chip coordinate to stage coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return np.array(chip_coordinate) + self._offset

    def stage_to_chip(self, stage_coordinate):
        """
        Translates stage coordinate to chip coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return np.array(stage_coordinate) + self._offset
