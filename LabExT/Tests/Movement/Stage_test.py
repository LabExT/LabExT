#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest.mock import Mock
from unittest import TestCase

from LabExT.Movement.Stage import Stage, StageError, assert_stage_connected, assert_driver_loaded
from LabExT.Movement.Stages.DummyStage import DummyStage


class StageTest(TestCase):
    def setUp(self) -> None:
        self.stage = Mock()

    def test_assert_driver_loaded_raises_error_if_driver_not_loaded(self):
        self.stage.driver_loaded = False

        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(StageError):
            assert_driver_loaded(func)(self.stage)

        func.assert_not_called()

    def test_assert_stage_connected_raises_error_if_not_connected(self):
        self.stage.driver_loaded = True
        self.stage.connected = False

        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(StageError):
            assert_stage_connected(func)(self.stage)

        func.assert_not_called()
