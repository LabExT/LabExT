#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from shutil import move
import unittest
import numpy as np
from unittest.mock import Mock, patch, call
from parameterized import parameterized

from LabExT.Tests.Utils import get_calibrations_from_file

from LabExT.Movement.config import State, Orientation, DevicePort, Axis, Direction
from LabExT.Movement.Stage import StageError
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Transformations import ChipCoordinate, CoordinatePairing, StageCoordinate
from LabExT.Movement.Calibration import Calibration, CalibrationError, assert_minimum_state_for_coordinate_system

EXPECTED_TO_REJECT = [
    (State.UNINITIALIZED, [State.CONNECTED, State.COORDINATE_SYSTEM_FIXED, State.SINGLE_POINT_FIXED, State.FULLY_CALIBRATED]),
    (State.CONNECTED, [State.COORDINATE_SYSTEM_FIXED, State.SINGLE_POINT_FIXED, State.FULLY_CALIBRATED]),
    (State.COORDINATE_SYSTEM_FIXED, [State.SINGLE_POINT_FIXED, State.FULLY_CALIBRATED]),
    (State.SINGLE_POINT_FIXED, [State.FULLY_CALIBRATED])]

EXPECTED_TO_ACCEPT = [
    (State.UNINITIALIZED, [State.UNINITIALIZED]),
    (State.CONNECTED, [State.UNINITIALIZED, State.CONNECTED]),
    (State.COORDINATE_SYSTEM_FIXED, [State.UNINITIALIZED, State.CONNECTED, State.COORDINATE_SYSTEM_FIXED]),
    (State.SINGLE_POINT_FIXED, [State.UNINITIALIZED, State.CONNECTED, State.COORDINATE_SYSTEM_FIXED, State.SINGLE_POINT_FIXED]),
    (State.FULLY_CALIBRATED, [State.UNINITIALIZED, State.CONNECTED, State.COORDINATE_SYSTEM_FIXED, State.SINGLE_POINT_FIXED, State.FULLY_CALIBRATED])]

VACHERIN_ROTATION, VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS = get_calibrations_from_file("vacherin.json", "left")

INVALID_AXES_MAPPING = [
    (Axis.X, Direction.POSITIVE, Axis.Y),
    (Axis.X, Direction.POSITIVE, Axis.Y),
    (Axis.Y, Direction.POSITIVE, Axis.Z)
]

VALID_AXES_MAPPING = [
    (Axis.X, Direction.NEGATIVE, Axis.Z),
    (Axis.Y, Direction.POSITIVE, Axis.X),
    (Axis.Z, Direction.NEGATIVE, Axis.Y)
]


class CalibrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = DummyStage('usb:123456789')

        self.mover = MoverNew(None)

        self.calibration = Calibration(
            self.mover, self.stage, Orientation.LEFT, DevicePort.INPUT)

    def set_valid_axes_rotation(self):
        for chip_axis, direction, stage_axis in VALID_AXES_MAPPING:
            self.calibration.update_axes_rotation(
                chip_axis, direction, stage_axis)

    def set_invalid_axes_rotation(self):
        for chip_axis, direction, stage_axis in INVALID_AXES_MAPPING:
            self.calibration.update_axes_rotation(
                chip_axis, direction, stage_axis)

    def set_valid_single_point_offset(self):
        self.calibration.update_single_point_offset(CoordinatePairing(
            self.calibration,
            StageCoordinate.from_numpy(VACHERIN_STAGE_COORDS[0]),
            Mock(),
            ChipCoordinate.from_numpy(VACHERIN_CHIP_COORDS[0])
        ))

    def set_valid_kabsch_rotation(self):
        for stage_coord, chip_coord in zip(
                VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS):
            self.calibration.update_kabsch_rotation(CoordinatePairing(
                calibration=self.calibration,
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord)))


class AssertMinimumStateForCoordinateSystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = Mock(spec=Calibration)
        self.func = Mock()
        self.func.__name__ = "Dummy Function"

        self.low_state = 0
        self.high_state = 1

        return super().setUp()

    def test_raises_error_if_coordinate_system_is_not_fixed(self):
        self.calibration.coordinate_system = None

        with self.assertRaises(CalibrationError):
            assert_minimum_state_for_coordinate_system()(self.func)(self.calibration)

        self.func.assert_not_called()

    @parameterized.expand(EXPECTED_TO_REJECT)
    def test_rejectes_all_states_higher_than_given_in_chip_system(
            self,
            given_state,
            required_states):
        self.calibration.coordinate_system = ChipCoordinate
        self.calibration.state = given_state

        for required_state in required_states:
            with self.assertRaises(CalibrationError):
                assert_minimum_state_for_coordinate_system(
                    chip_coordinate_system=required_state
                )(self.func)(self.calibration)

            self.func.assert_not_called()

    @parameterized.expand(EXPECTED_TO_REJECT)
    def test_rejectes_all_states_higher_than_given_in_stage_system(
            self,
            given_state,
            required_states):
        self.calibration.coordinate_system = StageCoordinate
        self.calibration.state = given_state

        for required_state in required_states:
            with self.assertRaises(CalibrationError):
                assert_minimum_state_for_coordinate_system(
                    stage_coordinate_system=required_state
                )(self.func)(self.calibration)

            self.func.assert_not_called()

    @parameterized.expand(EXPECTED_TO_ACCEPT)
    def test_accepts_all_states_higher_than_given_in_chip_system(
            self,
            given_state,
            required_states):
        self.calibration.coordinate_system = ChipCoordinate
        self.calibration.state = given_state

        for required_state in required_states:
            assert_minimum_state_for_coordinate_system(
                chip_coordinate_system=required_state
            )(self.func)(self.calibration)

            self.func.assert_called_once()
            self.func.reset_mock()

    @parameterized.expand(EXPECTED_TO_ACCEPT)
    def test_accepts_all_states_higher_than_given_in_stage_system(
            self,
            given_state,
            required_states):
        self.calibration.coordinate_system = StageCoordinate
        self.calibration.state = given_state

        for required_state in required_states:
            assert_minimum_state_for_coordinate_system(
                stage_coordinate_system=required_state
            )(self.func)(self.calibration)

            self.func.assert_called_once()
            self.func.reset_mock()


class CoordinateSystemControlTest(CalibrationTestCase):
    def test_set_chip_coordinate_system(self):
        with self.calibration.perform_in_chip_coordinates():
            self.assertEqual(
                self.calibration.coordinate_system,
                ChipCoordinate)

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_stage_coordinate_system(self):
        with self.calibration.perform_in_stage_coordinates():
            self.assertEqual(
                self.calibration.coordinate_system,
                StageCoordinate)

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_coordinate_system_twice(self):
        with self.assertRaises(CalibrationError):
            with self.calibration.perform_in_chip_coordinates():
                self.calibration.coordinate_system = StageCoordinate

        with self.assertRaises(CalibrationError):
            with self.calibration.perform_in_stage_coordinates():
                self.calibration.coordinate_system = ChipCoordinate

    @parameterized.expand([
        ('chip',), ('stage',), (ChipCoordinate(),), (StageCoordinate(),)
    ])
    def test_set_invalid_coordinate_system(self, invalid_system):
        with self.assertRaises(ValueError):
            self.calibration.coordinate_system = invalid_system

    def test_reset_coordinate_system(self):
        self.calibration.coordinate_system = ChipCoordinate
        self.assertEqual(self.calibration.coordinate_system, ChipCoordinate)

        self.calibration.coordinate_system = None
        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_chip_coordinate_system_with_block_error(self):
        func = Mock(side_effect=RuntimeError)

        with self.assertRaises(RuntimeError):
            with self.calibration.perform_in_chip_coordinates():
                self.assertEqual(
                    self.calibration.coordinate_system,
                    ChipCoordinate)
                func()

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_stage_coordinate_system_with_block_error(self):
        func = Mock(side_effect=RuntimeError)

        with self.assertRaises(RuntimeError):
            with self.calibration.perform_in_stage_coordinates():
                self.assertEqual(
                    self.calibration.coordinate_system,
                    StageCoordinate)
                func()

        self.assertIsNone(self.calibration.coordinate_system)


