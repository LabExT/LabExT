#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time
from math import ceil, floor, log10

import numpy as np

from LabExT.Instruments.InstrumentAPI import Instrument, InstrumentException


class LaserMainframeKeysight(Instrument):
    """
    ## LaserMainframeKeysight

    This class provides an interface to a Keysight 816x laser mainframe. Aside from the basic instrument properties,
    methods for swept wavelength measurements are included, see Keysight App Note 5992-1125EN.pdf.

    #### Properties

    handbook page refers to: Keysight 8164A/B Lightwave Measurement System Programming Guide (9018-01647.pdf)

    | property type | datatype | read/write | page in handbook | unit                       | description                                                     |
    |---------------|----------|------------|------------------|----------------------------|-----------------------------------------------------------------|
    | wavelength    | float    | rw         | 154/155          | nm                         | laser output wavelength                                         |
    | power         | float    | rw         | 148/149          | write: dBm; read: dBm or W | laser output power, read access units is set with unit property |
    | unit          | str      | rw         | 151/152          |                            | sets the unit for power read accesses                           |
    | enable        | bool     | rw         | 151              |                            | enable or disable laser output                                  |
    | min_lambda    | float    | r          | 175              | nm                         | minimum wavelength for sweeps                                   |
    | max_lambda    | float    | r          | 176              | nm                         | maximum wavelength for sweeps                                   |

    #### Methods

    * **sweep_wl_setup**: configure the laser for a swept wavelength measurement, needs sweep parameters!
    * **sweep_wl_get_n_points**: after sweep config, how many points will be in a sweep?
    * **sweep_wl_start**: tell the laser to start sweeping
    * **sweep_wl_busy**: query if the laser is busy sweeping
    * **sweep_wl_get_data**: after sweeping done, query the at which trigger outputs were generated

    """

    ignored_SCPI_error_numbers = [0, -420, -231, -261]

    def __init__(self, *args, **kwargs):
        # call Instrument constructor, creates VISA instrument
        super().__init__(*args, **kwargs)

        # due to old PMs being slow in sending data, we set a high network timeout value
        self._net_timeout_ms = kwargs.get("net_timeout_ms", 10000)
        self._net_chunk_size = kwargs.get("net_chunk_size_B", 1024)

        # instrument parameter on network, add to this list all object properties which should get freshly fetched
        # and added to self.instrument_paramters on each get_instrument_parameter() call
        self.networked_instrument_properties.extend([
            'wavelength',
            'power',
            'unit',
            'min_lambda',
            'max_lambda'
        ])

        self.sweep_configured = False
        self.send_hardware_trigger = False
        self.trigger_at_open = ''  # saves state of triggering upon connecting so we can restore on disconnect

    def open(self):
        """
        Open connection to instrument. We automatically unlock with the pin.
        Saves the current trigger setting, because it is changed by self.sweep_wl_setup

        Careful: needs to lock instrument-local thread-lock for laser unlocking purposes.
        """
        super().open()
        self._inst.timeout = self._net_timeout_ms
        self._inst.chunk_size = self._net_chunk_size
        with self.thread_lock:
            self.unlock_laser()
            self.trigger_at_open = self.query("trig:conf?")

    def close(self):
        if self._open:
            self.command("trig:conf " + self.trigger_at_open)
        super().close()

    def __enter__(self):
        """
        Makes this class a python context manager. Use the with statement to
        automatically shut off the laser if an error occurs in your code.
        """
        self.enable = True

    def __exit__(self, exc_type, exc_value, traceback):
        """ counterpart to the __enter__() function """
        self.enable = False

    #
    #   mainframe options
    #

    def unlock_laser(self, pin="1234"):
        """
        set lock for the instrument

        :param pin: string of the pin to unlock the device
        """
        self.command('LOCK 0,{:s}'.format(pin))

    def idn(self):
        """
        we extend the IDN to also get the chosen slot identification string
        """
        mf_idn = super().idn()
        if self.channel is not None:
            slot_idn = self.query_channel("slot", ":idn?").strip()
            return "Mainframe: " + str(mf_idn) + " Slot" + str(self.channel) + ": " + str(slot_idn)
        else:
            return mf_idn

    @property
    def min_lambda(self):
        """
        :return: minimum possible laser wavelength (for sweeps) in [nm]
        """
        min_lambda_possible = float(self.request_channel("sour", ":wav:swe:start? min"))
        # round the minimal possible wavelength to next 1nm
        min_lambda_possible = min_lambda_possible + 1e-9
        return ceil(min_lambda_possible * 1e9)

    @property
    def max_lambda(self):
        """
        :return: maximum possible laser wavelength (for sweeps) in [nm]
        """
        max_lambda_possible = float(self.request_channel("sour", ":wav:swe:stop? max"))
        # round the maximum possible wavelength to next 1nm
        max_lambda_possible = max_lambda_possible - 1e-9
        return floor(max_lambda_possible * 1e9)

    #
    #   swept wavelength settings
    #

    def sweep_wl_setup(self, start_nm, stop_nm, step_pm, sweep_speed_nm_per_s=40, send_hardware_trigger=True):
        """
        Setup the laser for a continuous wavelength sweep with recording of the wavelengths.

        Note that there are hardware limits imposed, it is recommended to read the used Laser's manual.
        * Agilent 8163/8164/8166: max 40 kHz trigger freq, max 10001 points saved

        See Keysight Application Note 5992-1125EN.pdf

        :param start_nm: start wavelength in [nm]
        :param stop_nm: stop wavelength in [nm]
        :param step_pm: step size in [pm]
        :param sweep_speed_nm_per_s: (default 40nm/s) sweep speed in [nm/s]
        :param send_hardware_trigger: (default True) configure the laser to
        """
        self.send_hardware_trigger = send_hardware_trigger

        self.command_channel("trig", ":inp sws")  # tell sweep to wait on software trigger
        if send_hardware_trigger:
            self.command("trig:conf loop")  # instruct mainframe to loop triggers internally to PMs
            self.command_channel("trig", ":outp stf")  # give trigger on WL step finished
        else:
            self.command("trig:conf def")
            self.command_channel("trig", ":outp dis")  # give trigger on WL step finished

        # setup sweep commands
        self.command_channel('sour', ':wav:swe:mode cont')
        self.command_channel('sour', ':wav:swe:star ' + str(start_nm) + 'nm')
        self.command_channel('sour', ':wav:swe:stop ' + str(stop_nm) + 'nm')
        self.command_channel('sour', ':wav:swe:step ' + str(step_pm) + 'pm')
        self.command_channel('sour', ':wav:swe:spe ' + str(sweep_speed_nm_per_s) + 'nm/s')
        if send_hardware_trigger:
            self.command_channel('sour', ':wav:swe:llog 1')
        else:
            self.command_channel('sour', ':wav:swe:llog 0')

        # check if sweep parameters are consistent
        r = self.request_channel('sour', ':wav:swe:chec?')
        if r[0:4] != '0,OK':
            raise InstrumentException('Sweep parameters incorrectly set! Error message: ' + str(r))

        # check if chosen laser power can be hold over whole sweeping range
        pmax_W = float(self.request_channel("sour", ":wav:swe:pmax? " + str(start_nm) + "nm," + str(stop_nm) + "nm"))
        pmax_dBm = 10 * log10(pmax_W * 1.e3)
        if "dBm" in self.unit:
            instr_p_dBm = self.power
        else:
            instr_p_dBm = 10 * log10(self.power * 1.e3)
        if instr_p_dBm > pmax_dBm:
            raise InstrumentException(("Laser power larger than maximum allowed over sweeping range! " +
                                       "Maximum in sweep range from {:.2f} nm to {:.2f} nm is {:.2f} dBm and the " +
                                       "laser is set to {:.2f} dBm.").format(
                start_nm, stop_nm, pmax_dBm, instr_p_dBm
            ))
        # set class internal flag
        self.sweep_configured = True

    def sweep_wl_get_n_points(self):
        """
        Returns the number of configured sweep points. Useful to tell the PM how many points to logg.
        """
        if not self.sweep_configured:
            return 0
        else:
            return int(self.request_channel("sour", ":wav:swe:exp?"))

    def sweep_wl_get_total_time(self):
        raise NotImplementedError

    def sweep_wl_start(self):
        """
        Starts the sweeping function immediately.

        Raises exception if sweep cannot be started within given network timeout time.
        """
        if not self.sweep_configured:
            raise InstrumentException("Cannot start sweep if sweep parameters were not configured yet.")
        self.command_channel("sour", ":wav:swe 1")
        start_time = time.time()
        while time.time() - start_time < (self._net_timeout_ms / 1000):
            flag = int(self.query_channel("sour", ":wav:swe:flag?"))
            # wait until flag is uneven (see p169 of 8163 programming manual)
            if flag % 2 == 1:
                break
        else:
            raise InstrumentException("Sweep function never waited for trigger within set network timeout.")
        # start sweep by sending software trigger
        self.command_channel("sour", ":wav:swe:soft")

    def sweep_wl_busy(self):
        """
        Returns True if the sweeping is in progress, False otherwise.
        """
        resp = int(self.query_channel("sour", ":wav:swe?"))
        if resp == 0:
            return False  # sweep done when flag is 0
        else:
            return True  # otherwise

    def sweep_wl_get_data(self, trigger_cleanup=True, **kwargs):
        """
        Reads the wavelengths vector generated during the sweep. Only really useful if used with sending
        hardware triggers.

        Returns the values as a numpy array of 64-bit floats.
        """
        self.write_channel("sour", ":read:data? llog")
        # pyvisa offers this function which takes care of all header stuff and binary conversion
        wl_data = self._inst.read_binary_values(datatype='d',
                                                is_big_endian=False,
                                                container=np.array,
                                                header_fmt='ieee')

        if trigger_cleanup:
            self.command_channel("trig", ":inp ign")
            self.command_channel("trig", ":outp dis")
            self.command("trig:conf def")

        return wl_data * 1e9  # convert m to nm

    #
    #   standard properties
    #

    @property
    def wavelength(self):
        """
        Get the wavelength of the laser.
        :return: a float number, the wavelength setting of the laser [nm]
        """
        return float(self.request_channel('sour', ':wav?').strip()) * 1e9  # instr has units of [m]

    @wavelength.setter
    def wavelength(self, wavelength_nm):
        """
        Set the wavelength of the laser.

        :param wavelength_nm: the desired wavelength [nm]
        :return: None
        """
        self.command_channel('sour', ':wav ' + str(wavelength_nm) + 'nm')

    @property
    def power(self):
        """
        Get the set output power of the laser. Query .unit to find the unit.
        """
        return float(self.request_channel('sour', ':pow?').strip())

    @power.setter
    def power(self, power_dBm):
        """
        Set the laser output power.
        """
        self.command_channel('sour', ':pow ' + str(power_dBm) + 'dBm')

    @property
    def unit(self):
        """
        Query the physical unit of the laser power.

        :return: a string, either 'dBm' or 'Watt'
        """
        r = int(self.request_channel('SOUR', ':POW:UNIT?'))
        return ['dBm', 'Watt'][r]

    @unit.setter
    def unit(self, pu):
        """
        Set the physical unit of laser power. Choose between 'dBm' and 'Watt'

        :param pu: a string, either 'dBm' or 'Watt'
        """
        if 'dbm' in pu.lower():
            self.command_channel('SOUR', ':POW:UNIT 0')
        elif 'watt' in pu.lower():
            self.command_channel('SOUR', ':POW:UNIT 1')
        else:
            raise InstrumentException('Unknown unit: {}, use dBm or Watt')

    @property
    def enable(self):
        """
        Return if the laser is on (True) or off (False)

        :return: a boolean
        """
        r = self.request_channel('sour', ':pow:stat?')
        if "1" in r.lower():
            return True
        else:
            return False

    @enable.setter
    def enable(self, b):
        """
        Set the laser on state.

        :param b: something boolean, if True, the laser switches on, False for off.
        :return: None
        """
        if b:
            self.command_channel('sour', ':pow:stat 1')
            time.sleep(1)
        else:
            self.command_channel('sour', ':pow:stat 0')
