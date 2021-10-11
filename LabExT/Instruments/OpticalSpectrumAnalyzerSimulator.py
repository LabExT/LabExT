#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import numpy as np

from LabExT.Instruments.DummyInstrument import DummyInstrument


class OpticalSpectrumAnalyzerSimulator(DummyInstrument):
    """
    ## OpticalSpectrumAnalyzerSimulator

    Software-only simulator of a real optical signal analyzer. Offers the same properties as
    [OpticalSpectrumAnalyzerAQ6370C](./OpticalSpectrumAnalyzerAQ6370C.md) class but
    mocks everything in software.

    Use this instrument to test your measurements requiring an optical spectrum analyzer.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Yokagawa properties
        self.sens_modes = ["NHLD", "NAUT", "MID", "HIGH1", "HIGH2", "HIGH3", "NORM"]
        self.sweep_modes = ["SING", "REP", "AUTO", "SEGM"]
        self.traces = ["TRA", "TRB", "TRC", "TRD", "TRE", "TRF", "TRG"]

        self._instrument_property_startwavelength = 1529.0
        self._instrument_property_stopwavelength = 1620.0
        self._instrument_property_span = 91.0
        self._instrument_property_centerwavelength = (1620.0 + 1529.0) / 2.0
        self._instrument_property_sweepresolution = 0.02
        self._instrument_property_npoints = int(91.0 / 0.02)
        self._instrument_property_autocenter = False
        self._instrument_property_act_trace = "TRA"
        self._instrument_property_sens_mode = "NHLD"
        self._instrument_property_sweep_mode = "SING"
        self._net_timeout_ms = 30000

    def idn(self):
        return "OpticalSpectrumAnalyzerSimulator class for SW testing."

    #
    #
    # Yokogawa/APEX common methods
    #
    #

    def run(self, measurement_type="single"):
        """
        Fakes the execution of an OSA run.
        Returns the trace of the measurement, which for the simulator is always set to 1.
        """
        return 1

    def stop(self):
        """
        Stops a fake measurement
        """
        pass

    def get_data(self, unit_x="nm", scale_y="log", trace_number=1):
        """
        Get the spectrum data of the fake measurement
        returns a 2D list [X-axis Data, Y-Axis Data]
        unit_x is a string which can be :
            - "nm" : get the X-Axis Data in nm (default)
            - "GHz": get the X-Axis Data in GHz
        scale_y is a string which can be :
            - "log" : get the Y-Axis Data in dBm (default)
            - "lin" : get the Y-Axis Data in mW
        TraceNumber is an integer between 1 (default) and 6
        """
        x_data = np.linspace(self._instrument_property_startwavelength,
                             self._instrument_property_stopwavelength,
                             self._instrument_property_npoints,
                             endpoint=True)
        y_data = 5 * np.random.random(len(x_data)) - 40.0
        y_data = y_data.tolist()

        if scale_y.lower() == "lin":
            y_data = np.exp(y_data / 20.0)
        elif scale_y.lower() == "log":
            pass
        else:
            raise ValueError("Invalid y axis scaling given. Scaling must be log or lin.")

        if unit_x.lower() == "ghz":
            x_data = 3e8 / x_data
        elif unit_x.lower() == "nm":
            pass
        else:
            raise ValueError("Invalid x-axis unit given. Unit must be nm or GHz.")
        x_data = x_data.tolist()

        return x_data, y_data

    @property
    def startwavelength(self):
        """
        Get the start wavelength of the measurement span of the fake OSA.
        Wavelength is expressed in nm
        """
        return self._instrument_property_startwavelength

    @startwavelength.setter
    def startwavelength(self, wavelength):
        """
        Set the start wavelength of the measurement span of the fake OSA.
        Wavelength is expressed in nm
        """
        self._instrument_property_startwavelength = wavelength
        self._instrument_property_span = self._instrument_property_stopwavelength - wavelength

    @property
    def stopwavelength(self):
        """
        Get the start wavelength of the measurement span of the fake OSA.
        Wavelength is expressed in nm
        """
        return self._instrument_property_stopwavelength

    @stopwavelength.setter
    def stopwavelength(self, wavelength):
        """
        Set the start wavelength of the measurement span of the fake OSA.
        Wavelength is expressed in nm
        """
        self._instrument_property_stopwavelength = wavelength
        self._instrument_property_span = wavelength - self._instrument_property_startwavelength

    @property
    def centerwavelength(self):
        """
        Get the wavelength measurement center of the fake OSA.
        Center is expressed in nm
        """
        return self._instrument_property_centerwavelength

    @centerwavelength.setter
    def centerwavelength(self, center):
        """
        Set the wavelength measurement center of the fake OSA.
        Center is expressed in nm
        """
        self._instrument_property_centerwavelength = center
        self._instrument_property_startwavelength = center - self._instrument_property_span / 2.0
        self._instrument_property_stopwavelength = center + self._instrument_property_span / 2.0

    @property
    def span(self):
        """
        Get the wavelength measurement span of the fake OSA.
        Span is expressed in nm
        """
        return self._instrument_property_span

    @span.setter
    def span(self, span):
        """
        Set the wavelength measurement span of the fake OSA.
        Span is expressed in nm
        """
        self._instrument_property_span = span
        self._instrument_property_startwavelength = self._instrument_property_centerwavelength - span / 2.0
        self._instrument_property_stopwavelength = self._instrument_property_centerwavelength + span / 2.0

    @property
    def sweepresolution(self):
        """
        Returns the set sweep resolution of the fake OSA in [nm].
        :return resolution  [nm]
        """
        return self._instrument_property_sweepresolution

    @sweepresolution.setter
    def sweepresolution(self, resolution):
        """
        Set the sweep wavelength measurement resolution of the fake OSA.
        resolution: Resolution in GHz
        """
        self._instrument_property_sweepresolution = resolution

    #
    #
    # Yokogawa only methods
    #
    #

    @property
    def active_trace(self):
        """
        Yokagawa method.
        returns the active trace which on the fake OSA is always `TRA`.
        :return: string active trace
        """
        return 'TRA'

    @active_trace.setter
    def active_trace(self, act_trace):
        """
        Yokagawa method.
        Sets the active trace on the fake OSA.
        """
        if act_trace not in self.traces:
            raise ValueError('Invalid trace given.')
        self._instrument_property_act_trace = act_trace

    # missing:
    # @property
    # def data_format(self):

    # missing:
    # @data_format.setter
    # def data_format(self, data_format='ASCII'):

    @property
    def sens_mode(self):
        """
        Returns current sensitivity mode of the fake OSA.
        :return: string sensitivity mode
        """
        return self._instrument_property_sens_mode

    @sens_mode.setter
    def sens_mode(self, sens_mode):
        """
        Yokagawa method.
        Returns the current sensitivity mode of the fake OSA.
        :return: string sensitivity mode
        """
        if sens_mode not in self.sens_modes:
            raise ValueError('Invalid sense mode given: ' + str(sens_mode))
        self._instrument_property_sens_mode = sens_mode

    @property
    def sweep_mode(self):
        """
        Returns current sweep mode of the fake OSA
        :return: string sweep mode
        """
        return self._instrument_property_sweep_mode

    @sweep_mode.setter
    def sweep_mode(self, sweep_mode):
        """
        Set sweep mode at the fake OSA
        :param sweep_mode: string
        :return:
        """
        if sweep_mode not in self.sweep_modes:
            raise ValueError('Invalid sweep mode given: ' + str(sweep_mode))
        self._instrument_property_sweep_mode = sweep_mode

    # missing:
    # @property
    # def marker_search_mode(self):

    # missing:
    # @marker_search_mode.setter
    # def marker_search_mode(self, search_mode):

    # missing:
    # def find_peak(self, peak_type):

    # missing:
    # def find_next_peak(self, peak_type):

    #
    #
    # APEX only methods
    #
    #

    @property
    def n_points(self):
        """
        Get the number of points of the fake OSA for the measurement.
        """
        return self._instrument_property_npoints

    @n_points.setter
    def n_points(self, n_points):
        """
        Set the number of points of the fake OSA for the measurement
        """
        self._instrument_property_npoints = n_points

    @property
    def autocenter(self):
        """
        Returns whether the autocenter functionality is activated in the fake OSA.
        """
        return self._instrument_property_autocenter

    @autocenter.setter
    def autocenter(self, autocenter):
        """
        Activate or deactive the auto center feature of the fake OSA.
        autocenter: Boolean, True for activation
        """
        self._instrument_property_autocenter = autocenter

    @property
    def x_axis_unit(self):
        """
        Not defined by APEX
        """
        return None

    @x_axis_unit.setter
    def x_axis_unit(self, unit):
        """
        does nothing
        """
        pass

    @property
    def y_axis_unit(self):
        """
        Not defined by APEX
        """
        return None

    @y_axis_unit.setter
    def y_axis_unit(self, unit):
        """
        does nothing"
        """
        pass

    def find_peaks(self, threshold):
        """
        sets markers on peaks above threshold in mW or dBM (depending on y axis unit)
        """
        pass

    def get_peaks(self):
        return [], []
