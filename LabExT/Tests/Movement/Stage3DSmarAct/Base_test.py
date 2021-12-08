#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import ctypes as ct
from unittest.mock import Mock, patch

from LabExT.Tests.Movement.Stage3DSmarAct.SmarActTestCase import SmarActTestCase, Stage3DSmarAct
from LabExT.Movement.Stage import Stage, StageError


class BaseTest(SmarActTestCase):
    def test_if_found_inall_stage_classes(self):
        self.assertIn(Stage3DSmarAct, Stage.get_all_stage_classes())

    def test_if_found_in_stage_discovery(self):
        expected_stages = ['usb:id:000000001', 'usb:id:000000002']
        stages_char_array = ct.create_string_buffer(
            bytes("\n".join(expected_stages), "utf-8"))

        self.mcsc_mock.SA_FindSystems = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                1: stages_char_array,
                2: ct.c_ulong(ct.sizeof(stages_char_array))
            })
        )

        for stage in list(
            filter(
                lambda s: isinstance(
                    s,
                    Stage3DSmarAct),
                Stage.discovery())):
            self.assertIn(stage.address.decode('utf-8'), expected_stages)

    def test_find_stages_successfully(self):
        expected_stages = ['usb:id:000000001', 'usb:id:000000002']
        stages_char_array = ct.create_string_buffer(
            bytes("\n".join(expected_stages), "utf-8"))
        expected_size = ct.sizeof(stages_char_array)

        self.mcsc_mock.SA_FindSystems = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                1: stages_char_array,
                2: ct.c_ulong(expected_size)
            })
        )

        stages = Stage3DSmarAct.find_stages()

        self.mcsc_mock.SA_FindSystems.assert_called_once()

        for stage in stages:
            self.assertIn(stage.address.decode('utf-8'), expected_stages)
            self.assertIsInstance(stage, Stage3DSmarAct)

    def test_find_stages_when_driver_not_loaded(self):
        with patch.object(Stage3DSmarAct, 'driver_loaded', False):
            self.assertEqual(Stage3DSmarAct.find_stages(), [])

    def test_find_stages_when_empty_buffer(self):
        self.mcsc_mock.SA_FindSystems = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                2: ct.c_ulong(0)
            })
        )

        self.assertEqual([], Stage3DSmarAct.find_stages())
        self.mcsc_mock.SA_FindSystems.assert_called_once()

    def test_connect_if_driver_not_loaded(self):
        with patch.object(Stage3DSmarAct, 'driver_loaded', False):
            with self.assertRaises(StageError):
                self.stage.connect()

    def test_connect_if_open_system_fails(self):
        self.mcsc_mock.SA_OpenSystem = Mock(return_value=self.MCSC_STATUS_ERR)

        with self.assertRaises(StageError):
            self.assertFalse(self.stage.connect())

        self.mcsc_mock.SA_OpenSystem.assert_called_once()
        self.assertFalse(self.stage.connected)
        self.assertIsNone(self.stage.handle)

    @patch.object(Stage3DSmarAct._Channel, "speed", None)
    @patch.object(Stage3DSmarAct._Channel, "acceleration", None)
    def test_connect_if_open_system_succeed(self):
        expected_handle = 42

        self.mcsc_mock.SA_OpenSystem = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                0: ct.c_ulong(expected_handle)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'is_sensor_linear', True):
            self.assertTrue(self.stage.connect())

        self.mcsc_mock.SA_OpenSystem.assert_called_once()
        self.assertTrue(self.stage.connected)
        self.assertEqual(self.stage.handle.value, expected_handle)

        self.assertEqual(len(self.stage.channels), 3)

    def test_connect_if_sensor_not_linear(self):
        expected_handle = 42

        self.mcsc_mock.SA_OpenSystem = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                0: ct.c_ulong(expected_handle)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'is_sensor_linear', False):
            with self.assertRaises(StageError) as error:
                self.stage.connect()

        self.mcsc_mock.SA_OpenSystem.assert_called_once()
        self.assertFalse(self.stage.connected)
        self.assertEqual(self.stage.handle.value, expected_handle)
        self.assertTrue(
            'has no supported linear sensor' in str(
                error.exception))
        self.assertEqual(len(self.stage.channels), 3)

    def test_disconnect_successfully(self):
        self.stage.connected = True
        self.mcsc_mock.SA_CloseSystem = Mock(return_value=self.MCSC_STATUS_OK)

        self.stage.disconnect()

        self.mcsc_mock.SA_CloseSystem.assert_called_once_with(
            self.stage.handle)
        self.assertFalse(self.stage.connected)

    def test_disconnect_unsuccessfully(self):
        self.stage.connected = True

        self.mcsc_mock.SA_CloseSystem = Mock(return_value=self.MCSC_STATUS_ERR)

        with self.assertRaises(StageError):
            self.stage.disconnect()

        self.mcsc_mock.SA_CloseSystem.assert_called_once_with(
            self.stage.handle)
        self.assertTrue(self.stage.connected)

    @patch.object(Stage3DSmarAct._Channel, "speed", None)
    @patch.object(Stage3DSmarAct._Channel, "acceleration", None)
    def test_connect_double_invocation(self):
        expected_handle = 42

        self.mcsc_mock.SA_OpenSystem = Mock(
            return_value=self.MCSC_STATUS_OK,
            side_effect=self.update_by_reference({
                0: ct.c_ulong(expected_handle)
            }))

        with patch.object(Stage3DSmarAct._Channel, 'is_sensor_linear', True):
            # First invocation should succeed
            self.assertTrue(self.stage.connect())
            # Second invocation
            self.assertTrue(self.stage.connect())

        # Test if SA_OpenSystem was only called once
        self.mcsc_mock.SA_OpenSystem.assert_called_once()
        self.assertTrue(self.stage.connected)
