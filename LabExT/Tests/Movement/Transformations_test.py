#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from LabExT.Wafer.Device import Device
import numpy as np

from LabExT.Movement.Transformations import CoordinatePairing, KabschRotation, SinglePointFixation


class SinglePointFixationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixation = SinglePointFixation()

    def test_is_valid_for_no_offset(self):
        self.assertFalse(self.fixation.is_valid)

    def test_update_missing_chip_coordinate(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=[1, 2],
            device=None,
            chip_coordinate=None
        )

        with self.assertRaises(ValueError):
            self.fixation.update(pairing)

        self.assertFalse(self.fixation.is_valid)

    def test_update_missing_stage_coordinate(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=None,
            device=None,
            chip_coordinate=[1, 2]
        )

        with self.assertRaises(ValueError):
            self.fixation.update(pairing)

        self.assertFalse(self.fixation.is_valid)

    def test_update(self):
        pairing = CoordinatePairing(
            calibration=None,
            stage_coordinate=[2, 4],
            device=None,
            chip_coordinate=[1, 5]
        )

        self.fixation.update(pairing)

        self.assertTrue(self.fixation.is_valid)

    def test_chip_to_stage_when_invalid(self):
        with self.assertRaises(RuntimeError):
            self.fixation.chip_to_stage([1, 2])

    def test_stage_to_chip_when_invalid(self):
        with self.assertRaises(RuntimeError):
            self.fixation.stage_to_chip([1, 2])

    def test_chip_to_stage_translates_chip_coordinate(self):
        stage_coordinate = [2, 4]
        chip_coordinate = [1, 5]
        expected_offset = np.array(stage_coordinate) - \
            np.array(chip_coordinate)

        self.fixation.update(CoordinatePairing(
            None, stage_coordinate, None, chip_coordinate
        ))

        self.assertTrue(
            (self.fixation.chip_to_stage([5, 6]) ==
             np.array([5, 6]) + expected_offset).all()
        )

    def test_stage_to_chip_translates_chip_coordinate(self):
        stage_coordinate = [2, 4]
        chip_coordinate = [1, 5]
        expected_offset = np.array(stage_coordinate) - \
            np.array(chip_coordinate)

        self.fixation.update(CoordinatePairing(
            None, stage_coordinate, None, chip_coordinate
        ))

        self.assertTrue(
            (self.fixation.stage_to_chip([5, 6]) ==
             np.array([5, 6]) - expected_offset).all()
        )

    def test_chip_to_stage_and_stage_to_chip_are_inversed(self):
        self.fixation.update(CoordinatePairing(
            None, [7, 1], None, [4, 2]
        ))

        chip_input_coordinate = [2, 3]
        self.assertTrue((chip_input_coordinate == self.fixation.stage_to_chip(
            self.fixation.chip_to_stage(chip_input_coordinate))).all())

        stage_input_coordinate = [2, 3]
        self.assertTrue((stage_input_coordinate == self.fixation.chip_to_stage(
            self.fixation.stage_to_chip(stage_input_coordinate))).all())

class KabschRotationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transformation = KabschRotation()

    def test_update_raises_value_error_if_no_pairing(self):
        with self.assertRaises(ValueError):
            self.transformation.update([1,2,3])

    def test_update_raises_value_error_if_stage_coordinate_missing(self):
        with self.assertRaises(ValueError):
            self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=None,
                device=object(),
                chip_coordinate=[1,2,3]
            ))

    def test_update_raises_value_error_if_chip_coordinate_missing(self):
        with self.assertRaises(ValueError):
            self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=[1,2,3],
                device=object(),
                chip_coordinate=None 
            ))

    def test_update_raises_value_error_if_device_missing(self):
        with self.assertRaises(ValueError):
            self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=[1,2,3],
                device=None,
                chip_coordinate=[1,2,3]
            ))

    def test_update_raises_value_error_if_device_duplicate(self):
        device = Device(0, [0, 0], [1, 1], "My Device 1")

        self.transformation.update(CoordinatePairing(
            calibration=None,
            stage_coordinate=[1,2,3],
            device=device,
            chip_coordinate=[0,0]
        ))

        with self.assertRaises(ValueError) as error:
             self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=[2,3,4],
                device=device,
                chip_coordinate=[1,1]
            ))
        
        self.assertEqual(str(error.exception), "A pairing with this device has already been saved.")

    def test_update_raises_value_error_if_coordinate_wrong_dimension(self):
        with self.assertRaises(ValueError):
            self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=[2],
                device=object(),
                chip_coordinate=[1]
            ))

        with self.assertRaises(ValueError):
            self.transformation.update(CoordinatePairing(
                calibration=None,
                stage_coordinate=[2,2,3,4],
                device=object(),
                chip_coordinate=[1,3,4,5]
            ))
