#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
import json

from unittest.mock import Mock, patch, call, mock_open
from parameterized import parameterized
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Movement.Calibration import DevicePort, Orientation

from LabExT.Movement.MoverNew import MoverError, MoverNew, assert_connected_stages
from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import Axis, Direction, CoordinateSystem


class AssertConnectedStagesTest(unittest.TestCase):
    """
    Tests decorator for assert_connected_stages.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.mover = MoverNew(None)

        return super().setUp()

    def test_assert_connected_stages_raises_error_if_no_stage_is_connected(
            self):
        self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.stage.disconnect()

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

        with patch.object(MoverNew, "MOVER_SETTINGS_FILE",
                          return_value="/mocked/mover_settings.json"):
            self.mover = MoverNew(None)

        return super().setUp()

    def test_default_mover_settings_after_initialization(self):
        self.assertEqual(self.mover._speed_xy, self.mover.DEFAULT_SPEED_XY)
        self.assertEqual(self.mover._speed_z, self.mover.DEFAULT_SPEED_Z)
        self.assertEqual(
            self.mover._acceleration_xy,
            self.mover.DEFAULT_ACCELERATION_XY)
        self.assertEqual(self.mover._z_lift, self.mover.DEFAULT_Z_LIFT)

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

    def test_set_stage_settings_successfully(self):
        self.assertIsNone(self.stage.get_speed_xy())
        self.assertIsNone(self.stage.get_speed_xy())
        self.assertIsNone(self.stage.get_acceleration_xy())

        self.mover.add_stage_calibration(
            self.stage, Orientation.BOTTOM, DevicePort.OUTPUT)

        self.assertEqual(self.stage.get_speed_xy(), self.mover._speed_xy)
        self.assertEqual(self.stage.get_speed_z(), self.mover._speed_z)
        self.assertEqual(
            self.stage.get_acceleration_xy(),
            self.mover._acceleration_xy)


class MoverStageSettingsTest(unittest.TestCase):
    """
    Tests stage settings.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        with patch.object(MoverNew, "MOVER_SETTINGS_FILE", "/mocked/mover_settings.json"):
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

    @patch.object(MoverNew, "MOVER_SETTINGS_FILE",
                  "/mocked/mover_settings.json")
    def test_dump_settings(self):
        self.mover.speed_xy = 1000
        self.mover.speed_z = 50
        self.mover.acceleration_xy = 200
        self.mover.z_lift = 24.5

        with patch('builtins.open', mock_open()) as m:
            self.mover.dump_settings()

        m.assert_called_once_with('/mocked/mover_settings.json', 'w')

        file_pointer = m()
        file_pointer.write.assert_has_calls(
            [
                call('{'),
                call('"speed_xy"'),
                call(': '),
                call('1000'),
                call(', '),
                call('"speed_z"'),
                call(': '),
                call('50'),
                call(', '),
                call('"acceleration_xy"'),
                call(': '),
                call('200'),
                call(', '),
                call('"z_lift"'),
                call(': '),
                call('24.5'),
                call('}')])

    @patch.object(MoverNew, "MOVER_SETTINGS_FILE",
                  "/mocked/mover_settings.json")
    @patch('os.path.exists')
    def test_load_settings(self, mock_exists):
        settings = json.dumps({
            "speed_xy": 350,
            "speed_z": 100,
            "acceleration_xy": 10,
            "z_lift": 50
        })

        mock_exists.return_value = True

        with patch("builtins.open", mock_open(read_data=settings)) as m:
            self.mover.load_settings()

        self.assertEqual(self.mover.speed_xy, 350)
        self.assertEqual(self.mover.speed_z, 100)
        self.assertEqual(self.mover.acceleration_xy, 10)
        self.assertEqual(self.mover.z_lift, 50)


