#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

from LabExT.Measurements.MeasAPI.Measurement import Measurement
from LabExT.Wafer.Device import Device


class ToDo:
    def __init__(self, device: Device, measurement: Measurement):
        self.device = device
        self.measurement = measurement
        self._timestamp = int(time.time() * 1e6)

    def __getitem__(self, item):
        """ make To-Do class compatible with old code which used (device,measurement) tuples as ToDos """
        if item == 0:
            return self.device
        elif item == 1:
            return self.measurement
        else:
            raise KeyError(item)

    def __str__(self):
        return "<ToDo: " + str(self.measurement.get_name_with_id()) + " on " + str(self.device.short_str()) + ">"

    def __repr__(self):
        return self.__str__()

    def get_hash(self):
        """calculate the unique but hardly one-way functional 'hash' of a to do"""
        hash = str(self.device.short_str())
        hash += str(self.measurement.get_name_with_id())
        hash += str(self._timestamp)
        return hash
