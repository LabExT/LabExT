#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Type, Dict, Any, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from LabExT.Movement.Coordinate import ChipCoordinate
from LabExT.Movement.config import Orientation

StagePolygonT = TypeVar("StagePolygonT", bound="StagePolygon")


class StagePolygon(ABC):
    """
    Abstract base class to generate polygons for stages.
    """

    @classmethod
    def load(cls: Type[StagePolygonT], polygon_data: Dict[str, Any]) -> StagePolygonT:
        """
        Returns a stage polygon reconstructed from polygon data.
        """
        polygon_raw = polygon_data.get("polygon_cls")
        if polygon_raw is None:
            raise ValueError("Cannot find and load stage polygon without polygon class name. "
                             "Please provide a key 'polygon_cls' in polygon_data argument.")

        # --- Case 1: polygon_cls is already a class subclassing StagePolygon ---
        if isinstance(polygon_raw, type) and issubclass(polygon_raw, StagePolygon):
            polygon_cls: Type[StagePolygonT] = polygon_raw

        # --- Case 2: polygon_cls is a string with a class name ---
        elif isinstance(polygon_raw, str):
            available = cls.find_polygon_classes()
            try:
                polygon_cls = next(pgc for pgc in available if pgc.__name__ == polygon_raw)
            except StopIteration:
                names = ", ".join(pgc.__name__ for pgc in available)
                raise ValueError(f"No polygon class found with name {polygon_raw}. Available subclasses: {names}")

        else:
            raise TypeError(f"Invalid value for 'polygon_cls': {polygon_raw!r} (type {type(polygon_raw).__name__}). "
                            f"Expected a subclass of StagePolygon or its class name.")

        try:
            orientation = Orientation(polygon_data["orientation"])
        except KeyError as e:
            valid = ", ".join(o.name for o in Orientation)
            raise ValueError(f"Invalid or missing 'orientation': {e}. Valid orientations: {valid}")

        parameters = polygon_data.get("parameters", {})

        return polygon_cls(orientation=orientation, parameters=parameters)

    @classmethod
    def find_polygon_classes(cls) -> List[Type[StagePolygonT]]:
        """
        Returns a list of available polygon classes.
        """
        return cls.__subclasses__()

    @classmethod
    def get_default_parameters(cls) -> Dict[str, Any]:
        """
        Returns default polygon configuration parameter
        """
        return {}

    def __init__(self, orientation: Orientation, parameters: Optional[Dict[str, Any]] = None) -> None:
        """
        Constructor for base  polygon
        Parameters
        ----------
        orientation: Orientation
            Polygon orientation in chip space
        parameters: Dict[str, Any] = {}
            Optional parameters to configure the polygon
        """
        self.orientation = orientation
        self.parameters = self.get_default_parameters() if parameters is None else parameters

    @abstractmethod
    def stage_in_meshgrid(
        self,
        position: ChipCoordinate,
        mesh_x: NDArray[np.float64],
        mesh_y: NDArray[np.float64],
        grid_size: float
    ) -> NDArray[np.float64]:
        """
        Returns a mask if a point in the meshgrid is in the stage.
        """
        ...

    def dump(self, stringify: bool = True) -> dict:
        """
        Returns polygon parameters as dict
        """
        if stringify:
            polygon_cls = self.__class__.__name__
        else:
            polygon_cls = self.__class__

        return {
            "polygon_cls": polygon_cls,
            "orientation": self.orientation.value,
            "parameters": self.parameters
        }


class SingleModeFiber(StagePolygon):
    """
    Polygon for single mode fiber.
    """

    @classmethod
    def get_default_parameters(cls) -> Dict[str, Any]:
        """
        Returns default parameter to set up a single mode fiber polygon
        """
        return {
            "Fiber Length": 8e4,        # [um] (8cm)
            "Fiber Radius": 75.0,       # [um]
            "Safety Distance": 75.0     # [um]
        }

    def stage_in_meshgrid(
        self,
        position: ChipCoordinate,
        mesh_x: NDArray[np.float64],
        mesh_y: NDArray[np.float64],
        grid_size: float
    ) -> NDArray[np.float64]:
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
        position: ChipCoordinate,
        grid_size: float,
        grid_epsilon: float = 10
    ) -> Tuple[float, float, float, float]:
        """
        Returns a tuple with the X- and Y-axis limits.

        Performs a case distinction according to the orientation of the stage.

        Artificially enlarges the outline, if it is too small for the grid:
        e.g. If the distance between x_max and x_min is less than or equal to the grid size,
        half the grid size plus an absolute epsilon is added/subtracted.

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
        fiber_radius = float(self.parameters.get("Fiber Radius", 75.0))
        fiber_length = float(self.parameters.get("Fiber Length", 8e4))
        safety_distance = float(self.parameters.get("Safety Distance", 75.0))

        safe_fiber_radius = fiber_radius + safety_distance

        x_min = position.x - safe_fiber_radius
        x_max = position.x + safe_fiber_radius
        y_min = position.y - safe_fiber_radius
        y_max = position.y + safe_fiber_radius

        if self.orientation == Orientation.LEFT:
            x_min -= fiber_length
        elif self.orientation == Orientation.RIGHT:
            x_max += fiber_length
        elif self.orientation == Orientation.BOTTOM:
            y_min -= fiber_length
        elif self.orientation == Orientation.TOP:
            y_max += fiber_length
        else:
            raise ValueError(f"No Stage Polygon defined for orientation {self.orientation}")

        # Make sure, that outline fits into meshgrid
        if np.abs(x_max - x_min) <= grid_size:
            x_max += grid_size / 2 + grid_epsilon
            x_min -= grid_size / 2 + grid_epsilon

        if np.abs(y_max - y_min) <= grid_size:
            y_max += grid_size / 2 + grid_epsilon
            y_min -= grid_size / 2 + grid_epsilon

        return x_min, x_max, y_min, y_max