class DetermineStateTest(CalibrationTestCase):
    def test_uninitialized_state_if_stage_is_not_set(self):
        self.calibration.stage = None

        self.calibration.determine_state()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

    def test_uninitialized_state_if_stage_is_not_connected(self):
        self.stage.disconnect()

        self.calibration.determine_state()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

    @patch.object(DummyStage, "get_status", side_effect=StageError)
    def test_uninitialized_state_if_stage_raises_error(self, status_mock):
        self.stage.connect()
        self.assertTrue(self.stage.connected)

        self.calibration.determine_state()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        status_mock.assert_called_once()

    @patch.object(DummyStage, "get_status", return_value=None)
    def test_uninitialized_state_if_stage_does_not_respond(self, status_mock):
        self.stage.connect()
        self.assertTrue(self.stage.connected)

        self.calibration.determine_state()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        status_mock.assert_called_once()

    def test_connected_state_if_axes_rotation_is_invalid(self):
        self.calibration.connect_to_stage()
        self.assertTrue(self.stage.connected)

        self.set_invalid_axes_rotation()
        self.assertFalse(self.calibration._axes_rotation.is_valid)

        self.calibration.determine_state()
        self.assertEqual(self.calibration.state, State.CONNECTED)

    def test_coordinate_system_state_if_single_point_offset_is_invalid(self):
        self.calibration.connect_to_stage()
        self.assertTrue(self.stage.connected)

        self.set_valid_axes_rotation()
        self.assertTrue(self.calibration._axes_rotation.is_valid)
        self.assertFalse(self.calibration._single_point_offset.is_valid)

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

    def test_single_point_offset_state_if_kabsch_rotation_is_invalid(self):
        self.calibration.connect_to_stage()
        self.assertTrue(self.stage.connected)

        self.set_valid_axes_rotation()
        self.assertTrue(self.calibration._axes_rotation.is_valid)

        self.set_valid_single_point_offset()
        self.assertTrue(self.calibration._single_point_offset.is_valid)

        self.assertFalse(self.calibration._kabsch_rotation.is_valid)
        self.assertEqual(self.calibration.state, State.SINGLE_POINT_FIXED)

    def test_fully_calibrated(self):
        self.calibration.connect_to_stage()
        self.assertTrue(self.stage.connected)

        self.set_valid_axes_rotation()
        self.assertTrue(self.calibration._axes_rotation.is_valid)

        self.set_valid_single_point_offset()
        self.assertTrue(self.calibration._single_point_offset.is_valid)

        self.set_valid_kabsch_rotation()
        self.assertTrue(self.calibration._kabsch_rotation.is_valid)

        self.assertEqual(self.calibration.state, State.FULLY_CALIBRATED)


