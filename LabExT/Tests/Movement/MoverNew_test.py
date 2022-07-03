#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from os.path import join, dirname, abspath

import unittest
import numpy as np
from unittest.mock import Mock, patch
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Movement.Calibration import DevicePort, Orientation

from LabExT.Movement.MoverNew import MoverError, MoverNew, Stage, assert_connected_stages


class AssertConnectedStagesTest(unittest.TestCase):
    """
    Tests decorator for assert_connected_stages.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')

        with patch.object(Stage, "find_available_stages", return_value=[]):
            with patch.object(Stage, "find_stage_classes", return_value=[]):
                self.mover = MoverNew(None)

        return super().setUp()

    def test_assert_connected_stages_raises_error_if_no_stage_is_connected(
            self):
        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)

        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(MoverError):
            assert_connected_stages(func)(self.mover)

        func.assert_not_called()

    def test_assert_connected_stages_calls_function_if_stage_is_connected(
            self):
        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.stage.connect()

        func = Mock()
        func.__name__ = 'Dummy Function'

        assert_connected_stages(func)(self.mover)
        func.assert_called_once()


class AddStageCalibrationTest(unittest.TestCase):
    """
    Tests adding new calibrations.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        with patch.object(Stage, "find_available_stages", return_value=[]):
            with patch.object(Stage, "find_stage_classes", return_value=[]):
                self.mover = MoverNew(None)

        return super().setUp()

    def test_add_stage_calibration_reject_invalid_orientations(self):
        current_calibrations = self.mover.calibrations

        with self.assertRaises(ValueError):
            self.mover.add_stage_calibration(
                self.stage, 1, DevicePort.INPUT)

        self.assertEqual(current_calibrations, self.mover.calibrations)

    def test_add_stage_calibration_reject_invalid_port(self):
        current_calibrations = self.mover.calibrations

        with self.assertRaises(ValueError):
            self.mover.add_stage_calibration(self.stage, Orientation.LEFT, 1)

        self.assertEqual(current_calibrations, self.mover.calibrations)

    def test_add_stage_calibration_reject_double_orientations(self):
        valid_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        current_calibrations = self.mover.calibrations

        self.assertEqual(current_calibrations[(
            Orientation.LEFT, DevicePort.INPUT)], valid_calibration)

        with self.assertRaises(MoverError) as error_context:
            self.mover.add_stage_calibration(
                self.stage2, Orientation.LEFT, DevicePort.OUTPUT)

        with self.assertRaises(KeyError):
            self.mover.calibrations[(Orientation.LEFT, DevicePort.OUTPUT)]

        self.assertEqual(
            "A stage has already been assigned for Left.", str(
                error_context.exception))
        self.assertEqual(current_calibrations, self.mover.calibrations)
        self.assertEqual(1, len(self.mover.calibrations))

    def test_add_stage_calibration_reject_double_ports(self):
        valid_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        current_calibrations = self.mover.calibrations

        self.assertEqual(current_calibrations[(
            Orientation.LEFT, DevicePort.INPUT)], valid_calibration)

        with self.assertRaises(MoverError) as error_context:
            self.mover.add_stage_calibration(
                self.stage2, Orientation.RIGHT, DevicePort.INPUT)

        with self.assertRaises(KeyError):
            self.mover.calibrations[(Orientation.RIGHT, DevicePort.INPUT)]

        self.assertEqual(
            "A stage has already been assigned for the Input port.", str(
                error_context.exception))
        self.assertEqual(current_calibrations, self.mover.calibrations)
        self.assertEqual(1, len(self.mover.calibrations))

    def test_add_stage_calibration_reject_double_stages(self):
        valid_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        current_calibrations = self.mover.calibrations

        self.assertEqual(current_calibrations[(
            Orientation.LEFT, DevicePort.INPUT)], valid_calibration)

        with self.assertRaises(MoverError) as error_context:
            self.mover.add_stage_calibration(
                self.stage, Orientation.TOP, DevicePort.OUTPUT)

        self.assertEqual("Stage {} has already an assignment.".format(
            str(self.stage)), str(error_context.exception))
        self.assertEqual(current_calibrations, self.mover.calibrations)
        self.assertEqual(1, len(self.mover.calibrations))

    def test_active_stage_includes_new_stage(self):
        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.mover.add_stage_calibration(
            self.stage2, Orientation.RIGHT, DevicePort.OUTPUT)

        self.assertIn(self.stage, self.mover.active_stages)
        self.assertIn(self.stage2, self.mover.active_stages)

    def test_left_and_input_calibration_property(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.assertEqual(calibration, self.mover.left_calibration)
        self.assertEqual(calibration, self.mover.input_calibration)

    def test_right_and_output_calibration_property(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.RIGHT, DevicePort.OUTPUT)
        self.assertEqual(calibration, self.mover.right_calibration)
        self.assertEqual(calibration, self.mover.output_calibration)

    def test_top_and_input_calibration_property(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.TOP, DevicePort.INPUT)
        self.assertEqual(calibration, self.mover.top_calibration)
        self.assertEqual(calibration, self.mover.input_calibration)

    def test_bottom_and_output_calibration_property(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.BOTTOM, DevicePort.OUTPUT)
        self.assertEqual(calibration, self.mover.bottom_calibration)
        self.assertEqual(calibration, self.mover.output_calibration)


class MoverStageSettingsTest(unittest.TestCase):
    """
    Tests stage settings.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        with patch.object(Stage, "find_available_stages", return_value=[]):
            with patch.object(Stage, "find_stage_classes", return_value=[]):
                self.mover = MoverNew(None)

        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.mover.add_stage_calibration(
            self.stage2, Orientation.RIGHT, DevicePort.OUTPUT)

        self.stage.connect()
        self.stage2.connect()
        return super().setUp()

    def test_set_speed_xy_raises_error_if_lower_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.speed_xy = self.mover.SPEED_LOWER_BOUND - 1

        self.assertEqual(
            "Speed for xy is out of valid range.", str(
                error.exception))
        self.assertTrue(all(
            s.get_speed_xy() == self.mover._speed_xy for s in self.mover.connected_stages))

    def test_set_speed_xy_raises_error_if_upper_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.speed_xy = self.mover.SPEED_UPPER_BOUND + 1

        self.assertEqual(
            "Speed for xy is out of valid range.", str(
                error.exception))
        self.assertTrue(all(
            s.get_speed_xy() == self.mover._speed_xy for s in self.mover.connected_stages))

    def test_set_speed_xy_for_all_stages(self):
        self.mover.speed_xy = 200

        self.assertEqual(self.mover._speed_xy, 200)
        self.assertTrue(
            all(s.get_speed_xy() == 200 for s in self.mover.connected_stages))

    def test_get_speed_xy(self):
        self.mover.speed_xy = 200
        self.assertEqual(self.mover.speed_xy, 200)

    def test_get_speed_xy_updates_differing_stages(self):
        self.mover.speed_xy = 200
        self.stage.set_speed_xy(300)

        self.assertEqual(self.mover.speed_xy, 200)
        self.assertEqual(self.stage.get_speed_xy(), 200)
        self.assertEqual(self.stage2.get_speed_xy(), 200)

    def test_set_speed_z_raises_error_if_lower_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.speed_z = self.mover.SPEED_LOWER_BOUND - 1

        self.assertEqual(
            "Speed for z is out of valid range.", str(
                error.exception))
        self.assertTrue(
            all(s.get_speed_z() == self.mover._speed_z for s in self.mover.connected_stages))

    def test_set_speed_z_raises_error_if_upper_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.speed_z = self.mover.SPEED_UPPER_BOUND + 1

        self.assertEqual(
            "Speed for z is out of valid range.", str(
                error.exception))
        self.assertTrue(
            all(s.get_speed_z() == self.mover._speed_z for s in self.mover.connected_stages))

    def test_set_speed_z_for_all_stages(self):
        self.mover.speed_z = 200

        self.assertEqual(self.mover._speed_z, 200)
        self.assertTrue(
            all(s.get_speed_z() == 200 for s in self.mover.connected_stages))

    def test_get_speed_z(self):
        self.mover.speed_z = 200
        self.assertEqual(self.mover.speed_z, 200)

    def test_get_speed_z_updates_differing_stages(self):
        self.mover.speed_z = 200
        self.stage.set_speed_z(300)

        self.assertEqual(self.mover.speed_z, 200)
        self.assertEqual(self.stage.get_speed_z(), 200)
        self.assertEqual(self.stage2.get_speed_z(), 200)

    def test_set_acceleration_xy_raises_error_if_lower_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.acceleration_xy = self.mover.ACCELERATION_LOWER_BOUND - 1

        self.assertEqual(
            "Acceleration for xy is out of valid range.", str(
                error.exception))
        self.assertTrue(all(s.get_acceleration_xy(
        ) == self.mover._acceleration_xy for s in self.mover.connected_stages))

    def test_set_acceleration_xy_raises_error_if_upper_bound_is_violated(self):
        with self.assertRaises(ValueError) as error:
            self.mover.acceleration_xy = self.mover.ACCELERATION_UPPER_BOUND + 1

        self.assertEqual(
            "Acceleration for xy is out of valid range.", str(
                error.exception))
        self.assertTrue(all(s.get_acceleration_xy(
        ) == self.mover._acceleration_xy for s in self.mover.connected_stages))

    def test_set_acceleration_xy_for_all_stages(self):
        self.mover.acceleration_xy = 200

        self.assertEqual(self.mover._acceleration_xy, 200)
        self.assertTrue(all(s.get_acceleration_xy() ==
                        200 for s in self.mover.connected_stages))

    def test_get_acceleration_xy(self):
        self.mover.acceleration_xy = 200
        self.assertEqual(self.mover.acceleration_xy, 200)

    def test_get_acceleration_xy_updates_differing_stages(self):
        self.mover.acceleration_xy = 200
        self.stage.set_acceleration_xy(300)

        self.assertEqual(self.mover.acceleration_xy, 200)
        self.assertEqual(self.stage.get_acceleration_xy(), 200)
        self.assertEqual(self.stage2.get_acceleration_xy(), 200)

    def test_set_z_lift_does_not_accept_negative_values(self):
        with self.assertRaises(ValueError):
            self.mover.z_lift = -10

    def test_set_z_lift_stores_positive_lift(self):
        self.mover.z_lift = 50

        self.assertEqual(self.mover.z_lift, 50)


class MoverLoadedFromFileTest(unittest.TestCase):

    def setUp(self) -> None:
        self.config_file = join(abspath(dirname(__file__)), "mover_sample_config.json")
        self.mover = MoverNew(None)

        with open(self.config_file, 'r') as fp:
            self.config = json.load(fp)

    def test_load_settings_from_file(self):
        self.mover.load_settings_from_file(self.config_file) 

        self.assertEqual(len(self.mover.active_stages), 2)
        self.assertEqual(len(self.mover.calibrations), 2)

        self.assertIsNotNone(self.mover.calibrations.get((Orientation.LEFT, DevicePort.INPUT)))
        self.assertIsNotNone(self.mover.calibrations.get((Orientation.RIGHT, DevicePort.OUTPUT)))

        left_cali = self.mover.left_calibration
        self.assertTrue(left_cali._axes_rotation.is_valid)
        self.assertTrue(left_cali._single_point_offset.is_valid)
        self.assertTrue(left_cali._kabsch_rotation.is_valid)

        right_cali = self.mover.left_calibration
        self.assertTrue(right_cali._axes_rotation.is_valid)
        self.assertTrue(right_cali._single_point_offset.is_valid)
        self.assertTrue(right_cali._kabsch_rotation.is_valid)

        self.assertEqual(self.mover.speed_xy, self.config["settings"]["speed_xy"])
        self.assertEqual(self.mover.speed_z, self.config["settings"]["speed_z"])
        self.assertEqual(self.mover.acceleration_xy, self.config["settings"]["acceleration_xy"])
        self.assertEqual(self.mover.z_lift, self.config["settings"]["z_lift"])
