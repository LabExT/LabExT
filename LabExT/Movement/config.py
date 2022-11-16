#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from enum import Enum, auto
from functools import total_ordering


class BaseEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    def __str__(self) -> str:
        return self.name.capitalize()


class Axis(BaseEnum):
    """Enumerate different axis."""
    X = 0
    Y = 1
    Z = 2

    def __str__(self) -> str: return f"{self.name}-Axis"


class Direction(BaseEnum):
    """Enumerate different axis directions."""
    NEGATIVE = -1
    POSITIVE = 1


class Orientation(BaseEnum):
    """Enumerate different stage orientations."""
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()


CLOCKWISE_ORDERING = [
    Orientation.TOP,
    Orientation.RIGHT,
    Orientation.BOTTOM,
    Orientation.LEFT]


class DevicePort(BaseEnum):
    """Enumerate different device ports."""
    INPUT = auto()
    OUTPUT = auto()


class CoordinateSystem(BaseEnum):
    """
    Enumerate different coordinate systems
    """
    UNKNOWN = auto()
    STAGE = auto()
    CHIP = auto()

@total_ordering
class State(BaseEnum):
    """
    Enumerate different calibration states.
    """
    UNINITIALIZED = 0
    CONNECTED = 1
    COORDINATE_SYSTEM_FIXED = 2
    SINGLE_POINT_FIXED = 3
    FULLY_CALIBRATED = 4

    def __str__(self) -> str: return self.name.replace('_', ' ').capitalize()

    def __eq__(self, other):
        """
        Compare two states for equality.
        """
        if self.__class__ is other.__class__:
            return self.value == other.value

        return NotImplemented

    def __lt__(self, other):
        """
        Compare two states on "less than".
        """
        if self.__class__ is other.__class__:
            return self.value < other.value

        return NotImplemented
