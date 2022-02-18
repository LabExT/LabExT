#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from unittest.mock import call, patch
import numpy as np

from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stage import Stage
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Movement.Calibration import AxesRotation, Axis, Calibration, CalibrationError, DevicePort, Direction, Orientation, State


class AxesRotationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rotation = AxesRotation()
        return super().setUp()

    def test_default_case(self):
        self.assertTrue((self.rotation._matrix == np.identity(3)).all())
        self.assertTrue(self.rotation.is_valid)

        chip_coordinate = np.array([1, 2, 3])
        expected_stage_coordinate = np.array([1, 2, 3])
        self.assertTrue((expected_stage_coordinate ==
                        self.rotation.chip_to_stage(chip_coordinate)).all())

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.rotation.update("X", Axis.X, Direction.POSITIVE)

        with self.assertRaises(ValueError):
            self.rotation.update(Axis.X, "X", Direction.POSITIVE)

        with self.assertRaises(ValueError):
            self.rotation.update(Axis.X, Axis.X, "positive")

    def test_double_x_axis_assignment(self):
        self.rotation.update(Axis.X, Axis.Y, Direction.POSITIVE)
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.Y, Axis.X, Direction.POSITIVE)
        self.assertTrue(self.rotation.is_valid)

    def test_double_y_axis_assignment(self):
        self.rotation.update(Axis.Y, Axis.X, Direction.POSITIVE)
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.X, Axis.Y, Direction.POSITIVE)
        self.assertTrue(self.rotation.is_valid)

    def test_double_z_axis_assignment(self):
        self.rotation.update(Axis.Z, Axis.Y, Direction.POSITIVE)
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.Y, Axis.Z, Direction.POSITIVE)
        self.assertTrue(self.rotation.is_valid)

    def test_switch_x_and_y_axis(self):
        self.rotation.update(Axis.X, Axis.Y, Direction.NEGATIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((0, 0, 0)), np.array((-1, 1, 0)), np.array((0, 0, 1)),
        ])))
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.Y, Axis.X, Direction.POSITIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((0, 1, 0)), np.array((-1, 0, 0)), np.array((0, 0, 1)),
        ])))
        self.assertTrue(self.rotation.is_valid)

    def test_switch_x_and_z_axis(self):
        self.rotation.update(Axis.X, Axis.Z, Direction.POSITIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((0, 0, 0)), np.array((0, 1, 0)), np.array((1, 0, 1)),
        ])))
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.Z, Axis.X, Direction.NEGATIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((0, 0, -1)), np.array((0, 1, 0)), np.array((1, 0, 0)),
        ])))
        self.assertTrue(self.rotation.is_valid)

    def test_switch_y_and_z_axis(self):
        self.rotation.update(Axis.Z, Axis.Y, Direction.NEGATIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((1, 0, 0)), np.array((0, 1, -1)), np.array((0, 0, 0)),
        ])))
        self.assertFalse(self.rotation.is_valid)

        self.rotation.update(Axis.Y, Axis.Z, Direction.POSITIVE)
        self.assertTrue(np.array_equal(self.rotation._matrix, np.array([
            np.array((1, 0, 0)), np.array((0, 0, -1)), np.array((0, 1, 0)),
        ])))
        self.assertTrue(self.rotation.is_valid)


class WiggleAxisTest(unittest.TestCase):
    def setUp(self) -> None:
        # Create Mover instance without stage discovery
        with patch.object(Stage, "find_available_stages", return_value=[]):
            with patch.object(Stage, "find_stage_classes", return_value=[]):
                self.mover = MoverNew(None)
                self.stage = DummyStage('usb:123456789')
                self.calibration = Calibration(
                    self.mover, self.stage, Orientation.LEFT, DevicePort.INPUT)

    def test_wiggle_axis_raises_error_if_axes_rotation_is_invalid(self):
        axes_rotation = AxesRotation()
        axes_rotation.update(
            chip_axis=Axis.X,
            stage_axis=Axis.Y,
            direction=Direction.POSITIVE)

        with self.assertRaises(CalibrationError):
            self.calibration.wiggle_axis(Axis.X, axes_rotation)

    @patch.object(DummyStage, "move_relative")
    def test_wiggle_axis_with_rotation(self, move_relative_mock):
        axes_rotation = AxesRotation()
        axes_rotation.update(
            chip_axis=Axis.X,
            stage_axis=Axis.Y,
            direction=Direction.NEGATIVE)
        axes_rotation.update(
            chip_axis=Axis.Y,
            stage_axis=Axis.Z,
            direction=Direction.POSITIVE)
        axes_rotation.update(
            chip_axis=Axis.Z,
            stage_axis=Axis.X,
            direction=Direction.NEGATIVE)

        self.assertTrue(axes_rotation.is_valid)
        wiggle_distance = 2000
        expected_movement_calls = [
            call(0, -2000.0, 0), call(0, 2000.0, 0),
            call(0, 0, 2000.0), call(0, 0, -2000.0),
            call(-2000.0, 0, 0), call(2000.0, 0, 0),
        ]

        self.calibration.wiggle_axis(Axis.X, axes_rotation, wiggle_distance)
        self.calibration.wiggle_axis(Axis.Y, axes_rotation, wiggle_distance)
        self.calibration.wiggle_axis(Axis.Z, axes_rotation, wiggle_distance)

        move_relative_mock.assert_has_calls(expected_movement_calls)

    @patch.object(DummyStage, "move_relative")
    @patch.object(DummyStage, "set_speed_xy")
    @patch.object(DummyStage, "set_speed_z")
    def test_wiggle_axis_sets_and_resets_speed(
            self,
            set_speed_z_mock,
            set_speed_xy_mock,
            move_relative_mock):
        current_speed_xy = self.stage._speed_xy
        current_speed_z = self.stage._speed_z

        self.calibration.wiggle_axis(Axis.X, AxesRotation(), wiggle_speed=5000)

        move_relative_mock.assert_has_calls(
            [call(1000.0, 0, 0), call(-1000.0, 0, 0)])
        set_speed_z_mock.assert_has_calls([call(5000), call(current_speed_z)])
        set_speed_xy_mock.assert_has_calls(
            [call(5000), call(current_speed_xy)])


class CalibrationTest(unittest.TestCase):
    def setUp(self) -> None:
        # Create Mover instance without stage discovery
        with patch.object(Stage, "find_available_stages", return_value=[]):
            with patch.object(Stage, "find_stage_classes", return_value=[]):
                self.mover = MoverNew(None)
                self.stage = DummyStage('usb:123456789')
                self.calibration = Calibration(
                    self.mover, self.stage, Orientation.LEFT, DevicePort.INPUT)

    def test_fix_coordinate_system_accepts_only_valid_rotations(self):
        axes_rotation = AxesRotation()
        axes_rotation.update(
            chip_axis=Axis.X,
            stage_axis=Axis.Y,
            direction=Direction.POSITIVE)

        with self.assertRaises(CalibrationError):
            self.calibration.fix_coordinate_system(axes_rotation)

    def test_fix_coordinate_system_saves_rotation(self):
        axes_rotation = AxesRotation()

        self.calibration.fix_coordinate_system(axes_rotation)

        self.assertEqual(self.calibration._axes_rotation, axes_rotation)
        self.assertEqual(
            self.calibration._state,
            State.COORDINATE_SYSTEM_FIXED)
