#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import csv
import datetime
from itertools import zip_longest
from os.path import join, exists
from pathlib import Path

import numpy as np

from LabExT.Exporter.ExportStep import ExportFormatStep

class ExportCSV(ExportFormatStep):
    FORMAT_TITLE = "Comma-Separated Values (.csv)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _export(self, data):
        """ Implementation of export in CSV format. """
        print("Exporting data to CSV format ...")

        directory_path = self.export_path.get()

        file_names = []
        for measurement in data:
            # get output directory and check for overwritin
            orig_file_name = Path(measurement['file_path_known']).stem
            oup_name = join(directory_path, orig_file_name) + ".csv"
            print(oup_name)
            if exists(oup_name):
                self.wizard.logger.warning("Not exporting {:s} due to existing target file.".format(oup_name))
                continue

            # gather header and values data
            column_names = [str(k) for k in measurement['values'].keys()]
            header_text = "# CSV exported measurement data from LabExT\n"
            header_text += "# original file: " + str(measurement['file_path_known']) + "\n"
            header_text += "# exported to csv on: {date:%Y-%m-%d_%H%M%S}\n".format(date=datetime.datetime.now())
            header_text += "# Careful! This file only contains the raw measured data and NO meta-data." + \
                            " It cannot be read-back into LabExT.\n"
            header_text += "# column names: \n"
            header_text += "# " + ", ".join(column_names) + "\n"

            values_matrix = zip_longest(*[v for v in measurement['values'].values()], fillvalue=np.nan)

            # export to csv
            with open(oup_name, 'w', newline='\n', encoding='utf-8') as csvfile:
                csvfile.write(header_text)
                writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_NONE)
                for row in values_matrix:
                    writer.writerow(["{:e}".format(v) for v in row])

            file_names.append(oup_name)

        self.wizard.logger.info('Exported %s files as .csv: %s', len(file_names), file_names)
        self.export_success()