#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from __future__ import annotations

import logging
import numpy as np

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Any, Dict, NamedTuple, Tuple, Type, Generator

from scipy.spatial.distance import pdist

from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import CoordinateSystem, Orientation

if TYPE_CHECKING:
    from LabExT.Movement.Calibration import Calibration
    from LabExT.Wafer.Chip import Chip


class Waypoint(NamedTuple):
    """
    Represents one waypoint calculated by a path planning algorithm.
    """
    calibration: Type["Calibration"]
    coordinate: Type[ChipCoordinate]
    wait_for_stopping: bool = False


# Type alias: Defines a mapping from calibration to waypoint
WaypointCommand = Dict[Type["Calibration"], Type[Waypoint]]


class PathPlanningError(RuntimeError):
    """
    Runtime Error for path planning
    """
    pass


class StagePolygon(ABC):
    """
    Abstract base class to generate polygons for stages.

    This class cannot be initialised.
    """

    @classmethod
    def load(cls, polygon_data: dict) -> Type[StagePolygon]:
        """
        Returns a stage polygon reconstructed from polygon data.
        """
        polygon_name = polygon_data.get("polygon_cls")
        if not polygon_name:
            raise ValueError(
                "Cannot find and load stage polygon without polygon class name. "
                "Please provide a key 'polygon_cls' in polygon_data argument.")

        if (isinstance(polygon_name, type) and
                issubclass(polygon_name, StagePolygon)):
            polygon_cls = polygon_name
        elif isinstance(polygon_name, str):
            available_classes = StagePolygon.find_polygon_classes()
            try:
                polygon_cls = next(
                    pg for pg in available_classes if pg.__name__ == polygon_name)
            except StopIteration:
                available_classes_str = ", ".join(
                    map(lambda pg: pg.__name__, available_classes))
                raise ValueError(
                    f"No polygon class found with name {polygon_name}. The following are available: "
                    f"{available_classes_str}")
        else:
            raise ValueError(
                f"Cannot restore stage polygon class with 'polygon_cls' equal to {polygon_name} of type {type(polygon_name)}. "
                "Please provide a value for 'polygon_cls' of type str or StagePolygon. "
                "If you provide a string, it must be the name of the polygon class.")

        try:
            orientation = Orientation[polygon_data["orientation"]]
        except KeyError as err:
            raise ValueError(
                f"The parameter 'orientation' in polygon_data is not defined: {err}. "
                f"Make sure to pass a valid orientation: {', '.join(map(str, list(Orientation)))}")

        return polygon_cls(
            orientation=orientation,
            parameters=polygon_data.get("parameters", {}))

    @classmethod
    def find_polygon_classes(cls) -> List[StagePolygon]:
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

    def __init__(
        self,
        orientation: Orientation,
        parameters: Dict[str, Any] = {}
    ) -> None:
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

        self.parameters = parameters
        if not self.parameters:
            self.parameters = self.get_default_parameters()

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
            "parameters": self.parameters}


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


