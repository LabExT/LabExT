#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import numpy as np

from unittest import TestCase

from parameterized import parameterized

from LabExT.Movement.config import Orientation
from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.PathPlanning import SingleModeFiber


class SingleModeFiberTest(TestCase):
    def test_left_outline_with_default_parameters(self):
        polygon = SingleModeFiber(Orientation.LEFT)
        x_min, x_max, y_min, y_max = polygon._create_outline(
            position=ChipCoordinate(0, 0, 0),
            grid_size=50)

        self.assertEqual(x_min, -80150.0)
        self.assertEqual(x_max, 150.0)
        self.assertEqual(y_min, -150.0)
        self.assertEqual(y_max, 150.0)

    def test_right_outline_with_default_parameters(self):
        polygon = SingleModeFiber(Orientation.RIGHT)
        x_min, x_max, y_min, y_max = polygon._create_outline(
            position=ChipCoordinate(0, 0, 0),
            grid_size=50)

        self.assertEqual(x_min, -150.0)
        self.assertEqual(x_max, 80150.0)
        self.assertEqual(y_min, -150.0)
        self.assertEqual(y_max, 150.0)

    def test_top_outline_with_default_parameters(self):
        polygon = SingleModeFiber(Orientation.TOP)
        x_min, x_max, y_min, y_max = polygon._create_outline(
            position=ChipCoordinate(0, 0, 0),
            grid_size=50)

        self.assertEqual(x_min, -150.0)
        self.assertEqual(x_max, 150.0)
        self.assertEqual(y_min, -150.0)
        self.assertEqual(y_max, 80150.0)

    def test_bottom_outline_with_default_parameters(self):
        polygon = SingleModeFiber(Orientation.BOTTOM)
        x_min, x_max, y_min, y_max = polygon._create_outline(
            position=ChipCoordinate(0, 0, 0),
            grid_size=50)

        self.assertEqual(x_min, -150.0)
        self.assertEqual(x_max, 150.0)
        self.assertEqual(y_min, -80150.0)
        self.assertEqual(y_max, 150.0)

    @parameterized.expand([
        (Orientation.LEFT,),
        (Orientation.RIGHT,),
        (Orientation.TOP,),
        (Orientation.BOTTOM,)
    ])
    def test_adjustment_to_gridsize(self, orientation):
        grid_size = 100
        polygon = SingleModeFiber(orientation, parameters={
            "Fiber Radius": 25.0,
            "Safety Distance": 25.0
        })

        x_min, x_max, y_min, y_max = polygon._create_outline(
            position=ChipCoordinate(0, 0, 0),
            grid_size=grid_size)

        self.assertGreater(abs(x_max - x_min), grid_size)
        self.assertGreater(abs(y_min - y_max), grid_size)

    def test_tiny_polygon_in_large_grid(self):
        grid_outline = (-100, 100), (-100, 100)
        grid_size = 10
        xs = np.arange(
            grid_outline[0][0],
            grid_outline[0][1] +
            grid_size,
            grid_size)
        ys = np.arange(
            grid_outline[1][0],
            grid_outline[1][1] +
            grid_size,
            grid_size)
        cx, cy = np.meshgrid(xs, ys)

        polygon = SingleModeFiber(Orientation.LEFT, parameters={
            "Fiber Radius": 1,
            "Safety Distance": 0,
            "Fiber Length": 0
        })

        mask = polygon.stage_in_meshgrid(
            ChipCoordinate(0, 0, 0), cx, cy, grid_size)

        self.assertTrue(mask.any())
