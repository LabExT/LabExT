#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Type

import numpy as np

from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import Orientation


class StagePolygon(ABC):
    """
    Abstract base class to generate polygons for stages.

    This class cannot be initialised.
    """

    @abstractmethod
    def __init__(
        self,
        orientation: Orientation,
        safety_distance: float = 75.0
    ) -> None:
        pass

    @abstractmethod
    def stage_in_meshgrid(
        self,
        position: Type[ChipCoordinate],
        mesh_x: np.ndarray,
        mesh_y: np.ndarray
    ) -> np.ndarray:
        """
        Returns a mask if a point in the meshgrid is in the stage.
        """
        pass


class SingleModeFiber(StagePolygon):
    """
    Polygon for single mode fiber.
    """

    FIBER_LENGTH = 8e4  # [um] (8cm)
    FIBER_RADIUS = 75.0  # [um]

    def __init__(
        self,
        orientation: Orientation,
        safety_distance: float = 75.0
    ) -> None:
        """
        Constructor for new single mode fiber polygon.

        Parameters
        ----------
        orientation: Orientation
            Orientation of the stage in space
        safety_distance: float
            Safety distance around the fiber in um.
        """
        self.orientation = orientation
        self.safety_distance = safety_distance

    def stage_in_meshgrid(self,
                          position: Type[ChipCoordinate],
                          mesh_x: np.ndarray,
                          mesh_y: np.ndarray,
                          ) -> np.ndarray:
        """
        Returns a mask if if a point of the single mode fiber in the meshgrid is in the stage.

        Parameters
        ----------
        position : ChipCoordinate
            Current position of the stage in Chip-Coordinates
        mesh_x : np.ndarray
            X values of the meshgrid
        mesh_y : np.ndarray
            Y values of the meshgrid
        """
        x_min, x_max, y_min, y_max = self._create_outline(position)
        return np.logical_and(
            np.logical_and(x_min <= mesh_x, mesh_x <= x_max),
            np.logical_and(y_min <= mesh_y, mesh_y <= y_max))

    def _create_outline(
        self,
        position: Type[ChipCoordinate]
    ) -> Tuple[float, float, float, float]:
        """
        Returns a tuple with the X- and Y-axis limits.

        Performs a case distinction according to the orientation of the stage.

        Parameters
        ----------
        position : ChipCoordinate
            Current position of the stage in Chip-Coordinates

        Raises
        ------
        ValueError
            If no outline is defined for the given orientation.
        """
        safe_fiber_radius = self.FIBER_RADIUS + self.safety_distance

        x_min = position.x - safe_fiber_radius
        x_max = position.x + safe_fiber_radius
        y_min = position.y - safe_fiber_radius
        y_max = position.y + safe_fiber_radius

        if self.orientation == Orientation.LEFT:
            x_min -= self.FIBER_LENGTH
        elif self.orientation == Orientation.RIGHT:
            x_max += self.FIBER_LENGTH
        elif self.orientation == Orientation.BOTTOM:
            y_min -= self.FIBER_LENGTH
        elif self.orientation == Orientation.TOP:
            y_max += self.FIBER_LENGTH

        return x_min, x_max, y_min, y_max
