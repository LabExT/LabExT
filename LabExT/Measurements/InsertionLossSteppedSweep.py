#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2024  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time
import numpy as np

from LabExT.Measurements.MeasAPI import *


class InsertionLossSteppedSweep(Measurement):
    """
    ## InsertionLossSteppedSweep

    This measurement uses a tunable laser source to make a spectral measurement by looping over the output signal
    wavelengths.  The optical power meter takes a measurement after a given stabilization time. The resulting arrays 
    of wavelength and detected signal samples provide a spectrum showing the wavelength dependence of the DUT.

    Currently this measurement supports Agilent/Keysight swept lasers (model numbers 816x, N777xC) and triggered power
    meters (model numbers 816x or N77xx).

    All triggers are sent by the computer and no trigger cables need to be connected

    #### laser parameters
    * **wavelength start**: starting wavelength of the laser sweep in [nm]
    * **wavelength stop**: stopping wavelength of the laser sweep in [nm]
    * **wavelength step**: wavelength step size of the laser sweep in [pm]
    * **sweep speed**: wavelength sweep speed in [nm/s]
    * **laser power**: laser instrument output power in [dBm]
    * **stabilization time**: time between changing the laser wavelength and sampling of the power [s]

    #### power meter parameter
    * **averaging time**: time over which a power measurement is averaged [s]
    * **powermeter range**: range of the power meter in [dBm]

    #### user parameter
    * **users comment**: this string will simply get stored in the saved output data file. Use this at your discretion.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'InsertionLossSteppedSweep'
        self.settings_path = 'InsertionLossSteppedSweep_settings.json'
        self.instr_laser = None
        self.instr_pm = None

    @staticmethod
    def get_default_parameter():
        return {
            # lower bound for sweep
            'wavelength start': MeasParamFloat(value=1530.0, unit='nm'),
            # upper bound for sweep
            'wavelength stop': MeasParamFloat(value=1570.0, unit='nm'),
            # step size
            'wavelength step': MeasParamFloat(value=10.0, unit='nm'),
            # laser stabilization time
            'stabilization time': MeasParamFloat(value=0.3, unit='s'),
            # power meter averaging time
            'averaging time': MeasParamFloat(value=0.1, unit='s'),
            # laser power in dBm
            'laser power': MeasParamFloat(value=6.0, unit='dBm'),
            # range of the power meter in dBm
            'powermeter range': MeasParamFloat(value=10.0, unit='dBm'),
            # let the user give some own comment
            'users comment': MeasParamString(value=''),
        }

    @staticmethod
    def get_wanted_instrument():
        return ['Laser', 'Power Meter']

    def algorithm(self, device, data, instruments, parameters):
        # get the parameters
        start_lambda = parameters.get('wavelength start').value
        end_lambda = parameters.get('wavelength stop').value
        lambda_step = parameters.get('wavelength step').value
        stabilization_time = parameters.get('stabilization time').value # EM
        averaging_time = parameters.get('averaging time').value # EM
        laser_power = parameters.get('laser power').value
        pm_range = parameters.get('powermeter range').value

        # get instrument pointers
        self.instr_pm = instruments['Power Meter']
        self.instr_laser = instruments['Laser']

        # open connection to Laser & PM
        self.instr_laser.open()
        self.instr_pm.open()

        # clear errors
        self.instr_laser.clear()
        self.instr_pm.clear()

        # Ask minimal possible wavelength
        min_lambda = float(self.instr_laser.min_lambda)

        # Ask maximal possible wavelength
        max_lambda = float(self.instr_laser.max_lambda)

        # change the minimal & maximal wavelengths if necessary
        if start_lambda < min_lambda or start_lambda > max_lambda:
            start_lambda = min_lambda
            parameters['wavelength start'].value = start_lambda
            self.logger.warning('start_lambda has been changed to smallest possible value ' + str(min_lambda))

        if end_lambda > max_lambda or end_lambda < min_lambda:
            end_lambda = max_lambda
            parameters['wavelength stop'].value = end_lambda
            self.logger.warning('end_lambda has been changed to greatest possible value ' + str(max_lambda))

        # write the measurement parameters into the measurement settings
        for pname, pparam in parameters.items():
            data['measurement settings'][pname] = pparam.as_dict()

        # Laser settings
        self.instr_laser.unit = 'dBm'
        self.instr_laser.power = laser_power
        self.instr_laser.wavelength = start_lambda
        number_of_points = int((end_lambda - start_lambda) / lambda_step) + 1

        # PM settings
        self.instr_pm.averagetime = averaging_time
        self.instr_pm.range = pm_range
        self.instr_pm.unit = 'dBm'

        # inform user
        self.logger.info(f"Sweeping over {number_of_points:d} samples "
                         f"at {self.instr_pm.averagetime:e}s sampling period.")

        power_data = list()
        wavelengths = np.linspace(start_lambda,end_lambda,number_of_points).tolist()

        self.instr_laser.enable = True # turn on laser

        # STARTET DIE MOTOREN!
        for idx, wavelength in enumerate(wavelengths):
            self.logger.info("Taking a power measurement at {} nm.".format(wavelength))

            # set laser and power wavelength
            self.instr_laser.wavelength = wavelength
            self.instr_pm.wavelength = wavelength
            
            # wait for the laser to stabilize and let one averaging time pass before taking a sample
            time.sleep(stabilization_time + averaging_time)

            # take a power measurement
            power_data.append(self.instr_pm.power)

        self.logger.info("Wavelength sweep done.")

        self.instr_laser.enable = False # turn off laser

        # Reset PM for manual Measurements
        self.instr_pm.range = 'auto'

        # convert numpy float32/float64 to python float
        data['values']['transmission [dBm]'] = power_data
        data['values']['wavelength [nm]'] = wavelengths

        # close connection
        self.instr_laser.close()
        self.instr_pm.close()

        # sanity check if data contains all necessary keys
        self._check_data(data)

        return data
