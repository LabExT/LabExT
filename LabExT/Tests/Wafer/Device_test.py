#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import random
from dataclasses import FrozenInstanceError
from unittest import TestCase

from LabExT.Wafer.Device import Device
from LabExT.Tests.Utils import randomword


def random_str():
    return randomword(random.randint(5, 25))


def random_float():
    return random.random() * random.randint(1, 1000)


class DeviceTest(TestCase):

    def create_random_dev(self):
        self.device = Device(id=random_str(),
                             in_position=[random_float(), random_float()],
                             out_position=[random_float(), random_float()],
                             type=random_str(),
                             parameters={random_str(): random.randint(1, 15), random_str(): random_str()})

    def test_empty(self):
        with self.assertRaises(TypeError):
            self.device = Device()

        self.device = Device('')
        self.assertEqual(self.device.id, '')

    def test_id_only_device(self):
        self.device = Device('abc')
        self.assertEqual(self.device.id, 'abc')
        self.assertEqual(self.device.in_position, [])
        self.assertEqual(self.device.type, '')
        self.assertIsInstance(self.device.as_dict(), dict)

    def test_random_device_init(self):
        for _ in range(20):
            _id = random_str()
            _input = [random_float(), random_float()]
            _output = [random_float(), random_float()]
            _type = random_str()
            _param = {random_str(): random.randint(1, 15), random_str(): random_str()}

            self.device = Device(_id, _input, _output, _type, _param)

            self.assertEqual(self.device.id, _id)
            self.assertEqual(self.device.in_position, _input)
            self.assertEqual(self.device.out_position, _output)
            self.assertEqual(self.device.parameters, _param)

    def test_fixed_attr(self):
        self.create_random_dev()
        with self.assertRaises(FrozenInstanceError):
            self.device.id = '1'

    def test_sorting(self):
        dev_a = Device('1')
        dev_b = Device('q')
        dev_c = Device(id='z', in_position=[2, 1])
        dev_d = Device(id='z', in_position=[1, 1])
        self.assertTrue(dev_a < dev_b)
        self.assertTrue(dev_a < dev_c)
        self.assertTrue(dev_b < dev_c)
        self.assertTrue(dev_d < dev_c)

    def test_full_device(self):
        self.device = Device('b2', [0, 0], [1, 1], 'test', {'more': 1})
        self.assertEqual(self.device.parameters, {'more': 1})
