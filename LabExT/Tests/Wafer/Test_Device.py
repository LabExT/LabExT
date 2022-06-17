#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest import TestCase

from LabExT.Wafer.Device import Device


class DeviceTest(TestCase):

    def setUp(self) -> None:
        self.device = Device('abc')
        print(self.device)

    def test_abc(self):
        self.assertEqual(self.device.id, 'abc')
        self.assertEqual(self.device.in_position, [])
        self.assertEqual(self.device.type, '')
        self.assertIsInstance(self.device.as_dict(), dict)

    def test_full_device(self):
        self.device = Device('b2', [0, 0], [1, 1], 'test', {'more': 1})
        self.assertEqual(self.device.parameters, {'more': 1})
        print(self.device)
