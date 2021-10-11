#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.

Required lab setup:
 N7744A power meter, WITH CAP REMOVED from testing channel so ambient light can enter the detector!
 After the test, please put protection caps on the optical inputs again.
"""

import time
import unittest

from LabExT.Instruments.InstrumentAPI import InstrumentException
from LabExT.Instruments.PowerMeterN7744A import PowerMeterN7744A


class Test_PowerMeterGenericKeysight(unittest.TestCase):
    #
    # test case constants
    #

    visa_address = "TCPIP0::ief-lab-n7744a-2.ee.ethz.ch::inst0"
    PMClass = PowerMeterN7744A  # pick PowerMeterGenericKeysight or PowerMeterN7744A
    channel = 1

    instr = None

    #
    # setup and teardown methods
    #

    def setUp(self) -> None:
        self.instr.logging_stop()

    @classmethod
    def setUpClass(cls) -> None:
        # This method gets executed ONCE before ALL test cases.
        cls.instr = cls.PMClass(visa_address=cls.visa_address, channel=cls.channel)
        cls.instr.open()

    @classmethod
    def tearDownClass(cls) -> None:
        # This method gets executed ONCE after ALL test cases.
        cls.instr.close()

    def tearDown(self) -> None:
        self.instr.logging_stop()

    #
    # test cases
    #

    def test_print_parameters(self):
        params = self.instr.get_instrument_parameter()
        print("\nInstrument parameters:")
        for k, v in params.items():
            print(" " + str(k) + ": " + str(v))
        for k, v in params.items():
            self.assertNotIn('not found!', str(v), msg='Invalid instrument parameter: ' + str(k))
            self.assertNotIn('ERROR getting', str(v), msg='Error getting instrument parameter: ' + str(k))

    def test_read_and_unit(self):
        with self.assertRaises(InstrumentException):
            self.instr.unit = 'blabla'
        with self.assertRaises(InstrumentException):
            self.instr.unit = ''
        self.instr.unit = 'DBM'
        self.instr.unit = 'dbm'
        self.instr.unit = 'dBm'
        p = self.instr.power
        self.assertLessEqual(p, 0.0)  # ambient light is surely less than 1mW power
        self.instr.unit = 'Watt'
        p = self.instr.power
        self.assertGreaterEqual(p, 0.0)  # it's valid to assume that there is some ambient light around
        self.instr.unit = 'dBm'

    def test_manual_triggering(self):
        self.instr.trigger(continuous=False)
        self.instr.trigger()  # manual trigger
        p1 = self.instr.fetch_power()  # no builtin triggering
        time.sleep(1.0)
        p2 = self.instr.fetch_power()
        self.assertEqual(p1, p2)
        self.instr.trigger(continuous=True)

    def test_range(self):
        self.instr.unit = 'dBm'
        self.instr.autoranging = True
        for r_test in [-10, -20, -30]:
            self.instr.range = r_test
            self.assertFalse(self.instr.autoranging)  # autoranging should be disabled on manually set range
            self.assertEqual(self.instr.range, r_test)
        self.instr.autoranging = True

    def test_wavelength(self):
        for wl_test in [1260, 1310, 1550, 1600]:
            self.instr.wavelength = wl_test
            self.assertEqual(self.instr.wavelength, wl_test)

    def test_averagetime(self):
        bkp_timeout = self.instr._inst.timeout
        self.instr.unit = 'dBm'
        for atime_test in [1.0, 0.1, 0.01, 0.001]:
            self.instr.averagetime = atime_test
            self.instr._inst.timeout = atime_test * 1.1 + 0.2  # account for some network delays
            p = self.instr.power  # this would trigger a VISA timeout exception
            self.assertLessEqual(p, 0.0)
            self.assertAlmostEqual(self.instr.averagetime, atime_test)
        self.instr._inst.timeout = bkp_timeout

    def test_logging(self):
        avg_time_s = 0.01
        N_points = 100
        self.instr.averagetime = avg_time_s
        self.instr.trigger(continuous=True)

        self.instr.logging_setup(n_measurement_points=N_points, triggered=False)

        self.instr.logging_start()

        # assert that the class reports logging busy
        self.assertTrue(self.instr.logging_busy())

        # check stopping of logging
        self.instr.logging_stop()
        self.assertFalse(self.instr.logging_busy())

        self.instr.logging_start()

        # check that we finish logging within given timeframe
        start_time_s = time.time()
        timeout_s = N_points * avg_time_s + 0.3  # account for some network delays
        current_time_s = 0
        while current_time_s < start_time_s + timeout_s:
            if not self.instr.logging_busy():
                break
            current_time_s = time.time()
        else:  # Yes, you can do this. The else-clause triggers if the "break" within while never got called
            self.fail("Power Meter did not execute auto-triggered logging within timeout!")

        power_data = self.instr.logging_get_data()
        self.assertEqual(len(power_data), N_points)


if __name__ == '__main__':
    unittest.main()
