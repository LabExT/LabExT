#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import random
from os.path import dirname, join
from unittest import TestCase

from LabExT.Wafer.Device import Device
from LabExT.Wafer.Chip import Chip


class ChipTest(TestCase):

    def test_missing_args_chip(self):
        with self.assertRaises(TypeError):
            _ = Chip()
        _ = Chip(name="example chip", devices=[], path="/example/path", _serialize_to_disk=False)

    def test_simple_chip(self):
        self.chip = Chip(name="Simple", devices=[], path="/example/path", _serialize_to_disk=False)
        self.assertEqual(self.chip.name, "Simple")
        self.assertEqual(self.chip._devices, [])
        self.assertEqual(self.chip.devices, {})
        self.assertEqual(self.chip.path, "/example/path")

    def test_devices_directly(self):
        devices = [
            Device(id="1", in_position=[1.0, 1.0], out_position=[2.0, 2.0], type="test"),
            Device(id="2", in_position=[3.0, 3.0], out_position=[4.0, 4.0], type="test"),
        ]
        self.chip = Chip(name="Direct", devices=devices, path="/example/path", _serialize_to_disk=False)
        self.assertEqual(self.chip.name, "Direct")
        self.assertEqual(len(self.chip.devices), 2)
        self.assertIsInstance(self.chip.devices["1"], Device)
        self.assertEqual(self.chip.path, "/example/path")
        self.assertEqual(self.chip.devices["1"].type, "test")
        self.assertEqual(self.chip.devices["2"].type, "test")
        self.assertEqual(self.chip.devices["1"].id, "1")
        self.assertEqual(self.chip.devices["2"].id, "2")

    def test_duplicate_dev_id(self):
        devices = [
            Device(id="1", in_position=[1.0, 1.0], out_position=[2.0, 2.0], type="test"),
            Device(id="1", in_position=[3.0, 3.0], out_position=[4.0, 4.0], type="test"),
            Device(id="2", in_position=[2.0, 2.0], out_position=[1.0, 1.0], type="test"),
        ]
        with self.assertRaises(AssertionError):
            Chip(name="Direct", devices=devices, path="/example/path", _serialize_to_disk=False)