class CalibrationTest(CalibrationTestCase):

    def test_position_in_stage_coordinate_raises_error_if_unconnected(self):
        self.calibration.disconnect_to_stage()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        with self.calibration.perform_in_stage_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.get_position()

    def test_position_in_chip_coordinate_raises_error_if_not_single_point_fixed(
            self):
        self.calibration.connect_to_stage()
        self.set_valid_axes_rotation()
        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        with self.calibration.perform_in_chip_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.get_position()

    @patch.object(DummyStage, "get_position")
    def test_position_in_stage_coordinates(self, get_position_mock):
        expected_position = [100, 200, 300]
        get_position_mock.return_value = expected_position

        with self.calibration.perform_in_stage_coordinates():
            self.calibration.connect_to_stage()
            position = self.calibration.get_position()

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        self.assertIsInstance(position, StageCoordinate)
        self.assertEqual(position.to_list(), expected_position)

        get_position_mock.assert_called_once()

    @patch.object(DummyStage, "get_position")
    def test_position_in_chip_coordinates_with_single_point_offset(
            self, get_position_mock):
        expected_stage_pos, expected_chip_pos = (
            VACHERIN_STAGE_COORDS[1], VACHERIN_CHIP_COORDS[1])
        get_position_mock.return_value = expected_stage_pos

        with self.calibration.perform_in_chip_coordinates():
            self.calibration.connect_to_stage()
            self.set_valid_single_point_offset()
            position = self.calibration.get_position()

        self.assertEqual(self.calibration.state, State.SINGLE_POINT_FIXED)

        self.assertIsInstance(position, ChipCoordinate)
        self.assertTrue(
            np.allclose(
                position.to_numpy(),
                expected_chip_pos,
                rtol=1,
                atol=1))

        get_position_mock.assert_called_once()

    @patch.object(DummyStage, "get_position")
    def test_position_in_chip_coordinates_with_kabsch_rotation(
            self, get_position_mock):
        expected_stage_pos, expected_chip_pos = (
            VACHERIN_STAGE_COORDS[3], VACHERIN_CHIP_COORDS[3])
        get_position_mock.return_value = expected_stage_pos

        with self.calibration.perform_in_chip_coordinates():
            self.calibration.connect_to_stage()
            self.set_valid_single_point_offset()
            self.set_valid_kabsch_rotation()
            position = self.calibration.get_position()

        self.assertEqual(self.calibration.state, State.FULLY_CALIBRATED)

        self.assertIsInstance(position, ChipCoordinate)
        self.assertTrue(
            np.allclose(
                position.to_numpy(),
                expected_chip_pos,
                rtol=1,
                atol=1))

        get_position_mock.assert_called_once()

    def test_move_relative_in_stage_coordinate_raises_error_if_unconnected(
            self):
        self.calibration.disconnect_to_stage()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        with self.calibration.perform_in_stage_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.move_relative(StageCoordinate(1, 2, 3))

    def test_move_relative_in_chip_coordinate_raises_error_if_axes_rotation_invalid(
            self):
        self.calibration.connect_to_stage()
        self.set_invalid_axes_rotation()
        self.assertEqual(self.calibration.state, State.CONNECTED)

        with self.calibration.perform_in_chip_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.move_relative(StageCoordinate(1, 2, 3))

    def test_move_relative_in_stage_coordinate_raises_error_if_offset_type_invalid(
            self):
        self.calibration.connect_to_stage()
        with self.calibration.perform_in_stage_coordinates():
            with self.assertRaises(TypeError):
                self.calibration.move_relative(ChipCoordinate(1, 2, 3))

    def test_move_relative_in_chip_coordinate_raises_error_if_offset_type_invalid(
            self):
        self.calibration.connect_to_stage()
        with self.calibration.perform_in_chip_coordinates():
            with self.assertRaises(TypeError):
                self.calibration.move_relative(StageCoordinate(1, 2, 3))

    @parameterized.expand([(True,), (False,)])
    @patch.object(DummyStage, "move_relative")
    def test_move_relative_in_stage_coordinates(
            self, wait_for_stopping, move_relative_mock):
        self.set_invalid_axes_rotation()
        required_movement = [100.0, 200.0, 300.0]

        with self.calibration.perform_in_stage_coordinates():
            self.calibration.connect_to_stage()
            self.calibration.move_relative(
                StageCoordinate.from_list(required_movement),
                wait_for_stopping)

        self.assertEqual(self.calibration.state, State.CONNECTED)
        move_relative_mock.assert_called_once_with(
            x=required_movement[0],
            y=required_movement[1],
            z=required_movement[2],
            wait_for_stopping=wait_for_stopping)

    @parameterized.expand([(True,), (False,)])
    @patch.object(DummyStage, "move_relative")
    def test_move_relative_in_chip_coordinates_with_axes_rotation(
            self, wait_for_stopping, move_relative_mock):
        self.set_valid_axes_rotation()
        required_movement = [100.0, 200.0, 300.0]

        with self.calibration.perform_in_chip_coordinates():
            self.calibration.connect_to_stage()
            self.calibration.move_relative(
                ChipCoordinate.from_list(required_movement),
                wait_for_stopping)

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)
        move_relative_mock.assert_called_once_with(
            x=required_movement[1],
            y=-required_movement[2],
            z=-required_movement[0],
            wait_for_stopping=wait_for_stopping)
    #
    #
    #

    def test_move_absolute_in_stage_coordinate_raises_error_if_unconnected(
            self):
        self.calibration.disconnect_to_stage()
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        with self.calibration.perform_in_stage_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.move_absolute(StageCoordinate(1, 2, 3))

    def test_move_absolute_in_chip_coordinate_raises_error_if_not_single_point_fixed(
            self):
        self.calibration.connect_to_stage()
        self.set_valid_axes_rotation()
        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        with self.calibration.perform_in_chip_coordinates():
            with self.assertRaises(CalibrationError):
                self.calibration.move_absolute(ChipCoordinate(1, 2, 3))

    def test_move_absolute_in_stage_coordinate_raises_error_if_coord_type_invalid(
            self):
        self.calibration.connect_to_stage()
        with self.calibration.perform_in_stage_coordinates():
            with self.assertRaises(TypeError):
                self.calibration.move_absolute(ChipCoordinate(1, 2, 3))

    def test_move_absolute_in_chip_coordinate_raises_error_if_coord_type_invalid(
            self):
        self.calibration.connect_to_stage()
        self.set_valid_single_point_offset()
        with self.calibration.perform_in_chip_coordinates():
            with self.assertRaises(TypeError):
                self.calibration.move_absolute(StageCoordinate(1, 2, 3))

    @parameterized.expand([(True,), (False,)])
    @patch.object(DummyStage, "move_absolute")
    def test_move_absolute_in_stage_coordinates(
            self, wait_for_stopping, move_absolute_mock):
        self.set_invalid_axes_rotation()
        required_movement = [100.0, 200.0, 300.0]

        with self.calibration.perform_in_stage_coordinates():
            self.calibration.connect_to_stage()
            self.calibration.move_absolute(
                StageCoordinate.from_list(required_movement),
                wait_for_stopping)

        self.assertEqual(self.calibration.state, State.CONNECTED)
        move_absolute_mock.assert_called_once_with(
            x=required_movement[0],
            y=required_movement[1],
            z=required_movement[2],
            wait_for_stopping=wait_for_stopping)

    @patch.object(DummyStage, "move_absolute")
    def test_move_absolute_in_chip_coordinates_with_single_point_offset(
            self, move_absolute_mock):
        self.set_valid_single_point_offset()
        expected_stage_pos, expected_chip_pos = (
            VACHERIN_STAGE_COORDS[1], VACHERIN_CHIP_COORDS[1])

        with self.calibration.perform_in_chip_coordinates():
            self.calibration.connect_to_stage()
            self.calibration.move_absolute(
                ChipCoordinate.from_numpy(expected_chip_pos),
                True)

        self.assertEqual(self.calibration.state, State.SINGLE_POINT_FIXED)

        move_absolute_mock.assert_called_once()

        stage_call = move_absolute_mock.call_args_list[0]
        self.assertTrue(
            np.allclose(
                expected_stage_pos,
                np.array([stage_call.kwargs['x'], stage_call.kwargs['y'], stage_call.kwargs['z']]),
                rtol=1,
                atol=1))

    @patch.object(DummyStage, "move_absolute")
    def test_move_absolute_in_chip_coordinates_with_kabsch_rotation(
            self, move_absolute_mock):
        self.set_valid_single_point_offset()
        self.set_valid_kabsch_rotation()
        expected_stage_pos, expected_chip_pos = (
            VACHERIN_STAGE_COORDS[3], VACHERIN_CHIP_COORDS[3])

        with self.calibration.perform_in_chip_coordinates():
            self.calibration.connect_to_stage()
            self.calibration.move_absolute(
                ChipCoordinate.from_numpy(expected_chip_pos),
                True)

        self.assertEqual(self.calibration.state, State.FULLY_CALIBRATED)

        move_absolute_mock.assert_called_once()

        stage_call = move_absolute_mock.call_args_list[0]
        self.assertTrue(
            np.allclose(
                expected_stage_pos,
                np.array([stage_call.kwargs['x'], stage_call.kwargs['y'], stage_call.kwargs['z']]),
                rtol=1,
                atol=1))
