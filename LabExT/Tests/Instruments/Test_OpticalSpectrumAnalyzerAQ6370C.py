#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.

Required lab setup:
 An OSA with no input.
"""

import unittest

import numpy as np

from LabExT.Instruments.OpticalSpectrumAnalyzerAQ6370C import OpticalSpectrumAnalyzerAQ6370C
from LabExT.Tests.Utils import ask_user_yes_no


class Test_OpticalSpectrumAnalyzerAQ6370C(unittest.TestCase):
    #
    # test case constants
    #

    visa_address = "TCPIP0::ief-lab-aq6370c-20-1.ee.ethz.ch::10001::SOCKET"
    instr = None

    user_interaction_required = False

    #
    # setup and teardown methods
    #

    @classmethod
    def setUpClass(cls) -> None:
        # This method gets executed ONCE before ALL test cases.
        cls.instr = OpticalSpectrumAnalyzerAQ6370C(visa_address=cls.visa_address)
        cls.instr.open()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.instr.active_trace = 'TRA'
        cls.instr.close()

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

    def test_wl_params(self):
        self.instr.centerwavelength = 1310
        self.instr.span = 10

        self.assertAlmostEqual(1305, self.instr.startwavelength)
        self.assertAlmostEqual(1315, self.instr.stopwavelength)
        self.assertAlmostEqual(1310, self.instr.centerwavelength)
        self.assertAlmostEqual(10, self.instr.span)

        if self.user_interaction_required:
            self.assertTrue(ask_user_yes_no("Is the OSA span from 1305nm to 1315nm?", default_answer=None))

        self.instr.startwavelength = 1540
        self.instr.stopwavelength = 1560

        self.assertAlmostEqual(1540, self.instr.startwavelength)
        self.assertAlmostEqual(1560, self.instr.stopwavelength)
        self.assertAlmostEqual(1550, self.instr.centerwavelength)
        self.assertAlmostEqual(20, self.instr.span)

        if self.user_interaction_required:
            self.assertTrue(ask_user_yes_no("Is the OSA span from 1540nm to 1560nm?", default_answer=None))

    def test_resolution(self):
        self.instr.sweepresolution = 1.0
        self.assertAlmostEqual(1.0, self.instr.sweepresolution)
        with self.assertRaises(ValueError):
            self.instr.sweepresolution = 0.0
        with self.assertRaises(ValueError):
            self.instr.sweepresolution = 100.0
        self.instr.sweepresolution = 0.02
        self.assertAlmostEqual(0.02, self.instr.sweepresolution)

    def test_sweep_modes(self):
        sweep_bkp = self.instr._sweep_mode
        for mode in self.instr._sweep_modes:
            self.instr._sweep_mode = mode
            self.assertEqual(mode, self.instr._sweep_mode)
        self.instr._sweep_mode = sweep_bkp
        if self.user_interaction_required:
            self.assertTrue(ask_user_yes_no("Is the Sweep Mode set to " + str(sweep_bkp) + "?", default_answer=None))

    # def test_sens_modes(self):
    #     sense_bkp = self.instr.sens_mode
    #     for mode in self.instr.sens_modes:
    #         self.instr.sens_mode = mode
    #         self.assertEqual(mode, self.instr.sens_mode)
    #     self.instr.sens_mode = sense_bkp
    #     if self.user_interaction_required:
    #         self.assertTrue(ask_user_yes_no("Is the Sense Mode set to " + str(sense_bkp) + "?", default_answer=None))

    # def test_trace(self):
    #     trace_bkp = self.instr.active_trace
    #     while True:
    #         trc = np.random.choice(self.instr.traces)
    #         if trc != trace_bkp:
    #             break
    #     self.instr.active_trace = trc
    #     self.assertEqual(trc, self.instr.active_trace)
    #     self.instr.active_trace = trace_bkp
    #     if self.user_interaction_required:
    #         self.assertTrue(ask_user_yes_no("Is the Active Trace set to " + str(trace_bkp) + "?", default_answer=None))

    def test_single_run(self):
        self.instr.startwavelength = 1540
        self.instr.stopwavelength = 1560
        self.instr.sweepresolution = 1.0
        wl, p = self.instr.get_data()
        self.assertTrue(len(wl) == len(p))
        self.assertTrue(all(np.diff(wl) >= 0.0))
        self.assertTrue(all(np.isfinite(p)))

    # def test_marker_search_mode(self):
    #     self.instr.marker_search_mode = 'ON'
    #     self.assertEqual(self.instr.marker_search_mode, 1)
    #     self.instr.marker_search_mode = '1'
    #     self.assertEqual(self.instr.marker_search_mode, 1)
    #     self.instr.marker_search_mode = 'OFF'
    #     self.assertEqual(self.instr.marker_search_mode, 0)
    #     self.instr.marker_search_mode = '0'
    #     self.assertEqual(self.instr.marker_search_mode, 0)
    #     with self.assertRaises(ValueError):
    #         self.instr.marker_search_mode = 'asdf'



if __name__ == '__main__':
    unittest.main()
