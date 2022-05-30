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
        mesh_y: np.ndarray,
        grid_size: float
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

    def stage_in_meshgrid(
        self,
        position: Type[ChipCoordinate],
        mesh_x: np.ndarray,
        mesh_y: np.ndarray,
        grid_size: float
    ) -> np.ndarray:
        """
        Returns a mask if a point of the single mode fiber in the meshgrid is in the stage.

        Parameters
        ----------
        position : ChipCoordinate
            Current position of the stage in Chip-Coordinates
        mesh_x : np.ndarray
            X values of the meshgrid
        mesh_y : np.ndarray
            Y values of the meshgrid
        grid_size : float
            Grid size of meshgrid
        """
        x_min, x_max, y_min, y_max = self._create_outline(position, grid_size)
        return np.logical_and(
            np.logical_and(x_min <= mesh_x, mesh_x <= x_max),
            np.logical_and(y_min <= mesh_y, mesh_y <= y_max))

    def _create_outline(
        self,
        position: Type[ChipCoordinate],
        grid_size: float,
        grid_epsilon: float = 10
    ) -> Tuple[float, float, float, float]:
        """
        Returns a tuple with the X- and Y-axis limits.

        Performs a case distinction according to the orientation of the stage.

        Artificially enlarges the outline, if it is too small for the grid:
        e.g. If the distance between x_max and x_min is less than or equal to the grid size,
        half the grid size plus an absolute epsilon is added/substracted.

        Parameters
        ----------
        position : ChipCoordinate
            Current position of the stage in Chip-Coordinates
        grid_size : float
            Grid size of meshgrid
        grid_epsilon : float
            Absolute summand to artificially enlarge the obstacle
            if it is too small for the meshgrid.

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
        else:
            raise ValueError(
                f"No Stage Polygon defined for orientation {self.orientation}")

        # Make sure, that outline fits into meshgrid
        if np.abs(x_max - x_min) <= grid_size:
            x_max += grid_size / 2 + grid_epsilon
            x_min -= grid_size / 2 + grid_epsilon

        if np.abs(y_max - y_min) <= grid_size:
            y_max += grid_size / 2 + grid_epsilon
            y_min -= grid_size / 2 + grid_epsilon

        return x_min, x_max, y_min, y_max
