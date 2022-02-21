#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from random import sample
from unittest.mock import Mock
from LabExT import rmsd
import pytest
import unittest
import numpy as np
from os.path import join

from LabExT.Wafer.Chip import Chip
from LabExT.Movement.Transformations import CoordinatePairing, Dimension, KabschRotation, SinglePointFixation, make_3d_coordinate


def kabsch_model(
        p_1_stage,
        p_1_chip,
        p_2_stage,
        p_2_chip,
        p_3_stage=None,
        p_3_chip=None):
    stage_coords = np.array([p_1_stage, p_2_stage])
    chip_coords = np.array([p_1_chip, p_2_chip])

    if p_3_stage is not None:
        stage_coords = np.append(stage_coords, [p_3_stage], axis=0)

    if p_3_chip is not None:
        chip_coords = np.append(chip_coords, [p_3_chip], axis=0)

    # translate coordinates to origin
    stage_offset = rmsd.centroid(stage_coords)
    stage_coords = stage_coords - stage_offset
    chip_offset = rmsd.centroid(chip_coords)
    chip_coords = chip_coords - chip_offset

    # calculate rotation matrix using kabsch algorithm
    matrix = rmsd.kabsch(chip_coords, stage_coords)

    return matrix, chip_offset, stage_offset


class Make3DCoordinateTest(unittest.TestCase):
    def test_make_3d_coordinate_reject_empty_coordinate(self):
        with self.assertRaises(ValueError):
            make_3d_coordinate(None)

        with self.assertRaises(ValueError):
            make_3d_coordinate([])

    def test_make_3d_coordinate_reject_1d_coordinate(self):
        with self.assertRaises(ValueError):
            make_3d_coordinate([1])

    def test_make_3d_coordinate_adds_zero_to_2d(self):
        self.assertTrue(
            (make_3d_coordinate([1, 2]) == np.array([1, 2, 0])).all())

    def test_make_3d_keeps_3d_unchanged(self):
        self.assertTrue(
            (make_3d_coordinate([1, 2, 3]) == np.array([1, 2, 3])).all())

    def test_make_3d_adds_requested_z_to_2d(self):
        self.assertTrue((make_3d_coordinate(
            [1, 2], set_z=100) == np.array([1, 2, 100])).all())

    def test_make_3d_reject_4d(self):
        with self.assertRaises(ValueError):
            make_3d_coordinate([1, 2, 3, 4])

    def test_make_3d_reject_matrices(self):
        with self.assertRaises(ValueError):
            make_3d_coordinate(np.array([[1, 2]]))

        with self.assertRaises(ValueError):
            make_3d_coordinate(np.array([[1], [2]]))

        with self.assertRaises(ValueError):
            make_3d_coordinate(np.array([[1, 2, 3]]))

        with self.assertRaises(ValueError):
            make_3d_coordinate(np.array([[1], [2], [3]]))


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
             np.append(np.array([5, 6]) + expected_offset, 0)).all()
        )

    def test_stage_to_chip_translates_stage_coordinate(self):
        stage_coordinate = [2, 4]
        chip_coordinate = [1, 5]
        expected_offset = np.array(stage_coordinate) - \
            np.array(chip_coordinate)

        self.fixation.update(CoordinatePairing(
            None, stage_coordinate, None, chip_coordinate
        ))

        self.assertTrue(
            (self.fixation.stage_to_chip([5, 6]) ==
             np.append(np.array([5, 6]) - expected_offset, 0)).all()
        )

    def test_chip_to_stage_and_stage_to_chip_are_inversed(self):
        self.fixation.update(CoordinatePairing(
            None, [7, 1], None, [4, 2]
        ))

        chip_input_coordinate = [2, 3, 0]
        self.assertTrue((chip_input_coordinate == self.fixation.stage_to_chip(
            self.fixation.chip_to_stage(chip_input_coordinate))).all())

        stage_input_coordinate = [2, 3, 0]
        self.assertTrue((stage_input_coordinate == self.fixation.chip_to_stage(
            self.fixation.stage_to_chip(stage_input_coordinate))).all())


