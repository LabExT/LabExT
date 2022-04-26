#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from typing import Type
import unittest
import numpy as np
from parameterized import parameterized

from LabExT.Movement.Transformations import Coordinate, ChipCoordinate,\
    StageCoordinate, CoordinatePairing, SinglePointFixation


class CoordinateTest(unittest.TestCase):

    list_parameterized = parameterized.expand([
        ([1, 2, 3, 4], 1, 2, 3),
        ([1, 2, 3], 1, 2, 3),
        ([1, 2], 1, 2, 0),
        ([1], 1, 0, 0),
        ([], 0, 0, 0)])
    array_parameterized = parameterized.expand([
        (np.array([1, 2, 3, 4]), 1, 2, 3),
        (np.array([1, 2, 3]), 1, 2, 3),
        (np.array([1, 2]), 1, 2, 0),
        (np.array([1]), 1, 0, 0),
        (np.array([]), 0, 0, 0)])

    def test_cannot_instantiate_base_class(self):
        with self.assertRaises(TypeError):
            Coordinate()

        with self.assertRaises(TypeError):
            Coordinate.from_list([1, 2, 3])

        with self.assertRaises(TypeError):
            Coordinate.from_numpy(np.array([1, 2, 3]))

    @parameterized.expand([
        (np.array([[1]]),), (np.array([[1], [2], [3]]),)
    ])
    def test_from_numpy_accepts_only_1D_arrays(self, array):
        with self.assertRaises(ValueError):
            Coordinate.from_numpy(array)

    @parameterized.expand([
        (StageCoordinate(1, 2, 3), ChipCoordinate(1, 2, 3)),
        (ChipCoordinate(1, 2, 3), StageCoordinate(1, 2, 3)),
        (StageCoordinate(1, 2, 3), StageCoordinate(4, 5, 6)),
        (ChipCoordinate(1, 2, 3), ChipCoordinate(4, 5, 6)),
    ])
    def test_unequal_coordinates(self, coord_1, coord_2):
        self.assertNotEqual(coord_1, coord_2)

    @parameterized.expand([
        (StageCoordinate(1, 2, 3), StageCoordinate(1, 2, 3)),
        (ChipCoordinate(1, 2, 3), ChipCoordinate(1, 2, 3)),
    ])
    def test_equal_coordinates(self, coord_1, coord_2):
        self.assertEqual(coord_1, coord_2)

    def assert_build_from_list(
            self,
            coordinate_type: Coordinate,
            list,
            x,
            y,
            z):
        self._assert_coordinate_with_correct_values(
            coordinate_type.from_list(list), x, y, z)

    def assert_build_from_numpy(
            self,
            coordinate_type: Coordinate,
            array,
            x,
            y,
            z):
        self._assert_coordinate_with_correct_values(
            coordinate_type.from_numpy(array), x, y, z)

    def _assert_coordinate_with_correct_values(
            self, coordinate: Type[Coordinate], x, y, z):
        self.assertEqual(coordinate.x, x)
        self.assertEqual(coordinate.y, y)
        self.assertEqual(coordinate.z, z)


class StageCooridnateTest(CoordinateTest):
    @CoordinateTest.list_parameterized
    def test_from_list(self, list, x, y, z):
        self.assert_build_from_list(StageCoordinate, list, x, y, z)

    @CoordinateTest.array_parameterized
    def test_from_numpy(self, array, x, y, z):
        self.assert_build_from_numpy(StageCoordinate, array, x, y, z)

    def test_to_list(self):
        self.assertEqual(StageCoordinate(1, 2, 3).to_list(), [1, 2, 3])

    def test_to_numpy(self):
        self.assertTrue(np.array_equal(
            StageCoordinate(1, 2, 3).to_numpy(), np.array([1, 2, 3])
        ))

    @parameterized.expand([
        (ChipCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)
    ])
    def test_add_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            StageCoordinate(1, 2, 3) + other

    @parameterized.expand([
        (ChipCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)
    ])
    def test_sub_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            StageCoordinate(1, 2, 3) - other

    def test_add_with_compatible_types(self):
        sum = StageCoordinate.from_list(
            [1, 2, 3]) + StageCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(sum, StageCoordinate)
        self.assertEqual(sum.to_list(), [2, 4, 6])

    def test_sub_with_compatible_types(self):
        diff = StageCoordinate.from_list(
            [1, 2, 3]) - StageCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(diff, StageCoordinate)
        self.assertEqual(diff.to_list(), [0, 0, 0])

    def test_multiplication_with_scalar(self):
        mult = StageCoordinate(1, 2, 3) * 2
        self.assertIsInstance(mult, StageCoordinate)
        self.assertEqual(mult.to_list(), [2, 4, 6])


