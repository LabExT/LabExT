#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from os.path import join, exists
from pathlib import Path

from LabExT.Exporter.ExportStep import ExportFormatStep

class ExportJSON(ExportFormatStep):
    FORMAT_TITLE = "JavaScript Object Notation (.json)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _export(self, data):
        """ Implementation of export in YAML format. """
        print("Exporting data to YAML format ...")

        directory_path = self.export_path.get()

        file_names = []
        for measurement in data:
            # get output directory and check for overwriting
            orig_file_name = Path(measurement['file_path_known']).stem
            oup_name = join(directory_path, orig_file_name) + ".json"
        
            if exists(oup_name):
                self.wizard.logger.warning("Not exporting {:s} due to existing target file.".format(oup_name))
                continue

            # export to yaml
            with open(oup_name, 'w', newline='\n', encoding='utf-8') as file:
                file.write(json.dumps(measurement, indent=4) + '\n')


            file_names.append(oup_name)

        self.wizard.logger.info('Exported %s files as .json: %s', len(file_names), file_names)
        self.export_success()