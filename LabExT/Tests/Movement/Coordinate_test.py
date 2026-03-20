#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""
import unittest
from typing import Type, List

import numpy as np
from numpy.typing import NDArray
from parameterized import parameterized

from LabExT.Movement.Coordinate import Coordinate, StageCoordinate, ChipCoordinate


class CoordinateTest(unittest.TestCase):

    list_parameterized = parameterized.expand([
        ([1, 2, 3, 4], 1, 2, 3),
        ([1, 2, 3], 1, 2, 3),
        ([1, 2], 1, 2, 0),
        ([1], 1, 0, 0),
        ([], 0, 0, 0)
    ])
    array_parameterized = parameterized.expand([
        (np.array([1, 2, 3, 4]), 1, 2, 3),
        (np.array([1, 2, 3]), 1, 2, 3),
        (np.array([1, 2]), 1, 2, 0),
        (np.array([1]), 1, 0, 0),
        (np.array([]), 0, 0, 0)
    ])

    def test_cannot_instantiate_base_class(self):
        with self.assertRaises(TypeError):
            Coordinate()

        with self.assertRaises(TypeError):
            Coordinate.from_list([1, 2, 3])

        with self.assertRaises(TypeError):
            Coordinate.from_numpy(np.array([1, 2, 3]))

    @parameterized.expand([(np.array([[1]]),), (np.array([[1], [2], [3]]),)])
    def test_from_numpy_accepts_only_1D_arrays(self, array: NDArray[np.float64]):
        with self.assertRaises(ValueError):
            Coordinate.from_numpy(array)

    @parameterized.expand([
        (StageCoordinate(1, 2, 3), ChipCoordinate(1, 2, 3)),
        (ChipCoordinate(1, 2, 3), StageCoordinate(1, 2, 3)),
        (StageCoordinate(1, 2, 3), StageCoordinate(4, 5, 6)),
        (ChipCoordinate(1, 2, 3), ChipCoordinate(4, 5, 6)),
    ])
    def test_unequal_coordinates(self, coord_1: Coordinate, coord_2: Coordinate):
        self.assertNotEqual(coord_1, coord_2)

    @parameterized.expand([
        (StageCoordinate(1, 2, 3), StageCoordinate(1, 2, 3)),
        (ChipCoordinate(1, 2, 3), ChipCoordinate(1, 2, 3)),
    ])
    def test_equal_coordinates(self, coord_1: Coordinate, coord_2: Coordinate):
        self.assertEqual(coord_1, coord_2)

    def assert_build_from_list(
            self,
            coordinate_type: Type[Coordinate],
            _list: List[float],
            x: float,
            y: float,
            z: float
    ):
        self._assert_coordinate_with_correct_values(
            coordinate_type.from_list(_list), x, y, z)

    def assert_build_from_numpy(
            self,
            coordinate_type: Type[Coordinate],
            array: NDArray[np.float64],
            x: float,
            y: float,
            z: float
    ):
        self._assert_coordinate_with_correct_values(coordinate_type.from_numpy(array), x, y, z)

    def _assert_coordinate_with_correct_values(self, coordinate: Coordinate, x: float, y: float, z: float):
        self.assertEqual(coordinate.x, x)
        self.assertEqual(coordinate.y, y)
        self.assertEqual(coordinate.z, z)


class StageCoordinateTest(CoordinateTest):
    @CoordinateTest.list_parameterized
    def test_from_list(self, _list: List[float], x: float, y: float, z: float):
        self.assert_build_from_list(StageCoordinate, _list, x, y, z)

    @CoordinateTest.array_parameterized
    def test_from_numpy(self, array: NDArray[np.float64], x: float, y: float, z: float):
        self.assert_build_from_numpy(StageCoordinate, array, x, y, z)

    def test_to_list(self):
        self.assertEqual(StageCoordinate(1, 2, 3).to_list(), [1, 2, 3])

    def test_to_numpy(self):
        self.assertTrue(np.array_equal(StageCoordinate(1, 2, 3).to_numpy(), np.array([1, 2, 3])))

    @parameterized.expand([(ChipCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)])
    def test_add_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            StageCoordinate(1, 2, 3) + other

    @parameterized.expand([(ChipCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)])
    def test_sub_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            StageCoordinate(1, 2, 3) - other

    def test_add_with_compatible_types(self):
        _sum = StageCoordinate.from_list([1, 2, 3]) + StageCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(_sum, StageCoordinate)
        self.assertEqual(_sum.to_list(), [2, 4, 6])

    def test_sub_with_compatible_types(self):
        diff = StageCoordinate.from_list([1, 2, 3]) - StageCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(diff, StageCoordinate)
        self.assertEqual(diff.to_list(), [0, 0, 0])

    def test_multiplication_with_scalar(self):
        mult = StageCoordinate(1, 2, 3) * 2
        self.assertIsInstance(mult, StageCoordinate)
        self.assertEqual(mult.to_list(), [2, 4, 6])


class ChipCoordinateTest(CoordinateTest):
    @CoordinateTest.list_parameterized
    def test_from_list(self, _list: List[float], x: float, y: float, z: float):
        self.assert_build_from_list(ChipCoordinate, _list, x, y, z)

    @CoordinateTest.array_parameterized
    def test_from_numpy(self, array: NDArray[np.float64], x: float, y: float, z: float):
        self.assert_build_from_numpy(ChipCoordinate, array, x, y, z)

    def test_to_list(self):
        self.assertEqual(ChipCoordinate(1, 2, 3).to_list(), [1, 2, 3])

    def test_to_numpy(self):
        self.assertTrue(np.array_equal(ChipCoordinate(1, 2, 3).to_numpy(), np.array([1, 2, 3])))

    @parameterized.expand([(StageCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)])
    def test_add_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            ChipCoordinate(1, 2, 3) + other

    @parameterized.expand([(StageCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)])
    def test_sub_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            ChipCoordinate(1, 2, 3) - other

    def test_add_with_compatible_types(self):
        _sum = ChipCoordinate.from_list([1, 2, 3]) + ChipCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(_sum, ChipCoordinate)
        self.assertEqual(_sum.to_list(), [2, 4, 6])

    def test_sub_with_compatible_types(self):
        diff = ChipCoordinate.from_list([1, 2, 3]) - ChipCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(diff, ChipCoordinate)
        self.assertEqual(diff.to_list(), [0, 0, 0])

    def test_multiplication_with_scalar(self):
        mult = ChipCoordinate(1, 2, 3) * 2
        self.assertIsInstance(mult, ChipCoordinate)
        self.assertEqual(mult.to_list(), [2, 4, 6])
