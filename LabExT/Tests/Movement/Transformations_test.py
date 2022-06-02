#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from typing import Type
import unittest
from unittest.mock import Mock
import numpy as np
from parameterized import parameterized
from itertools import product, combinations, permutations
from scipy.spatial.transform import Rotation
from LabExT.Movement.Calibration import Calibration

from LabExT.Movement.config import Direction, Axis
from LabExT.Movement.Transformations import Coordinate, ChipCoordinate, KabschRotation,\
    StageCoordinate, CoordinatePairing, SinglePointOffset, AxesRotation, Transformation, TransformationError, assert_valid_transformation
from LabExT.Tests.Utils import get_calibrations_from_file


POSSIBLE_AXIS_ROTATIONS = list(product(
    permutations(Axis), product(
        Direction, repeat=3)))

VACHERIN_ROTATION, VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS = get_calibrations_from_file("vacherin.json", "left")

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


class StageCoordinateTest(CoordinateTest):
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


class TransformationTest(unittest.TestCase):
    pass


class AssertValidTransformationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.func = Mock()
        self.transformation = Mock(spec=Transformation)
        return super().setUp()

    def test_with_invalid_transformation(self):
        self.transformation.is_valid = False

        with self.assertRaises(TransformationError):
            assert_valid_transformation(self.func)(self.transformation)

        self.func.assert_not_called()

    def test_with_valid_transformation(self):
        self.transformation.is_valid = True

        assert_valid_transformation(self.func)(self.transformation)

        self.func.assert_called_once()


class AxesRotationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = AxesRotation()
        return super().setUp()

    def test_initialization(self):
        self.rotation.initialize()

        self.assertTrue((self.rotation.matrix == np.identity(3)).all())
        self.assertTrue(self.rotation.is_valid)

    @parameterized.expand(product(combinations(Axis, 2), Direction))
    def test_switch_axes(self, mapping, direction):
        chip_axis, stage_axis = mapping

        self.rotation.update(chip_axis, direction, stage_axis)
        self.assertFalse(self.rotation.is_valid)
        self.rotation.update(stage_axis, direction, chip_axis)
        self.assertTrue(self.rotation.is_valid)

        chip_axis_unit = ChipCoordinate.from_list(
            [1 if axis == chip_axis else 0 for axis in Axis])
        stage_axis_unit = StageCoordinate.from_list(
            [1 if axis == stage_axis else 0 for axis in Axis])

        self.assertEqual(
            self.rotation.chip_to_stage(chip_axis_unit),
            stage_axis_unit * direction.value)
        self.assertEqual(
            self.rotation.stage_to_chip(stage_axis_unit),
            chip_axis_unit * direction.value)

    @parameterized.expand(zip(
        POSSIBLE_AXIS_ROTATIONS,
        [np.array(d) * np.array(p) for p in permutations([1,2,3]) for d in product([-1,1],repeat=3)]))
    def test_possible_axes_assignments(
            self,
            stage_axes_mapping,
            expected_chip_coordinate):
        stage_axes, direction = stage_axes_mapping
        for idx, chip_axis in enumerate(Axis):
            self.rotation.update(chip_axis, direction[idx], stage_axes[idx])

        self.assertTrue(self.rotation.is_valid)

        chip_coord = ChipCoordinate.from_list(expected_chip_coordinate)
        stage_coord = StageCoordinate(1, 2, 3)

        self.assertEqual(self.rotation.stage_to_chip(stage_coord), chip_coord)
        self.assertEqual(self.rotation.chip_to_stage(chip_coord), stage_coord)


class SinglePointOffsetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = AxesRotation()
        self.transformation = SinglePointOffset(self.rotation)
        return super().setUp()

    def test_initialization(self):
        self.transformation.initialize()

        self.assertIsNone(self.transformation.stage_offset)
        self.assertFalse(self.transformation.is_valid)

    @parameterized.expand([
        (CoordinatePairing(None, None, None, None),),
        (CoordinatePairing(None, StageCoordinate(1, 2, 3), None, None),),
        (CoordinatePairing(None, None, None, ChipCoordinate(1, 2, 3)),),
    ])
    def test_update_with_invalid_pairings(self, invalid_pairing):
        with self.assertRaises(ValueError):
            self.transformation.update(invalid_pairing)

        self.assertIsNone(self.transformation.pairing)
        self.assertIsNone(self.transformation.stage_offset)

    @parameterized.expand(POSSIBLE_AXIS_ROTATIONS)
    def test_reversibility(self, stage_axes, directions):
        for idx, chip_axis in enumerate(Axis):
            self.rotation.update(chip_axis, directions[idx], stage_axes[idx])

        chip_coordinate = ChipCoordinate.from_list([-1550, 1120, 0])
        stage_coordinate = StageCoordinate.from_list(
            [23236.35, -7888.67, 18956.06])

        self.transformation.update(CoordinatePairing(
            calibration=Mock(),
            stage_coordinate=stage_coordinate,
            device=Mock(),
            chip_coordinate=chip_coordinate))

        self.assertEqual(
            self.transformation.chip_to_stage(chip_coordinate),
            stage_coordinate)
        self.assertEqual(self.transformation.stage_to_chip(
            stage_coordinate), chip_coordinate)

    @parameterized.expand([
        (-1050, 570, 0),
        (2295, 1287.5, 0),
        (1046.25, -1337.5, 0),
        (-50, 1120, 0)
    ])
    def test_against_kabsch_rotation(self, chip_x, chip_y, chip_z):
        self.rotation.matrix = VACHERIN_ROTATION

        stage_offset = VACHERIN_STAGE_COORDS.mean(axis=0)
        chip_offset = VACHERIN_CHIP_COORDS.mean(axis=0)
        kabsch, _ = Rotation.align_vectors(
            VACHERIN_CHIP_COORDS - chip_offset, VACHERIN_STAGE_COORDS - stage_offset)

        device_coordinate = ChipCoordinate(chip_x, chip_y, chip_z)

        expected_stage_coordinate = kabsch.apply(
            device_coordinate.to_numpy()) + stage_offset

        self.transformation.update(CoordinatePairing(
            calibration=Mock(),
            stage_coordinate=StageCoordinate(*VACHERIN_STAGE_COORDS[0]),
            device=None,
            chip_coordinate=ChipCoordinate(*VACHERIN_CHIP_COORDS[0])))

        self.assertTrue(np.allclose(
            expected_stage_coordinate,
            self.transformation.chip_to_stage(device_coordinate).to_numpy(),
            rtol=1,
            atol=1))


class KabschRotationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transformation = KabschRotation()
        self.calibration = Mock(spec=Calibration)
        return super().setUp()

    def test_initialization(self):
        self.transformation.initialize()

        self.assertIsNone(self.transformation.rotation)
        self.assertIsNone(self.transformation.chip_offset)
        self.assertIsNone(self.transformation.stage_offset)
        self.assertIsNone(self.transformation.rmsd)
        self.assertEqual(self.transformation.pairings, [])

        self.assertFalse(self.transformation.is_valid)

    @parameterized.expand([
        (CoordinatePairing(None, None, None, None),),
        (CoordinatePairing(None, StageCoordinate(1, 2, 3), None, None),),
        (CoordinatePairing(None, None, None, ChipCoordinate(1, 2, 3)),),
        (CoordinatePairing(None, StageCoordinate(1, 2, 3), None, ChipCoordinate(1, 2, 3)),),
        (CoordinatePairing(Mock(), StageCoordinate(1, 2, 3), None, ChipCoordinate(1, 2, 3)),),
        (CoordinatePairing(None, StageCoordinate(1, 2, 3), Mock(), ChipCoordinate(1, 2, 3)),),
    ])
    def test_update_with_invalid_pairing(self, invalid_pairing):
        with self.assertRaises(ValueError):
            self.transformation.update(invalid_pairing)

        self.assertNotIn(invalid_pairing, self.transformation.pairings)

    def test_update_with_double_device(self):
        device = Mock()
        pairing = CoordinatePairing(
            calibration=self.calibration,
            stage_coordinate=StageCoordinate(1,2,3),
            device=device,
            chip_coordinate=ChipCoordinate(4,5,6))

        self.transformation.update(pairing)
        self.assertIn(pairing, self.transformation.pairings)

        pairing_2 = CoordinatePairing(
            calibration=self.calibration,
            stage_coordinate=StageCoordinate(7,8,9),
            device=device,
            chip_coordinate=ChipCoordinate(8,7,6))

        with self.assertRaises(ValueError):
            self.transformation.update(pairing_2)

        self.assertNotIn(pairing_2, self.transformation.pairings)

    @parameterized.expand([(np.delete(VACHERIN_STAGE_COORDS, (i), axis=0), np.delete(VACHERIN_CHIP_COORDS, (i), axis=0), VACHERIN_STAGE_COORDS[i,:], VACHERIN_CHIP_COORDS[i,:]) for i in range(0,4)])
    def test_transformation_estimates_fourth_variable(self, stage_coordinates, chip_coordinates, test_stage_coordinate, test_chip_coordinate):
        for stage_coord, chip_coord in zip(stage_coordinates, chip_coordinates):
            pairing = CoordinatePairing(
                calibration=Mock(),
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord))

            self.transformation.update(pairing)
            self.assertIn(pairing, self.transformation.pairings)

        self.assertTrue(self.transformation.is_valid)

        test_stage_coordinate = StageCoordinate.from_numpy(test_stage_coordinate)
        test_chip_coordinate = ChipCoordinate.from_numpy(test_chip_coordinate)

        self.assertTrue(np.allclose(test_stage_coordinate.to_numpy(), self.transformation.chip_to_stage(test_chip_coordinate).to_numpy(), rtol=1, atol=1))
        self.assertTrue(np.allclose(test_chip_coordinate.to_numpy(), self.transformation.stage_to_chip(test_stage_coordinate).to_numpy(), rtol=1, atol=1))

    
    def test_reversibility(self):
        for stage_coord, chip_coord in zip(VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS):
            self.transformation.update(CoordinatePairing(
                calibration=Mock(),
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord)))

        chip_coordinate = ChipCoordinate(1,2,3)
        stage_coordinate = StageCoordinate(4,5,6)

        self.assertTrue(np.allclose(
            self.transformation.stage_to_chip(self.transformation.chip_to_stage(chip_coordinate)).to_numpy(),
            chip_coordinate.to_numpy()))
        self.assertTrue(np.allclose(
            self.transformation.chip_to_stage(self.transformation.stage_to_chip(stage_coordinate)).to_numpy(),
            stage_coordinate.to_numpy()))


class KabschOrientationTest(unittest.TestCase):

    def setUp(self) -> None:
        self.stage_coords = np.array([
            [17232.05, 258.53, 9674.18],
            [17229.81, 807.78, 9676.27],
            [20582.50, -2968.97, 9694.711]
        ])
        self.stage_offset = self.stage_coords.mean(axis=0)

        self.chip_coords = np.array([
            [-1050.00, 570, 0],
            [-1050.00, 1120, 0],
            [2295.00, -2650, 0]
        ])
        self.chip_offset = self.chip_coords.mean(axis=0)

        self.rotation, self._rmsd = Rotation.align_vectors(
            (self.chip_coords - self.chip_offset),
            (self.stage_coords - self.stage_offset))

        self.axes_rotation = np.array([
            [1,0,0],
            [0,1,0],
            [0,0,-1]
        ])


    def test_x_unit_direction(self):
        chip_x_unit = [1,0,0]

        abs_stage_x_unit = self.rotation.apply(chip_x_unit, inverse=True)
        rel_stage_x_unit = self.axes_rotation.dot(chip_x_unit)

        self.assertTrue(np.allclose(rel_stage_x_unit, abs_stage_x_unit, rtol=1))

    def test_y_unit_direction(self):
        chip_y_unit = [0,1,0]

        abs_stage_y_unit = self.rotation.apply(chip_y_unit, inverse=True)
        rel_stage_y_unit = self.axes_rotation.dot(chip_y_unit)

        self.assertTrue(np.allclose(rel_stage_y_unit, abs_stage_y_unit, rtol=1))

    def test_z_unit_direction(self):
        chip_z_unit = [0,0,1]

        abs_stage_z_unit = self.rotation.apply(chip_z_unit, inverse=True)
        rel_stage_z_unit = self.axes_rotation.dot(chip_z_unit)

        self.assertTrue(np.allclose(abs_stage_z_unit, rel_stage_z_unit, rtol=1))
