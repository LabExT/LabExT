#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from typing import Dict
from collections import defaultdict


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
        self.chip_available = self._experiment_manager.chip is not None

        self.logger = logging.getLogger()

        # locals
        self._view = None

        # saved user settings
        self.settings_file_name = 'EditMeasurementWizard_settings.json'
        """The file name used for caching user-entries for the next time the wizard is opened."""

        # user selected data
        self.settings: Dict[int, Dict] = defaultdict(lambda: {})
        """Maps the stage number to the previous entries of the WizardEntry."""
        self.results: Dict[int] = {}
        """Maps the stage number to the results of the WizardEntry."""

    def set_view(self, view):
        self._view = view