class KabschRotationBaseTest(unittest.TestCase):
    """
    Testing properties for Kabsch Rotation which holds for 2D and 3D.
    """

    def setUp(self) -> None:
        self.rotation = KabschRotation()
        self.chip = Chip(join(pytest.fixture_folder, "QuarkJaejaChip.csv"))
        self.calibration = Mock()

    def test_change_rotation_dimension_reject_invalid_values(self):
        with self.assertRaises((TypeError, ValueError)):
            self.rotation.change_rotation_dimension(2)

        with self.assertRaises((TypeError, ValueError)):
            self.rotation.change_rotation_dimension(3)

        with self.assertRaises((TypeError, ValueError)):
            self.rotation.change_rotation_dimension('foo')

    def test_change_rotation_dimension_to_2D(self):
        self.rotation.change_rotation_dimension(Dimension.TWO)

        self.assertTrue(self.rotation.is_2D)
        self.assertFalse(self.rotation.is_3D)

    def test_change_rotation_dimension_to_3D(self):
        self.rotation.change_rotation_dimension(Dimension.THREE)

        self.assertTrue(self.rotation.is_3D)
        self.assertFalse(self.rotation.is_2D)

    def test_update_reject_incomplete_pairings(self):
        with self.assertRaises(ValueError) as error:
            self.rotation.update(CoordinatePairing(
                None, [1, 2, 3], self.chip._devices.get(1000), [4, 5, 6]))
            self.assertEqual(str(error.exception),
                             "Use a complete CoordinatePairing object to update the rotation. ")

        with self.assertRaises(ValueError) as error:
            self.rotation.update(
                CoordinatePairing(
                    self.calibration, None, self.chip._devices.get(1000), [
                        4, 5, 6]))
            self.assertEqual(str(error.exception),
                             "Use a complete CoordinatePairing object to update the rotation. ")

        with self.assertRaises(ValueError) as error:
            self.rotation.update(CoordinatePairing(
                self.calibration, [1, 2, 3], None, [4, 5, 6]))
            self.assertEqual(str(error.exception),
                             "Use a complete CoordinatePairing object to update the rotation. ")

        with self.assertRaises(ValueError) as error:
            self.rotation.update(
                CoordinatePairing(
                    self.calibration, [
                        1, 2, 3], self.chip._devices.get(1000), None))
            self.assertEqual(str(error.exception),
                             "Use a complete CoordinatePairing object to update the rotation. ")

        self.assertEqual([], self.rotation.pairings)

    def test_update_rejects_pairing_if_device_was_used_before(self):
        pairing = CoordinatePairing(
            self.calibration, [
                1, 2, 3], self.chip._devices.get(1000), [
                4, 5, 6])

        self.rotation.update(pairing)
        self.assertEqual([pairing], self.rotation.pairings)

        with self.assertRaises(ValueError) as error:
            self.rotation.update(
                CoordinatePairing(
                    self.calibration, [
                        10, 20, 30], self.chip._devices.get(1000), [
                        40, 50, 60]))
            self.assertEqual(str(error.exception),
                             "A pairing with this device has already been saved.")

        self.assertEqual([pairing], self.rotation.pairings)

    def test_update_set_of_coordinates(self):
        pairing_1 = CoordinatePairing(
            self.calibration, [
                1, 2, 3], self.chip._devices.get(1000), [
                4, 5, 6])
        pairing_2 = CoordinatePairing(
            self.calibration, [7, 8], self.chip._devices.get(1001), [9, 10])

        self.rotation.update(pairing_1)

        self.assertIn([1, 2, 3], self.rotation._stage_coordinates.tolist())
        self.assertIn([4, 5, 6], self.rotation._chip_coordinates.tolist())
        self.assertIn(pairing_1, self.rotation.pairings)

        self.rotation.update(pairing_2)

        self.assertIn([7, 8, 0], self.rotation._stage_coordinates.tolist())
        self.assertIn([9, 10, 0], self.rotation._chip_coordinates.tolist())
        self.assertIn(pairing_2, self.rotation.pairings)


