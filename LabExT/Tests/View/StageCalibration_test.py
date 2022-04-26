#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from LabExT.Movement.Transformations import CoordinatePairing, SinglePointFixation
from LabExT.Wafer.Device import Device
import numpy as np
from tkinter import DISABLED, NORMAL
from unittest.mock import Mock, patch
from LabExT.Tests.Utils import TKinterTestCase, with_stage_discovery_patch
from LabExT.Movement.Calibration import CalibrationError, AxesRotation, Axis, DevicePort, Direction, Orientation, State
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Movement.Stage import Stage

from LabExT.View.StageCalibration.StageCalibrationController import StageCalibrationController


class StageCalibrationControllerTest(unittest.TestCase):

    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []

        self.experiment_manager = Mock()
        self.mover = MoverNew(self.experiment_manager)

        self.stage = DummyStage('usb:123456789')
        self.stage_2 = DummyStage('usb:987654321')

    def test_with_no_calibrations(self):
        with self.assertRaises(AssertionError) as error:
            StageCalibrationController(self.experiment_manager, self.mover)

        self.assertEqual(
            "Cannot calibrate mover without any connected stage. ", str(
                error.exception))

    def test_with_no_connected_calibration(self):
        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)

        with self.assertRaises(AssertionError) as error:
            StageCalibrationController(self.experiment_manager, self.mover)

        self.assertEqual(
            "Cannot calibrate mover without any connected stage. ", str(
                error.exception))

    def test_save_coordinate_system_empty(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)
        result = controller.save_coordinate_system({})

        self.assertTrue(result)
        self.assertTrue(
            all(c._axes_rotation is None for c in self.mover.calibrations.values()))

    def test_save_coordinate_system_stores_rotation(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        rotation = AxesRotation()

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)
        result = controller.save_coordinate_system({calibration: rotation})

        self.assertTrue(result)
        self.assertEqual(calibration._axes_rotation, rotation)
        self.assertEqual(calibration.state, State.COORDINATE_SYSTEM_FIXED)

    def test_save_coordinate_system_with_invalid_rotation(self):
        calibration_1 = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration_1.connect_to_stage()

        calibration_2 = self.mover.add_stage_calibration(
            self.stage_2, Orientation.RIGHT, DevicePort.OUTPUT)
        calibration_2.connect_to_stage()

        invalid_rotation = AxesRotation()
        invalid_rotation.update(Axis.X, Axis.Y, Direction.NEGATIVE)

        valid_rotation = AxesRotation()

        self.assertFalse(invalid_rotation.is_valid)
        self.assertTrue(valid_rotation.is_valid)

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)

        with self.assertRaises(CalibrationError):
            controller.save_coordinate_system(
                {calibration_1: invalid_rotation, calibration_2: valid_rotation})

        self.assertIsNone(calibration_1._axes_rotation)
        self.assertEqual(calibration_2._axes_rotation, valid_rotation)

    def test_save_single_point_fixation_empty(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)
        result = controller.save_single_point_fixation({})

        self.assertTrue(result)
        self.assertTrue(
            all(c._single_point_fixation is None for c in self.mover.calibrations.values()))

    def test_save_single_point_fixation_stores_fixation(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        translation = SinglePointFixation()
        translation.update(
            CoordinatePairing(
                calibration, [
                    1, 2], None, [
                    3, 4]))

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)
        result = controller.save_single_point_fixation(
            {calibration: translation})

        self.assertTrue(result)
        self.assertEqual(calibration._single_point_fixation, translation)
        self.assertEqual(calibration.state, State.SINGLE_POINT_FIXED)

    def test_save_single_point_fixation_with_invalid_fixation(self):
        calibration_1 = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration_1.connect_to_stage()

        calibration_2 = self.mover.add_stage_calibration(
            self.stage_2, Orientation.RIGHT, DevicePort.OUTPUT)
        calibration_2.connect_to_stage()

        invalid_translation = SinglePointFixation()

        valid_translation = SinglePointFixation()
        valid_translation.update(
            CoordinatePairing(
                calibration_2, [
                    1, 2], None, [
                    3, 4]))

        self.assertFalse(invalid_translation.is_valid)
        self.assertTrue(valid_translation.is_valid)

        controller = StageCalibrationController(
            self.experiment_manager, self.mover)

        with self.assertRaises(CalibrationError):
            controller.save_single_point_fixation(
                {calibration_1: invalid_translation, calibration_2: valid_translation})

        self.assertIsNone(calibration_1._single_point_fixation)
        self.assertEqual(
            calibration_2._single_point_fixation,
            valid_translation)


