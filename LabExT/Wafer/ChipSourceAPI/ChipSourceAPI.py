#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import TYPE_CHECKING
from os.path import dirname, join

from LabExT.PluginLoader import PluginLoader
from LabExT.Wafer.ChipSourceAPI import ChipSourceStep


if TYPE_CHECKING:
    from LabExT.ExperimentManager import ExperimentManager
else:
    ExperimentManager = None


class ChipSourceAPI:
    def __init__(self, experiment_manager: ExperimentManager):
        self._experiment_manager = experiment_manager
        self.logger = logging.getLogger()
        self.plugin_loader = PluginLoader()
        self.plugin_loader_stats = {}
        self.chip_sources = {}

    def load_all_chip_sources(self) -> None:
        """
        This function dynamically loads all chip source addons.
        """
        self.plugin_loader_stats.clear()

        # include chip sources from LabExT core first
        chip_source_search_path = [join(dirname(dirname(__file__)), "ChipSources")]
        chip_source_search_path += self._experiment_manager.addon_settings["addon_search_directories"]

        for cssp in chip_source_search_path:
            plugins = self.plugin_loader.load_plugins(cssp, plugin_base_class=ChipSourceStep, recursive=True)
            unique_plugins = {k: v for k, v in plugins.items() if k not in self.chip_sources}
            self.plugin_loader_stats[cssp] = len(unique_plugins)
            self.chip_sources.update(unique_plugins)
