#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

from LabExT.Measurements.MeasAPI import *


class InsertionLossSweep(Measurement):
    """
    ## InsertionLossSweep

    This measurement uses a tunable laser source to make a fast high-resolution spectral measurement by sweeping the
    output signal wavelength at a fixed speed, synchronized with an optical power meter. The laser measures and logs
    the wavelength values during the sweep with a chosen interval and outputs electrical output triggers to synchronize
    detection sampling. The resulting arrays of wavelength and detected signal samples provide a spectrum showing the
    wavelength dependence of the DUT.

    Currently this measurement supports Agilent/Keysight swept lasers (model numbers 816x) and triggered power
    meters (model numbers 816x or N77xx). The measurement procedure is described in the Keysight application
    note 5992-1125EN, see https://www.keysight.com/ch/de/assets/7018-04983/application-notes/5992-1125.pdf.

    #### example lab setup
    ```
    laser -> DUT -> power meter
      \--trigger-cable--/
    ```
    If your optical power meter is NOT in the same mainframe as the swept laser, you must connect the laser's trigger
    output port to the power meters's trigger input port with a BNC cable!

    #### laser parameters
    * **wavelength start**: starting wavelength of the laser sweep in [nm]
    * **wavelength stop**: stopping wavelength of the laser sweep in [nm]
    * **wavelength step**: wavelength step size of the laser sweep in [pm]
    * **sweep speed**: wavelength sweep speed in [nm/s]
    * **laser power**: laser instrument output power in [dBm]

    #### power meter parameter
    * **powermeter range**: range of the power meter in [dBm]

    #### user parameter
    * **users comment**: this string will simply get stored in the saved output data file. Use this at your discretion.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'InsertionLossSweep'
        self.settings_path = 'InsertionLossSweep_settings.json'
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
            'wavelength step': MeasParamFloat(value=10.0, unit='pm'),
            # sweep speed in nm/s
            'sweep speed': MeasParamFloat(value=40.0, unit='nm/s'),
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
        center_wavelength = (start_lambda + end_lambda) / 2
        lambda_step = parameters.get('wavelength step').value
        sweep_speed = parameters.get('sweep speed').value
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
        self.instr_laser.wavelength = center_wavelength
        self.instr_laser.sweep_wl_setup(start_lambda, end_lambda, lambda_step, sweep_speed)
        number_of_points = self.instr_laser.sweep_wl_get_n_points()

        # PM settings
        self.instr_pm.wavelength = center_wavelength
        self.instr_pm.range = pm_range
        self.instr_pm.unit = 'dBm'
        max_avg_time = abs(start_lambda - end_lambda) / (sweep_speed * number_of_points)
        self.instr_pm.averagetime = max_avg_time / 2
        # note: this check makes sense here, since the instrument might quietly set avg. time to something larger
        # than desired
        if self.instr_pm.averagetime > max_avg_time:
            raise RuntimeError("Power meter minimum average time is longer than one WL step time!")
        self.instr_pm.logging_setup(n_measurement_points=number_of_points,
                                    triggered=True,
                                    trigger_each_meas_separately=True)

        # inform user
        self.logger.info(f"Sweeping over {number_of_points:d} samples "
                         f"at {self.instr_pm.averagetime:e}s sampling period.")

        # STARTET DIE MOTOREN!
        with self.instr_laser:

            # start sweeping
            self.instr_pm.logging_start()
            self.instr_laser.sweep_wl_start()

            # wait for sweep finish
            while self.instr_laser.sweep_wl_busy():
                time.sleep(0.2)

            # wait for pm finished logging, needs to be time-out checked since hw triggering of PM could silently fail
            time_start_wait_pms = time.time()
            while self.instr_pm.logging_busy():
                if time.time() - time_start_wait_pms > 3.0:
                    raise RuntimeError("PM did not finish sweep in 3 seconds after laser sweep done.")
                time.sleep(0.1)

        # read out data
        self.logger.info("Downloading optical power data from power meter.")
        power_data = self.instr_pm.logging_get_data()
        self.logger.info("Downloading wavelength data from laser.")
        used_n_samples = self.instr_laser.sweep_wl_get_n_points()
        lambda_data = self.instr_laser.sweep_wl_get_data(N_samples=used_n_samples)

        # Reset PM for manual Measurements
        self.instr_pm.range = 'auto'

        # convert numpy float32/float64 to python float
        data['values']['transmission [dBm]'] = power_data.tolist()
        data['values']['wavelength [nm]'] = lambda_data.tolist()

        # close connection
        self.instr_laser.close()
        self.instr_pm.close()

        # sanity check if data contains all necessary keys
        self._check_data(data)

        return data
