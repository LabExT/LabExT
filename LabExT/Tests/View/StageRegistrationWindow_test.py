#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest.mock import Mock, patch
from flaky import flaky
from LabExT.Measurements.MeasAPI.Measparam import MeasParamAuto
from LabExT.Movement.PathPlanning import SingleModeFiber

from LabExT.Movement.config import DevicePort, Orientation

from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Stages.DummyStage import DummyStage
from LabExT.Tests.Utils import TKinterTestCase

from LabExT.Movement.Calibration import Calibration
from LabExT.View.Movement.StageRegistrationWindow import StageRegistrationWindow


@flaky(max_runs=3)
class StageRegistrationWindowTest(TKinterTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.available_stages = [
            (DummyStage, 'usb:123456789'),
            (DummyStage, 'usb:987654321')
        ]

        self.mover = MoverNew(None)
        self.mover.polygon_api.import_classes()

        self.on_finish = Mock()

    def setup_window(self):
        return StageRegistrationWindow(
            self.root,
            self.mover,
            on_finish=self.on_finish)

    def assert_called_with_new_calibration(
        self,
        stage_cls,
        stage_address,
        port,
        stage_polygon,
        stage_parameters
    ) -> None:
        self.on_finish.assert_called_once()

        args, _ = self.on_finish.call_args
        calibration = args[0]

        self.assertIsInstance(calibration, Calibration)

        self.assertIsInstance(calibration.stage, stage_cls)
        self.assertEqual(calibration.stage.address, stage_address)

        self.assertEqual(calibration.device_port, port)

        if stage_polygon:
            self.assertIsInstance(calibration.stage_polygon, stage_polygon)
            self.assertEqual(
                calibration.stage_polygon.parameters,
                stage_parameters)
        else:
            self.assertIsNone(calibration.stage_polygon)

    @patch.object(MoverNew, "get_available_stages")
    def test_if_no_stages_available(self, available_stages):
        available_stages.return_value = []
        window = self.setup_window()

        self.assertEqual(
            window._select_stage_button["state"],
            "disabled")

    @patch.object(MoverNew, "get_available_stages")
    def test_select_stage(self, available_stages):
        available_stages.return_value = [
            (DummyStage, 'usb:123456789'), (DummyStage, 'usb:987654321')]
        window = self.setup_window()

        window._stage_table.set_selected_stage(0)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:123456789')

        window._clear_stage_button.invoke()
        self.assertIsNone(window._stage)

        window._stage_table.set_selected_stage(1)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:987654321')

    @patch.object(MoverNew, "get_available_stages")
    def test_select_stage_without_automatic_movement(self, available_stages):
        available_stages.return_value = [
            (DummyStage, 'usb:123456789'), (DummyStage, 'usb:987654321')]
        window = self.setup_window()

        window._stage_table.set_selected_stage(0)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:123456789')

        window._stage_port_var.set(window.NO_PORT_OPTION)

        self.assertEqual(window._finish_button["state"], "normal")

        window._finish_button.invoke()

        self.assert_called_with_new_calibration(
            DummyStage, 'usb:123456789', None, None, None)

    @patch.object(MoverNew, "get_available_stages")
    def test_select_stage_with_input_port(self, available_stages):
        available_stages.return_value = [
            (DummyStage, 'usb:123456789'), (DummyStage, 'usb:987654321')]
        window = self.setup_window()

        window._stage_table.set_selected_stage(1)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:987654321')

        window._stage_port_var.set(
            window.PORT_OPTION_TEMPLATE.format(
                port=DevicePort.INPUT))
        self.assertEqual(window._finish_button["state"], "normal")
        self.assertEqual(window._port, DevicePort.INPUT)
        self.assertEqual(window._stage_polygon_cls, window.DEFAULT_POLYGON)
        self.assertEqual(
            window._stage_polygon_parameters,
            window.DEFAULT_POLYGON.default_parameters)

        window._finish_button.invoke()

        self.assert_called_with_new_calibration(
            DummyStage,
            'usb:987654321',
            DevicePort.INPUT,
            window.DEFAULT_POLYGON,
            window.DEFAULT_POLYGON.default_parameters)

    @patch.object(MoverNew, "get_available_stages")
    def test_select_stage_with_output_port(self, available_stages):
        available_stages.return_value = [
            (DummyStage, 'usb:123456789'), (DummyStage, 'usb:987654321')]
        window = self.setup_window()

        window._stage_table.set_selected_stage(0)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:123456789')

        window._stage_port_var.set(
            window.PORT_OPTION_TEMPLATE.format(
                port=DevicePort.OUTPUT))
        self.assertEqual(window._finish_button["state"], "normal")
        self.assertEqual(window._port, DevicePort.OUTPUT)
        self.assertEqual(window._stage_polygon_cls, window.DEFAULT_POLYGON)
        self.assertEqual(
            window._stage_polygon_parameters,
            window.DEFAULT_POLYGON.default_parameters)

        window._finish_button.invoke()

        self.assert_called_with_new_calibration(
            DummyStage,
            'usb:123456789',
            DevicePort.OUTPUT,
            window.DEFAULT_POLYGON,
            window.DEFAULT_POLYGON.default_parameters)

    @patch.object(MoverNew, "get_available_stages")
    def test_select_stage_with_single_mode_fiber(self, available_stages):
        available_stages.return_value = [
            (DummyStage, 'usb:123456789'), (DummyStage, 'usb:987654321')]
        window = self.setup_window()

        window._stage_table.set_selected_stage(0)
        window._select_stage_button.invoke()
        self.assertIsInstance(window._stage, DummyStage)
        self.assertEqual(window._stage.address, 'usb:123456789')

        window._stage_port_var.set(
            window.PORT_OPTION_TEMPLATE.format(
                port=DevicePort.INPUT))
        self.assertEqual(window._finish_button["state"], "normal")
        self.assertEqual(window._port, DevicePort.INPUT)

        window._stage_polygon_var.set("SingleModeFiber")
        self.assertEqual(window._stage_polygon_cls, SingleModeFiber)
        self.assertEqual(
            window._stage_polygon_parameters,
            SingleModeFiber.default_parameters)

        window._polygon_cfg_table.parameter_source = {
            "Orientation": MeasParamAuto(Orientation.RIGHT),
            "Fiber Length": MeasParamAuto(10000),
            "Fiber Radius": MeasParamAuto(200),
            "Safety Distance": MeasParamAuto(100)
        }

        window._finish_button.invoke()

        self.assert_called_with_new_calibration(
            DummyStage,
            'usb:123456789',
            DevicePort.INPUT,
            SingleModeFiber,
            {
                "Orientation": Orientation.RIGHT,
                "Fiber Length": 10000,
                "Fiber Radius": 200,
                "Safety Distance": 100})