class ChipCoordinateTest(CoordinateTest):
    @CoordinateTest.list_parameterized
    def test_from_list(self, list, x, y, z):
        self.assert_build_from_list(ChipCoordinate, list, x, y, z)

    @CoordinateTest.array_parameterized
    def test_from_numpy(self, array, x, y, z):
        self.assert_build_from_numpy(ChipCoordinate, array, x, y, z)

    def test_to_list(self):
        self.assertEqual(ChipCoordinate(1, 2, 3).to_list(), [1, 2, 3])

    def test_to_numpy(self):
        self.assertTrue(np.array_equal(
            ChipCoordinate(1, 2, 3).to_numpy(), np.array([1, 2, 3])
        ))

    @parameterized.expand([
        (StageCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)
    ])
    def test_add_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            ChipCoordinate(1, 2, 3) + other

    @parameterized.expand([
        (StageCoordinate(1, 2, 3),), ([1, 2, 3],), (np.array([1, 2, 3]),)
    ])
    def test_sub_with_incompatible_types(self, other):
        with self.assertRaises(TypeError):
            ChipCoordinate(1, 2, 3) - other

    def test_add_with_compatible_types(self):
        sum = ChipCoordinate.from_list(
            [1, 2, 3]) + ChipCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(sum, ChipCoordinate)
        self.assertEqual(sum.to_list(), [2, 4, 6])

    def test_sub_with_compatible_types(self):
        diff = ChipCoordinate.from_list(
            [1, 2, 3]) - ChipCoordinate.from_list([1, 2, 3])
        self.assertIsInstance(diff, ChipCoordinate)
        self.assertEqual(diff.to_list(), [0, 0, 0])

    def test_multiplication_with_scalar(self):
        mult = ChipCoordinate(1, 2, 3) * 2
        self.assertIsInstance(mult, ChipCoordinate)
        self.assertEqual(mult.to_list(), [2, 4, 6])


class SinglePointFixationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixation = SinglePointFixation()

    def test_is_valid_for_no_offset(self):
        self.assertFalse(self.fixation.is_valid)

    def test_update_missing_chip_coordinate(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=[1, 2],
            device=None,
            chip_coordinate=None
        )

        with self.assertRaises(ValueError):
            self.fixation.update(pairing)

        self.assertFalse(self.fixation.is_valid)

    def test_update_missing_stage_coordinate(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=None,
            device=None,
            chip_coordinate=[1, 2]
        )

        with self.assertRaises(ValueError):
            self.fixation.update(pairing)

        self.assertFalse(self.fixation.is_valid)

    def test_update(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=[2, 4],
            device=None,
            chip_coordinate=[1, 5]
        )

        self.fixation.update(pairing)

        self.assertTrue(self.fixation.is_valid)

    def test_chip_to_stage_when_invalid(self):
        with self.assertRaises(RuntimeError):
            self.fixation.chip_to_stage([1, 2])

    def test_stage_to_chip_when_invalid(self):
        with self.assertRaises(RuntimeError):
            self.fixation.stage_to_chip([1, 2])

    def test_chip_to_stage_translates_chip_coordinate(self):
        stage_coordinate = [2, 4]
        chip_coordinate = [1, 5]
        expected_offset = np.array(stage_coordinate) - \
            np.array(chip_coordinate)

        self.fixation.update(CoordinatePairing(
            None, stage_coordinate, None, chip_coordinate
        ))

        self.assertTrue(
            (self.fixation.chip_to_stage([5, 6]) ==
             np.array([5, 6]) + expected_offset).all()
        )

    def test_stage_to_chip_translates_chip_coordinate(self):
        stage_coordinate = [2, 4]
        chip_coordinate = [1, 5]
        expected_offset = np.array(stage_coordinate) - \
            np.array(chip_coordinate)

        self.fixation.update(CoordinatePairing(
            None, stage_coordinate, None, chip_coordinate
        ))

        self.assertTrue(
            (self.fixation.stage_to_chip([5, 6]) ==
             np.array([5, 6]) + expected_offset).all()
        )
