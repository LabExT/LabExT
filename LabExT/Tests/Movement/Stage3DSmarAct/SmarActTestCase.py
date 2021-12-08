#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import ctypes as ct
import json
import unittest
from importlib import reload
from unittest.mock import Mock, patch, DEFAULT, mock_open

from LabExT.Utils import get_configuration_file_path

orig_import = __import__
orig_open = open


def open_mock(*args, **kargs):
    if args[0] == get_configuration_file_path('mcsc_module_path.txt'):
        return mock_open(read_data=json.dumps(
            '/path/to/control/module'))(*args, **kargs)
    return orig_open(*args, **kargs)


MCSControl_Mock = Mock()


def import_mock(name, *args):
    if name == 'MCSControl_PythonWrapper.MCSControl_PythonWrapper':
        return MCSControl_Mock
    return orig_import(name, *args)


with patch('builtins.open', side_effect=open_mock):
    with patch('builtins.__import__', side_effect=import_mock):
        from LabExT.Movement.Stage3DSmarAct import Stage3DSmarAct


class SmarActTestCase(unittest.TestCase):
    MCSC_STATUS_OK = 0
    MCSC_STATUS_ERR = 1

    def setUp(self) -> None:
        self.mcsc_mock = MCSControl_Mock.MCSControl_PythonWrapper
        self.mcsc_mock.SA_OK = self.MCSC_STATUS_OK

        self.address = b'usb:id:000000000'
        self.channel_index = 42

        self.stage = Stage3DSmarAct(self.address)
        self.channel = Stage3DSmarAct._Channel(self.stage, self.channel_index)
        return super().setUp()

    def tearDown(self) -> None:
        self.stage.connected = True
        self.mcsc_mock.SA_CloseSystem = Mock(return_value=self.MCSC_STATUS_OK)

    def update_by_reference(self, mapping):
        def inner(*args):
            for arg_no, c_type in mapping.items():
                args[arg_no].value = c_type.value
            return DEFAULT
        return inner

    def _to_nanometer(self, um: int) -> int:
        return um * 1e3

    def _to_mircometer(self, nm: int) -> int:
        return nm * 1e-3
