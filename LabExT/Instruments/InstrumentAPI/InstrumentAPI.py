#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from os.path import dirname

from LabExT.Instruments.InstrumentAPI._Instrument import Instrument
from LabExT.Instruments.InstrumentAPI.InstrumentSetup import create_instrument_obj_impl
from LabExT.PluginLoader import import_plugins_from_paths


class InstrumentAPI:
    def __init__(self, experiment_manager):
        self._experiment_manager = experiment_manager
        self.logger = logging.getLogger()
        self.plugin_loader_stats = {}
        self.instruments = {}

    def load_all_instruments(self):
        """ executes the loading of additional Instrument classes from all configured addon directories """
        instrs_search_paths = [dirname(dirname(__file__))]  # include Instrs. from LabExT core first
        instrs_search_paths += self._experiment_manager.addon_settings['addon_search_directories']

        self.instruments, self.plugin_loader_stats = import_plugins_from_paths(
            base_class=Instrument, search_paths=instrs_search_paths)

        self.logger.debug('Available instruments loaded. Found: %s', [k for k in self.instruments.keys()])

    def create_instrument_obj(self, instrument_type, selected_instruments, initialized_instruments):
        """Initialises instrument based on type and category.

        Parameters
        ----------
        instrument_type : str
            Type of instrument: Laser, PowerMeter etc. as specified in instruments.config file.
        selected_instruments : dict
            A dictionary containing the instrument type strings as key and the chosen description dict as value
        initialized_instruments : dict
            A dictionary to which the instantiated instrument objects should be stored. Uses a tuple
            (instr type, class name) as keys and the instantiated instrument object as value.

        Returns
        -------
        Initialised instrument.
        """
        return create_instrument_obj_impl(self, instrument_type, selected_instruments, initialized_instruments)
