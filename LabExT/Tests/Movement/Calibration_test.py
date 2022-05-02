#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""

import unittest
from unittest.mock import Mock
from parameterized import parameterized
from LabExT.Movement.Transformations import ChipCoordinate, CoordinatePairing, StageCoordinate, TransformationError

from LabExT.Movement.config import Direction, Orientation, DevicePort, State, Axis
from LabExT.Movement.Stage import Stage, StageError
from LabExT.Movement.Calibration import Calibration, assert_minimum_state_for_coordinate_system, CalibrationError

from LabExT.Tests.Utils import get_calibrations_from_file

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


class CalibrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = Mock(spec=Stage)
        self.stage.connected = False

        self.calibration = Calibration(
            self.stage, Orientation.LEFT, DevicePort.INPUT)

        return super().setUp()

    def test_set_chip_coordinate_system(self):
        with self.calibration.in_chip_coordinates():
            self.assertEqual(
                self.calibration.coordinate_system,
                ChipCoordinate)

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_stage_coordinate_system(self):
        with self.calibration.in_stage_coordinates():
            self.assertEqual(
                self.calibration.coordinate_system,
                StageCoordinate)

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_coordinate_system_twice(self):
        with self.assertRaises(CalibrationError):
            with self.calibration.in_chip_coordinates():
                self.calibration.coordinate_system = StageCoordinate

        with self.assertRaises(CalibrationError):
            with self.calibration.in_chip_coordinates():
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
            with self.calibration.in_chip_coordinates():
                self.assertEqual(
                    self.calibration.coordinate_system,
                    ChipCoordinate)
                func()

        self.assertIsNone(self.calibration.coordinate_system)

    def test_set_stage_coordinate_system_with_block_error(self):
        func = Mock(side_effect=RuntimeError)

        with self.assertRaises(RuntimeError):
            with self.calibration.in_stage_coordinates():
                self.assertEqual(
                    self.calibration.coordinate_system,
                    StageCoordinate)
                func()

        self.assertIsNone(self.calibration.coordinate_system)

    def test_connect_successfully(self):
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)
        self.calibration.connect_to_stage()
        self.assertGreaterEqual(self.calibration.state, State.CONNECTED)

    def test_connect_unsuccessully(self):
        self.stage.get_status = Mock(side_effect=StageError)
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

        self.calibration.connect_to_stage()

        self.assertEqual(self.calibration.state, State.UNINITIALIZED)

    @parameterized.expand([
        (INVALID_AXES_MAPPING, False, State.CONNECTED),
        (VALID_AXES_MAPPING, True, State.COORDINATE_SYSTEM_FIXED)
    ])
    def test_update_axes_rotation(self, assignment, expected_valid, expected_state):
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)
        self.calibration.connect_to_stage()

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        for chip_axis, direction, stage_axis in assignment:
            self.calibration.update_axes_rotation(chip_axis, direction, stage_axis)

        self.assertEqual(self.calibration._axes_rotation.is_valid, expected_valid)
        self.assertEqual(self.calibration.state, expected_state)

    def test_update_single_point_offset_with_invalid_rotation(self):
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)
        self.calibration.connect_to_stage()

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        for chip_axis, direction, stage_axis in INVALID_AXES_MAPPING:
            self.calibration.update_axes_rotation(chip_axis, direction, stage_axis)

        self.assertFalse(self.calibration._axes_rotation.is_valid)

        with self.assertRaises(TransformationError):
            self.calibration.update_single_point_offset(CoordinatePairing(
                calibration=self.calibration,
                stage_coordinate=StageCoordinate(1,2,3),
                device=Mock(),
                chip_coordinate=ChipCoordinate(4,5,6)))

        self.assertEqual(self.calibration.state, State.CONNECTED)

    def test_update_single_point_offset_with_valid_rotation(self):
        self.assertEqual(self.calibration.state, State.UNINITIALIZED)
        self.calibration.connect_to_stage()

        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)

        for chip_axis, direction, stage_axis in VALID_AXES_MAPPING:
            self.calibration.update_axes_rotation(chip_axis, direction, stage_axis)

        self.assertTrue(self.calibration._axes_rotation.is_valid)

        self.calibration.update_single_point_offset(CoordinatePairing(
            calibration=self.calibration,
            stage_coordinate=StageCoordinate(1,2,3),
            device=Mock(),
            chip_coordinate=ChipCoordinate(4,5,6)))

        self.assertEqual(self.calibration.state, State.SINGLE_POINT_FIXED)

    def test_update_kabsch_rotation(self):
        for stage_coord, chip_coord in zip(VACHERIN_STAGE_COORDS, VACHERIN_CHIP_COORDS):
           self.calibration.update_kabsch_rotation(CoordinatePairing(
                calibration=self.calibration,
                stage_coordinate=StageCoordinate.from_numpy(stage_coord),
                device=Mock(),
                chip_coordinate=ChipCoordinate.from_numpy(chip_coord)))

        self.assertTrue(self.calibration._kabsch_rotation.is_valid)
        
        self.assertEqual(self.calibration.state, State.COORDINATE_SYSTEM_FIXED)
        self.calibration.update_single_point_offset(CoordinatePairing(
            calibration=self.calibration,
            stage_coordinate=StageCoordinate(1,2,3),
            device=Mock(),
            chip_coordinate=ChipCoordinate(4,5,6)))

        self.assertEqual(self.calibration.state, State.FULLY_CALIBRATED)


    def test_position(self):
        pass