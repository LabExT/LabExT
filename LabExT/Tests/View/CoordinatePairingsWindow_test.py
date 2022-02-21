#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import pytest
from os.path import join
from unittest.mock import Mock, patch

from LabExT.Wafer.Chip import Chip
from LabExT.Movement.Calibration import Calibration, DevicePort, Orientation
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stage import Stage
from LabExT.Movement.Transformations import CoordinatePairing
from LabExT.Tests.Utils import TKinterTestCase, with_stage_discovery_patch
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow


class CoordinatePairingsWindowTest(TKinterTestCase):
    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []

        self.chip = Chip(join(pytest.fixture_folder, "QuarkJaejaChip.csv"))
        self.experiment_manager = Mock()
        self.experiment_manager.chip = self.chip

        self.mover = MoverNew(self.experiment_manager)

        self.stage_1 = Mock(spec=Stage)
        self.stage_2 = Mock(spec=Stage)
        self.stage_1.connected = True
        self.stage_2.connected = True

        self.in_calibration = Calibration(
            self.mover,
            self.stage_1,
            Orientation.LEFT,
            DevicePort.INPUT)
        self.out_calibration = Calibration(
            self.mover,
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
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        self.assertEqual([], window.pairings)

    def test_pairings_returns_an_empty_list_if_no_stage_cooridnates(self):
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        window._device_table.set_selected_device(1000)
        window._select_device_button.invoke()

        self.assertEqual([], window.pairings)

    def test_reset_device_selection(self):
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            self.in_calibration,
            self.out_calibration)

        window._device_table.set_selected_device(1000)
        window._select_device_button.invoke()

        self.assertEqual(window._device, self.chip._devices.get(1000))

        window._clear_device_button.invoke()

        self.assertIsNone(window._device)

    def test_pairings_for_input_calibration(self):
        window = CoordinatePairingsWindow(
            self.experiment_manager, self.root, self.in_calibration)

        window._device_table.set_selected_device(1000)
        window._select_device_button.invoke()

        self.in_calibration.stage.position = [100, 200, 300]

        window._finish_button.invoke()

        expected_pairings = CoordinatePairing(
            calibration=self.in_calibration,
            stage_coordinate=[100, 200, 300],
            device=self.chip._devices.get(1000),
            chip_coordinate=self.chip._devices.get(1000)._in_position
        )

        self.assertEqual(window.pairings, [expected_pairings])

    def test_pairings_for_output_calibration(self):
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            out_calibration=self.out_calibration)

        window._device_table.set_selected_device(1100)
        window._select_device_button.invoke()

        self.out_calibration.stage.position = [10, 20, 30]

        window._finish_button.invoke()

        expected_pairings = CoordinatePairing(
            calibration=self.out_calibration,
            stage_coordinate=[10, 20, 30],
            device=self.chip._devices.get(1100),
            chip_coordinate=self.chip._devices.get(1100)._out_position
        )

        self.assertEqual(window.pairings, [expected_pairings])

    def test_pairings_for_input_and_output_calibration(self):
        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            in_calibration=self.in_calibration,
            out_calibration=self.out_calibration)

        window._device_table.set_selected_device(1111)
        window._select_device_button.invoke()

        self.in_calibration.stage.position = [1, 2, 3]
        self.out_calibration.stage.position = [4, 5, 6]

        window._finish_button.invoke()

        expected_pairing_1 = CoordinatePairing(
            calibration=self.in_calibration,
            stage_coordinate=[1, 2, 3],
            device=self.chip._devices.get(1111),
            chip_coordinate=self.chip._devices.get(1111)._in_position,
        )

        expected_pairing_2 = CoordinatePairing(
            calibration=self.out_calibration,
            stage_coordinate=[4, 5, 6],
            device=self.chip._devices.get(1111),
            chip_coordinate=self.chip._devices.get(1111)._out_position
        )

        self.assertEqual(
            window.pairings, [
                expected_pairing_1, expected_pairing_2])

    def test_on_finish_callback(self):
        on_finish = Mock()

        window = CoordinatePairingsWindow(
            self.experiment_manager,
            self.root,
            in_calibration=self.in_calibration,
            out_calibration=self.out_calibration,
            on_finish=on_finish)

        window._device_table.set_selected_device(1212)
        window._select_device_button.invoke()

        self.in_calibration.stage.position = [1, 2, 3]
        self.out_calibration.stage.position = [4, 5, 6]

        window._finish_button.invoke()

        on_finish.assert_called_once_with([
            CoordinatePairing(
                calibration=self.in_calibration,
                stage_coordinate=[1, 2, 3],
                device=self.chip._devices.get(1212),
                chip_coordinate=self.chip._devices.get(1212)._in_position,
            ),
            CoordinatePairing(
                calibration=self.out_calibration,
                stage_coordinate=[4, 5, 6],
                device=self.chip._devices.get(1212),
                chip_coordinate=self.chip._devices.get(1212)._out_position
            )
        ])
