#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from os.path import dirname, join
from unittest import TestCase

from LabExT.Wafer.Device import Device
from LabExT.Wafer.Chip import Chip


class ChipTest(TestCase):

    def setUp(self) -> None:
        self.chip = Chip(name='Simple')

    def test_simple(self):
        self.assertEqual(self.chip.name, 'Simple')
        self.assertEqual(self.chip._devices, [])
        self.assertEqual(self.chip.devices, {})
        with self.assertRaises(ValueError):
            self.chip._load_information()

    def test_direct(self):
        devices = [
            Device(id='1', in_position=[1., 1.], out_position=[2., 2.], type='test'),
            Device(id='2', in_position=[3., 3.], out_position=[4., 4.], type='test')
        ]
        self.chip = Chip(name='Direct', devices=devices)
        self.assertEqual(self.chip.name, 'Direct')
        self.assertIsInstance(self.chip.devices['1'], Device)
        with self.assertRaises(ValueError):
            self.chip._load_information()

    def test_loading_from_csv(self):
        chip_name = 'TestFile'
        filepath = join(dirname(dirname(__file__)), 'example_chip_description_PhoeniX_style.csv')

        self.chip = Chip.from_file(filepath=filepath, name=chip_name)
        self.assertEqual(self.chip.name, chip_name)
        sample_dev = self.chip._devices[0]
        self.assertIsInstance(sample_dev.id, str)
        self.assertEqual(self.chip.devices[sample_dev.id], sample_dev)

    def test_loading_from_json(self):
        pass
