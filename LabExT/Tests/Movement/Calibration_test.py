#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from unittest.mock import Mock
from parameterized import parameterized

from LabExT.Movement.config import State, Orientation, DevicePort
from LabExT.Movement.Stage import Stage
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Transformations import ChipCoordinate, StageCoordinate
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


class CoordinateSystemControlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = Mock(spec=Stage)
        self.stage.connected = False

        self.mover = MoverNew(None)

        self.calibration = Calibration(
            self.mover, self.stage, Orientation.LEFT, DevicePort.INPUT)

        return super().setUp()

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
