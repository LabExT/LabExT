#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import unittest
from pathlib import Path

import numpy as np
from parameterized import parameterized

from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Measurements.MeasAPI import Measurement


def check_InsertionLossSweep_data_output_heuristics(test_inst, data_dict, params_dict):
    # length of all output data vectors should be equal
    len_trans = len(data_dict['values']['wavelength [nm]'])
    if not params_dict['discard raw transmission data']:
        test_inst.assertTrue(len(data_dict['values']['transmission [dBm]']) == len_trans)
        test_inst.assertFalse(np.any(np.isnan(data_dict['values']['transmission [dBm]'])))
    if params_dict['file path to reference meas.']:
        test_inst.assertTrue(len(data_dict['values']['referenced transmission [dB]']) == len_trans)
        test_inst.assertFalse(np.any(np.isnan(data_dict['values']['referenced transmission [dB]'])))

    # make sure that there are no NANs in the output
    test_inst.assertFalse(np.any(np.isnan(data_dict['values']['wavelength [nm]'])))

    # test wavelength start and end
    test_inst.assertTrue(np.isclose(data_dict['values']['wavelength [nm]'][0],
                               params_dict['wavelength start']))
    test_inst.assertTrue(np.isclose(data_dict['values']['wavelength [nm]'][-1],
                               params_dict['wavelength stop']))
    

def check_InsertionLossSweep_exact_data_output(test_inst, data_dict, params_dict, rng_seed):
        
    # target data was generated with these params
    test_inst.assertEqual(params_dict['wavelength start'], 1530.0)
    test_inst.assertEqual(params_dict['wavelength stop'], 1570.0)
    test_inst.assertEqual(params_dict['wavelength step'], 10.0)
    np.testing.assert_allclose(data_dict['values']['wavelength [nm]'], np.arange(153000, 157001, 1) / 100)
    
    if not params_dict['discard raw transmission data']:
        test_inst.assertEqual(params_dict['powermeter range'], 10.0)
        with open(Path(__file__).parent / f'../Fixtures/power_meter_sim_seed_{rng_seed:d}.json', 'r') as fp:
            rnd_power_meter_data = json.load(fp)
        np.testing.assert_allclose(data_dict['values']['transmission [dBm]'], rnd_power_meter_data)


class InsertionLossSweepTest(unittest.TestCase):
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
        meas_params = {
            key: params[key].value for key in params.keys()
        }
        check_InsertionLossSweep_data_output_heuristics(test_inst=self, data_dict=data, params_dict=meas_params)

    @parameterized.expand([(True,), (False,), (True, 11354), (False, 11354), (True, 98749), (False, 98749)])
    def test_default_parameters_with_reference(self, discard_data, rng_seed=None):

        #
        # parameter and instrument preparation section
        # note: always operate on a copy of data, since the algorithm is supposed to fill it
        #

        data = Measurement.setup_return_dict()

        instrs = self.instrs.copy()
        instrs['Power Meter 2'] = None  # would trigger AttributeError in case of usage inside class

        params = InsertionLossSweep.get_default_parameter()
        params['file path to reference meas.'].value = \
            str((Path(__file__).parent / '../Fixtures/example_InsertionLossSweep_default_reference.json').resolve())
        params['discard raw transmission data'].value = discard_data

        #
        # run the measurement algorithm
        #

        self.meas = InsertionLossSweep()
        if rng_seed is not None:
            np.random.seed(rng_seed)
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
        meas_params = {
            key: params[key].value for key in params.keys()
        }
        check_InsertionLossSweep_data_output_heuristics(test_inst=self, data_dict=data, params_dict=meas_params)
        if rng_seed is not None:
            check_InsertionLossSweep_exact_data_output(test_inst=self, data_dict=data, params_dict=meas_params, rng_seed=rng_seed)

