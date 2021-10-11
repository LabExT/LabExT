#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

import numpy as np

from LabExT.Instruments.InstrumentAPI import Instrument, InstrumentException


class OpticalSpectrumAnalyzerAQ6370C(Instrument):
    """
    ## OpticalSpectrumAnalyzerAQ6370C

    This class provides an interface to a Yokogawa AQ6370C optical spectrum analyzer. See the following two links for
    the users and programmers guide:

    * [User Manual](https://cdn.tmi.yokogawa.com/IMAQ6370C-01EN.pdf)
    * [Programmer / Remote Control Manual](https://cdn.tmi.yokogawa.com/1/6057/files/IMAQ6370C-17EN.pdf)

    #### Properties

    handbook page refers to: Yokogawa AQ6370C Remote Control Manual (IMAQ6370C-17EN.pdf)

    | property type    | datatype | read/write | page in handbook | unit | description                                                       |
    |------------------|----------|------------|------------------|------|-------------------------------------------------------------------|
    | startwavelength  | float    | rw         | 7-88             | nm   | Sets/queries the measurement start wavelength.                    |
    | stopwavelength   | float    | rw         | 7-88             | nm   | Sets/queries the measurement stop wavelength.                     |
    | centerwavelength | float    | rw         | 7-87             | nm   | Sets/queries the measurement center wavelength.                   |
    | spam             | float    | rw         | 7-87             | nm   | Sets/queries the measurement span.                                |
    | sweepresolution  | float    | rw         | 7-85             | nm   | Sets/queries the measurement resolution (between 0.02nm and 2nm). |
    | n_points         | int      | rw         | 7-86             |      | Sets/queries the number of samples measured per sweep.            |
    | sens_mode        | str      | r          | 7-85             |      | Queries the sensitivity setting of the OSA, see below.            |

    The sensitivity modes is any of: 'NHLD', 'NAUT', 'MID', 'HIGH1', 'HIGH2', 'HIGH3', 'NORM'.

    #### Methods
    * **run**: triggers a new measurement and waits until the sweep is over
    * **stop**: stops sweeping
    * **get_data**: downloads the wavelength and power data of the last measurement

    """

    ignored_SCPI_error_numbers = [0, 2]

    def __init__(self, *args, **kwargs):
        # call Instrument constructor, creates VISA instrument
        super().__init__(*args, **kwargs)

        self.sens_modes = ['NHLD', 'NAUT', 'MID', 'HIGH1', 'HIGH2', 'HIGH3', 'NORM']
        self._sweep_modes = ['SING', 'REP', 'AUTO', 'SEGM']
        self._traces = ['TRA', 'TRB', 'TRC', 'TRD', 'TRE', 'TRF', 'TRG']

        self._net_timeout_ms = kwargs.get("net_timeout_ms", 30000)

        self.networked_instrument_properties.extend([
            'startwavelength',
            'stopwavelength',
            'centerwavelength',
            'sweepresolution',
            'n_points',
            'sens_mode',
            '_sweep_mode',
            '_active_trace'
        ])

    def open(self):
        """
        Open the connection to the instrument. Automatically re-uses any old connection if it is already open.

        :return: None
        """
        super().open()

        self._inst.read_termination = '\r\n'

        authentication = self._inst.query('open "anonymous"')
        ready = self._inst.query(" ")

        if authentication != 'AUTHENTICATE CRAM-MD5.' or ready != 'ready':
            raise InstrumentException('Authentication failed')

    #
    # run / stop / get data
    #

    def run(self, measurement_type='single'):
        """
        Starts a measurement and returns the currently active trace (between 1 and 7)
        Valid Types are: "singe" (default), "auto", "repeat".
        :return: active trace number
        """
        self.logger.info('Starting {type} sweep'.format(type=measurement_type))

        if measurement_type.lower() == 'single':
            # set sens mode
            # self.command(':SENS:SENS NORM')
            self._sweep_mode = 'SING'
            self.clear()
            self.write(':INIT')

            # Wait for sweep to finish
            operation_event = 0
            while not (operation_event & 0b1):
                time.sleep(1)
                operation_event = int(self.query(':STAT:OPER:EVEN?'))
                self.logger.info('Waiting for OSA to finish sweep...')

        elif measurement_type.lower() == 'auto':
            raise NotImplementedError('The {type} sweep type is not implemented yet'.format(type=measurement_type))
        elif measurement_type.lower() == 'repeat':
            raise NotImplementedError('The {type} sweep type is not implemented yet'.format(type=measurement_type))
        else:
            raise ValueError('Invalid sweep type given: {type}'.format(type=measurement_type))

        self.logger.info('OSA Sweep finished')

        trace_text = self._active_trace
        return self._traces.index(trace_text) + 1

    def stop(self):
        """
        Stops a measurement
        """
        self.command(':ABOR')

    @property
    def _active_trace(self):
        """
        Returns the currently active trace
        :return: string active trace
        """
        r = self.request(':TRAC:ACT?')
        return r

    @_active_trace.setter
    def _active_trace(self, act_trace):
        """
        Sets the active trace, displays it and enables recording to it.
        :param act_trace: string trace
        :return:
        """
        if act_trace not in self._traces:
            raise ValueError('Invalid trace given.')
        # enable writing and display for currently selected trace
        self.command(':TRAC:ATTR:' + str(act_trace) + ' WRITE')
        self.command(':TRAC:STATE:' + str(act_trace) + ' ON')
        # fix all other _traces to not be written to
        for fix_trace in self._traces:
            if act_trace == fix_trace:
                continue
            self.command(':TRAC:ATTR:' + str(fix_trace) + ' FIX')
        # set active trace, must be last command given
        self.command(':TRAC:ACT ' + str(act_trace))

    def get_data(self):
        """
        Get the spectrum data of the measurement. Units depend on the setting on the instrument.
        :return: 2D list with [X-axis Data, Y-Axis Data]
        """
        # Make sure the correct data format is used
        # set data format to ascii
        self.command('FORMAT:DATA ASCII')
        act_trace = self._active_trace

        wavelength_samples = self.query_ascii_values(':TRAC:DATA:X? {trace}'.format(
            trace=act_trace),
            container=np.ndarray) * 1e9 # data is returned in unit [m], we want it in [nm]
        power_samples = self.query_ascii_values(':TRAC:DATA:Y? {trace}'.format(
            trace=act_trace),
            container=list)

        return [wavelength_samples.tolist(), power_samples]

    #
    # wavelength properties
    #

    @property
    def startwavelength(self):
        """
        Returns the start wavelength of the currently set scan window
        :return: start wavelength in nm
        """
        return float(self.request(':SENS:WAV:STAR?')) * 1e9

    @startwavelength.setter
    def startwavelength(self, start_wavelength_nm):
        """
        Set the start wavelength of the scan window
        :param start_wavelength_nm: start wavelength in nm
        """
        self.command(':SENS:WAV:STAR {start:0.3f}nm'.format(start=start_wavelength_nm))

    @property
    def stopwavelength(self):
        """
        Returns the stop wavelength of the currently set scan window
        :return: stop wavelength in nm
        """
        return float(self.request(':SENS:WAV:STOP?')) * 1e9

    @stopwavelength.setter
    def stopwavelength(self, stop_wavelength_nm):
        """
        Set the stop wavelength of the scan window
        :param stop_wavelength_nm: stop wavelength in nm
        """
        self.command(':SENS:WAV:STOP {stop:0.3f}nm'.format(stop=stop_wavelength_nm))

    @property
    def centerwavelength(self):
        """
        Returns current center wavelength [nm].
        :return: center wavelength in nm
        """
        return float(self.request(':SENS:WAV:CENT?')) * 1e9

    @centerwavelength.setter
    def centerwavelength(self, centerwavelength_nm):
        """
        Sets center wavelength
        :param centerwavelength_nm: wavelength in nm
        """
        if not 600 <= centerwavelength_nm <= 1700:
            raise ValueError('Center wavelength is out of range. Must be between 600 nm and 1700 nm.')

        self.command(':SENS:WAV:CENT {center:0.3f}nm'.format(center=centerwavelength_nm))

    @property
    def span(self):
        """
        Returns current span
        :return: span in nm
        """
        return float(self.request(':SENS:WAV:SPAN?')) * 1e9

    @span.setter
    def span(self, span_nm):
        """
        Sets span
        :param span_nm: span in nm
        """
        self.command(':SENS:WAV:SPAN {span:0.3f}nm'.format(span=span_nm))

    #
    # resolution and sensitivity
    #

    @property
    def sweepresolution(self):
        """
        Returns current resolution
        :return: resolution in nm
        """
        return float(self.request(':SENS:BAND:RES?')) * 1e9

    @sweepresolution.setter
    def sweepresolution(self, resolution_nm):
        """
        Sets resolution
        :param resolution_nm: resolution in nm
        """
        if not 0.02 <= resolution_nm <= 2:
            raise ValueError('Resolution must be between 0.02 nm and 2 nm.')
        self.command(':SENS:BAND:RES {:0.3f}nm'.format(resolution_nm))

    @property
    def _sweep_mode(self):
        """
        Returns current sweep mode
        :return: string sweep mode
        """
        return self._sweep_modes[int(self.request(':INIT:SMODE?')) - 1]

    @_sweep_mode.setter
    def _sweep_mode(self, _sweep_mode):
        """
        Set sweep mode
        :param _sweep_mode: string
        :return:
        """
        if _sweep_mode not in self._sweep_modes:
            raise ValueError('Invalid sweep mode given: ' + str(_sweep_mode))
        self.command(':INIT:SMODE ' + str(_sweep_mode))

    @property
    def sens_mode(self):
        """
        Returns current sensitivity mode
        :return: string sensitivity mode
        """
        return self.sens_modes[int(self.request(':SENS:SENS?'))]

    @property
    def n_points(self):
        """
        Get the number of points for the measurement
        """
        return int(self.query(":SENSe:SWEep:POINTS?"))

    @n_points.setter
    def n_points(self, n_points):
        """
        Set the number of points for the measurement
        """
        self.command(":SENSe:SWEep:POINTS " + str(n_points))

