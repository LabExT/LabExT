#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import numpy as np

from LabExT.Instruments.InstrumentAPI import Instrument, InstrumentException


class PowerMeterGenericKeysight(Instrument):
    """
    ## LaserMainframeKeysight

    This class provides an interface to Keysight optical power meters, e.g. modules in a 816x mainframes and the N77xx
    multiport power meters. Aside from the basic instrument properties, methods for triggered measurements are
    included as used for swept wavelength measurements, see Keysight App Note 5992-1125EN.pdf.

    #### Properties

    handbook page refers to: Keysight N77xx Series Programming Guide (9018-02434.pdf)

    | property type | datatype | read/write | page in handbook | unit | description                                                     |
    |---------------|----------|------------|------------------|------|-----------------------------------------------------------------|
    | wavelength    | float    | rw         | 138/139          | nm   | sets sensor wavelength                                          |
    | unit          | str      | rw         | 138              |      | sets the unit for power read accesses                           |
    | range         | float    | rw         | 134              | dBm  | set the range of the power sensor (the max expected opt. power) |
    | autoranging   | bool     | rw         | 133              |      | enable or disable automatic adaption of the range setting       |
    | averagetime   | float    | rw         | 133              | s    | averaging time per measurement                                  |

    #### Methods

    * **logging_setup**: configure the power meter for a series of logged measurements, setup triggering settings
    * **logging_start**: start the logging function, starts immediately or next trigger depending on configuration
    * **logging_stop**: stop any logging
    * **logging_busy**: query if the logging function is running
    * **logging_get_data**: after logging stopped, fetch the whole data of the last logged series

    """

    ignored_SCPI_error_numbers = [0, -410, -420, -231, -213, -261]

    def __init__(self, *args, **kwargs):
        """
        We let the power meter to keep track internally of the last set average time.
        """
        super().__init__(*args, **kwargs)

        # keep track of last set average time
        self._last_set_atime_s = 0.2  # Keysight default value

        # safe instrument specific settings
        self._net_timeout_ms = kwargs.get("net_timeout_ms", 10000)
        self._net_chunk_size = kwargs.get("net_chunk_size_B", 1024)
        self._always_returns_sweep_in_Watt = kwargs.get("always_returns_sweep_in_Watt", True)

        # instrument parameter on network, add to this list all object properties which should get freshly fetched
        # and added to self.instrument_paramters on each get_instrument_parameter() call
        self.networked_instrument_properties.extend([
            'wavelength',
            'unit',
            'range',
            'autoranging',
            'averagetime'
        ])

    def open(self):
        super().open()
        self._inst.timeout = self._net_timeout_ms
        self._inst.chunk_size = self._net_chunk_size

    #
    # logging functions
    #

    def logging_setup(self, n_measurement_points=10000, triggered=False, trigger_each_meas_separately=True):
        """
        Use this function to setup automatic logging of samples, 
        either based on external electrical trigger or on time interval (set by the average time property)

        If the laser is in the same mainframe as the power meter, the internal loop triggering setup must be setup
        from the laser class!

        See Keysight Application Note 5992-1125EN.pdf
        """
        # setup triggering
        if triggered:
            if trigger_each_meas_separately:
                # every external trigger starts a new power measurement until all points are measured
                self.command_channel('trig', ':inp sme')
            else:
                # the external trigger starts the whole logging function and it continues w/o further trigger
                self.command_channel('trig', ':inp cme')
        else:
            # we let the PM run in free-running mode
            self.command_channel('trig', ':inp ign')
        # disable any trigger outputs of PM (needed e.g. in case laser an PM are in same mainframe)
        self.command_channel('trig', ':outp dis')
        self.command_channel('sens', ':func:par:logg {:d},{:.6f}s'.format(n_measurement_points, self._last_set_atime_s))

    def logging_start(self):
        """
        Commands the logging function to start.

        Do NOT set any instrument properties after this command as it stops the logging again.
        """
        self.write_channel('sens', ':func:stat logg,star')

    def logging_stop(self):
        """
        Stops any logging function.
        """
        self.write_channel('sens', ':func:stat logg,stop')

    def logging_busy(self):
        """
        Returns True if the logging is busy, False if logging is not busy.
        """
        resp = self.query_channel('sens', ':func:stat?').lower()
        if 'none' in resp:
            # if no function is selected, the progress indicator is irrelevant
            return False
        elif 'progress' in resp:
            return True
        else:
            return False

    def logging_get_data(self, trigger_cleanup=True):
        """
        Reads the logging data from the power meter and returns a numpy array
        of the logged power values.

        Attention! Some of the old Agilent/Keysight mainframe modules always use Watts as units!

        Returns the values as a numpy array.
        """
        self.write_channel('sens', ':func:res?')
        # pyvisa offers this function which takes care of all header stuff and binary conversion
        pwr_data = self._inst.read_binary_values(datatype='f',
                                                 is_big_endian=False,
                                                 container=np.array,
                                                 header_fmt='ieee')

        if trigger_cleanup:
            self.command_channel('trig', ':outp dis')
            self.command_channel('trig', ':inp ign')
            self.trigger(continuous=True)

        if self._always_returns_sweep_in_Watt:
            # if the attached power meter is one of the Agilent modules, it returns optical power
            # ALWAYS in watts :/ seriously Agilent?
            # if you subclass this, set self._always_returns_sweep_in_Watt in your __init__
            # according to your hardware
            if 'dbm' in self.unit.lower():
                pwr_data = 10 * np.log10(pwr_data * 1e3)

        return pwr_data

    #
    # standard properties of power meter channels
    #

    @property
    def wavelength(self):
        """
        Read the wavelength calibration setting.

        :return: the current wavelength setting [nm]
        """
        return float(self.request_channel(':SENS', ':POW:WAV?').strip()) * 1e9

    @wavelength.setter
    def wavelength(self, wl_nm):
        """
        Set the wavelength calibration setting.

        :param wl_nm: desired vacuum wavelength to calibrate for [nm]
        :return: None
        """
        self.command_channel(':SENS', ':POW:WAV {:f} nm'.format(wl_nm))

    @property
    def unit(self):
        """
        Query the physical unit of the measured power.

        :return: a string, either 'dBm' or 'Watt'
        """
        r = int(self.request_channel(':SENS', ':POW:UNIT?'))
        return ['dBm', 'Watt'][r]

    @unit.setter
    def unit(self, pu):
        """
        Set the physical unit of measured power. Choose between 'dBm' and 'Watt'

        :param pu: a string, either 'dBm' or 'Watt'
        """
        if 'dbm' in pu.lower():
            self.command_channel(':SENS', ':POW:UNIT 0')
        elif 'watt' in pu.lower():
            self.command_channel(':SENS', ':POW:UNIT 1')
        else:
            raise InstrumentException('Unknown unit: {}, use dBm or Watt')

    @property
    def range(self):
        """
        Query the range (i.e. sensitivity) setting.

        :return: a float number, specifying the currently set sensitivity
        """
        return float(self.request_channel(':SENS', ':POW:RANG?').strip())

    @range.setter
    def range(self, range_dBm):
        """
        Set the range (i.e. sensitivity) setting.

        :param range_dBm: a float number of the desired sensitivity in dBm, or 'auto'
        """
        if 'auto' in str(range_dBm).lower():
            self.command_channel(':SENS', ':POW:RANG:AUTO 1')
        else:
            self.command_channel(':SENS', ':POW:RANG:AUTO 0')
            self.command_channel(':SENS', ':POW:RANG {:f}'.format(range_dBm))

    @property
    def autoranging(self):
        """
        Query if autoranging is on.

        :return: a boolean, True if autoranging is on, False if off
        """
        resp = self.request_channel(':SENS', ':POW:RANG:AUTO?').strip().lower()
        if '1' in resp or 'on' in resp:
            return True
        elif '0' in resp or 'off' in resp:
            return False
        else:
            raise InstrumentException('Power meter returned something not understandable: ' + str(resp))

    @autoranging.setter
    def autoranging(self, autorange):
        """
        Enable or disable automatic range finding for power meters.
        """
        if autorange:
            self.command_channel(':SENS', ':POW:RANG:AUTO 1')
        else:
            self.command_channel(':SENS', ':POW:RANG:AUTO 0')

    @property
    def averagetime(self):
        """
        Query the current averaging time setting.

        :return: a float number, specifying the current averaging time [s]
        """
        self._last_set_atime_s = float(self.request_channel(':SENS', ':POW:ATIME?').strip())
        return self._last_set_atime_s

    @averagetime.setter
    def averagetime(self, atime_s):
        """
        Set the averaging time setting.

        :param atime_s: a float, specifying the new averageing time [s]
        :return: None
        """
        self.command_channel(':SENS', ':POW:ATIME {:f} s'.format(atime_s))
        self._last_set_atime_s = atime_s

    @property
    def power(self):
        """
        Read the optical power currently measured. This call triggers the power meter.

        :return: the optical power, measured right now
        """
        # we must adapt the network timeout to at least be larger than the aperture time of the power meter
        if self._inst.timeout < self._last_set_atime_s * 1.1:
            self.logger.warning("Resetting connection timeout to allow at least one average-time period to pass.")
            self._inst.timeout = self._last_set_atime_s * 1.1

        r = float(self.query_channel(':READ', ':POW?').strip())
        if r > 1e20:
            r = float('inf')
            self.logger.warning('OPM: Sensitivity is too low.')
        return r

    #
    # manual triggering
    #

    def trigger(self, continuous=None):
        """
        Set the trigger of the power meter
        :param continuous: None for immediate trigger, True for continuous, False for stopping acquisition.
        """
        if continuous is None:
            # send immediate trigger
            self.write_channel(':INIT', ':IMM')
        elif continuous:
            self.command_channel(':INIT', ':CONT ON')
        else:
            self.command_channel(':INIT', ':CONT OFF')

    def fetch_power(self):
        """
        Read the power which was measured on the last trigger.
        """
        r = float(self.query_channel(':FETCH', ':POW?').strip())
        if r > 1e20:
            r = float('nan')
            self.logger.warning('OPM: Sensitivity is too low.')
        return r
