#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

import numpy as np

from LabExT.Instruments.DummyInstrument import DummyInstrument
from LabExT.Instruments.InstrumentAPI import InstrumentException


class PowerMeterSimulator(DummyInstrument):
    """
    ## PowerMeterSimulator

    Software-only simulator of a real power meter instrument. Offers the same properties as
    [PowerMeterGenericKeysight](./PowerMeterGenericKeysight.md) class (including logging feature!) but
    mocks everything in software.

    Use this instrument to test your measurements requiring a power meter.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # logging simulation
        self._n_measurement_points = 0

        # properties
        self._instrument_property_wavelength = 1550
        self._instrument_property_unit = 'dBm'
        self._instrument_property_range = -30
        self._instrument_property_autorange = True
        self._instrument_property_avgtime = 0.001

        # triggering simulation
        self._trigger = "cont"
        self._last_val = -99.0

    def _simulate_opt_power_value(self):
        return 2 * np.random.standard_normal() + self._instrument_property_range - 5

    def idn(self):
        return "PowerMeterSimulator for SW testing."

    #
    # logging functions
    #

    def logging_setup(self, n_measurement_points=10000, **kwargs):
        self._n_measurement_points = n_measurement_points

    def logging_busy(self):
        return False

    def logging_get_data(self, **kwargs):
        pwr_data = 2 * np.random.standard_normal(self._n_measurement_points) + self._instrument_property_range - 5
        return pwr_data

    #
    # standard properties of power meter channels
    #

    @property
    def wavelength(self):
        return self._instrument_property_wavelength

    @wavelength.setter
    def wavelength(self, wl_nm):
        self._instrument_property_wavelength = wl_nm

    @property
    def unit(self):
        return self._instrument_property_unit

    @unit.setter
    def unit(self, pu):
        if 'dbm' in pu.lower():
            self._instrument_property_unit = pu
        elif 'watt' in pu.lower():
            self._instrument_property_unit = pu
        else:
            raise InstrumentException('Unknown unit: {}, use dBm or Watt')

    @property
    def range(self):
        return self._instrument_property_range

    @range.setter
    def range(self, range_dBm):
        if 'auto' in str(range_dBm).lower():
            self._instrument_property_autorange = True
            self._instrument_property_range = -30
        else:
            self._instrument_property_autorange = False
            self._instrument_property_range = range_dBm

    @property
    def autoranging(self):
        return self._instrument_property_autorange

    @autoranging.setter
    def autoranging(self, autorange):
        self._instrument_property_autorange = autorange

    @property
    def averagetime(self):
        return self._instrument_property_avgtime

    @averagetime.setter
    def averagetime(self, atime_s):
        self._instrument_property_avgtime = atime_s

    @property
    def power(self):
        time.sleep(self._instrument_property_avgtime)
        self._last_val = self._simulate_opt_power_value()
        return self._last_val

    #
    # manual triggering
    #

    def trigger(self, continuous=None):
        if continuous is None:
            self._trigger = 'on'
            time.sleep(self._instrument_property_avgtime)
        elif continuous:
            self._trigger = 'on'
        else:
            self._trigger = 'off'

    def fetch_power(self):
        if self._trigger == 'on':
            self._last_val = self._simulate_opt_power_value()
            if self.range < -30:
                # just for GUI test purposes here
                self.logger.warning('OPM: Sensitivity is too low.')
            return self._last_val
        elif self._trigger == 'off':
            return self._last_val
        else:
            raise RuntimeError("PowerMeterDummy class _trigger property wrong value:" + str(self._trigger))