class CanMoveRelativelyTest(unittest.TestCase):

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        self.mover = MoverNew(None)

    def test_with_no_calibrations(self):
        self.assertFalse(self.mover.can_move_relatively)

    def test_with_one_valid_calibration(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        self.assertTrue(
            calibration._axes_rotation.is_valid)

        self.assertTrue(self.mover.can_move_relatively)

    def test_with_one_invalid_calibration(self):
        calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        calibration.connect_to_stage()

        calibration.update_axes_rotation(Axis.X, Direction.NEGATIVE, Axis.Y)
        self.assertFalse(
            calibration._axes_rotation.is_valid)

        self.assertFalse(self.mover.can_move_relatively)

    def test_with_one_valid_and_one_invalid_calibration(self):
        valid_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        valid_calibration.connect_to_stage()

        self.assertTrue(
            valid_calibration._axes_rotation.is_valid)

        invalid_calibration = self.mover.add_stage_calibration(
            self.stage2, Orientation.RIGHT, DevicePort.OUTPUT)
        invalid_calibration.connect_to_stage()

        invalid_calibration.update_axes_rotation(
            Axis.X, Direction.NEGATIVE, Axis.Y)
        self.assertFalse(
            invalid_calibration._axes_rotation.is_valid)

        self.assertFalse(self.mover.can_move_relatively)


class RelativeMovementTest(unittest.TestCase):

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        self.mover = MoverNew(None)

        self.left_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.right_calibration = self.mover.add_stage_calibration(
            self.stage2, Orientation.RIGHT, DevicePort.OUTPUT)

        self.left_calibration.connect_to_stage()
        self.right_calibration.connect_to_stage()

    def test_raises_error_if_axes_rotation_in_valid(self):
        self.left_calibration.update_axes_rotation(
            Axis.X, Direction.NEGATIVE, Axis.Y)
        self.assertFalse(self.left_calibration._axes_rotation.is_valid)

        movement_command = {Orientation.LEFT: ChipCoordinate(1, 2, 3)}
        with self.assertRaises(MoverError):
            self.mover.move_relative(movement_command)

    def test_raises_error_if_stage_is_disconnected(self):
        self.right_calibration.disconnect_to_stage()

        movement_command = {Orientation.RIGHT: ChipCoordinate(1, 2, 3)}
        with self.assertRaises(MoverError):
            self.mover.move_relative(movement_command)

    def test_raises_error_if_requested_stage_is_unavailable(self):
        movement_commands = {Orientation.TOP: ChipCoordinate(1, 2, 3)}
        with self.assertRaises(MoverError):
            self.mover.move_relative(movement_commands)

    @patch.object(DummyStage, "move_relative")
    def test_move_relative_with_ordering(self, move_relative_mock):
        self.left_calibration.update_axes_rotation(
            Axis.X, Direction.NEGATIVE, Axis.Z)
        self.left_calibration.update_axes_rotation(
            Axis.Y, Direction.POSITIVE, Axis.X)
        self.left_calibration.update_axes_rotation(
            Axis.Z, Direction.NEGATIVE, Axis.Y)

        self.assertTrue(self.left_calibration._axes_rotation.is_valid)

        self.right_calibration.update_axes_rotation(
            Axis.X, Direction.POSITIVE, Axis.Y)
        self.right_calibration.update_axes_rotation(
            Axis.Y, Direction.POSITIVE, Axis.Z)
        self.right_calibration.update_axes_rotation(
            Axis.Z, Direction.NEGATIVE, Axis.X)

        self.assertTrue(self.right_calibration._axes_rotation.is_valid)

        left_requested_offset = ChipCoordinate(42, 8, -17)
        right_requested_offset = ChipCoordinate(72, -42, 31)

        expected_left_offset = self.left_calibration._axes_rotation.chip_to_stage(
            left_requested_offset)
        expected_right_offset = self.right_calibration._axes_rotation.chip_to_stage(
            right_requested_offset)

        requested_ordering = [
            Orientation.BOTTOM,
            Orientation.RIGHT,
            Orientation.TOP,
            Orientation.LEFT]

        self.mover.move_relative(
            {Orientation.LEFT: left_requested_offset, Orientation.RIGHT: right_requested_offset},
            requested_ordering)

        move_relative_mock.assert_has_calls(
            [
                call(
                    x=expected_right_offset.x,
                    y=expected_right_offset.y,
                    z=expected_right_offset.z,
                    wait_for_stopping=True),
                call(
                    x=expected_left_offset.x,
                    y=expected_left_offset.y,
                    z=expected_left_offset.z,
                    wait_for_stopping=True),
            ],
            any_order=False)


class CoordinateSystemControlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        self.mover = MoverNew(None)

        self.left_calibration = self.mover.add_stage_calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)
        self.right_calibration = self.mover.add_stage_calibration(
            self.stage2, Orientation.RIGHT, DevicePort.OUTPUT)

        self.left_calibration.connect_to_stage()
        self.right_calibration.connect_to_stage()

    @parameterized.expand([(CoordinateSystem.CHIP,),
                          (CoordinateSystem.STAGE,), (CoordinateSystem.UNKNOWN,)])
    def test_set_valid_coordinate_system(self, valid_system):

        left_calibration_prior = self.left_calibration.coordinate_system
        right_calibration_prior = self.right_calibration.coordinate_system

        with self.mover.set_stages_coordinate_system(valid_system):
            self.assertEqual(
                self.left_calibration.coordinate_system, valid_system)
            self.assertEqual(
                self.right_calibration.coordinate_system, valid_system)

        self.assertEqual(
            self.left_calibration.coordinate_system, left_calibration_prior)
        self.assertEqual(
            self.right_calibration.coordinate_system, right_calibration_prior)

    def test_set_valid_coordinate_system_with_block_error(self):
        func = Mock(side_effect=RuntimeError)

        left_calibration_prior = self.left_calibration.coordinate_system
        right_calibration_prior = self.right_calibration.coordinate_system

        with self.assertRaises(RuntimeError):
            with self.mover.set_stages_coordinate_system(CoordinateSystem.CHIP):
                func()

        self.assertEqual(
            self.left_calibration.coordinate_system, left_calibration_prior)
        self.assertEqual(
            self.right_calibration.coordinate_system, right_calibration_prior)

    def test_set_nested_coordinate_system(self):
        self.left_calibration.set_coordinate_system(CoordinateSystem.UNKNOWN)
        self.right_calibration.set_coordinate_system(CoordinateSystem.UNKNOWN)

        with self.mover.set_stages_coordinate_system(CoordinateSystem.CHIP):
            self.assertEqual(
                self.left_calibration.coordinate_system, CoordinateSystem.CHIP)
            self.assertEqual(
                self.right_calibration.coordinate_system,
                CoordinateSystem.CHIP)

            with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
                self.assertEqual(
                    self.left_calibration.coordinate_system,
                    CoordinateSystem.STAGE)
                self.assertEqual(
                    self.right_calibration.coordinate_system,
                    CoordinateSystem.STAGE)

            self.assertEqual(
                self.left_calibration.coordinate_system, CoordinateSystem.CHIP)
            self.assertEqual(
                self.right_calibration.coordinate_system,
                CoordinateSystem.CHIP)

        self.assertEqual(
            self.left_calibration.coordinate_system, CoordinateSystem.UNKNOWN)
        self.assertEqual(
            self.right_calibration.coordinate_system, CoordinateSystem.UNKNOWN)
