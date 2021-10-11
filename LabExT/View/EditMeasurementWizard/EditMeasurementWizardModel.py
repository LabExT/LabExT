#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging


class EditMeasurementWizardModel:
    """
    The view model for the main window.
    This class provides the data from the business logic to the view.

    Attributes
    ----------
    """

    def __init__(self, experiment_manager):

        self._experiment_manager = experiment_manager
        self._experiment = self._experiment_manager.exp
        self.chip_available = True if self._experiment_manager.chip is not None else False

        self.logger = logging.getLogger()

        # locals
        self._view = None

        # saved user settings
        self.settings_file_name = 'EditMeasurementWizard_settings.json'
        self.instrument_settings_file_name = 'EditMeasurementWizard_instr_settings.json'
        self.adhoc_device_save_file_name = 'EditMeasurementWizard_adhoc_settings.json'
        self.saved_s0_device_id = None
        self.saved_s1_measurement_name = None
        self.saved_s1_measurement_nr = None

        # user selected data
        self.s0_device = None
        self.s1_measurement = None
        self.s1_available_instruments = None

    @property
    def saved_s0_device_id(self):
        return self._saved_s0_device_id

    @saved_s0_device_id.setter
    def saved_s0_device_id(self, new_id):
        self._saved_s0_device_id = new_id

    @property
    def saved_s1_measurement_name(self):
        return self._saved_s1_measurement_name

    @saved_s1_measurement_name.setter
    def saved_s1_measurement_name(self, new_name):
        self._saved_s1_measurement_name = new_name

    @property
    def saved_s1_measurement_nr(self):
        return self._saved_s1_measurement_nr

    @saved_s1_measurement_nr.setter
    def saved_s1_measurement_nr(self, new_nr):
        self._saved_s1_measurement_nr = new_nr

    @property
    def s0_device(self):
        return self._s0_device

    @s0_device.setter
    def s0_device(self, new_dev):
        self._s0_device = new_dev

    @property
    def s1_measurement(self):
        return self._s1_measurement

    @s1_measurement.setter
    def s1_measurement(self, new_measurement):
        self._s1_measurement = new_measurement

    @property
    def s1_available_instruments(self):
        return self._s1_available_instruments

    @s1_available_instruments.setter
    def s1_available_instruments(self, new_instr):
        self._s1_available_instruments = new_instr

    def set_view(self, view):
        self._view = view
