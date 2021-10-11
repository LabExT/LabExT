#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest

import numpy as np

from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Measurements.MeasAPI import Measurement


def check_ILsweep_data_output(test_inst, data_dict, params_dict):
    # length of all output data vectors should be equal
    len_trans = len(data_dict['values']['transmission [dBm]'])
    for k, v in data_dict['values'].items():
        test_inst.assertTrue(len(v) == len_trans)

    # make sure that there are no NANs in the output
    test_inst.assertFalse(np.any(np.isnan(data_dict['values']['wavelength [nm]'])))
    test_inst.assertFalse(np.any(np.isnan(data_dict['values']['transmission [dBm]'])))

    # test wavelength start and end
    test_inst.assertTrue(np.isclose(data_dict['values']['wavelength [nm]'][0],
                               params_dict['wavelength start'].value))
    test_inst.assertTrue(np.isclose(data_dict['values']['wavelength [nm]'][-1],
                               params_dict['wavelength stop'].value))


class Test_InsertionLossSweep(unittest.TestCase):
    """
    Test for the InsertionLossSweep measurement.

    Required lab setup:
    laser -> <open>
    <open> -> power meter
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
            'Laser': LaserSimulator(),
            'Power Meter': PowerMeterSimulator()
        }

        # defaults
        self.meas_default_params = InsertionLossSweep.get_default_parameter()

    def tearDown(self) -> None:
        for _, instr in self.meas.instruments:
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
        instrs['Power Meter 2'] = None  # would trigger AttributeError in case of usage inside class

        params = InsertionLossSweep.get_default_parameter()

        #
        # run the measurement algorithm
        #

        self.meas = InsertionLossSweep()
        self.meas.algorithm(None,
                            data=data,
                            instruments=instrs,
                            parameters=params)

        #
        # test output section
        #

        # see if measurement actually filled all necessary fields
        self.meas._check_data(data=data)

        # check rest of data
        check_ILsweep_data_output(test_inst=self, data_dict=data, params_dict=params)



if __name__ == '__main__':
    unittest.main()
