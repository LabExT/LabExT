#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import ctypes as ct
from enum import Enum
from unittest.mock import Mock, patch

from LabExT.Tests.Movement.Stage3DSmarAct.SmarActTestCase import SmarActTestCase, Stage3DSmarAct
from LabExT.Movement.Stage3DSmarAct import MovementType
from LabExT.Movement.Stage import StageError


class ChannelTest(SmarActTestCase):
    def test_channel_initialization(self):
        self.assertEqual(self.channel._handle.value, 42)

    # Testing channel status

    def test_get_status(self):
        expected_status = 2
        self.mcsc_mock.SA_GetStatus_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(expected_status)
            }))

        actual_status = self.channel.status

        self.mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status)
        self.assertEqual(self.channel._status, expected_status)

    def test_get_humanized_status(self):
        expected_status = 1
        expected_status_string = 'MY_CUSTOM_STATUS'
        self.mcsc_mock.SA_GetStatus_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(expected_status)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'STATUS_CODES', {
            expected_status: expected_status_string
        }):
            actual_status = self.channel.humanized_status

        self.mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status_string)
        self.assertEqual(self.channel._status, expected_status)

    def test_get_humanized_status_if_unknown(self):
        expected_status = 1
        expected_status_string = "Unknown status code: " + str(expected_status)
        self.mcsc_mock.SA_GetStatus_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(expected_status)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'STATUS_CODES', {}):
            actual_status = self.channel.humanized_status

        self.mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status_string)
        self.assertEqual(self.channel._status, expected_status)

    # Testing channel sensor

    def test_get_sensor(self):
        expected_sensor = 1
        self.mcsc_mock.SA_GetSensorType_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(expected_sensor)
            }))

        actual_sensor = self.channel.sensor

        self.mcsc_mock.SA_GetSensorType_S.assert_called_once()
        self.assertEqual(actual_sensor, expected_sensor)
        self.assertEqual(self.channel._sensor, expected_sensor)

    def test_is_sensor_linear(self):
        expected_sensor = 1
        self.mcsc_mock.SA_GetSensorType_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(expected_sensor)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'LINEAR_SENSORS', [1]):
            self.assertTrue(self.channel.is_sensor_linear)

        self.mcsc_mock.SA_GetSensorType_S.assert_called_once()

    # Testing channel position

    def test_get_position_when_stored_correctly(self):
        expected_position = 128
        self.channel._position = expected_position

        self.mcsc_mock.SA_GetPosition_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(expected_position)))
            }))

        actual_position = self.channel.position

        self.mcsc_mock.SA_GetPosition_S.assert_called_once()
        self.assertEqual(actual_position, expected_position)
        self.assertEqual(self.channel._position, expected_position)

    def test_get_position_when_stored_incorrectly(self):
        system_position = 256
        stored_position = 512

        self.channel._position = stored_position
        self.mcsc_mock.SA_GetPosition_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(system_position)))
            }))

        actual_position = self.channel.position

        self.mcsc_mock.SA_GetPosition_S.assert_called_once()
        self.assertEqual(actual_position, system_position)
        self.assertEqual(self.channel._position, system_position)

    # Testing channel speed

    def test_get_speed_when_stored_correctly(self):
        expected_speed = 500
        self.channel._speed = expected_speed

        self.mcsc_mock.SA_GetClosedLoopMoveSpeed_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(expected_speed)))
            }))

        actual_speed = self.channel.speed

        self.mcsc_mock.SA_GetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(actual_speed, expected_speed)
        self.assertEqual(self.channel._speed, expected_speed)

    def test_get_speed_when_stored_incorrectly(self):
        system_speed = 400
        stored_speed = 500

        self.channel._speed = stored_speed
        self.mcsc_mock.SA_GetClosedLoopMoveSpeed_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(system_speed)))
            }))

        actual_speed = self.channel.speed

        self.mcsc_mock.SA_GetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(actual_speed, system_speed)
        self.assertEqual(self.channel._speed, system_speed)

    def test_set_speed_successfully(self):
        new_speed = 600

        self.mcsc_mock.SA_SetClosedLoopMoveSpeed_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(new_speed)))
            }))

        self.channel.speed = new_speed

        self.mcsc_mock.SA_SetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(
            self.mcsc_mock.SA_SetClosedLoopMoveSpeed_S.call_args.args[2].value, int(
                self._to_nanometer(new_speed)))
        self.assertEqual(self.channel._speed, new_speed)

    def test_set_speed_unsuccessfully(self):
        current_speed = 700
        new_speed = 600

        self.channel._speed = current_speed
        self.mcsc_mock.SA_SetClosedLoopMoveSpeed_S = Mock(
            return_value=self.MCSC_STATUS_ERR,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(self._to_nanometer(new_speed)))
            }))

        with self.assertRaises(StageError):
            self.channel.speed = new_speed

        self.mcsc_mock.SA_SetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(self.channel._speed, current_speed)

    # Testing channel acceleration

    def test_get_acceleration_when_stored_correctly(self):
        expected_acceleration = 500
        self.channel._acceleration = expected_acceleration

        self.mcsc_mock.SA_GetClosedLoopMoveAcceleration_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(expected_acceleration)
            }))

        actual_acceleration = self.channel.acceleration

        self.mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(actual_acceleration, expected_acceleration)
        self.assertEqual(self.channel._acceleration, expected_acceleration)

    def test_get_acceleration_when_stored_incorrectly(self):
        system_acceleration = 400
        stored_acceleration = 500

        self.channel._acceleration = stored_acceleration
        self.mcsc_mock.SA_GetClosedLoopMoveAcceleration_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(system_acceleration)
            }))

        actual_acceleration = self.channel.acceleration

        self.mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(actual_acceleration, system_acceleration)
        self.assertEqual(self.channel._acceleration, system_acceleration)

    def test_set_acceleration_successfully(self):
        new_acceleration = 600

        self.mcsc_mock.SA_SetClosedLoopMoveAcceleration_S = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(new_acceleration))
            }))

        self.channel.acceleration = new_acceleration

        self.mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(
            self.mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.call_args.args[2].value,
            int(new_acceleration))
        self.assertEqual(self.channel._acceleration, new_acceleration)

    def test_set_acceleration_unsuccessfully(self):
        current_acceleration = 700
        new_acceleration = 600

        self.channel._acceleration = current_acceleration
        self.mcsc_mock.SA_SetClosedLoopMoveAcceleration_S = Mock(
            return_value=self.MCSC_STATUS_ERR,
            side_effect=self.update_by_reference({
                2: ct.c_int(int(current_acceleration))
            }))

        with self.assertRaises(StageError):
            self.channel.acceleration = new_acceleration

        self.mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(self.channel._acceleration, current_acceleration)

    # Testing channel movement mode

    def test_set_movement_mode_relative(self):
        expected_movement_mode = MovementType.RELATIVE

        self.channel.movement_mode = expected_movement_mode

        self.assertEqual(self.channel.movement_mode, expected_movement_mode)
        self.assertEqual(self.channel._movement_mode, expected_movement_mode)

    def test_set_movement_mode_absolute(self):
        expected_movement_mode = MovementType.ABSOLUTE

        self.channel.movement_mode = expected_movement_mode

        self.assertEqual(self.channel.movement_mode, expected_movement_mode)
        self.assertEqual(self.channel._movement_mode, expected_movement_mode)

    def test_set_movement_mode_invalid(self):
        current_mode = self.channel._movement_mode

        class DummyMode(Enum):
            CUSTOM_MODE = 3

        with self.assertRaises(ValueError) as error:
            self.channel.movement_mode = DummyMode.CUSTOM_MODE

        self.assertTrue('Invalid movement mode' in str(error.exception))
        self.assertEqual(self.channel.movement_mode, current_mode)
        self.assertEqual(self.channel._movement_mode, current_mode)

    # Testing channel movement

    def test_move_relative(self):
        requested_diff = 200

        self.channel.movement_mode = MovementType.RELATIVE
        self.assertEqual(self.channel.movement_mode, MovementType.RELATIVE)

        self.mcsc_mock.SA_GotoPositionRelative_S = Mock(
            return_value=self.MCSC_STATUS_OK)
        self.mcsc_mock.SA_GotoPositionAbsolute_S = Mock(
            return_value=self.MCSC_STATUS_OK)

        self.channel.move(requested_diff, MovementType.RELATIVE, False)

        self.mcsc_mock.SA_GotoPositionRelative_S.assert_called_once()
        self.mcsc_mock.SA_GotoPositionAbsolute_S.assert_not_called()
        self.assertEqual(
            self.mcsc_mock.SA_GotoPositionRelative_S.call_args.args[2].value, int(
                self._to_nanometer(requested_diff)))

    def test_move_absolute(self):
        requested_diff = 200

        self.mcsc_mock.SA_GotoPositionRelative_S = Mock(
            return_value=self.MCSC_STATUS_OK)
        self.mcsc_mock.SA_GotoPositionAbsolute_S = Mock(
            return_value=self.MCSC_STATUS_OK)

        self.channel.move(
            diff=requested_diff,
            mode=MovementType.ABSOLUTE,
            wait_for_stopping=False)

        self.mcsc_mock.SA_GotoPositionRelative_S.assert_not_called()
        self.mcsc_mock.SA_GotoPositionAbsolute_S.assert_called_once()
        self.assertEqual(self.channel.movement_mode, MovementType.ABSOLUTE)
        self.assertEqual(
            self.mcsc_mock.SA_GotoPositionAbsolute_S.call_args.args[2].value, int(
                self._to_nanometer(requested_diff)))

    def test_find_reference_mark(self):
        self.mcsc_mock.SA_BACKWARD_DIRECTION = 1
        self.mcsc_mock.SA_AUTO_ZERO = 1
        self.mcsc_mock.SA_FindReferenceMark_S = Mock(
            return_value=self.MCSC_STATUS_OK)

        self.channel.find_reference_mark()

        self.mcsc_mock.SA_FindReferenceMark_S.assert_called_once_with(
            self.stage.handle, self.channel._handle, 1, 0, 1)

    # Testing channel control

    def test_channel_stop(self):
        self.mcsc_mock.SA_Stop_S = Mock(return_value=self.MCSC_STATUS_OK)

        self.channel.stop()

        self.mcsc_mock.SA_Stop_S.assert_called_once_with(
            self.stage.handle,
            self.channel._handle
        )
