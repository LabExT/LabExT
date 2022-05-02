#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest.mock import Mock, patch
from LabExT.Movement.Calibration import Calibration, DevicePort, Orientation
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stage import Stage
from LabExT.Movement.Transformations import CoordinatePairing
from LabExT.Tests.Utils import TKinterTestCase, with_stage_discovery_patch
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow

from LabExT.Wafer.Device import Device


class Foo(TKinterTestCase):
    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []

        self.devices = {
            0: Device(0, [0, 0], [1, 1], "My Device 1")
        }

        self.experiment_manager = Mock()

        self.stage_1 = Mock(spec=Stage)
        self.stage_2 = Mock(spec=Stage)
        self.stage_1.connected = True
        self.stage_2.connected = True

        self.in_calibration = Calibration(
            self.stage_1,
            Orientation.LEFT,
            DevicePort.INPUT)
        self.out_calibration = Calibration(
            self.stage_2,
            Orientation.RIGHT,
            DevicePort.OUTPUT)

    def test_raises_error_if_no_calibration_is_given(self):
        with self.assertRaises(ValueError):
            CoordinatePairingsWindow(self.experiment_manager, self.root)

    def test_raises_error_if_no_chip_is_imported(self):
        self.experiment_manager.chip = None
        with self.assertRaises(ValueError):
            CoordinatePairingsWindow(self.experiment_manager, self.root)

    def test_pairings_returns_an_empty_list_for_no_device(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        self.assertEqual([], window.pairings)

    def test_pairings_returns_an_empty_list_if_no_stage_cooridnates(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        window._device_table.set_selected_device(0)
        window._select_device_button.invoke()

        self.assertEqual([], window.pairings)

    def test_reset_device_selection(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        window._device_table.set_selected_device(0)
        window._select_device_button.invoke()

        self.assertEqual(window._device, self.devices.get(0))

        window._clear_device_button.invoke()

        self.assertIsNone(window._device)

    def test_pairings_for_input_calibration(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager, self.root, self.in_calibration)

        window._device_table.set_selected_device(0)
        window._select_device_button.invoke()

        self.in_calibration.stage.get_current_position.return_value = [3, 9]

        window._finish_button.invoke()

        expected_pairings = CoordinatePairing(
            calibration=self.in_calibration,
            stage_coordinate=[3, 9],
            device=self.devices.get(0),
            chip_coordinate=[0, 0]
        )

        self.assertEqual(window.pairings, [expected_pairings])

    def test_pairings_for_output_calibration(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            out_calibration=self.out_calibration)

        window._device_table.set_selected_device(0)
        window._select_device_button.invoke()

        self.out_calibration.stage.get_current_position.return_value = [4, 8]

        window._finish_button.invoke()

        expected_pairings = CoordinatePairing(
            calibration=self.out_calibration,
            stage_coordinate=[4, 8],
            device=self.devices.get(0),
            chip_coordinate=[1, 1]
        )

        self.assertEqual(window.pairings, [expected_pairings])

    def test_pairings_for_input_and_output_calibration(self):
        self.experiment_manager.chip._devices = self.devices
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            in_calibration=self.in_calibration,
            out_calibration=self.out_calibration)

        window._device_table.set_selected_device(0)
        window._select_device_button.invoke()

        self.in_calibration.stage.get_current_position.return_value = [4, 8]
        self.out_calibration.stage.get_current_position.return_value = [3, 9]

        window._finish_button.invoke()

        expected_pairing_1 = CoordinatePairing(
            calibration=self.in_calibration,
            stage_coordinate=[4, 8],
            device=self.devices.get(0),
            chip_coordinate=[0, 0]
        )

        expected_pairing_2 = CoordinatePairing(
            calibration=self.out_calibration,
            stage_coordinate=[3, 9],
            device=self.devices.get(0),
            chip_coordinate=[1, 1]
        )

        self.assertEqual(
            window.pairings, [
                expected_pairing_1, expected_pairing_2])
