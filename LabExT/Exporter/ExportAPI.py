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
from LabExT.Exporter.ExportStep import ExportFormatStep


if TYPE_CHECKING:
    from LabExT.ExperimentManager import ExperimentManager
else:
    ExperimentManager = None


class ExportFormatAPI:
    """
    API class for the export format plugins.
    Loads all classes that inherit ExportFormatStep and provides them to the ExperimentManager.
    """
    def __init__(self, experiment_manager: ExperimentManager):
        self._experiment_manager = experiment_manager
        self.logger = logging.getLogger()
        self.plugin_loader = PluginLoader()
        self.plugin_loader_stats = {}
        self.export_formats = {}

    def load_all_export_formats(self) -> None:
        """
        This function dynamically loads all export format addons.
        """
        self.plugin_loader_stats.clear()

        # include export format from LabExT core first
        export_format_search_path = [join(dirname(__file__), "Formats")]
        export_format_search_path += self._experiment_manager.addon_settings["addon_search_directories"]

        for export_format in export_format_search_path:
            plugins = self.plugin_loader.load_plugins(export_format, plugin_base_class=ExportFormatStep, recursive=True)
            unique_plugins = {k: v for k, v in plugins.items() if k not in self.export_formats}
            self.plugin_loader_stats[export_format] = len(unique_plugins)
            self.export_formats.update(unique_plugins)
