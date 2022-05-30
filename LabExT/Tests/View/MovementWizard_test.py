#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from flaky import flaky

from tkinter import DISABLED, NORMAL
from unittest.mock import Mock, patch
from LabExT.Tests.Utils import TKinterTestCase, with_stage_discovery_patch
from LabExT.Movement.Calibration import DevicePort, Orientation
from LabExT.Movement.MoverNew import MoverError, MoverNew
from LabExT.Movement.Stages.DummyStage import DummyStage

from LabExT.View.MovementWizard.MovementWizardController import MovementWizardController, Stage

@flaky(max_runs=3)
class MovementWizardAssignmentStepTest(TKinterTestCase):
    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        self.experiment_manager = Mock()

        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:987654321')

        stage_classes_mock.return_value = [DummyStage]
        available_stages_mock.return_value = [self.stage, self.stage2]

        self.mover = MoverNew(self.experiment_manager)
        self.controller = MovementWizardController(
            self.experiment_manager, self.mover, self.root)
        self.view = self.controller.view

        # Start Wizard at assignment step
        self.view.current_step = self.view.assign_stages_step

    def test_orientation_selection(self):
        self.view.stage_orientation_var[self.stage].set(Orientation.TOP)
        self.assertEqual(
            self.view._current_stage_assignment[self.stage][0], Orientation.TOP)

        self.view.stage_orientation_var[self.stage].set(Orientation.BOTTOM)
        self.assertEqual(
            self.view._current_stage_assignment[self.stage][0], Orientation.BOTTOM)

        self.view.stage_orientation_var[self.stage2].set(Orientation.LEFT)
        self.assertEqual(
            self.view._current_stage_assignment[self.stage2][0], Orientation.LEFT)

        self.view.stage_orientation_var[self.stage2].set(Orientation.RIGHT)
        self.assertEqual(
            self.view._current_stage_assignment[self.stage2][0], Orientation.RIGHT)

    def test_assignment_reset(self):
        self.assertIsNone(self.view._current_stage_assignment.get(self.stage))

        self.view.stage_orientation_var[self.stage].set(Orientation.TOP)
        self.assertIsNotNone(
            self.view._current_stage_assignment.get(
                self.stage))

        self.view.stage_orientation_var[self.stage].set("-- unused --")
        self.assertIsNone(self.view._current_stage_assignment.get(self.stage))

    def test_port_selection_without_orientation_selection_before(self):
        self.assertIsNone(self.view._current_stage_assignment.get(self.stage))

        self.view.stage_port_var[self.stage].set(DevicePort.INPUT)
        self.assertIsNone(self.view._current_stage_assignment.get(self.stage))

    def test_port_selection_with_orientation_selection(self):
        self.assertIsNone(self.view._current_stage_assignment.get(self.stage))

        self.view.stage_orientation_var[self.stage].set(Orientation.BOTTOM)
        self.view.stage_port_var[self.stage].set(DevicePort.OUTPUT)
        self.assertEqual(self.view._current_stage_assignment.get(
            self.stage), (Orientation.BOTTOM, DevicePort.OUTPUT))

        self.view.stage_orientation_var[self.stage].set(Orientation.TOP)
        self.view.stage_port_var[self.stage].set(DevicePort.INPUT)
        self.assertEqual(self.view._current_stage_assignment.get(
            self.stage), (Orientation.TOP, DevicePort.INPUT))

    def test_assignment_valid(self):
        self.view.stage_orientation_var[self.stage].set(Orientation.BOTTOM)
        self.view.stage_port_var[self.stage].set(DevicePort.OUTPUT)

        self.view.stage_orientation_var[self.stage2].set(Orientation.TOP)
        self.view.stage_port_var[self.stage2].set(DevicePort.INPUT)

        self.assertEqual(self.view._error_label["text"], "")
        self.assertEqual(self.view._next_button["state"], NORMAL)

    def test_empty_assignment(self):
        self.assertEqual(
            self.view._error_label["text"],
            "Please assign at least one to proceed.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

        self.view.stage_orientation_var[self.stage].set("-- unused --")
        self.view.stage_orientation_var[self.stage2].set("-- unused --")
        self.assertEqual(
            self.view._error_label["text"],
            "Please assign at least one to proceed.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

    def test_invalid_assignment_with_double_orientation(self):
        self.view.stage_orientation_var[self.stage].set(Orientation.BOTTOM)
        self.view.stage_orientation_var[self.stage2].set(Orientation.BOTTOM)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

        self.view.stage_orientation_var[self.stage].set(Orientation.TOP)
        self.view.stage_orientation_var[self.stage2].set(Orientation.TOP)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

        self.view.stage_orientation_var[self.stage].set(Orientation.LEFT)
        self.view.stage_orientation_var[self.stage2].set(Orientation.LEFT)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

        self.view.stage_orientation_var[self.stage].set(Orientation.RIGHT)
        self.view.stage_orientation_var[self.stage2].set(Orientation.RIGHT)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

    def test_invalid_assignment_with_double_port(self):
        self.view.stage_orientation_var[self.stage].set(Orientation.BOTTOM)
        self.view.stage_orientation_var[self.stage2].set(Orientation.TOP)

        self.view.stage_port_var[self.stage].set(DevicePort.INPUT)
        self.view.stage_port_var[self.stage2].set(DevicePort.INPUT)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)

        self.view.stage_port_var[self.stage].set(DevicePort.OUTPUT)
        self.view.stage_port_var[self.stage2].set(DevicePort.OUTPUT)
        self.assertEqual(
            self.view._error_label["text"],
            "Please do not assign a orientation or device port twice.")
        self.assertEqual(self.view._next_button["state"], DISABLED)


@flaky(max_runs=3)
class MovementWizardControllerTest(unittest.TestCase):
    @with_stage_discovery_patch
    def setUp(self, available_stages_mock, stage_classes_mock) -> None:
        super().setUp()
        self.experiment_manager = Mock()

        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []
       
        self.mover = MoverNew(self.experiment_manager)
        self.controller = MovementWizardController(
            self.experiment_manager, self.mover)

        self.stage = DummyStage('usb:123456789')
        self.stage2 = DummyStage('usb:987654321')

    def test_save_empty_assigment(self):
        self.controller.save({})

        self.assertEqual({}, self.mover.calibrations)
        self.assertEqual([], self.mover.connected_stages)
        self.assertFalse(self.mover.has_connected_stages)

    def test_save_one_stage(self):
        self.controller.save(
            {self.stage: (Orientation.LEFT, DevicePort.INPUT)})

        self.assertIsNotNone(self.mover.left_calibration)
        self.assertEqual(self.mover.left_calibration.stage, self.stage)

        self.assertIsNotNone(self.mover.input_calibration)
        self.assertEqual(self.mover.input_calibration.stage, self.stage)

        self.assertIn(self.stage, self.mover.connected_stages)
        self.assertTrue(self.mover.has_connected_stages)

    def test_save_double_port(self):
        with self.assertRaises(MoverError):
            self.controller.save({
                self.stage: (Orientation.LEFT, DevicePort.INPUT),
                self.stage2: (Orientation.RIGHT, DevicePort.INPUT),
            })

        self.assertFalse(self.mover.has_connected_stages)
        self.assertEqual({}, self.mover.calibrations)

    def test_save_double_orientation(self):
        with self.assertRaises(MoverError):
            self.controller.save({
                self.stage: (Orientation.LEFT, DevicePort.INPUT),
                self.stage2: (Orientation.LEFT, DevicePort.OUTPUT),
            })

        self.assertFalse(self.mover.has_connected_stages)
        self.assertEqual({}, self.mover.calibrations)

    def test_save_sets_stage_settings(self):
        self.controller.save(
            stage_assignment={
                self.stage: (Orientation.LEFT, DevicePort.INPUT),
                self.stage2: (Orientation.RIGHT, DevicePort.OUTPUT)
            },
            speed_xy=300,
            speed_z=400,
            acceleration_xy=100
        )

        self.assertTrue(self.mover.has_connected_stages)
        self.assertEqual(2, len(self.mover.calibrations))

        self.assertEqual(300, self.mover.left_calibration.stage.get_speed_xy())
        self.assertEqual(
            300, self.mover.right_calibration.stage.get_speed_xy())
        self.assertEqual(
            300, self.mover.input_calibration.stage.get_speed_xy())
        self.assertEqual(
            300, self.mover.output_calibration.stage.get_speed_xy())
        self.assertEqual(300, self.mover.speed_xy)

        self.assertEqual(400, self.mover.left_calibration.stage.get_speed_z())
        self.assertEqual(400, self.mover.right_calibration.stage.get_speed_z())
        self.assertEqual(400, self.mover.input_calibration.stage.get_speed_z())
        self.assertEqual(
            400, self.mover.output_calibration.stage.get_speed_z())
        self.assertEqual(400, self.mover.speed_z)

        self.assertEqual(
            100, self.mover.left_calibration.stage.get_acceleration_xy())
        self.assertEqual(
            100, self.mover.right_calibration.stage.get_acceleration_xy())
        self.assertEqual(
            100, self.mover.input_calibration.stage.get_acceleration_xy())
        self.assertEqual(
            100, self.mover.output_calibration.stage.get_acceleration_xy())
        self.assertEqual(100, self.mover.acceleration_xy)


@flaky(max_runs=3)
class MovementWizardIntegrationTest(TKinterTestCase):
    def setUp(self):
        super().setUp()
        self.experiment_manager = Mock()

    @with_stage_discovery_patch
    def test_with_empty_stages(
            self,
            available_stages_mock,
            stage_classes_mock):
        available_stages_mock.return_value = []
        stage_classes_mock.return_value = []

        self.mover = MoverNew(self.experiment_manager)
        self.controller = MovementWizardController(
            self.experiment_manager, self.mover, self.root)
        wizard = self.controller.view

        self.assertEqual(wizard._finish_button["state"], DISABLED)
        self.assertEqual(wizard._next_button["state"], NORMAL)
        self.assertEqual(wizard._previous_button["state"], DISABLED)

        # Proceed to next step
        wizard._next_button.invoke()

        self.assertEqual(wizard._finish_button["state"], DISABLED)
        self.assertEqual(wizard._next_button["state"], DISABLED)
        self.assertEqual(wizard._previous_button["state"], NORMAL)
        self.assertEqual(
            wizard._error_label["text"],
            "Please assign at least one to proceed.")

    @with_stage_discovery_patch
    def test_setup_of_two_stages(
            self,
            available_stages_mock,
            stage_classes_mock):
        """
        This test tests a complete walk through the wizard
        """
        stage = DummyStage('usb:123456789')
        stage2 = DummyStage('usb:987654321')

        available_stages_mock.return_value = [stage, stage2]
        stage_classes_mock.return_value = [DummyStage]

        self.mover = MoverNew(self.experiment_manager)
        self.controller = MovementWizardController(
            self.experiment_manager, self.mover, self.root)
        wizard = self.controller.view

        self.assertEqual(wizard._finish_button["state"], DISABLED)
        self.assertEqual(wizard._next_button["state"], NORMAL)
        self.assertEqual(wizard._previous_button["state"], DISABLED)

        # Proceed to next step
        wizard._next_button.invoke()

        self.assertEqual(wizard._finish_button["state"], DISABLED)
        self.assertEqual(wizard._next_button["state"], DISABLED)
        self.assertEqual(wizard._previous_button["state"], NORMAL)
        self.assertEqual(
            wizard._error_label["text"],
            "Please assign at least one to proceed.")

        # Assign stages invalid
        wizard.stage_orientation_var[stage].set(Orientation.BOTTOM)
        wizard.stage_port_var[stage].set(DevicePort.OUTPUT)

        wizard.stage_orientation_var[stage2].set(Orientation.TOP)
        wizard.stage_port_var[stage2].set(DevicePort.OUTPUT)

        self.assertEqual(wizard._next_button["state"], DISABLED)
        self.assertEqual(
            wizard._error_label["text"],
            "Please do not assign a orientation or device port twice.")

        # Assign stages valid
        wizard.stage_orientation_var[stage].set(Orientation.LEFT)
        wizard.stage_port_var[stage].set(DevicePort.OUTPUT)

        wizard.stage_orientation_var[stage2].set(Orientation.RIGHT)
        wizard.stage_port_var[stage2].set(DevicePort.INPUT)

        self.assertEqual(wizard._next_button["state"], NORMAL)
        self.assertEqual(wizard._error_label["text"], "")

        # Proceed to next step
        wizard._next_button.invoke()

        self.assertEqual(wizard._finish_button["state"], NORMAL)
        self.assertEqual(wizard._next_button["state"], DISABLED)
        self.assertEqual(wizard._previous_button["state"], NORMAL)

        # Set speed for xy to zero
        wizard.xy_speed_var.set(0)

        # Wizard warns for zero speed, when try to finish
        with patch("LabExT.View.MovementWizard.MovementWizardView.messagebox.askokcancel", autospec=True) as messagebox_mock:
            messagebox_mock.return_value = False

            wizard._finish_button.invoke()

            messagebox_mock.assert_called_once()
            self.assertFalse(self.mover.has_connected_stages)

        # Set settings
        wizard.xy_speed_var.set(400)
        wizard.z_speed_var.set(200)
        wizard.xy_acceleration_var.set(100)

        with patch("LabExT.View.MovementWizard.MovementWizardView.messagebox.showinfo", autospec=True) as messagebox_mock:
            wizard._finish_button.invoke()

            self.assertTrue(self.mover.has_connected_stages)
            self.assertEqual(2, len(self.mover.calibrations))

            # Test stage assignment and settings
            self.assertEqual(
                400, self.mover.left_calibration.stage.get_speed_xy())
            self.assertEqual(
                400, self.mover.right_calibration.stage.get_speed_xy())
            self.assertEqual(
                400, self.mover.input_calibration.stage.get_speed_xy())
            self.assertEqual(
                400, self.mover.output_calibration.stage.get_speed_xy())
            self.assertEqual(400, self.mover.speed_xy)

            self.assertEqual(
                200, self.mover.left_calibration.stage.get_speed_z())
            self.assertEqual(
                200, self.mover.right_calibration.stage.get_speed_z())
            self.assertEqual(
                200, self.mover.input_calibration.stage.get_speed_z())
            self.assertEqual(
                200, self.mover.output_calibration.stage.get_speed_z())
            self.assertEqual(200, self.mover.speed_z)

            self.assertEqual(
                100, self.mover.left_calibration.stage.get_acceleration_xy())
            self.assertEqual(
                100, self.mover.right_calibration.stage.get_acceleration_xy())
            self.assertEqual(
                100, self.mover.input_calibration.stage.get_acceleration_xy())
            self.assertEqual(
                100, self.mover.output_calibration.stage.get_acceleration_xy())
            self.assertEqual(100, self.mover.acceleration_xy)

            # Check if stages are connected
            self.assertTrue(stage.connected)
            self.assertTrue(stage2.connected)

            # Test if stages are assigned
            self.assertEqual(self.mover.calibrations[(
                Orientation.LEFT, DevicePort.OUTPUT)].stage, stage)
            self.assertEqual(self.mover.calibrations[(
                Orientation.RIGHT, DevicePort.INPUT)].stage, stage2)

            messagebox_mock.assert_called_once_with(
                message="Successfully connected to 2 stages.")
