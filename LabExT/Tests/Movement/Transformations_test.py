#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

from typing import Type
import unittest
from  numpy.testing import assert_array_equal
from unittest.mock import Mock
import numpy as np
from parameterized import parameterized
from itertools import product, combinations, permutations
from scipy.spatial.transform import Rotation
from LabExT.Movement.Calibration import Calibration

from LabExT.Movement.config import Direction, Axis
from LabExT.Movement.Transformations import Coordinate, ChipCoordinate, KabschRotation,\
    StageCoordinate, CoordinatePairing, SinglePointOffset, AxesRotation, Transformation, TransformationError,\
    assert_valid_transformation, rigid_transform_with_orientation_preservation
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

    
    def test_to_storable_format(self):
        self.rotation.update(Axis.X, Direction.NEGATIVE, Axis.Y)
        self.rotation.update(Axis.Y, Direction.POSITIVE, Axis.Z)
        self.rotation.update(Axis.Z, Direction.NEGATIVE, Axis.X)

        self.assertTrue(self.rotation.is_valid)

        self.assertDictEqual(
            self.rotation.to_storable_format(),
            {
                'X': ('NEGATIVE', 'Y'),
                'Y': ('POSITIVE', 'Z'),
                'Z': ('NEGATIVE', 'X')
            })

    def test_from_storable_format(self):
        stored_mapping = {
            'Z': ('NEGATIVE', 'Z'),
            'Y': ('NEGATIVE', 'X'),
            'X': ('POSITIVE', 'Y')
        }

        rotation = AxesRotation.from_storable_format(stored_mapping)

        self.assertTrue(rotation.is_valid)
        assert_array_equal(rotation.matrix, [
            [0, -1, 0],
            [1,0,0],
            [0,0,-1]
        ])

    def test_from_storable_format_raises_error_if_invalid(self):
        stored_mapping = {
            'X': ('NEGATIVE', 'Z'),
            'Y': ('NEGATIVE', 'X'),
            'Z': ('POSITIVE', 'Z')
        }

        with self.assertRaises(TransformationError):
            AxesRotation.from_storable_format(stored_mapping)

    def test_to_storable_and_from_storable(self):
        self.rotation.update(Axis.X, Direction.NEGATIVE, Axis.Z)
        self.rotation.update(Axis.Y, Direction.NEGATIVE, Axis.X)
        self.rotation.update(Axis.Z, Direction.POSITIVE, Axis.Y)

        current_matrix = self.rotation.matrix

        self.assertTrue(self.rotation.is_valid)

        from_stored_rotation = AxesRotation.from_storable_format(
            self.rotation.to_storable_format())

        self.assertTrue(from_stored_rotation.is_valid)

        assert_array_equal(current_matrix, from_stored_rotation.matrix)


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

    def test_to_storable_format(self):
        chip_coordinate = ChipCoordinate.from_list([-1550, 1120, 0])
        stage_coordinate = StageCoordinate.from_list(
            [23236.35, -7888.67, 18956.06])

        self.transformation.update(CoordinatePairing(
            calibration=Mock(),
            stage_coordinate=stage_coordinate,
            device=Mock(),
            chip_coordinate=chip_coordinate))

        self.assertDictEqual(
            self.transformation.to_storable_format(),
            {
                "stage_coordinate": stage_coordinate.to_list(),
                "chip_coordinate": chip_coordinate.to_list()
            }
        )

    def test_from_storable_format(self):
        stored_format = {
            "stage_coordinate": [19,293.03,1029.02],
            "chip_coordinate": [110203,29342,0],
        }

        transformation = SinglePointOffset.from_storable_format(self.rotation, stored_format)

        assert_array_equal(
            transformation.stage_offset.to_numpy(),
            np.array([110203,29342,0]) - np.array([19,293.03,1029.02]))

    def test_to_storable_and_from_storable(self):
        chip_coordinate = ChipCoordinate.from_list([-1550, 1120, 0])
        stage_coordinate = StageCoordinate.from_list(
            [23236.35, -7888.67, 18956.06])

        self.transformation.update(CoordinatePairing(
            calibration=Mock(),
            stage_coordinate=stage_coordinate,
            device=Mock(),
            chip_coordinate=chip_coordinate))

        current_offset = self.transformation.stage_offset.to_numpy()

        from_stored_offset = SinglePointOffset.from_storable_format(
            self.transformation.axes_rotation,
            self.transformation.to_storable_format())

        assert_array_equal(current_offset, from_stored_offset.stage_offset.to_numpy())


class RigidTransformationTest(unittest.TestCase):
    
    def assert_rmse_less_than(self, set_a, set_b, bound):
        _, n = set_a.shape
        diff = np.array(set_a) - np.array(set_b)
        rmsd = np.sqrt((diff * diff).sum() / n)

        self.assertLess(rmsd, bound,
            f"Difference between start dataset and end dataset is greater than {bound} after recovery.")

    def test_with_random_rotation_and_translation(self):
        N = 10

        R = Rotation.random().as_matrix()
        t = np.random.rand(3,1)

        start_dataset = np.random.rand(3, N)
        target_dataset = (R @ start_dataset) + t

        R_ret, t_ret, R_inv_ret, t_inv_ret = rigid_transform_with_orientation_preservation(
            S=start_dataset,
            T=target_dataset)

        target_dataset_ret = R_ret @ start_dataset + t_ret
        start_dataset_ret = R_inv_ret @ target_dataset + t_inv_ret

        self.assert_rmse_less_than(target_dataset_ret, target_dataset, 1e-5)
        self.assert_rmse_less_than(start_dataset_ret, start_dataset, 1e-5)


class KabschRotationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transformation = KabschRotation()
        self.calibration = Mock(spec=Calibration)
        return super().setUp()

    def test_initialization(self):
        self.transformation.initialize()

        self.assertIsNone(self.transformation.rotation_to_chip)
        self.assertIsNone(self.transformation.rotation_to_stage)
        self.assertIsNone(self.transformation.translation_to_chip)
        self.assertIsNone(self.transformation.translation_to_stage)
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

        ret_stage_coordinate = self.transformation.chip_to_stage(test_chip_coordinate)
        ret_chip_coordinate = self.transformation.stage_to_chip(test_stage_coordinate)

        np.testing.assert_allclose(test_stage_coordinate.to_numpy(), ret_stage_coordinate.to_numpy(), atol=20, rtol=1e-3)
        np.testing.assert_allclose(test_chip_coordinate.to_numpy(), ret_chip_coordinate.to_numpy(), atol=20, rtol=1e-3)

    
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

    def test_to_storable_format(self):
        for stage_coord, chip_coord in zip(VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS):
            self.transformation.update(CoordinatePairing(
                calibration=Mock(),
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord)))

        self.assertEqual([
            {
                'stage_coordinate': [23236.35, -7888.67, 18956.06],
                'chip_coordinate': [-1550.0, 1120.0, 0.0]
            },
            {
                'stage_coordinate': [23744.6, -9172.55, 18956.1],
                'chip_coordinate': [-1050.0, -160.0, 0.0]
            }, 
            {
                'stage_coordinate': [25846.07, -10348.82, 18955.11],
                'chip_coordinate': [1046.25, -1337.5, 0.0]
            },
            {
                'stage_coordinate': [25837.8, -7721.47, 18972.08],
                'chip_coordinate': [1046.25, 1287.5, 0.0]
            }],
            self.transformation.to_storable_format())

    def test_to_storable_and_from_storable(self):
        for stage_coord, chip_coord in zip(VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS):
            self.transformation.update(CoordinatePairing(
                calibration=Mock(),
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord)))

        current_matrix = self.transformation.rotation.as_matrix()
        current_stage_offset = self.transformation.stage_offset
        current_chip_offset = self.transformation.chip_offset

        kabsch_from_stored = KabschRotation.from_storable_format(
            self.transformation.to_storable_format())

        assert_array_equal(current_matrix, kabsch_from_stored.rotation.as_matrix())
        assert_array_equal(current_stage_offset, kabsch_from_stored.stage_offset)
        assert_array_equal(current_chip_offset, kabsch_from_stored.chip_offset)


class KabschOrientationPerservationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        stage_coords = [
            StageCoordinate(*[17232.05, 258.53, 9674.18]),
            StageCoordinate(*[17229.81, 807.78, 9676.27]),
            StageCoordinate(*[20582.50, -2968.97, 9694.711])]

        chip_coords = [
            ChipCoordinate(*[-1050.00, 570, 0]),
            ChipCoordinate(*[-1050.00, 1120, 0]),
            ChipCoordinate(*[2295.00, -2650, 0])]

        cls.axes_rotation_matrix = np.array([
            [1,0,0],
            [0,1,0],
            [0,0,-1]
        ])

        cls.axes_rotation = AxesRotation()
        cls.axes_rotation.update(Axis.Z, Direction.NEGATIVE, Axis.Z)

        cls.kabsch = KabschRotation(cls.axes_rotation)
        for stage_coord, chip_coord in zip(stage_coords, chip_coords):
            cls.kabsch.update(CoordinatePairing(Mock(), stage_coord, Mock(), chip_coord))

    def test_axes_sanity_check(self):
        np.testing.assert_array_equal(self.axes_rotation.matrix, self.axes_rotation_matrix)

    def test_x_unit_direction(self):
        chip_x_unit = [1,0,0]

        kabsch_stage_x_unit = self.kabsch.rotation_to_stage.dot(chip_x_unit)
        user_stage_x_unit = self.axes_rotation.chip_to_stage(ChipCoordinate(*chip_x_unit))

        np.testing.assert_allclose(
            kabsch_stage_x_unit, user_stage_x_unit.to_numpy(),
            rtol=1e-5,
            atol=1)

    def test_y_unit_direction(self):
        chip_y_unit = [0,1,0]

        kabsch_stage_y_unit = self.kabsch.rotation_to_stage.dot(chip_y_unit)
        user_stage_y_unit = self.axes_rotation.chip_to_stage(ChipCoordinate(*chip_y_unit))

        np.testing.assert_allclose(
            kabsch_stage_y_unit, user_stage_y_unit.to_numpy(),
            rtol=1e-5,
            atol=1)

    def test_z_unit_direction(self):
        chip_z_unit = [0,0,1]

        kabsch_stage_z_unit = self.kabsch.rotation_to_stage.dot(chip_z_unit)
        user_stage_z_unit = self.axes_rotation.chip_to_stage(ChipCoordinate(*chip_z_unit))
        
        np.testing.assert_allclose(
            kabsch_stage_z_unit, user_stage_z_unit.to_numpy(),
            rtol=1e-5,
            atol=1)