class AxesCalibrationStepTest(TKinterTestCase):

    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []

        self.experiment_manager = Mock()
        self.mover = MoverNew(self.experiment_manager)

        self.stage = DummyStage('usb:123456789')

        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        self.controller = StageCalibrationController(
            self.experiment_manager, self.mover, self.root)
        self.view = self.controller.view

        self.view.current_step = self.view.fix_coordinate_system_step

        self.axis_vars = self.view._axis_calibration_vars[calibration]
        self.current_rotation = self.view._current_axes_rotations[calibration]
        self.wiggle_buttons = self.view._axis_wiggle_buttons[calibration]

    def _option_key(self, direction, axis):
        return "{} {}".format(direction, axis)

    def test_default_case(self):
        self.assertTrue(
            np.array_equal(
                self.current_rotation._matrix,
                np.identity(3)))
        self.assertTrue(self.current_rotation.is_valid)

    def test_switch_x_and_y_axis(self):
        self.axis_vars[Axis.X].set(
            self._option_key(Direction.NEGATIVE, Axis.Y))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((0, 0, 0)), np.array((-1, 1, 0)), np.array((0, 0, 1)),
        ])))
        self.assertFalse(self.current_rotation.is_valid)
        self.assertEqual(self.view._next_button["state"], DISABLED)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a stage axis twice.")

        self.axis_vars[Axis.Y].set(
            self._option_key(Direction.POSITIVE, Axis.X))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((0, 1, 0)), np.array((-1, 0, 0)), np.array((0, 0, 1)),
        ])))
        self.assertTrue(self.current_rotation.is_valid)
        self.assertEqual(self.view._error_label["text"], "")

    def test_switch_x_and_z_axis(self):
        self.axis_vars[Axis.X].set(
            self._option_key(Direction.POSITIVE, Axis.Z))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((0, 0, 0)), np.array((0, 1, 0)), np.array((1, 0, 1)),
        ])))
        self.assertFalse(self.current_rotation.is_valid)
        self.assertEqual(self.view._next_button["state"], DISABLED)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a stage axis twice.")

        self.axis_vars[Axis.Z].set(
            self._option_key(Direction.NEGATIVE, Axis.X))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((0, 0, -1)), np.array((0, 1, 0)), np.array((1, 0, 0)),
        ])))
        self.assertTrue(self.current_rotation.is_valid)
        self.assertEqual(self.view._error_label["text"], "")

    def test_switch_y_and_z_axis(self):
        self.axis_vars[Axis.Z].set(
            self._option_key(Direction.NEGATIVE, Axis.Y))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((1, 0, 0)), np.array((0, 1, -1)), np.array((0, 0, 0)),
        ])))
        self.assertFalse(self.current_rotation.is_valid)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a stage axis twice.")

        self.axis_vars[Axis.Y].set(
            self._option_key(Direction.POSITIVE, Axis.Z))
        self.assertTrue(np.array_equal(self.current_rotation._matrix, np.array([
            np.array((1, 0, 0)), np.array((0, 0, -1)), np.array((0, 1, 0)),
        ])))
        self.assertTrue(self.current_rotation.is_valid)
        self.assertEqual(self.view._error_label["text"], "")

    @patch("LabExT.View.StageCalibration.StageCalibrationView.messagebox.askokcancel", autospec=True)
    def test_wiggle_axis_warns_user(self, askokcancel_mock):
        askokcancel_mock.return_value = False

        self.wiggle_buttons[Axis.X].invoke()

        askokcancel_mock.assert_called_once()

    @patch("LabExT.View.StageCalibration.StageCalibrationView.messagebox.showerror", autospec=True)
    def test_wiggle_axis_does_not_wiggle_do_axis_at_the_same_time(
            self, showerror_mock):
        self.view._performing_wiggle = True
        showerror_mock.return_value = None

        self.wiggle_buttons[Axis.X].invoke()

        showerror_mock.assert_called_once_with(
            "Error", "Stage cannot wiggle because another stage is being wiggled. ")
