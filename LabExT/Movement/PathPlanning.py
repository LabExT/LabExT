#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


from time import time
from typing import Dict, Tuple, Type

import warnings
import numpy as np

from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import Orientation
from LabExT.Wafer.Chip import Chip


class PotenialField:

    GRID_SIZE = 100.0
    REPULSIVE_GAIN = 100.0
    ATTRACTIVE_GAIN = 5.0
    FIBER_RADIUS = 125.0

    MOTIONS = [[1, 0],
              [0, 1],
              [-1, 0],
              [0, -1],
              [-1, -1],
              [-1, 1],
              [1, -1],
              [1, 1]]

    def __init__(self, chip, start: Type[ChipCoordinate], goal: Type[ChipCoordinate]) -> None:
        self.start = start
        self.goal = goal

        self.chip = chip
        self.chip_outline = self._get_chip_outline(chip, tol=100)
        
        self.x_coords = np.arange(self.chip_outline[0][0], self.chip_outline[0][1] + self.GRID_SIZE, self.GRID_SIZE)
        self.y_coords = np.arange(self.chip_outline[1][0], self.chip_outline[1][1] + self.GRID_SIZE, self.GRID_SIZE)
        self.cx, self.cy = np.meshgrid(self.x_coords, self.y_coords)

        self.current_idx = np.array(
            [np.argmin(np.abs(self.x_coords - self.start.x)),
            np.argmin(np.abs(self.y_coords - self.start.y))])
        self.distance_to_goal =  np.hypot(
            self.x_coords[self.current_idx[0]] - self.goal.x,
            self.y_coords[self.current_idx[1]] - self.goal.y)

        self.attractive_potenial_field = self.ATTRACTIVE_GAIN * np.hypot(self.cx - self.goal.x, self.cy - self.goal.y)
        self.potential_field = np.zeros_like(self.cx) + self.attractive_potenial_field

    def add_obstacles(self, obstacles: Dict[Orientation, Type[ChipCoordinate]]):
        """
        Calc Heavy
        """
        start = time()

        self.potential_field = np.zeros_like(self.cx) + self.attractive_potenial_field
        for orientation, position in obstacles.items():
            outline = self._get_obstacle_outline(position, orientation)
            in_obstacle = np.logical_and(
                np.logical_and(outline[0][0] <= self.cx, self.cx <= outline[0][1]),
                np.logical_and(outline[1][0] <= self.cy, self.cy <= outline[1][1]))

            for ox, oy in zip(self.cx[in_obstacle], self.cy[in_obstacle]):
                o_dist = np.hypot(self.cx - ox, self.cy - oy)
                field_mask = o_dist < 5 * self.FIBER_RADIUS
                rep_field = self.REPULSIVE_GAIN * (1.0 / o_dist - 1.0 / self.FIBER_RADIUS) ** 2

                self.potential_field[field_mask] += rep_field[field_mask]
        
        # print(f"New Potential field in: {time() - start}")


    def waypoints(self):
        """
        Generator to calculate all waypoints in the given potential field.
        This generator calculates an infinite number of waypoints with the last waypoints being the actual destination.

        Returns a tuple, where the first value is the waypoint and the second value indicates
        whether there are more (different) waypoints to follow, i.e. the algorithm has not yet converged.
        """
        while self.distance_to_goal > self.GRID_SIZE:
            next_potenial = self.potential_field[self.current_idx[1], self.current_idx[0]]
            next_idx = self.current_idx.copy()

            for mx, my in self.MOTIONS:
                possible_idx = self.current_idx + np.array([mx, my])
                possible_potential = self.potential_field[possible_idx[1], possible_idx[0]]
                if possible_potential < next_potenial:
                    next_potenial = possible_potential
                    next_idx = possible_idx

            if np.all(next_idx == self.current_idx):
                warnings.warn("LOCAL MINIMUM")
                # return

            self.current_idx = next_idx
            self.distance_to_goal =  np.hypot(
                self.x_coords[self.current_idx[0]] - self.goal.x,
                self.y_coords[self.current_idx[1]] - self.goal.y)

            yield ChipCoordinate(
                x=self.x_coords[self.current_idx[0]],
                y=self.y_coords[self.current_idx[1]]), False
        else:
            yield self.goal, True

    def _get_chip_outline(self, chip: Type[Chip], tol=0):
        all_ports = np.concatenate([
           [d._in_position for d in chip._devices.values()],
            [d._out_position for d in chip._devices.values()]
        ], axis=0)

        xs = all_ports[:,0]
        ys = all_ports[:,1]

        return (
            (xs.min() - tol, xs.max() + tol), # X-min, X-max
            (ys.min() - tol, ys.max() + tol) # Y-min, Y-max
        )

    def _get_obstacle_outline(
        self,
        position: Type[ChipCoordinate],
        orientation: Orientation,
        fiber_length = 1e4,
        fiber_radius = 75.0,
        safety_distance = 75.0
    ) -> tuple:
        outline_offset = fiber_radius + safety_distance


        if orientation == Orientation.LEFT:
            return (
                (position.x - outline_offset - fiber_length, position.x + outline_offset),
                (position.y - outline_offset, position.y + outline_offset)
            )

        if orientation == Orientation.RIGHT:
            return (
                (position.x - outline_offset, position.x + outline_offset + fiber_length),
                (position.y - outline_offset, position.y + outline_offset)
            )

        if orientation == Orientation.BOTTOM:
            raise NotImplementedError

        if orientation == Orientation.TOP:
            raise NotImplementedError


class PathPlanning:

    def __init__(
        self,
        start_goal_coordinates: Dict[Orientation, Tuple[Type[ChipCoordinate], Type[ChipCoordinate]]],
        chip: Type[Chip]
    ) -> None:
        self.chip = chip

        self.potenial_fields = {}
        self.current_move = {}
        self.field_converged = {}

        for orientation, (start, goal) in start_goal_coordinates.items():
            potenial_field = PotenialField(chip, start, goal)
            potenial_field.add_obstacles(
                {o: s for o, (s, _) in start_goal_coordinates.items() if o != orientation})

            self.potenial_fields[orientation] = potenial_field
            self.current_move[orientation] = start
            self.field_converged[orientation] = False

    def waypoints(self):
        """
        Generator to calculate all waypoints for all stages.
        """
        while not all(self.field_converged.values()):
            for orientation, potential_field in self.potenial_fields.items():
                next_waypoint, converged = next(potential_field.waypoints())

                self.field_converged[orientation] = converged
                self.current_move[orientation] = next_waypoint

                potential_field.add_obstacles(
                    {o: p for o, p in self.current_move.items() if o != orientation})

            yield self.current_move
