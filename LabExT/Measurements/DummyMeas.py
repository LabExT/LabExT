#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from time import sleep

import numpy as np

from LabExT.Measurements.MeasAPI import *
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.ViewModel.Utilities.ObservableList import ObservableList


class DummyMeas(Measurement):
    """
    ## DummyMeas
    A very simple dummy measurement, mainly geared for software testing. Generates a fixed amount of samples drawn
    from the normal distribution with a settable std. deviation and mean. This can be useful to generate some
    measured data for debugging other software parts which rely on that.

    #### example setup
    ```
    no setup needed, only software
    ```

    #### parameters
    * **number of points**: How many samples should be generated?
    * **total measurement time**: How much time should the sample generation take? Useful for e.g. debugging
     live plotting.
    * **mean**: The mean of the normal distributed, generated samples.
    * **std. deviation**: The standard deviation of the normal distributed, generated samples.
    * **simulate measurement error**: If set, will raise a generic Exception to test how the GUI handles error.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'DummyMeas'
        self.settings_path = 'DummyMeas_settings.json'

        self.plot = None

        self.parameters = DummyMeas.get_default_parameter()
        self.wanted_instruments = DummyMeas.get_wanted_instrument()

    @classmethod
    def get_default_parameter(cls):
        return {
            'number of points': MeasParamInt(value=100),
            'total measurement time': MeasParamFloat(value=2.0),
            'mean': MeasParamFloat(value=0.0),
            'std. deviation': MeasParamFloat(value=1.0),
            'simulate measurement error': MeasParamBool(value=False)
        }

    @classmethod
    def get_wanted_instrument(cls):
        return []

    def algorithm(self, device, data, instruments, parameters):

        # get the parameters
        n_points = parameters.get('number of points').value
        tot_time = parameters.get('total measurement time').value
        ptime = tot_time / n_points
        y_mean = parameters.get('mean').value
        y_stddev = parameters.get('std. deviation').value
        raise_error = parameters['simulate measurement error'].value

        # write the measurement parameters into the measurement settings
        for pname, pparam in parameters.items():
            data['measurement settings'][pname] = pparam.as_dict()

        # start live plottings
        if self._experiment is not None:
            self.plot = PlotData(ObservableList(), ObservableList())
            self._experiment.live_plot_collection.append(self.plot)

        # provoke error if set in parameters
        if raise_error:
            raise Exception("DummyMeas simulated measurement exception.")

        # generate some dummy data
        xvec = np.arange(0, n_points)
        yvec = y_stddev * np.random.randn(n_points) + y_mean

        if self._experiment is not None:
            # play to live plot
            for x, y in zip(xvec, yvec):
                self.plot.x.append(x)
                self.plot.y.append(y)
                sleep(ptime)
        else:
            sleep(tot_time)

        # convert numpy float32/float64 to python float
        data['values']['point indices'] = [x.item() for x in xvec]
        data['values']['point values'] = [y.item() for y in yvec]

        # sanity check if data contains all necessary keys
        self._check_data(data)

        # remove live plot again from experiment
        if self._experiment is not None:
            self._experiment.live_plot_collection.remove(self.plot)

        return data
