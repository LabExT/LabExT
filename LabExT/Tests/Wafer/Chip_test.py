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

    def test_empty_chip(self):
        self.chip = Chip()
        self.assertIsNone(self.chip.name)

    def test_simple_chip(self):
        self.chip = Chip(name='Simple')
        self.assertEqual(self.chip.name, 'Simple')
        self.assertEqual(self.chip._devices, [])
        self.assertEqual(self.chip.devices, {})
        with self.assertRaises(ValueError):
            self.chip._load_information()

    def test_devices_directly(self):
        devices = [
            Device(id='1', in_position=[1., 1.], out_position=[2., 2.], type='test'),
            Device(id='2', in_position=[3., 3.], out_position=[4., 4.], type='test')
        ]
        self.chip = Chip(name='Direct', devices=devices)
        self.assertEqual(self.chip.name, 'Direct')
        self.assertEqual(len(self.chip.devices), 2)
        self.assertIsInstance(self.chip.devices['1'], Device)
        self.assertIsNone(self.chip.path)
        with self.assertRaises(ValueError):
            self.chip._load_information()

    def test_loading_from_csv(self):
        chip_name = 'TestChip'
        filepath = join(dirname(dirname(__file__)), 'example_chip_description_PhoeniX_style.csv')

        self.chip = Chip.from_file(filepath=filepath, name=chip_name)
        self.assertEqual(self.chip.path, filepath)
        self.assertEqual(self.chip.name, chip_name)
        self.assertEqual(len(self.chip.devices), 49)
        random_dev_id = random.choice(list(self.chip.devices.keys()))
        sample_dev = self.chip.devices[random_dev_id]
        self.assertIsInstance(sample_dev, Device)
        self.assertIsInstance(sample_dev.id, str)
        self.assertIsInstance(sample_dev.in_position, list)
        self.assertIsInstance(sample_dev.out_position, list)
        self.assertIsInstance(sample_dev.type, str)
        self.assertIsInstance(sample_dev.parameters, dict)
        self.assertEqual(self.chip.devices[sample_dev.id], sample_dev)

    def test_loading_from_json(self):
        pass
