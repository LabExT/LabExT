#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest.mock import Mock
import pytest

from LabExT.Movement.config import DevicePort, Orientation

from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stage import Stage
from LabExT.Tests.Utils import TKinterTestCase
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow

from LabExT.Wafer.Device import Device
from LabExT.Wafer.Chip import Chip


class CoordinatePairingsWindowTest(TKinterTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.device = Device(id="101", type="My Device 1", in_position=[0, 0], out_position=[1, 1])
        self.chip = Chip(name="My Chip", devices=[self.device], path="/example/path", _serialize_to_disk=False)
        self.mover = MoverNew(None)

        self.stage_1 = Mock(spec=Stage)
        self.stage_2 = Mock(spec=Stage)
        self.stage_1.connected = True
        self.stage_2.connected = True

        self.stage_1_position = [23744.60, -9172.55, 18956.10]
        self.stage_2_position = [23236.35, -7888.67, 18956.06]
        self.stage_1.get_position.return_value = self.stage_1_position
        self.stage_2.get_position.return_value = self.stage_2_position

        self.on_finish = Mock()

    def setup_calibrations(self):
        self.in_calibration = self.mover.add_stage_calibration(self.stage_1, Orientation.LEFT, DevicePort.INPUT)
        self.out_calibration = self.mover.add_stage_calibration(self.stage_2, Orientation.RIGHT, DevicePort.OUTPUT)

    def setup_window(self, with_input_stage=True, with_output_stage=True):
        return CoordinatePairingsWindow(
            self.root,
            self.mover,
            self.chip,
            self.on_finish,
            with_input_stage=with_input_stage,
            with_output_stage=with_output_stage,
        )

    @pytest.mark.flaky(reruns=3)
    def test_raises_error_if_no_chip_is_imported(self):
        with self.assertRaises(ValueError):
            CoordinatePairingsWindow(self.root, self.mover, None, self.on_finish)

    @pytest.mark.flaky(reruns=3)
    def test_raises_error_if_input_is_requested_but_not_defined(self):
        with self.assertRaises(ValueError):
            CoordinatePairingsWindow(self.root, self.mover, self.chip, self.on_finish, with_input_stage=True)

    @pytest.mark.flaky(reruns=3)
    def test_raises_error_if_output_is_requested_but_not_defined(self):
        with self.assertRaises(ValueError):
            CoordinatePairingsWindow(self.root, self.mover, self.chip, self.on_finish, with_output_stage=True)

    @pytest.mark.flaky(reruns=3)
    def test_no_callback_for_no_device_selection(self):
        self.setup_calibrations()
        window = self.setup_window()

        window._finish_button.invoke()

        self.on_finish.assert_not_called()

    @pytest.mark.flaky(reruns=3)
    def test_device_selection(self):
        self.setup_calibrations()
        window = self.setup_window()

        window._device_table.set_selected_device(101)
        window._select_device_button.invoke()

        self.assertEqual(window._device, self.device)

    @pytest.mark.flaky(reruns=3)
    def test_device_reset(self):
        self.setup_calibrations()
        window = self.setup_window()

        window._device_table.set_selected_device(101)
        window._select_device_button.invoke()
        self.assertEqual(window._device, self.device)

        window._clear_device_button.invoke()
        self.assertIsNone(window._device)

    @pytest.mark.flaky(reruns=3)
    def test_pairings_for_input_stage(self):
        self.setup_calibrations()
        window = self.setup_window(with_input_stage=True, with_output_stage=False)

        window._device_table.set_selected_device(101)
        window._select_device_button.invoke()
        window._finish_button.invoke()

        self.on_finish.assert_called_once()

        args, _ = self.on_finish.call_args
        pairings = args[0]

        self.assertEqual(1, len(pairings))
        self.assertEqual(self.in_calibration, pairings[0].calibration)
        self.assertEqual(self.device, pairings[0].device)
        self.assertEqual(self.stage_1_position, pairings[0].stage_coordinate.to_list())
        self.assertEqual([0, 0, 0], pairings[0].chip_coordinate.to_list())

    @pytest.mark.flaky(reruns=3)
    def test_pairings_for_output_stage(self):
        self.setup_calibrations()
        window = self.setup_window(with_input_stage=False, with_output_stage=True)

        window._device_table.set_selected_device(101)
        window._select_device_button.invoke()
        window._finish_button.invoke()

        self.on_finish.assert_called_once()

        args, _ = self.on_finish.call_args
        pairings = args[0]

        self.assertEqual(1, len(pairings))
        self.assertEqual(self.out_calibration, pairings[0].calibration)
        self.assertEqual(self.device, pairings[0].device)
        self.assertEqual(self.stage_2_position, pairings[0].stage_coordinate.to_list())
        self.assertEqual([1, 1, 0], pairings[0].chip_coordinate.to_list())

    @pytest.mark.flaky(reruns=3)
    def test_pairings_for_input_and_output_stage(self):
        self.setup_calibrations()
        window = self.setup_window(with_input_stage=True, with_output_stage=True)

        window._device_table.set_selected_device(101)
        window._select_device_button.invoke()
        window._finish_button.invoke()

        self.on_finish.assert_called_once()

        args, _ = self.on_finish.call_args
        pairings = args[0]

        self.assertEqual(2, len(pairings))

        input_pairing = pairings[0]
        self.assertEqual(self.in_calibration, input_pairing.calibration)
        self.assertEqual(self.device, input_pairing.device)
        self.assertEqual(self.stage_1_position, input_pairing.stage_coordinate.to_list())
        self.assertEqual([0, 0, 0], input_pairing.chip_coordinate.to_list())

        output_pairing = pairings[1]
        self.assertEqual(self.out_calibration, output_pairing.calibration)
        self.assertEqual(self.device, output_pairing.device)
        self.assertEqual(self.stage_2_position, output_pairing.stage_coordinate.to_list())
        self.assertEqual([1, 1, 0], output_pairing.chip_coordinate.to_list())