class KabschRotation2DTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = KabschRotation()
        self.rotation.change_rotation_dimension(Dimension.TWO)
        self.chip = Chip(join(pytest.fixture_folder, "QuarkJaejaChip.csv"))
        self.calibration = Mock()

    def test_initial_invalid(self):
        self.assertFalse(self.rotation.is_valid)

    def test_with_one_pairing(self):
        self.rotation.update(CoordinatePairing(
            self.calibration, [1, 2], self.chip._devices.get(1000), [4, 5]))

        self.assertFalse(self.rotation.is_valid)
        with self.assertRaises(RuntimeError):
            self.rotation.chip_to_stage([0, 0, 0])
        with self.assertRaises(RuntimeError):
            self.rotation.stage_to_chip([0, 0, 0])

    def test_against_golden_model(self):
        stage_coordinate_1 = sample(range(-1000, 1000), 2)
        stage_coordinate_2 = sample(range(-1000, 1000), 2)
        device_1 = self.chip._devices.get(1000)
        device_2 = self.chip._devices.get(1001)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                device_1,
                device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                device_2,
                device_2._in_position))

        self.assertTrue(self.rotation.is_valid)

        matrix, chip_offset, stage_offset = kabsch_model(
            stage_coordinate_1, device_1._in_position, stage_coordinate_2, device_2._in_position)

        self.assertTrue(
            np.allclose(
                matrix,
                self.rotation._rotation.as_matrix()[
                    :2,
                    :2]))
        self.assertTrue(np.allclose(
            chip_offset, self.rotation._chip_offset[:2]))
        self.assertTrue(np.allclose(
            stage_offset, self.rotation._stage_offset[:2]))

        chip_input = sample(range(-1000, 1000), 2)
        stage_input = sample(range(-1000, 1000), 2)

        self.assertTrue(
            np.allclose(
                np.append(
                    np.dot(
                        chip_input -
                        chip_offset,
                        matrix) +
                    stage_offset,
                    0),
                self.rotation.chip_to_stage(chip_input)))

        self.assertTrue(
            np.allclose(
                np.append(
                    np.dot(
                        stage_input -
                        stage_offset,
                        np.linalg.inv(matrix)) +
                    chip_offset,
                    0),
                self.rotation.stage_to_chip(stage_input)))

    def test_chip_to_stage_and_stage_to_chip_are_inversed(self):
        stage_coordinate_1 = sample(range(-1000, 1000), 2)
        stage_coordinate_2 = sample(range(-1000, 1000), 2)
        device_1 = self.chip._devices.get(1000)
        device_2 = self.chip._devices.get(1001)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                device_1,
                device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                device_2,
                device_2._in_position))

        chip_input = sample(range(-1000, 1000), 2)
        stage_input = sample(range(-1000, 1000), 2)

        self.assertTrue(
            np.allclose(
                np.append(
                    chip_input, 0), self.rotation.stage_to_chip(
                    self.rotation.chip_to_stage(chip_input))))

        self.assertTrue(
            np.allclose(
                np.append(
                    stage_input, 0), self.rotation.chip_to_stage(
                    self.rotation.stage_to_chip(stage_input))))

    def test_chip_to_stage_and_stage_to_chip_remain_z_value(self):
        stage_coordinate_1 = sample(range(-1000, 1000), 2)
        stage_coordinate_2 = sample(range(-1000, 1000), 2)
        device_1 = self.chip._devices.get(1000)
        device_2 = self.chip._devices.get(1001)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                device_1,
                device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                device_2,
                device_2._in_position))

        chip_input = sample(range(-1000, 1000), 3)
        stage_input = sample(range(-1000, 1000), 3)

        self.assertEqual(
            chip_input[2],
            self.rotation.chip_to_stage(chip_input)[2])
        self.assertEqual(
            stage_input[2],
            self.rotation.stage_to_chip(stage_input)[2])


