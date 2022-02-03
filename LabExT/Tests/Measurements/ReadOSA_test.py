#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest
from LabExT.Tests.Utils import mark_as_laboratory_test

import numpy as np

from LabExT.Instruments.OpticalSpectrumAnalyzerAQ6370C import OpticalSpectrumAnalyzerAQ6370C
from LabExT.Measurements.MeasAPI import Measurement
from LabExT.Measurements.ReadOSA import ReadOSA

@mark_as_laboratory_test
class ReadOSATest(unittest.TestCase):
    """
    Test for the ReadOSA measurement.
    required lab setup:
    - OSA
    """

    #
    # test case constants
    #

    user_input_required = False
    meas = None

    #
    # setup and teardown methods
    #

    def setUp(self) -> None:
        #
        # Initialize desired instruments here!
        #

        # software only tests:
        self.instrs = {
            'OSA': OpticalSpectrumAnalyzerAQ6370C(visa_address="TCPIP0::ief-lab-aq6370c-20-1.ee.ethz.ch::10001::SOCKET")
        }

        # defaults
        self.meas_default_params = ReadOSA.get_default_parameter()

    def tearDown(self) -> None:
        for _, instr in self.meas.instruments.items():
            instr.close()

    #
    # test cases
    #

    def test_default_parameters(self):

        #
        # parameter and instrument preparation section
        # note: always operate on a copy of data, since the algorithm is supposed to fill it
        #

        data = Measurement.setup_return_dict()

        instrs = self.instrs.copy()

        #
        # run the measurement algorithm
        #

        self.meas = ReadOSA()
        self.meas.algorithm(None,  # no device given
                            data=data,
                            instruments=instrs,
                            parameters=self.meas_default_params)

        #
        # test output section
        #

        # see if measurement actually filled all necessary fields
        self.meas._check_data(data=data)

        # length of all output data vectors should be equal
        self.assertTrue(len(data['values']['transmission [dBm]']) == len(data['values']['wavelength [nm]']))

        # make sure that there are no NANs in the output
        self.assertFalse(np.any(np.isnan(data['values']['transmission [dBm]'])))
        self.assertFalse(np.any(np.isnan(data['values']['wavelength [nm]'])))

    def test_parameters(self):
        data = Measurement.setup_return_dict()

        instrs = self.instrs.copy()
        params = self.meas_default_params.copy()

        #
        # run the measurement algorithm
        #
        center_wl = 1530.0
        span = 5.0
        no_points = 1000
        resolution = 0.002
        params['OSA center wavelength'].value = center_wl
        params['OSA span'].value = span
        params['no of points'].value = no_points
        params['sweep resolution'].value = resolution

        self.meas = ReadOSA()

        self.meas.algorithm(None,  # no device given
                            data=data,
                            instruments=instrs,
                            parameters=params)

        # see if measurement actually filled all necessary fields
        self.meas._check_data(data=data)
        instr_parameter = self.instrs['OSA'].get_instrument_parameter()

        self.assertAlmostEqual(center_wl, instr_parameter['centerwavelength'], places=4)
        self.assertAlmostEqual(span, instr_parameter['span'], places=4)
        self.assertAlmostEqual(no_points, instr_parameter['n_points'], places=4)
        self.assertAlmostEqual(resolution, instr_parameter['sweepresolution'], places=4)

