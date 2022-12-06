#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import ctypes as ct
from contextlib import contextmanager
from enum import Enum
from itertools import product
import unittest
from parameterized import parameterized
from unittest.mock import Mock, ANY, call, patch, DEFAULT
from LabExT.Movement.Stage import Stage, StageError
import LabExT.Movement.Stages.Stage3DSmarAct as SmarActModule

import LabExT.Tests.Fixtures.MCSControlInterface as MCSControlInterface

MCSC_STATUS_OK = 0
MCSC_STATUS_ERR = 1


def with_MCSControl_driver_patch(func):
    """
    Patches MCSControl Driver
    """
    patch_driver_loaded = patch.object(
        SmarActModule.Stage3DSmarAct, 'driver_loaded', True)
    patch_mcsc = patch(
        'LabExT.Movement.Stages.Stage3DSmarAct.MCSC',
        spec=MCSControlInterface)

    return patch_mcsc(patch_driver_loaded(func))


def update_by_reference(mapping):
    """
    Updates a passed argument by reference.
    """
    def inner(*args):
        for arg_no, c_type in mapping.items():
            args[arg_no].value = c_type.value
        return DEFAULT
    return inner


def to_nanometer(um: int) -> int:
    return um * 1e3


def to_mircometer(nm: int) -> int:
    return nm * 1e-3


class SmarActTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.stage_address = 'usb:id:000000000'
        self.stage = SmarActModule.Stage3DSmarAct(self.stage_address)
        return super().setUp()

    def tearDown(self) -> None:
        self.stage.connected = False
        del self.stage

        return super().tearDown()

    @contextmanager
    def assert_exit_without_error(self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_OK = MCSC_STATUS_OK
        yield

    @contextmanager
    def assert_exit_with_error(
            self,
            mcsc_mock: MCSControlInterface,
            status_code: int):
        expected_error = "My Custom Error"
        mcsc_mock.SA_GetStatusInfo.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatusInfo.side_effect = update_by_reference({
            1: ct.c_char_p(expected_error.encode("utf-8"))
        })

        with self.assertRaises(StageError) as error_context:
            yield

        self.assertEqual("MCSControl Error: {}".format(
            expected_error), str(error_context.exception))
        mcsc_mock.SA_GetStatusInfo.assert_called_once_with(status_code, ANY)

    def assert_mock_has_call_with_arguments(self, func, args):
        """
        Checks if a driver function mock was called with a list of arguments with ctypes.
        """
        self.assertTrue(self._mock_has_call_with_arguments(func, args))

    def _mock_has_call_with_arguments(self, func, args):
        """
        Returns True if mock function has any call with given arguments
        """
        def extract_value(args): return [
            v.value if isinstance(
                v, ct._SimpleCData) else v for v in args]

        return any(
            extract_value(
                mock_call[0]) == extract_value(expected_args) for mock_call,
            expected_args in product(
                func.call_args_list,
                [args]))

    @contextmanager
    def assert_stage_disconnect(self, stage, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_CloseSystem.return_value = MCSC_STATUS_OK
        yield

    @contextmanager
    def successful_stage_connection(
            self, stage, mcsc_mock: MCSControlInterface):
        """
        Use this context manager when a connected stage with channels is needed.
        """
        system_handle = 42

        # Mock out system opening
        mcsc_mock.SA_OpenSystem.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_OpenSystem.side_effect = update_by_reference({
            0: ct.c_ulong(system_handle)
        })

        # Mock out sensor fetching
        mcsc_mock.SA_GetSensorType_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetSensorType_S.side_effect = update_by_reference({
            2: ct.c_ulong(1)
        })

        # Assume speed and acceleration setting works
        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_OK

        # Connect to Stage
        with patch.object(SmarActModule.Stage3DSmarAct._Channel, 'LINEAR_SENSORS', [1]):
            with self.assert_exit_without_error(mcsc_mock):
                stage.connect()
                yield(system_handle)


class BaseTest(SmarActTestCase):
    """
    Testing of Stage3DSmarAct base methods.
    """

    #
    #   Testing Initialization
    #

    def test_stage_initialization(self):
        self.assertIsNone(self.stage.handle)
        self.assertEqual({}, self.stage.channels)
        self.assertEqual(
            self.stage.address,
            self.stage_address.encode('utf-8'))

    def test_address_string(self):
        self.assertEqual(self.stage.address_string, self.stage_address)

    def test_to_string(self):
        self.assertEqual(str(self.stage),
                         "SmarAct Piezo-Stage at usb:id:000000000")

    #
    #   Testing Stage Discovery
    #

    @with_MCSControl_driver_patch
    def test_find_stage_addresses(self, mcsc_mock: MCSControlInterface):
        expected_stages = ['usb:id:000000001', 'usb:id:000000002']
        stages_char_array = ct.create_string_buffer(
            bytes("\n".join(expected_stages), "utf-8"))
        expected_size = ct.sizeof(stages_char_array)

        mcsc_mock.SA_FindSystems.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_FindSystems.side_effect = update_by_reference({
            1: stages_char_array,
            2: ct.c_ulong(expected_size)
        })

        with self.assert_exit_without_error(mcsc_mock):
            stages = SmarActModule.Stage3DSmarAct.find_stage_addresses()

            mcsc_mock.SA_FindSystems.assert_called_once()
            self.assertEqual(stages, expected_stages)

    @with_MCSControl_driver_patch
    def test_find_stage_addresses_when_empty_buffer(
            self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_FindSystems.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_FindSystems.side_effect = update_by_reference({
            2: ct.c_ulong(0)
        })

        with self.assert_exit_without_error(mcsc_mock):
            self.assertEqual(
                [], SmarActModule.Stage3DSmarAct.find_stage_addresses())
            mcsc_mock.SA_FindSystems.assert_called_once()

    #
    #   Testing Connect
    #

    @with_MCSControl_driver_patch
    def test_connect_if_open_system_fails(
            self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_OpenSystem.return_value = MCSC_STATUS_ERR

        with self.assert_exit_with_error(mcsc_mock, MCSC_STATUS_ERR):
            self.stage.connect()

        mcsc_mock.SA_OpenSystem.assert_called_once()
        self.assertFalse(self.stage.connected)
        self.assertIsNone(self.stage.handle)
        self.assertEqual({}, self.stage.channels)

    @with_MCSControl_driver_patch
    def test_connect_if_sensor_not_linear(
            self, mcsc_mock: MCSControlInterface):
        expected_handle = 42

        mcsc_mock.SA_OpenSystem.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_OpenSystem.side_effect = update_by_reference({
            0: ct.c_ulong(expected_handle)
        })

        mcsc_mock.SA_GetSensorType_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetSensorType_S.side_effect = update_by_reference({
            2: ct.c_ulong(50)
        })

        with self.assert_exit_without_error(mcsc_mock):
            with self.assertRaises(StageError) as error_context:
                self.stage.connect()

        mcsc_mock.SA_OpenSystem.assert_called_once()
        mcsc_mock.SA_GetSensorType_S.assert_called()
        self.assertTrue(
            'has no supported linear sensor' in str(
                error_context.exception))

        self.assertFalse(self.stage.connected)
        self.assertIsNone(self.stage.handle)
        self.assertEqual({}, self.stage.channels)

    @with_MCSControl_driver_patch
    def test_connect(self, mcsc_mock: MCSControlInterface):
        linear_sensor_code = 1
        expected_handle = 42

        mcsc_mock.SA_OpenSystem.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_OpenSystem.side_effect = update_by_reference({
            0: ct.c_ulong(expected_handle)
        })

        mcsc_mock.SA_GetSensorType_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetSensorType_S.side_effect = update_by_reference({
            2: ct.c_ulong(linear_sensor_code)
        })

        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_OK

        with patch.object(SmarActModule.Stage3DSmarAct._Channel, 'LINEAR_SENSORS', [linear_sensor_code]):
            with self.assert_exit_without_error(mcsc_mock):
                self.stage.connect()

        mcsc_mock.SA_OpenSystem.assert_called_once()
        mcsc_mock.SA_GetSensorType_S.assert_called()
        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.assert_called()
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.assert_called()

        self.assertTrue(self.stage.connected)
        self.assertEqual(self.stage.handle.value, expected_handle)

    #
    #   Testing Disconnect
    #

    @with_MCSControl_driver_patch
    def test_disconnect_successfully(self, mcsc_mock: MCSControlInterface):
        self.stage.connected = True

        mcsc_mock.SA_CloseSystem.return_value = MCSC_STATUS_OK

        with self.assert_exit_without_error(mcsc_mock):
            self.stage.disconnect()

        mcsc_mock.SA_CloseSystem.assert_called_once_with(self.stage.handle)
        self.assertFalse(self.stage.connected)
        self.assertIsNone(self.stage.handle)

    @with_MCSControl_driver_patch
    def test_disconnect_unsuccessfully(self, mcsc_mock: MCSControlInterface):
        self.stage.connected = True

        mcsc_mock.SA_CloseSystem.return_value = MCSC_STATUS_ERR

        with self.assert_exit_with_error(mcsc_mock, MCSC_STATUS_ERR):
            self.stage.disconnect()

        mcsc_mock.SA_CloseSystem.assert_called_once_with(self.stage.handle)
        self.assertTrue(self.stage.connected)

    #
    #   Testing Movement
    #

    @with_MCSControl_driver_patch
    def test_move_relative_without_waiting(
            self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_GotoPositionRelative_S.return_value = MCSC_STATUS_OK

        with self.successful_stage_connection(self.stage, mcsc_mock) as system_handle:
            with self.assert_exit_without_error(mcsc_mock):
                self.stage.move_relative(100, 200, wait_for_stopping=False)

        mcsc_mock.SA_GotoPositionAbsolute_S.assert_not_called()
        mcsc_mock.SA_GetStatus_S.assert_not_called()

        self.assert_mock_has_call_with_arguments(
            mcsc_mock.SA_GotoPositionRelative_S,
            (ct.c_ulong(system_handle), ct.c_ulong(0), ct.c_int(100000), 0)
        )

        self.assert_mock_has_call_with_arguments(
            mcsc_mock.SA_GotoPositionRelative_S,
            (ct.c_ulong(system_handle), ct.c_ulong(1), ct.c_int(200000), 0)
        )

    @parameterized.expand([
        (100, 200, 300),
        (100, 200, None),
        (100, None, 300),
        (100, None, None),
        (None, 200, 300),
        (None, 200, None),
        (None, None, 300),
        (None, None, None)
    ])
    @with_MCSControl_driver_patch
    def test_move_absolute_v2_without_waiting(
            self, x, y, z, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_GotoPositionAbsolute_S.return_value = MCSC_STATUS_OK

        with self.successful_stage_connection(self.stage, mcsc_mock) as system_handle:
            with self.assert_exit_without_error(mcsc_mock):
                self.stage.move_absolute(x, y, z, wait_for_stopping=False)

        def expected_arguments(axis_identifer, diff):
            return (
                ct.c_ulong(system_handle),
                ct.c_ulong(axis_identifer),
                ANY if diff is None else ct.c_int(int(to_nanometer(diff))),
                0
            )

        self.assertEqual(
            self._mock_has_call_with_arguments(
                mcsc_mock.SA_GotoPositionAbsolute_S,
                expected_arguments(0, x)
            ),
            True if x is not None else False)

        self.assertEqual(
            self._mock_has_call_with_arguments(
                mcsc_mock.SA_GotoPositionAbsolute_S,
                expected_arguments(1, y)
            ),
            True if y is not None else False)

        self.assertEqual(
            self._mock_has_call_with_arguments(
                mcsc_mock.SA_GotoPositionAbsolute_S,
                expected_arguments(2, z)
            ),
            True if z is not None else False)

    @with_MCSControl_driver_patch
    @patch("LabExT.Movement.Stages.Stage3DSmarAct.time.sleep")
    @patch.object(SmarActModule.Stage3DSmarAct._Channel, 'STATUS_CODES',
                  {MCSControlInterface.SA_STOPPED_STATUS: 'SA_STOPPED_STATUS'})
    def test_move_relative_with_waiting(
            self, sleep_mock, mcsc_mock: MCSControlInterface):
        """
        Simple test, if sleep gets triggered when status is not stopped
        """
        mcsc_mock.SA_GotoPositionRelative_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatus_S.return_value = MCSC_STATUS_OK

        mcsc_mock.SA_GetStatus_S.side_effect = update_by_reference({
            2: ct.c_ulong(MCSControlInterface.SA_STOPPED_STATUS)
        })

        with self.successful_stage_connection(self.stage, mcsc_mock):
            with self.assert_exit_without_error(mcsc_mock):
                self.stage.move_relative(-100, -200, wait_for_stopping=True)

        sleep_mock.assert_called_once()
        self.assertEqual(3, mcsc_mock.SA_GetStatus_S.call_count)

    @with_MCSControl_driver_patch
    @patch("LabExT.Movement.Stages.Stage3DSmarAct.time.sleep")
    @patch.object(SmarActModule.Stage3DSmarAct._Channel, 'STATUS_CODES',
                  {MCSControlInterface.SA_STOPPED_STATUS: 'SA_STOPPED_STATUS'})
    def test_move_absolute_v2_with_waiting(
            self, sleep_mock, mcsc_mock: MCSControlInterface):
        """
        Simple test, if sleep gets triggered when status is not stopped
        """
        mcsc_mock.SA_GotoPositionAbsolute_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatus_S.return_value = MCSC_STATUS_OK

        mcsc_mock.SA_GetStatus_S.side_effect = update_by_reference({
            2: ct.c_ulong(MCSControlInterface.SA_STOPPED_STATUS)
        })

        with self.successful_stage_connection(self.stage, mcsc_mock):
            with self.assert_exit_without_error(mcsc_mock):
                self.stage.move_absolute(-1000, 200,
                                         2000, wait_for_stopping=True)

        sleep_mock.assert_called_once()
        self.assertEqual(3, mcsc_mock.SA_GetStatus_S.call_count)


class ChannelTest(SmarActTestCase):
    """
    Testing of a Stage3DSmarAct channel. A channel represents one axis.
    """

    def setUp(self) -> None:
        super().setUp()

        self.channel = SmarActModule.Stage3DSmarAct._Channel(
            self.stage, 0, "X")

    #
    #   Testing Channel Status
    #

    @with_MCSControl_driver_patch
    def test_get_status(self, mcsc_mock: MCSControlInterface):
        expected_status_code = 2

        mcsc_mock.SA_GetStatus_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatus_S.side_effect = update_by_reference({
            2: ct.c_ulong(expected_status_code)
        })

        with self.assert_exit_without_error(mcsc_mock):
            actual_status = self.channel.status

        mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status_code)
        self.assertEqual(self.channel._status, expected_status_code)

    @with_MCSControl_driver_patch
    def test_get_humanized_status(self, mcsc_mock: MCSControlInterface):
        expected_status = 1
        expected_status_string = 'MY_CUSTOM_STATUS'

        mcsc_mock.SA_GetStatus_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatus_S.side_effect = update_by_reference({
            2: ct.c_ulong(expected_status)
        })

        with self.assert_exit_without_error(mcsc_mock):
            with patch.object(SmarActModule.Stage3DSmarAct._Channel, 'STATUS_CODES', {
                expected_status: expected_status_string
            }):
                actual_status = self.channel.humanized_status

        mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status_string)
        self.assertEqual(self.channel._status, expected_status)

    @with_MCSControl_driver_patch
    def test_get_humanized_status_if_unknown(
            self, mcsc_mock: MCSControlInterface):
        expected_status = 1
        expected_status_string = "Unknown status code: " + str(expected_status)

        mcsc_mock.SA_GetStatus_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetStatus_S.side_effect = update_by_reference({
            2: ct.c_ulong(1)
        })

        with self.assert_exit_without_error(mcsc_mock):
            with patch.object(SmarActModule.Stage3DSmarAct._Channel, 'STATUS_CODES', {}):
                actual_status = self.channel.humanized_status

        mcsc_mock.SA_GetStatus_S.assert_called_once()
        self.assertEqual(actual_status, expected_status_string)
        self.assertEqual(self.channel._status, expected_status)

    #
    #   Testing Channel Sensor
    #

    @with_MCSControl_driver_patch
    def test_get_sensor(self, mcsc_mock: MCSControlInterface):
        expected_sensor = 1

        mcsc_mock.SA_GetSensorType_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetSensorType_S.side_effect = update_by_reference({
            2: ct.c_ulong(expected_sensor)
        })

        with self.assert_exit_without_error(mcsc_mock):
            actual_sensor = self.channel.sensor

        mcsc_mock.SA_GetSensorType_S.assert_called_once()
        self.assertEqual(actual_sensor, expected_sensor)
        self.assertEqual(self.channel._sensor, expected_sensor)

    @with_MCSControl_driver_patch
    def test_is_sensor_linear(self, mcsc_mock: MCSControlInterface):
        expected_sensor = 1

        mcsc_mock.SA_GetSensorType_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetSensorType_S.side_effect = update_by_reference({
            2: ct.c_ulong(expected_sensor)
        })

        with self.assert_exit_without_error(mcsc_mock):
            with patch.object(SmarActModule.Stage3DSmarAct._Channel, 'LINEAR_SENSORS', [1]):
                self.assertTrue(self.channel.is_sensor_linear)

        mcsc_mock.SA_GetSensorType_S.assert_called_once()

    #
    #   Testing Channel Position
    #

    @with_MCSControl_driver_patch
    def test_get_position_when_stored_correctly(
            self, mcsc_mock: MCSControlInterface):
        expected_position = 128
        self.channel._position = expected_position

        mcsc_mock.SA_GetPosition_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetPosition_S.side_effect = update_by_reference({
            2: ct.c_int(int(to_nanometer(expected_position)))
        })

        with self.assert_exit_without_error(mcsc_mock):
            actual_position = self.channel.position

        mcsc_mock.SA_GetPosition_S.assert_called_once()
        self.assertEqual(actual_position, expected_position)
        self.assertEqual(self.channel._position, expected_position)

    @with_MCSControl_driver_patch
    def test_get_position_when_stored_incorrectly(
            self, mcsc_mock: MCSControlInterface):
        system_position = 256
        stored_position = 512

        self.channel._position = stored_position
        mcsc_mock.SA_GetPosition_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetPosition_S.side_effect = update_by_reference({
            2: ct.c_int(int(to_nanometer(system_position)))
        })

        with self.assert_exit_without_error(mcsc_mock):
            actual_position = self.channel.position

        mcsc_mock.SA_GetPosition_S.assert_called_once()
        self.assertEqual(actual_position, system_position)
        self.assertEqual(self.channel._position, system_position)

    #
    #   Testing Channel Speed
    #

    @with_MCSControl_driver_patch
    def test_get_speed_when_stored_correctly(
            self, mcsc_mock: MCSControlInterface):
        expected_speed = 500
        self.channel._speed = expected_speed

        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.side_effect = update_by_reference(
            {2: ct.c_int(int(to_nanometer(expected_speed)))})

        with self.assert_exit_without_error(mcsc_mock):
            actual_speed = self.channel.speed

        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(actual_speed, expected_speed)
        self.assertEqual(self.channel._speed, expected_speed)

    @with_MCSControl_driver_patch
    def test_get_speed_when_stored_incorrectly(
            self, mcsc_mock: MCSControlInterface):
        system_speed = 400
        stored_speed = 500

        self.channel._speed = stored_speed
        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.side_effect = update_by_reference(
            {2: ct.c_int(int(to_nanometer(system_speed)))})

        with self.assert_exit_without_error(mcsc_mock):
            actual_speed = self.channel.speed

        mcsc_mock.SA_GetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(actual_speed, system_speed)
        self.assertEqual(self.channel._speed, system_speed)

    @with_MCSControl_driver_patch
    def test_set_speed_successfully(self, mcsc_mock: MCSControlInterface):
        new_speed = 600

        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.side_effect = update_by_reference(
            {2: ct.c_int(int(to_nanometer(new_speed)))})

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.speed = new_speed

        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(self.channel._speed, new_speed)

    @with_MCSControl_driver_patch
    def test_set_speed_unsuccessfully(self, mcsc_mock: MCSControlInterface):
        current_speed = 700
        new_speed = 600

        self.channel._speed = current_speed
        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.return_value = MCSC_STATUS_ERR
        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.side_effect = update_by_reference(
            {2: ct.c_int(int(to_nanometer(new_speed)))})

        with self.assert_exit_with_error(mcsc_mock, MCSC_STATUS_ERR):
            self.channel.speed = new_speed

        mcsc_mock.SA_SetClosedLoopMoveSpeed_S.assert_called_once()
        self.assertEqual(self.channel._speed, current_speed)

    #
    #   Testing channel acceleration
    #

    @with_MCSControl_driver_patch
    def test_get_acceleration_when_stored_correctly(
            self, mcsc_mock: MCSControlInterface):
        expected_acceleration = 500
        self.channel._acceleration = expected_acceleration

        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.side_effect = update_by_reference(
            {2: ct.c_int(expected_acceleration)})

        with self.assert_exit_without_error(mcsc_mock):
            actual_acceleration = self.channel.acceleration

        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(actual_acceleration, expected_acceleration)
        self.assertEqual(self.channel._acceleration, expected_acceleration)

    @with_MCSControl_driver_patch
    def test_get_acceleration_when_stored_incorrectly(
            self, mcsc_mock: MCSControlInterface):
        system_acceleration = 400
        stored_acceleration = 500

        self.channel._acceleration = stored_acceleration
        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.side_effect = update_by_reference(
            {2: ct.c_int(system_acceleration)})

        with self.assert_exit_without_error(mcsc_mock):
            actual_acceleration = self.channel.acceleration

        mcsc_mock.SA_GetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(actual_acceleration, system_acceleration)
        self.assertEqual(self.channel._acceleration, system_acceleration)

    @with_MCSControl_driver_patch
    def test_set_acceleration_successfully(
            self, mcsc_mock: MCSControlInterface):
        new_acceleration = 600

        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.side_effect = update_by_reference(
            {2: ct.c_int(int(new_acceleration))})

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.acceleration = new_acceleration

        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(self.channel._acceleration, new_acceleration)

    @with_MCSControl_driver_patch
    def test_set_acceleration_unsuccessfully(
            self, mcsc_mock: MCSControlInterface):
        current_acceleration = 700
        new_acceleration = 600

        self.channel._acceleration = current_acceleration
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.return_value = MCSC_STATUS_ERR
        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.side_effect = update_by_reference(
            {2: ct.c_int(int(current_acceleration))})

        with self.assert_exit_with_error(mcsc_mock, MCSC_STATUS_ERR):
            self.channel.acceleration = new_acceleration

        mcsc_mock.SA_SetClosedLoopMoveAcceleration_S.assert_called_once()
        self.assertEqual(self.channel._acceleration, current_acceleration)

    #
    #   Testing channel movement mode
    #

    @with_MCSControl_driver_patch
    def test_set_movement_mode_relative(self, _: MCSControlInterface):
        expected_movement_mode = SmarActModule.MovementType.RELATIVE

        self.channel.movement_mode = expected_movement_mode

        self.assertEqual(self.channel.movement_mode, expected_movement_mode)
        self.assertEqual(self.channel._movement_mode, expected_movement_mode)

    @with_MCSControl_driver_patch
    def test_set_movement_mode_absolute(self, _: MCSControlInterface):
        expected_movement_mode = SmarActModule.MovementType.ABSOLUTE

        self.channel.movement_mode = expected_movement_mode

        self.assertEqual(self.channel.movement_mode, expected_movement_mode)
        self.assertEqual(self.channel._movement_mode, expected_movement_mode)

    @with_MCSControl_driver_patch
    def test_set_movement_mode_invalid(self, _: MCSControlInterface):
        current_mode = self.channel._movement_mode

        class DummyMode(Enum):
            CUSTOM_MODE = 3

        with self.assertRaises(ValueError) as error:
            self.channel.movement_mode = DummyMode.CUSTOM_MODE

        self.assertTrue('Invalid movement mode' in str(error.exception))
        self.assertEqual(self.channel.movement_mode, current_mode)
        self.assertEqual(self.channel._movement_mode, current_mode)

    #
    #   Testing channel movement
    #

    @with_MCSControl_driver_patch
    def test_move_relative(self, mcsc_mock: MCSControlInterface):
        requested_diff = 200

        self.channel.movement_mode = SmarActModule.MovementType.RELATIVE
        self.assertEqual(
            self.channel.movement_mode,
            SmarActModule.MovementType.RELATIVE)

        mcsc_mock.SA_GotoPositionRelative_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GotoPositionAbsolute_S.return_value = MCSC_STATUS_OK

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.move(
                requested_diff,
                SmarActModule.MovementType.RELATIVE)

        mcsc_mock.SA_GotoPositionRelative_S.assert_called_once()
        mcsc_mock.SA_GotoPositionAbsolute_S.assert_not_called()
        self.assertEqual(
            self.channel.movement_mode,
            SmarActModule.MovementType.RELATIVE)

    @with_MCSControl_driver_patch
    def test_move_absolute(self, mcsc_mock: MCSControlInterface):
        requested_diff = 200

        mcsc_mock.SA_GotoPositionRelative_S.return_value = MCSC_STATUS_OK
        mcsc_mock.SA_GotoPositionAbsolute_S.return_value = MCSC_STATUS_OK

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.move(
                requested_diff,
                SmarActModule.MovementType.ABSOLUTE)

        mcsc_mock.SA_GotoPositionRelative_S.assert_not_called()
        mcsc_mock.SA_GotoPositionAbsolute_S.assert_called_once()
        self.assertEqual(
            self.channel.movement_mode,
            SmarActModule.MovementType.ABSOLUTE)

    @with_MCSControl_driver_patch
    def test_find_reference_mark(self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_BACKWARD_DIRECTION = 1
        mcsc_mock.SA_AUTO_ZERO = 1
        mcsc_mock.SA_FindReferenceMark_S.return_value = MCSC_STATUS_OK

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.find_reference_mark()

        mcsc_mock.SA_FindReferenceMark_S.assert_called_once_with(
            self.stage.handle, self.channel._handle, 1, 0, 1)

    #
    #   Testing channel control
    #

    @with_MCSControl_driver_patch
    def test_channel_stop(self, mcsc_mock: MCSControlInterface):
        mcsc_mock.SA_Stop_S.return_value = MCSC_STATUS_OK

        with self.assert_exit_without_error(mcsc_mock):
            self.channel.stop()

        mcsc_mock.SA_Stop_S.assert_called_once_with(
            self.stage.handle,
            self.channel._handle
        )