class PathPlanning(ABC):
    """
    Abstract base class for path planning.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__()

    @abstractmethod
    def set_stage_target(
        self,
        calibration: Type["Calibration"],
        target: Type[ChipCoordinate]
    ) -> None:
        """
        Sets a new traget for given calibration.

        Parameters
        ----------
        calibration: Calibration
            Instance of a calibration for which a target cooridnate is to be set.
        target: ChipCoordinate
            3D coordinate in the chip system as a target for the passed calibration.
        """
        pass

    @abstractmethod
    def trajectory(self) -> Generator[WaypointCommand, Any, Any]:
        """
        Generates the next waypoint of the path planner.

        The generator must generate waypoint commands.
        These are (named) tuples consisting of the calibration for which the command is meant,
        the calibration coordinate, and a `wait_for_stopping` specifying
        whether the stage should wait until this waypoint command has been executed.
        """
        pass


class PotentialField:
    """
    Waypoint calculation with potential field algorithm.
    A potential field is created for each stage, with all other stages being obstacles.

    This algorithm operates in 2D (x,y), assuming that the stages are on a plane.

    Parts of this algorithm are based on the implementation in
    https://github.com/AtsushiSakai/PythonRobotics/blob/master/PathPlanning/PotentialFieldPlanning/potential_field_planning.py released under MIT license.
    """

    FIBER_RADIUS = 125.0

    MOTIONS = [[1, 0],
               [0, 1],
               [-1, 0],
               [0, -1],
               [-1, -1],
               [-1, 1],
               [1, -1],
               [1, 1]]

    def __init__(
        self,
        calibration: Type["Calibration"],
        target_coordinate: Type[ChipCoordinate],
        grid_size: float = 50.0,
        grid_outline: tuple = ((-5000, 5000), (-5000, 5000)),
        repulsive_gain: float = 10000.0,
        attractive_gain: float = 1.0
    ) -> None:
        """
        Constructor for new Potential Field

        Parameters
        ----------
        calibration: Calibration
            Instance of a calibration
        target_coordinate: ChipCoordinate
            Target in chip coordinates
        grid_size: float
            Size of the potential field grid
        grid_outline: tuple
            Outline (x_min, x_max, y_min, y_max) of the potential field grid
        repulsive_gain: tuple
            Repulsive gain in the potential field
        attractive_gain: tuple
            Attractive gain in the potential field
        """
        # Stage calibration for this potential field
        self.calibration = calibration

        # Fields settings
        self.grid_size = grid_size
        self.grid_outline = grid_outline
        self.repulsive_gain = repulsive_gain
        self.attractive_gain = attractive_gain

        # Read current stage position
        with self.calibration.perform_in_system(CoordinateSystem.CHIP):
            self.start_coordinate = self.calibration.get_position()

        # Set up field tiles
        self.x_coords = np.arange(
            self.grid_outline[0][0],
            self.grid_outline[0][1] +
            self.grid_size,
            self.grid_size)
        self.y_coords = np.arange(
            self.grid_outline[1][0],
            self.grid_outline[1][1] +
            self.grid_size,
            self.grid_size)
        self.cx, self.cy = np.meshgrid(self.x_coords, self.y_coords)

        # Get current Idx of field tile
        self.current_idx = np.array(
            [np.argmin(np.abs(self.x_coords - self.start_coordinate.x)),
                np.argmin(np.abs(self.y_coords - self.start_coordinate.y))])

        # current position in terms of field tiles
        self.current_position = ChipCoordinate(
            x=self.x_coords[self.current_idx[0]],
            y=self.y_coords[self.current_idx[1]],
            z=self.start_coordinate.z)

        # field target
        self.target_coordinate = target_coordinate

        if not np.isclose(
                self.start_coordinate.z,
                self.target_coordinate.z,
                rtol=1.e-5,
                atol=10e-3):
            raise ValueError(
                f"Start z level {self.start_coordinate.z} is not close to target z level {self.target_coordinate.z}. "
                "The Path Planning algorithm assumes that start and target are on the same z level.")

        # Calculate potential field
        self.attractive_potential_field = self.attractive_gain * \
            np.hypot(self.cx - self.target_coordinate.x, self.cy - self.target_coordinate.y)
        self.potential_field = np.zeros_like(
            self.cx) + self.attractive_potential_field

    def next_waypoint(self) -> Waypoint:
        """
        Generates iterativly the next waypoint in the given potential field.

        It calculates an infinite number of waypoints with the last waypoints being the actual destination.

        Returns
        -------
        Returns a 2D coordinate as next potential field waypoint.
        """
        distance_to_target = np.hypot(
            self.current_position.x - self.target_coordinate.x,
            self.current_position.y - self.target_coordinate.y)

        if distance_to_target <= self.grid_size:
            self.current_position = self.target_coordinate
        else:
            self.current_idx = self._find_lowest_potential()

            self.current_position = ChipCoordinate(
                x=self.x_coords[self.current_idx[0]],
                y=self.y_coords[self.current_idx[1]],
                z=self.start_coordinate.z)

        return Waypoint(
            calibration=self.calibration,
            coordinate=self.current_position,
            wait_for_stopping=False)

    def set_stage_obstacles(
        self,
        *calibrations: List[Type["Calibration"]],
        safety_multiplier: int = 5
    ) -> None:
        """
        Creates an obstacle in the potential field for each passed calibration.

        Parameters
        ----------
        calibrations : List[Calibration]
            List of calibration instances
        safety_multiplier: int
            Multiplier of the fiber radius to calculate the field mask
        """
        self.potential_field = np.zeros_like(
            self.cx) + self.attractive_potential_field

        for calibration in calibrations:
            with calibration.perform_in_system(CoordinateSystem.CHIP):
                stage_mask = calibration.stage_polygon.stage_in_meshgrid(
                    calibration.get_position(),
                    self.cx,
                    self.cy,
                    self.grid_size)

            for ox, oy in zip(self.cx[stage_mask], self.cy[stage_mask]):
                o_dist = np.hypot(self.cx - ox, self.cy - oy)
                field_mask = o_dist < safety_multiplier * self.FIBER_RADIUS
                rep_field = self.repulsive_gain * (1.0 / o_dist) ** 2

                self.potential_field[field_mask] += rep_field[field_mask]

    def _find_lowest_potential(self) -> np.ndarray:
        """
        Finds lowest potential around current position.

        Returns
        -------
        Returns the index of the lowest potential.
        """
        curr_potenial = self.potential_field[self.current_idx[1],
                                             self.current_idx[0]]
        curr_idx = self.current_idx.copy()

        for mx, my in self.MOTIONS:
            possible_idx = self.current_idx + np.array([mx, my])
            possible_potential = self.potential_field[possible_idx[1],
                                                      possible_idx[0]]
            if possible_potential < curr_potenial:
                curr_potenial = possible_potential
                curr_idx = possible_idx

        return curr_idx


class CollisionAvoidancePlanning(PathPlanning):
    """
    Main class for collision avoidance path planning
    using the potential field algorithm.
    """

    def __init__(
        self,
        chip,
        abort_local_minimum: int = 3
    ) -> None:
        """
        Constructor for the Path Planning.
        Parameters
        ----------
        chip: Chip
            Instance of the a chip
        abort_local_minimum: int = 3
            Number of identical movements before an error is raised.
        """
        self.chip: Type[Chip] = chip
        self.grid_size, self.grid_outline = self._get_grid_properties(
            padding=100)

        self.abort_local_minimum = abort_local_minimum

        self.potential_fields = {}
        self.last_moves = []

    def set_stage_target(
        self,
        calibration: Type["Calibration"],
        target: Type[ChipCoordinate]
    ) -> None:
        """
        Registers a target for the given calibration.

        Parameters
        ----------
        calibration : Calibration
            Instance of a calibrated stage, such that the stage can move in chip coordinates.
        target : ChipCoordinate
            Target of the stage in chip coordinates.
        """
        self.potential_fields[calibration] = PotentialField(
            calibration,
            target,
            self.grid_size,
            self.grid_outline)

    def trajectory(self) -> Generator[WaypointCommand, None, None]:
        """
        Generator to calculate a trajectory for all stages.

        Returns a mapping between calibration and next waypoint (in chip coordinates).

        Updates the obstacles after each stage waypoint.

        Raises
        ------
        PathPlanningError
            If no progress has been made.
        """
        while not all(f.current_position ==
                      f.target_coordinate for f in self.potential_fields.values()):

            next_move = {}

            for calibration, potential_field in self.potential_fields.items():
                potential_field.set_stage_obstacles(*[
                    obstacle_calibration for obstacle_calibration in self.potential_fields.keys() if obstacle_calibration != calibration
                ])

                next_move[calibration] = potential_field.next_waypoint()

            if self._last_waypoints_equal(next_move):
                raise PathPlanningError(
                    f"Path-finding algorithm makes no progress. The last {self.abort_local_minimum} movements were identical!")

            self.last_moves.append(next_move)
            yield next_move

    def _get_grid_properties(
        self,
        padding: float = 0,
        maximum_gird_size: float = 100
    ) -> tuple:
        """
        Dynamically calculates the grid outline based on the points of the chip.

        Dynamically calculates the grid size by calculating
        the smallest distance between two points on the chip

        Parameters
        ----------
        padding: float = 0
            Grid outline padding.
        maximum_gird_size: float = 100
            Grid size that must not be exceeded.
        """
        all_points = np.concatenate([
            [d.in_position for d in self.chip.devices.values()],
            [d.out_position for d in self.chip.devices.values()]
        ], axis=0)

        xs = all_points[:, 0]
        ys = all_points[:, 1]

        outline = (
            (xs.min() - padding, xs.max() + padding),  # X-min, X-max
            (ys.min() - padding, ys.max() + padding)  # Y-min, Y-max
        )
        grid_size = min(np.floor(np.min(pdist(all_points))), maximum_gird_size)

        return grid_size, outline

    def _last_waypoints_equal(self, next_command: WaypointCommand) -> bool:
        """
        Returns True if all last moves are equal to the new move.

        Parameters
        ----------
        next_command: WaypointCommand
            next waypoint commands
        """
        if len(self.last_moves) == 0:
            return False

        for last_move in self.last_moves[-self.abort_local_minimum:]:
            for calibration, waypoint in last_move.items():
                if next_command[calibration].coordinate != waypoint.coordinate:
                    return False

        return True


class SingleStagePlanning(PathPlanning):
    """
    Path planning for single stage movements.
    """

    def __init__(
        self,
        max_lift_correction: float = 100,
        correction_tolerance: float = 10
    ) -> None:
        """
        Constructor for the single stage path planning.
        Parameters
        ----------
        max_lift_correction: float = 100 [um]
            Upper limit for z level correction.
        correction_tolerance: float = 10 [um]
            Additional correction: Will be added to the delta of the Z-level.
        """
        super().__init__()
        self.max_lift_correction = max_lift_correction
        self.correction_tolerance = correction_tolerance

        self.calibration = None

        self.target_chip_coordinate = None
        self.target_stage_coordinate = None

        self.start_chip_coordinate = None
        self.start_stage_coordinate = None

    def set_stage_target(
        self,
        calibration: Type["Calibration"],
        target: Type[ChipCoordinate]
    ) -> None:
        """
        Sets the traget coordinate for given calibrations.
        """
        if self.calibration is not None:
            raise PathPlanningError(
                "A calibration and target coordinate is already set. This Path Planning does support only one stage.")

        self.calibration = calibration

        # Get current stage position in chip system
        with self.calibration.perform_in_system(CoordinateSystem.CHIP):
            self.start_chip_coordinate = self.calibration.get_position()

        self.target_chip_coordinate = target

        self.start_stage_coordinate = calibration.transform_chip_to_stage_coordinate(
            chip_coordinate=self.start_chip_coordinate)
        self.target_stage_coordinate = calibration.transform_chip_to_stage_coordinate(
            chip_coordinate=self.target_chip_coordinate)

    def trajectory(self) -> Generator[WaypointCommand, Any, Any]:
        """
        Calculates waypoints for a simple stage from start to finish as a generator.
        Checks beforehand whether the current z-lift is sufficient to compensate for the chip inclination without danger.
        If not, the stage is first moved upwards and then lowered again.
        """
        z_level_correction = self._z_level_correction()
        for waypoint in [
            Waypoint(
                self.calibration,
                ChipCoordinate(
                    x=self.start_chip_coordinate.x,
                    y=self.start_chip_coordinate.y,
                    z=self.start_chip_coordinate.z +
                    z_level_correction),
                wait_for_stopping=True),
            Waypoint(
                self.calibration,
                ChipCoordinate(
                    x=self.target_chip_coordinate.x,
                    y=self.target_chip_coordinate.y,
                    z=self.target_chip_coordinate.z +
                    z_level_correction),
                wait_for_stopping=True),
            Waypoint(
                self.calibration,
                self.target_chip_coordinate,
                wait_for_stopping=True)]:
            yield {
                self.calibration: waypoint}

    def _z_level_correction(self) -> float:
        """
        Calculates a new z-level height.
        If the current lift of the stage is lower than the Z difference between the start and target,
        we are in danger of driving into the chip.
        We calculate a z level equal to the delta in Z between the start and target plus tolerance.
        The height is limited upwards by max_lift_correction
        Returns
        ------
        z_correction : float
            New z level height
        Raises
        ------
        PathPlanningError
            If new z level height is greater than max_lift_correction
        """
        start_target_z_delta = np.ceil(np.abs(
            self.target_stage_coordinate.z - self.start_stage_coordinate.z))

        self.logger.debug(
            f"[{self.calibration}] Z-delta between start and target: {start_target_z_delta} um")

        z_correction = start_target_z_delta + self.correction_tolerance
        self.logger.debug(
            f"[{self.calibration}] Calculated z correction of {z_correction} (Tolerance: {self.correction_tolerance})")

        if z_correction > self.max_lift_correction:
            raise PathPlanningError(
                f"Correction lift of {z_correction} exceed max lift correction of {self.max_lift_correction}")

        return z_correction
