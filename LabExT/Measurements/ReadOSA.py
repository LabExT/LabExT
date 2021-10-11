#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from time import sleep

from LabExT.Measurements.MeasAPI import *


class ReadOSA(Measurement):
    """
    ## ReadOSA

    This class performs a measurement that sets up and runs a single sweep at an OSA and returns the data collected.
    Data returned corresponds to a 'snapshot' of the OSAs screen after a sweep.

    ### Example Setup

    ```
    DUT -> OSA
    ```

    The only instrument required for this measurement is an OSA, either a APEX, Yokagawa or HP model. This measurement
    can for example be used in longterm measurements where a signal generator and laser are operated manually.

    ### OSA Parameters
    - **OSA center wavelength**: Center wavelength of the OSA in [nm]. Stays fixed throughout the measurement if
    autocenter is disabled.
    - **auto center**: If selected, the OSA runs a sweep and determines the center wavelength by itself. If disabled,
    then the wavelength set in 'OSA center frequency' is used.
    - **OSA span**: Span of the OSA in [nm]. Determines in which region the spectrum is recorded. The optical power at
    all wavelengths within [$f_{center} - \frac{span}{2}$, $f_{center} + \frac{span}{2}$] are recorded.
    - **number of points**: Number of points the OSA records. Should be bigger than span / sweep resolution
    - **sweep resolution**: Resolution of the OSA sweep in [nm]. Allowed values are dependent on the OSA model.
    Yokagawa AQ6370C: 0.02 nm and 2 nm, HP70951A: > 0.08 nm, APEX: > 4e-5 nm.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'ReadOSA'
        self.settings_path = 'ReadOSA_settings.json'
        self.instr_osa = None

    @staticmethod
    def get_default_parameter():
        return {
            # osa settings
            'OSA center wavelength': MeasParamFloat(value=1550.0, unit='nm'),
            'OSA span': MeasParamFloat(value=2.0, unit='nm'),
            'no of points': MeasParamInt(value=2000),
            'sweep resolution': MeasParamFloat(value=0.08, unit='nm')
        }

    @staticmethod
    def get_wanted_instrument():
        return ['OSA']

    def algorithm(self, device, data, instruments, parameters):
        # get osa parameters
        osa_center_wl_nm = float(parameters.get('OSA center wavelength').value)
        osa_span_nm = float(parameters.get('OSA span').value)
        sweep_resolution_nm = float(parameters.get('sweep resolution').value)
        no_points = int(parameters.get('no of points').value)

        # write the measurement parameters into the measurement settings
        for pname, pparam in parameters.items():
            data['measurement settings'][pname] = pparam.as_dict()

        self.instr_osa = instruments['OSA']

        self.instr_osa.open()

        # set instrument parameters
        self.instr_osa.span = osa_span_nm
        self.instr_osa.centerwavelength = osa_center_wl_nm
        self.instr_osa.sweepresolution = sweep_resolution_nm
        self.instr_osa.n_points = no_points

        # everything is set up, run the sweep
        self.logger.info('OSA running sweep')
        self.instr_osa.run()

        sleep(0.5)

        # pull data from OSA
        x_data_nm, y_data_dbm = self.instr_osa.get_data()
        self.logger.info('OSA data received')

        # copy the read data over to the json
        data['values']['wavelength [nm]'] = x_data_nm
        data['values']['transmission [dBm]'] = y_data_dbm

        # close instrument connection
        self.instr_osa.close()
        self.logger.info('closed connection to OSA')

        # check data for sanity
        self._check_data(data)
        return data
