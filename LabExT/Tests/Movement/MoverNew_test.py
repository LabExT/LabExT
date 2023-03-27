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
from LabExT.Movement.Calibration import Calibration

from LabExT.Movement.MoverNew import MoverError, MoverNew, assert_connected_stages
from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import DevicePort, Orientation, Axis, Direction, CoordinateSystem


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
        self.mover.register_stage_calibration(Calibration(
            self.mover, self.stage, DevicePort.INPUT))
        self.stage.disconnect()

        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(MoverError):
            assert_connected_stages(func)(self.mover)

        func.assert_not_called()

    def test_assert_connected_stages_calls_function_if_stage_is_connected(
            self):
        self.mover.register_stage_calibration(Calibration(
            self.mover, self.stage, DevicePort.INPUT))
        self.stage.connect()

        func = Mock()
        func.__name__ = 'Dummy Function'

        assert_connected_stages(func)(self.mover)
        func.assert_called_once()


class RegisterStageCalibrationTest(unittest.TestCase):
    """
    Tests register new calibrations.
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

    def test_register_reject_double_ports(self):
        valid_calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(valid_calibration)
        current_calibrations = self.mover.calibrations

        self.assertIn(valid_calibration, self.mover.calibrations)
        self.assertEqual(
            self.mover.get_port_assigned_calibration(DevicePort.INPUT),
            valid_calibration)

        with self.assertRaises(MoverError) as error_context:
            self.mover.register_stage_calibration(Calibration(
                self.mover, self.stage2, DevicePort.INPUT))

        self.assertEqual(
            "A Stage has already been assigned for device port Input", str(
                error_context.exception))
        self.assertEqual(current_calibrations, self.mover.calibrations)
        self.assertEqual(1, len(self.mover.calibrations))

    def test_register_stage_calibration_reject_double_stages(self):
        valid_calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(valid_calibration)
        current_calibrations = self.mover.calibrations

        self.assertIn(valid_calibration, self.mover.calibrations)
        self.assertEqual(
            self.mover.get_port_assigned_calibration(DevicePort.INPUT),
            valid_calibration)

        with self.assertRaises(MoverError) as error_context:
            self.mover.register_stage_calibration(Calibration(
                self.mover, self.stage, DevicePort.OUTPUT))

        self.assertEqual("The stage '{}' has already been registered.".format(
            str(self.stage)), str(error_context.exception))
        self.assertEqual(current_calibrations, self.mover.calibrations)
        self.assertEqual(1, len(self.mover.calibrations))

    def test_active_stage_includes_new_stage(self):
        self.mover.register_stage_calibration(Calibration(
            self.mover, self.stage, DevicePort.INPUT))
        self.mover.register_stage_calibration(Calibration(
            self.mover, self.stage2, DevicePort.OUTPUT))

        self.assertIn(self.stage, self.mover.active_stages)
        self.assertIn(self.stage2, self.mover.active_stages)

    def test_left_and_input_calibration_property(self):
        calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(calibration)

        self.assertEqual(calibration, self.mover.input_calibration)

    def test_right_and_output_calibration_property(self):
        calibration = Calibration(
            self.mover, self.stage, DevicePort.OUTPUT)
        self.mover.register_stage_calibration(calibration)

        self.assertEqual(calibration, self.mover.output_calibration)

    def test_set_stage_settings_successfully(self):
        self.assertIsNone(self.stage.get_speed_xy())
        self.assertIsNone(self.stage.get_speed_xy())
        self.assertIsNone(self.stage.get_acceleration_xy())

        calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(calibration)

        self.assertEqual(self.stage.get_speed_xy(), self.mover._speed_xy)
        self.assertEqual(self.stage.get_speed_z(), self.mover._speed_z)
        self.assertEqual(
            self.stage.get_acceleration_xy(),
            self.mover._acceleration_xy)

    def test_deregister_stage_calibration_if_missing(self):
        calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)

        self.assertNotIn(calibration, self.mover.calibrations)

        with self.assertRaises(MoverError):
            self.mover.deregister_stage_calibration(calibration)

    def test_deregister_stage_calibration(self):
        calibration = Calibration(self.mover, self.stage)
        self.mover.register_stage_calibration(calibration)

        self.assertIn(calibration, self.mover.calibrations)

        self.mover.deregister_stage_calibration(calibration)

        self.assertNotIn(calibration, self.mover.calibrations)

    def test_deregister_stage_calibration_with_port(self):
        calibration = Calibration(self.mover, self.stage, DevicePort.INPUT)
        calibration2 = Calibration(self.mover, self.stage2, DevicePort.OUTPUT)
        self.mover.register_stage_calibration(calibration)
        self.mover.register_stage_calibration(calibration2)

        self.assertTrue(calibration.is_automatic_movement_enabled)
        self.assertTrue(calibration2.is_automatic_movement_enabled)

        self.assertIn(calibration, self.mover.calibrations)
        self.assertIn(calibration2, self.mover.calibrations)
        self.assertEqual(
            self.mover.get_port_assigned_calibration(DevicePort.INPUT),
            calibration)
        self.assertEqual(
            self.mover.get_port_assigned_calibration(DevicePort.OUTPUT),
            calibration2)

        # Deregister input calibration
        self.mover.deregister_stage_calibration(calibration)

        self.assertNotIn(calibration, self.mover.calibrations)
        self.assertIsNone(
            self.mover.get_port_assigned_calibration(
                DevicePort.INPUT))
        self.assertEqual(
            self.mover.get_port_assigned_calibration(DevicePort.OUTPUT),
            calibration2)

        # Deregister output calibration
        self.mover.deregister_stage_calibration(calibration2)

        self.assertNotIn(calibration2, self.mover.calibrations)
        self.assertIsNone(
            self.mover.get_port_assigned_calibration(
                DevicePort.OUTPUT))


class MoverStageSettingsTest(unittest.TestCase):
    """
    Tests stage settings.
    """

    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        with patch.object(MoverNew, "MOVER_SETTINGS_FILE", "/mocked/mover_settings.json"):
            self.mover = MoverNew(None)

        calibration1 = Calibration(self.mover, self.stage, DevicePort.INPUT)
        calibration2 = Calibration(self.mover, self.stage2, DevicePort.OUTPUT)

        self.mover.register_stage_calibration(calibration1)
        self.mover.register_stage_calibration(calibration2)

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
        calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(calibration)
        calibration.connect_to_stage()

        self.assertTrue(
            calibration._axes_rotation.is_valid)

        self.assertTrue(self.mover.can_move_relatively)

    def test_with_one_invalid_calibration(self):
        calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(calibration)
        calibration.connect_to_stage()

        calibration.update_axes_rotation(Axis.X, Direction.NEGATIVE, Axis.Y)
        self.assertFalse(
            calibration._axes_rotation.is_valid)

        self.assertFalse(self.mover.can_move_relatively)

    def test_with_one_valid_and_one_invalid_calibration(self):
        valid_calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.mover.register_stage_calibration(valid_calibration)
        valid_calibration.connect_to_stage()

        self.assertTrue(
            valid_calibration._axes_rotation.is_valid)

        invalid_calibration = Calibration(
            self.mover, self.stage2, DevicePort.OUTPUT)
        self.mover.register_stage_calibration(invalid_calibration)
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

        self.input_calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.output_calibration = Calibration(
            self.mover, self.stage2, DevicePort.OUTPUT)

        self.mover.register_stage_calibration(self.input_calibration)
        self.mover.register_stage_calibration(self.output_calibration)

        self.input_calibration.connect_to_stage()
        self.output_calibration.connect_to_stage()

    def test_raises_error_if_axes_rotation_in_valid(self):
        self.input_calibration.update_axes_rotation(
            Axis.X, Direction.NEGATIVE, Axis.Y)
        self.assertFalse(self.input_calibration._axes_rotation.is_valid)

        movement_command = {Orientation.LEFT: ChipCoordinate(1, 2, 3)}
        with self.assertRaises(MoverError):
            self.mover.move_relative(movement_command)

    def test_raises_error_if_stage_is_disconnected(self):
        self.output_calibration.disconnect_to_stage()

        movement_command = {Orientation.RIGHT: ChipCoordinate(1, 2, 3)}
        with self.assertRaises(MoverError):
            self.mover.move_relative(movement_command)

    @patch.object(DummyStage, "move_relative")
    def test_move_relative_with_ordering(self, move_relative_mock):
        self.input_calibration.update_axes_rotation(
            Axis.X, Direction.NEGATIVE, Axis.Z)
        self.input_calibration.update_axes_rotation(
            Axis.Y, Direction.POSITIVE, Axis.X)
        self.input_calibration.update_axes_rotation(
            Axis.Z, Direction.NEGATIVE, Axis.Y)

        self.assertTrue(self.input_calibration._axes_rotation.is_valid)

        self.output_calibration.update_axes_rotation(
            Axis.X, Direction.POSITIVE, Axis.Y)
        self.output_calibration.update_axes_rotation(
            Axis.Y, Direction.POSITIVE, Axis.Z)
        self.output_calibration.update_axes_rotation(
            Axis.Z, Direction.NEGATIVE, Axis.X)

        self.assertTrue(self.output_calibration._axes_rotation.is_valid)

        input_requested_offset = ChipCoordinate(42, 8, -17)
        output_requested_offset = ChipCoordinate(72, -42, 31)

        expected_input_offset = self.input_calibration._axes_rotation.chip_to_stage(
            input_requested_offset)
        expected_output_offset = self.output_calibration._axes_rotation.chip_to_stage(
            output_requested_offset)

        self.mover.move_relative({
            self.input_calibration: input_requested_offset,
            self.output_calibration: output_requested_offset})

        move_relative_mock.assert_has_calls(
            [
                call(
                    x=expected_input_offset.x,
                    y=expected_input_offset.y,
                    z=expected_input_offset.z,
                    wait_for_stopping=True),
                call(
                    x=expected_output_offset.x,
                    y=expected_output_offset.y,
                    z=expected_output_offset.z,
                    wait_for_stopping=True),
            ],
            any_order=False)


class CoordinateSystemControlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:9887654321')

        self.mover = MoverNew(None)

        self.input_calibration = Calibration(
            self.mover, self.stage, DevicePort.INPUT)
        self.output_calibration = Calibration(
            self.mover, self.stage2, DevicePort.OUTPUT)

        self.mover.register_stage_calibration(self.input_calibration)
        self.mover.register_stage_calibration(self.output_calibration)

        self.input_calibration.connect_to_stage()
        self.output_calibration.connect_to_stage()

    @parameterized.expand([(CoordinateSystem.CHIP,),
                          (CoordinateSystem.STAGE,), (CoordinateSystem.UNKNOWN,)])
    def test_set_valid_coordinate_system(self, valid_system):

        left_calibration_prior = self.input_calibration.coordinate_system
        right_calibration_prior = self.output_calibration.coordinate_system

        with self.mover.set_stages_coordinate_system(valid_system):
            self.assertEqual(
                self.input_calibration.coordinate_system, valid_system)
            self.assertEqual(
                self.output_calibration.coordinate_system, valid_system)

        self.assertEqual(
            self.input_calibration.coordinate_system, left_calibration_prior)
        self.assertEqual(
            self.output_calibration.coordinate_system, right_calibration_prior)

    def test_set_valid_coordinate_system_with_block_error(self):
        func = Mock(side_effect=RuntimeError)

        left_calibration_prior = self.input_calibration.coordinate_system
        right_calibration_prior = self.output_calibration.coordinate_system

        with self.assertRaises(RuntimeError):
            with self.mover.set_stages_coordinate_system(CoordinateSystem.CHIP):
                func()

        self.assertEqual(
            self.input_calibration.coordinate_system, left_calibration_prior)
        self.assertEqual(
            self.output_calibration.coordinate_system, right_calibration_prior)

    def test_set_nested_coordinate_system(self):
        self.input_calibration.set_coordinate_system(CoordinateSystem.UNKNOWN)
        self.output_calibration.set_coordinate_system(CoordinateSystem.UNKNOWN)

        with self.mover.set_stages_coordinate_system(CoordinateSystem.CHIP):
            self.assertEqual(
                self.input_calibration.coordinate_system,
                CoordinateSystem.CHIP)
            self.assertEqual(
                self.output_calibration.coordinate_system,
                CoordinateSystem.CHIP)

            with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
                self.assertEqual(
                    self.input_calibration.coordinate_system,
                    CoordinateSystem.STAGE)
                self.assertEqual(
                    self.output_calibration.coordinate_system,
                    CoordinateSystem.STAGE)

            self.assertEqual(
                self.input_calibration.coordinate_system,
                CoordinateSystem.CHIP)
            self.assertEqual(
                self.output_calibration.coordinate_system,
                CoordinateSystem.CHIP)

        self.assertEqual(
            self.input_calibration.coordinate_system, CoordinateSystem.UNKNOWN)
        self.assertEqual(
            self.output_calibration.coordinate_system,
            CoordinateSystem.UNKNOWN)
