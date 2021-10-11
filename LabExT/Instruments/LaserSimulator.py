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


class LaserSimulator(DummyInstrument):
    """
    ## LaserSimulator

    Software-only simulator of a real laser instrument. Offers the same properties as the
    [LaserMainframeKeysight](./LaserMainframeKeysight.md) class (including sweep feature!) but mocks
    everything in software.

    Use this instrument to test your measurements requiring a Laser.
    """

    def __init__(self, *args, **kwargs):
        # call Instrument constructor, creates VISA instrument
        super().__init__(*args, **kwargs)

        # properties
        self._instrument_property_wavelength = 1550
        self._instrument_property_unit = 'dBm'
        self._instrument_property_enable = False
        self._instrument_property_power = 0.0
        self._sweep_property_start_nm = 1450
        self._sweep_property_stop_nm = 1650
        self._sweep_property_step_pm = 20
        self._sweep_property_speed_nmps = 9999
        self._sweep_start_time = None

    def __enter__(self):
        super().__enter__()
        self.enable = True

    def __exit__(self, exc_type, exc_value, traceback):
        self.enable = False
        super().__exit__(exc_type, exc_value, traceback)

    def idn(self):
        return "LaserSimulator class for SW testing."

    #
    #   mainframe options
    #

    @property
    def min_lambda(self):
        return 1000.0

    @property
    def max_lambda(self):
        return 1700.0

    #
    #   standard properties
    #

    @property
    def wavelength(self):
        return self._instrument_property_wavelength

    @wavelength.setter
    def wavelength(self, wl_nm):
        self._instrument_property_wavelength = wl_nm

    @property
    def power(self):
        return self._instrument_property_power

    @power.setter
    def power(self, power_dBm):
        self._instrument_property_power = power_dBm

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
    def enable(self):
        return self._instrument_property_enable

    @enable.setter
    def enable(self, b):
        if b:
            self._instrument_property_enable = True
        else:
            self._instrument_property_enable = False

    #
    # additional functions, such that we can simulate IL sweeps
    #

    def sweep_wl_setup(self, start_nm, stop_nm, step_pm, sweep_speed_nm_per_s, **kwargs):
        self._sweep_property_start_nm = start_nm
        self._sweep_property_stop_nm = stop_nm
        self._sweep_property_step_pm = step_pm
        self._sweep_property_speed_nmps = sweep_speed_nm_per_s

    def sweep_wl_start(self):
        self._sweep_start_time = time.time()

    def sweep_wl_get_n_points(self):
        return int(abs((self._sweep_property_stop_nm - self._sweep_property_start_nm)
                       / (self._sweep_property_step_pm / 1000)) + 1)

    def sweep_wl_busy(self):
        if self._sweep_start_time is None:
            raise RuntimeError("Sweep has not been started.")
        meas_time = abs(self._sweep_property_start_nm - self._sweep_property_stop_nm) / self._sweep_property_speed_nmps
        # "realistic" wait for sweep to be over
        if time.time() - meas_time > self._sweep_start_time:
            # laser is not busy anymore when enough time passed since call of sweep_wl_start
            return False
        else:
            return True

    def sweep_wl_get_data(self, N_samples):
        return np.linspace(self._sweep_property_start_nm,
                           self._sweep_property_stop_nm,
                           num=N_samples)
