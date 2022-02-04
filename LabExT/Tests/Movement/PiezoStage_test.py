#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest

import numpy as np

from LabExT.Movement.Stages import Stage3DSmarAct
from LabExT.Tests.Utils import ask_user_yes_no, mark_as_laboratory_test

@mark_as_laboratory_test
class Test_PiezoStage(unittest.TestCase):

    user_input_required = True
    z_axis_direction = -1

    @classmethod
    def setUpClass(cls) -> None:
        # This method gets executed ONCE before ALL test cases.
        address = b'usb:id:276053211'
        cls.stage = Stage3DSmarAct(address)

    #
    # test cases
    #

    def test_set_get_xy_speed(self):
        # get speeds to reset later
        xy_speed = self.stage.get_speed_xy()

        xy_speeds = [20, 50, 400, 3000]

        for speed in xy_speeds:
            self.stage.set_speed_xy(speed)
            self.assertAlmostEqual(speed, self.stage.get_speed_xy())

        # reset stage speed
        self.stage.set_speed_xy(xy_speed)

    def test_set_get_z_speed(self):
        z_speed = self.stage.get_speed_z()
        z_speeds = [5, 20, 50, 1500]
        for speed in z_speeds:
            self.stage.set_speed_z(speed)
            self.assertAlmostEqual(speed, self.stage.get_speed_z())

        # reset stage speed
        self.stage.set_speed_xy(z_speed)

    def test_set_get_xy_acc(self):
        # get speeds to reset later
        xy_acc = self.stage.get_acceleration_xy()

        xy_accs = [2, 5, 40, 300]

        for acc in xy_accs:
            self.stage.set_acceleration_xy(acc)
            self.assertAlmostEqual(acc, self.stage.get_acceleration_xy())

        # reset stage speed
        self.stage.set_acceleration_xy(xy_acc)

    def test_params(self):
        # z-axis direction
        self.stage.z_axis_direction = 1
        self.assertEqual(1, self.stage.z_axis_direction)

        self.stage.z_axis_direction = -1
        self.assertEqual(-1, self.stage.z_axis_direction)

    def test_current_position(self):

        pos = self.stage.get_current_position()
        pos = [elem * 1e3 for elem in pos]

        if self.user_input_required:
            self.assertTrue(ask_user_yes_no(f"Is the Piezo-Stage at position {pos}?", default_answer=True))

    def test_move_relative(self):

        # move 1mm in x and y
        self.stage.move_relative(1000, 1000)

        if self.user_input_required:
            self.assertTrue(ask_user_yes_no("Has the Piezo-Stage moved +1mm in x and y?", default_answer=True))

    def test_move_absolute(self):

        positions = np.array([[0, 0],
                              [1000, 800],
                              [-300, -300]])
        for i in range(np.shape(positions)[0]):
            self.stage.move_absolute(positions[i, :])

            if self.user_input_required:
                self.assertTrue(ask_user_yes_no(f"Has the Piezo-Stage moved to absolute position {positions[i, :] * 1e3}?",
                                                default_answer=True))

    def test_lower_lift_stage(self):

        pos0 = self.stage.get_current_position()
        z_lift_0 = self.stage.get_lift_distance()
        lift = 1000
        self.stage.set_speed_z(500)
        # user has to set the correct z axis direction here
        self.stage.z_axis_direction = self.z_axis_direction

        self.stage.set_lift_distance(lift)
        self.stage.lift_stage()
        if self.user_input_required:
            self.assertTrue(ask_user_yes_no(f"Has the stage moved up by {lift}um"))

        self.stage.lower_stage()

        if self.user_input_required:
            self.assertTrue(ask_user_yes_no(f"Has the stage lowered down by {lift}um"))

    def test_wiggle_z_axis_positioner(self):

        self.stage.wiggle_z_axis_positioner()
        # user has to set the correct z axis direction here
        self.stage.z_axis_direction = self.z_axis_direction

        if self.user_input_required:
            self.assertTrue(ask_user_yes_no("Has the stage wiggled (first up then down or vice versa?)"))

