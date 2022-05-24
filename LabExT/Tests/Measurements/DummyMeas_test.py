#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import unittest

import numpy as np

from LabExT.Measurements.DummyMeas import DummyMeas
from LabExT.Measurements.MeasAPI import Measurement


def check_DummyMeas_data_output(test_inst, data_dict, params_dict):
    # force all to be numpy arrays
    values_arr = {}
    for k, v in data_dict['values'].items():
        values_arr[k] = np.array(v)

    # check data point output
    n_data = len(values_arr['point indices'])
    test_inst.assertTrue(params_dict['number of points'] == n_data)
    np.testing.assert_array_equal(values_arr['point indices'], np.arange(n_data))

    # check noise output
    test_inst.assertTrue(len(values_arr['point values']) == n_data)
    test_inst.assertTrue(np.all(np.isfinite(values_arr['point values'])))


class DummyMeasTest(unittest.TestCase):
    """
    Test for the DummyMeas measurement.

    Required lab setup: none, only SW testing
    """

    #
    # test case constants
    #

    user_input_required = False
    meas = None

    #
    # test cases
    #

    def test_default_parameters(self):

        #
        # parameter and instrument preparation section
        # note: always operate on a copy of data, since the algorithm is supposed to fill it
        #

        data = Measurement.setup_return_dict()

        params = DummyMeas.get_default_parameter()

        #
        # run the measurement algorithm
        #

        self.meas = DummyMeas()
        self.meas.algorithm(None,  # no device given
                            data=data,
                            instruments={},
                            parameters=params)

        #
        # test output section
        #

        self.meas._check_data(data=data)

        # check data output
        meas_params = {
            key: params[key].value for key in params.keys()
        }
        check_DummyMeas_data_output(self, data, meas_params)

    def test_raise_error(self):
        #
        # parameter and instrument preparation section
        # note: always operate on a copy of data, since the algorithm is supposed to fill it
        #

        data = Measurement.setup_return_dict()

        params = DummyMeas.get_default_parameter()
        params['simulate measurement error'].value = True

        #
        # run the measurement algorithm
        #

        self.meas = DummyMeas()
        with self.assertRaises(Exception):
            self.meas.algorithm(None,  # no device given
                                data=data,
                                instruments={},
                                parameters=params)

