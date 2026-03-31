#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type

import numpy as np
from numpy.typing import NDArray

CoordinateT = TypeVar("CoordinateT", bound="Coordinate")


class Coordinate(ABC, Generic[CoordinateT]):
    """
    Abstract base class of a coordinate with X, Y and Z values.

    The base class cannot be initialised directly.
    """
    @classmethod
    def from_list(cls: Type[CoordinateT], _list: list) -> CoordinateT:
        """
        Returns a new coordinate, created from a list.
        """
        return cls(*_list[:3])

    @classmethod
    def from_numpy(cls: Type[CoordinateT], array: NDArray[np.float64]) -> CoordinateT:
        """
        Returns a new coordinate created from a one-dimensional numpy array.
        """
        if array.ndim != 1:
            raise ValueError("The given array is not a 1D-Array.")

        return cls(*array.tolist()[:3])

    @abstractmethod
    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        return f"[{self.x:.2f}, {self.y:.2f}, {self.z:.2f}]"

    def __add__(self, other: CoordinateT) -> CoordinateT:
        """
        Adds two coordinates. Returns a new coordinate of the same type.
        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, type(self)):
            raise TypeError(f"Invalid types: {type(self)} and {type(other)} cannot be added.")

        return type(self).from_numpy(self.to_numpy() + other.to_numpy())

    def __sub__(self, other: CoordinateT) -> CoordinateT:
        """
        Subtracts two coordinates. Returns a new coordinate of the same type.
        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, type(self)):
            raise TypeError(f"Invalid types: {type(self)} and {type(other)} cannot be added.")

        return type(self).from_numpy(self.to_numpy() - other.to_numpy())

    def __eq__(self, other: CoordinateT) -> bool:
        """
        Compares two coordinates.
        Two coordinates are equal, if they are of the same type and all values are equal.
        """
        if not isinstance(other, type(self)):
            return False

        return other.x == self.x and other.y == self.y and other.z == self.z

    def __mul__(self, scalar: float) -> CoordinateT:
        """
        Multiplies the coordinate by a scalar.
        Returns a new coordinate of the same type.
        """
        return type(self).from_numpy(self.to_numpy() * scalar)

    @property
    def is_zero(self) -> bool:
        """
        Returns True if the coordinate is equal to [0,0,0]
        """
        return bool(np.all(self.to_numpy() == 0))

    def to_list(self) -> list:
        """
        Returns the coordinate as a list.
        """
        return [self.x, self.y, self.z]

    def to_numpy(self) -> NDArray[np.float64]:
        """
        Returns the coordinate as a numpy array.
        """
        return np.array(self.to_list())


class StageCoordinate(Coordinate):
    """
    A Coordinate in the coordinate system of a stage.
    """

    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        super().__init__(x, y, z)


class ChipCoordinate(Coordinate):
    """
    A Coordinate in the coordinate system of a chip.
    """

    def __init__(self, x: float = 0, y: float = 0, z: float = 0) -> None:
        super().__init__(x, y, z)
