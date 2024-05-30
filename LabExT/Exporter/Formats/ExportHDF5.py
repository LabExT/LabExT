#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import h5py
from os.path import join, exists
from pathlib import Path

from LabExT.Exporter.ExportStep import ExportFormatStep

def write_metadata(group, metadata, path):
    for k, v in metadata.items():
        if isinstance(v, dict):
            write_metadata(group, v, path + k + ' - ')
        else:
            group.attrs[path + k] = str(v)

class ExportHDF5(ExportFormatStep):
    FORMAT_TITLE = "Hierarchical Data Format (.h5)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _export(self, data):
        """ Implementation of export in hdf5 format. """
        print("Exporting data to HDF5 format ...")

        directory_path = self.export_path.get()

        file_names = []
        for measurement in data:
            # get output directory and check for overwritin
            orig_file_name = Path(measurement['file_path_known']).stem
            oup_name = join(directory_path, orig_file_name) + ".h5"
        
            if exists(oup_name):
                self.wizard.logger.warning("Not exporting {:s} due to existing target file.".format(oup_name))
                continue
            
            with h5py.File(oup_name, "w") as file:
                group = file.create_group("values")
                for k, v in measurement["values"].items():
                    group.create_dataset(k, data=v, dtype='f')
                
                metadata = measurement.copy()
                metadata.pop("values")

                write_metadata(file, metadata, '')
                
            file_names.append(oup_name)

        self.wizard.logger.info('Exported %s files as .h5: %s', len(file_names), file_names)
        self.export_success()