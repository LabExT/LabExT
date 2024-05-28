#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2024  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from os.path import dirname, join, exists
from os import remove
from itertools import zip_longest
from unittest.mock import Mock
import pytest
import uuid
import time

import numpy as np

from LabExT.Tests.Utils import TKinterTestCase
from LabExT.Utils import setup_user_settings_directory
from LabExT.Exporter.Formats.ExportCSV import ExportCSV
from LabExT.Exporter.Formats.ExportHDF5 import ExportHDF5
from LabExT.Exporter.ExportWizard import ExportWizard
from LabExT.ViewModel.Utilities.ObservableList import ObservableList

        
class MockTKVar:
    def __init__(self, value):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value
        
    __repr__ = __str__ = lambda self: self.value
            
class ExportDataTest(TKinterTestCase):

    def setUp(self) -> None:
        super().setUp()

        setup_user_settings_directory(makedir_if_needed=True)

        self.expm = Mock()
        self.expm.export_format_api.export_formats = {
            "ExportCSV": ExportCSV,
            "ExportHDF5": ExportHDF5,
        }

        file_name = join(dirname(dirname(__file__)), "example_measurement.json")
        self.expm.exp.measurements = ObservableList()

        with open(file_name) as f:
            meas_dict = json.load(f)

            # mock the loading of the measurement
            # this is normally done in the ExperimentManager
            meas_dict["file_path_known"] = file_name

            for k in ["timestamp start", "timestamp", "timestamp end"]:
                if k in meas_dict:
                    meas_dict["timestamp_known"] = meas_dict[k]
                    break
          
            for k in ["measurement name", "name"]:
                if k in meas_dict:
                    meas_dict["name_known"] = meas_dict[k]
                    break
           
            meas_dict["measurement id long"] = uuid.uuid4().hex

            for k in ["timestamp iso start", "timestamp_known"]:
                if k in meas_dict:
                    meas_dict["timestamp_iso_known"] = meas_dict[k]
                    break

            self.expm.exp.measurements.append(meas_dict)

    def setup_window(self):
        return ExportWizard(master=self.root, experiment_manager=self.expm)

    @pytest.mark.flaky(reruns=3)
    def test_create_window_instantiate_steps(self):
        window = self.setup_window()
        self.assertIsInstance(window.source_config_steps_insts["Comma-Separated Values (.csv)"], ExportCSV)
        self.assertIsInstance(window.source_config_steps_insts["Hierarchical Data Format (.h5)"], ExportHDF5)

    @pytest.mark.flaky(reruns=3)
    def test_csv_format(self):
        export_dir = dirname(dirname(__file__))
        file_path = join(export_dir, "example_measurement.csv")

        # remove the target file if it exists
        if exists(file_path):
            print(f"removing target export file: {file_path}")
            remove(file_path)

        window = self.setup_window()
        
        window.current_step._select_all_button.invoke()
        window.current_step.source_options_sel_var.set("Comma-Separated Values (.csv)")
        self.pump_events()

        # check if all measurements are selected
        # should only be one measurement, so order of the list is not important
        selected_measurements = list(window.current_step._meas_table.selected_measurements.values())
        all_measurements = list(self.expm.exp.measurements)
        self.assertEqual(selected_measurements, all_measurements)

        window._next_button.invoke()
        self.pump_events()

        # check if we actually are in the ExportCSV step
        self.assertIsInstance(window.current_step, ExportCSV)

        def do_export():
            window.current_step._export(window.selected_data)
        
        # normally, the export is done in a separate thread but this was causing issues with the test
        window.current_step.on_next = do_export
        
        window.current_step.export_path = MockTKVar(export_dir)
        window._next_button.invoke()
        self.pump_events()

        # file gets exported in a separate thread
        window._next_button.invoke()
        self.pump_events()

        self.assertTrue(exists(file_path))
        
        # get the values from the measurement
        measurement = self.expm.exp.measurements[0]
        values_matrix = list(zip_longest(*[v for v in measurement['values'].values()], fillvalue=np.nan))
        values_matrix =  [",".join(["{:e}".format(v) for v in l]) for l in values_matrix]

        csv_data = ""
        with open(file_path) as f:
            csv_data = f.read()

        # check the header of the csv file
        self.assertTrue(csv_data.startswith("# CSV exported measurement data from LabExT"))

        # get the data from the csv file, remove header and empty lines
        csv_data = csv_data.split("\n")
        csv_data = list(filter(lambda x: not x.startswith("#") and x != '', csv_data))

        self.assertTrue(len(csv_data) == len(values_matrix))
        
        # check the content of the csv file against the values from the measurement
        for i, line in enumerate(csv_data):
            self.assertTrue(line == values_matrix[i])

        # clean up
        remove(file_path)

        window._finish_button.invoke()
        self.pump_events()