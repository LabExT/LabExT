#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


class ExperimentWizardModel:
    def __init__(self, controller):
        self.controller = controller

        # tracks at which instruction the user currently is
        self.current_step = 0
        self.measurement_parameters = {}
        self.instrument_list = []

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, new_step):
        self._current_step = new_step