class KabschRotation3DTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = KabschRotation()
        self.rotation.change_rotation_dimension(Dimension.THREE)
        self.chip = Chip(join(pytest.fixture_folder, "QuarkJaejaChip.csv"))
        self.calibration = Mock()

    def test_initial_invalid(self):
        self.assertFalse(self.rotation.is_valid)

    def test_with_one_pairing(self):
        self.rotation.update(CoordinatePairing(
            self.calibration, [1, 2, 3], self.chip._devices.get(1000), [4, 5]))

        self.assertFalse(self.rotation.is_valid)
        with self.assertRaises(RuntimeError):
            self.rotation.chip_to_stage([0, 0, 0])
        with self.assertRaises(RuntimeError):
            self.rotation.stage_to_chip([0, 0, 0])

    def test_with_two_pairings(self):
        self.rotation.update(CoordinatePairing(
            self.calibration, [1, 2, 3], self.chip._devices.get(1000), [4, 5]))

        self.rotation.update(
            CoordinatePairing(
                self.calibration, [
                    10, 20, 30], self.chip._devices.get(1001), [
                    40, 50]))

        self.assertFalse(self.rotation.is_valid)
        with self.assertRaises(RuntimeError):
            self.rotation.chip_to_stage([0, 0, 0])
        with self.assertRaises(RuntimeError):
            self.rotation.stage_to_chip([0, 0, 0])

    def test_against_golden_model(self):
        stage_coordinate_1 = sample(range(-1000, 1000), 3)
        stage_coordinate_2 = sample(range(-1000, 1000), 3)
        stage_coordinate_3 = sample(range(-1000, 1000), 3)
        device_1 = self.chip._devices.get(1000)
        device_2 = self.chip._devices.get(1001)
        device_3 = self.chip._devices.get(1002)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                device_1,
                device_1._out_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                device_2,
                device_2._out_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                device_3,
                device_3._out_position))

        self.assertTrue(self.rotation.is_valid)

        matrix, chip_offset, stage_offset = kabsch_model(
            stage_coordinate_1,
            np.append(device_1._out_position, 0),
            stage_coordinate_2,
            np.append(device_2._out_position, 0),
            stage_coordinate_3,
            np.append(device_3._out_position, 0))

        self.assertTrue(
            np.allclose(
                matrix,
                self.rotation._rotation.as_matrix()))
        self.assertTrue(np.allclose(chip_offset, self.rotation._chip_offset))
        self.assertTrue(np.allclose(stage_offset, self.rotation._stage_offset))

        chip_input = sample(range(-1000, 1000), 3)
        stage_input = sample(range(-1000, 1000), 3)

        self.assertTrue(np.allclose(
            np.dot(chip_input - chip_offset, matrix) + stage_offset,
            self.rotation.chip_to_stage(chip_input)
        ))

        self.assertTrue(
            np.allclose(
                np.dot(
                    stage_input -
                    stage_offset,
                    np.linalg.inv(matrix)) +
                chip_offset,
                self.rotation.stage_to_chip(stage_input)))

    def test_chip_to_stage_and_stage_to_chip_are_inversed(self):
        stage_coordinate_1 = sample(range(-1000, 1000), 3)
        stage_coordinate_2 = sample(range(-1000, 1000), 3)
        stage_coordinate_3 = sample(range(-1000, 1000), 3)
        device_1 = self.chip._devices.get(1000)
        device_2 = self.chip._devices.get(1001)
        device_3 = self.chip._devices.get(1002)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                device_1,
                device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                device_2,
                device_2._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                device_3,
                device_3._in_position))

        chip_input = sample(range(-1000, 1000), 3)
        stage_input = sample(range(-1000, 1000), 3)

        self.assertTrue(
            np.allclose(
                chip_input,
                self.rotation.stage_to_chip(
                    self.rotation.chip_to_stage(chip_input))))

        self.assertTrue(
            np.allclose(
                stage_input,
                self.rotation.chip_to_stage(
                    self.rotation.stage_to_chip(stage_input))))


class KabschRotationDimensionCastTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = KabschRotation()
        self.chip = Chip(join(pytest.fixture_folder, "QuarkJaejaChip.csv"))
        self.calibration = Mock()

        self.device_1 = self.chip._devices.get(1000)
        self.device_2 = self.chip._devices.get(1001)
        self.device_3 = self.chip._devices.get(1002)

    def test_3D_to_2D_casting(self):
        self.rotation.change_rotation_dimension(Dimension.THREE)

        stage_coordinate_1 = sample(range(-1000, 1000), 3)
        stage_coordinate_2 = sample(range(-1000, 1000), 3)
        stage_coordinate_3 = sample(range(-1000, 1000), 3)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                self.device_1,
                self.device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                self.device_2,
                self.device_2._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                self.device_3,
                self.device_3._in_position))

        self.assertTrue(self.rotation.is_valid)
        self.rotation.change_rotation_dimension(Dimension.TWO)

        self.assertTrue(self.rotation.is_valid)
        self.assertTrue(self.rotation.is_2D)

        matrix, chip_offset, stage_offset = kabsch_model(
            stage_coordinate_1[:2],
            self.device_1._in_position,
            stage_coordinate_2[:2],
            self.device_2._in_position,
            stage_coordinate_3[:2],
            self.device_3._in_position)

        self.assertTrue(
            np.allclose(
                matrix,
                self.rotation._rotation.as_matrix()[
                    :2,
                    :2]))
        self.assertTrue(np.allclose(
            chip_offset, self.rotation._chip_offset[:2]))
        self.assertTrue(np.allclose(
            stage_offset, self.rotation._stage_offset[:2]))

    def test_2D_to_3D_casting(self):
        self.rotation.change_rotation_dimension(Dimension.TWO)

        stage_coordinate_1 = sample(range(-1000, 1000), 2)
        stage_coordinate_2 = sample(range(-1000, 1000), 2)
        stage_coordinate_3 = sample(range(-1000, 1000), 2)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                self.device_1,
                self.device_1._out_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                self.device_2,
                self.device_2._out_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                self.device_3,
                self.device_3._out_position))

        self.assertTrue(self.rotation.is_valid)
        self.rotation.change_rotation_dimension(Dimension.THREE)

        self.assertTrue(self.rotation.is_valid)
        self.assertTrue(self.rotation.is_3D)

        matrix, chip_offset, stage_offset = kabsch_model(
            np.append(stage_coordinate_1, 0),
            np.append(self.device_1._out_position, 0),
            np.append(stage_coordinate_2, 0),
            np.append(self.device_2._out_position, 0),
            np.append(stage_coordinate_3, 0),
            np.append(self.device_3._out_position, 0))

        self.assertTrue(
            np.allclose(
                matrix,
                self.rotation._rotation.as_matrix()))
        self.assertTrue(np.allclose(chip_offset, self.rotation._chip_offset))
        self.assertTrue(np.allclose(stage_offset, self.rotation._stage_offset))

    def test_2D_casting_is_inversed(self):
        self.rotation.change_rotation_dimension(Dimension.THREE)

        stage_coordinate_1 = sample(range(-1000, 1000), 3)
        stage_coordinate_2 = sample(range(-1000, 1000), 3)
        stage_coordinate_3 = sample(range(-1000, 1000), 3)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                self.device_1,
                self.device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                self.device_2,
                self.device_2._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                self.device_3,
                self.device_3._in_position))

        matrix_3D = self.rotation._rotation.as_matrix()
        stage_offset_3D = self.rotation._stage_offset
        chip_offset_3D = self.rotation._chip_offset

        self.rotation.change_rotation_dimension(Dimension.TWO)
        self.rotation.change_rotation_dimension(Dimension.THREE)

        self.assertTrue(
            np.allclose(
                matrix_3D,
                self.rotation._rotation.as_matrix()))
        self.assertTrue(
            np.allclose(
                chip_offset_3D,
                self.rotation._chip_offset))
        self.assertTrue(
            np.allclose(
                stage_offset_3D,
                self.rotation._stage_offset))

    def test_3D_casting_is_inversed(self):
        self.rotation.change_rotation_dimension(Dimension.TWO)

        stage_coordinate_1 = sample(range(-1000, 1000), 2)
        stage_coordinate_2 = sample(range(-1000, 1000), 2)
        stage_coordinate_3 = sample(range(-1000, 1000), 2)

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_1,
                self.device_1,
                self.device_1._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_2,
                self.device_2,
                self.device_2._in_position))

        self.rotation.update(
            CoordinatePairing(
                self.calibration,
                stage_coordinate_3,
                self.device_3,
                self.device_3._in_position))

        matrix_2D = self.rotation._rotation.as_matrix()
        stage_offset_2D = self.rotation._stage_offset
        chip_offset_2D = self.rotation._chip_offset

        self.rotation.change_rotation_dimension(Dimension.THREE)
        self.rotation.change_rotation_dimension(Dimension.TWO)

        self.assertTrue(
            np.allclose(
                matrix_2D,
                self.rotation._rotation.as_matrix()))
        self.assertTrue(
            np.allclose(
                chip_offset_2D,
                self.rotation._chip_offset))
        self.assertTrue(
            np.allclose(
                stage_offset_2D,
                self.rotation._stage_offset))
