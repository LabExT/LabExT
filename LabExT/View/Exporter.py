#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import csv
import datetime
import logging
from itertools import zip_longest
from os import makedirs
from os.path import abspath, basename, join, exists
from tkinter import Tk, Toplevel, Button

import numpy as np

from LabExT.Utils import run_with_wait_window
from LabExT.View.Controls.ParameterTable import ParameterTable, ConfigParameter
from LabExT.View.MeasurementTable import MeasurementTable


class Exporter:
    """Handles the export of measurements into different data formats.

    Attributes
    ----------
    export_options : dict
        All possible export options currently supported.
    measurement_selection : list
        List of all measurements to be exported.
    """

    def __init__(self, parent: Tk, experiment_manager):
        """Constructor

        Parameters
        ----------
        parent : Tk
            Tkinter parent window.
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self._root = parent
        self._experiment_manager = experiment_manager
        self._default_path = self._experiment_manager.exp._default_save_path

        self.logger = logging.getLogger()

        self._meas_window = Toplevel(self._root)
        self._meas_window.lift()
        self._meas_window.geometry(
            '+%d+%d' % (self._root.winfo_screenwidth() / 4,
                        self._root.winfo_screenheight() / 4))

        # ###################
        # _MEASUREMENT TABLE_
        # ###################
        self._meas_table = MeasurementTable(parent=self._meas_window,
                                            experiment_manager=self._experiment_manager,
                                            total_col_width=750,
                                            do_changed_callbacks=False,
                                            allow_only_single_meas_name=False)
        self._meas_table.grid(row=0, column=0, padx=5, pady=5, sticky="nswe")
        self._meas_table.title = "Finished Measurements"
        self._meas_table.regenerate()

        self.export_options = {
            'Output File Format': ConfigParameter(
                self._meas_window,
                value=[
                    'comma-separated values (.csv)'
                    # 'HDF5 (.h5)'  # not implemented yet
                ],
                parameter_type='dropdown'),
            'Output Directory': ConfigParameter(
                self._meas_window,
                value=self._default_path,
                parameter_type='folder'
            )
        }

        self._option_table = ParameterTable(self._meas_window)
        self._option_table.grid(row=1, column=0, padx=5, pady=5, sticky="nswe")
        self._option_table.title = 'Export Settings'
        self._option_table.parameter_source = self.export_options

        self._continue_button = Button(
            self._meas_window, text='Export!', command=self._export)
        self._continue_button.grid(row=2, column=0, padx=5, pady=5, sticky='e')

        self._select_all_button = Button(
            self._meas_window,
            text='Select All Measurements',
            command=self._meas_table.click_on_all)
        self._select_all_button.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        # enable scaling
        self._meas_window.rowconfigure(0, weight=1)
        self._meas_window.columnconfigure(0, weight=1)

    def _export(self):
        """
        Calls export functions depending on export formats selected
        by user and closes chooser window.
        """
        self._continue_button.config(state='disabled')
        self._select_all_button.config(state='disabled')

        self.measurement_selection = [v for v in self._meas_table.selected_measurements.values()]
        output_ff_str = self.export_options['Output File Format'].value
        output_dir = abspath(self.export_options['Output Directory'].value)
        makedirs(output_dir, exist_ok=True)

        if ".h5" in output_ff_str.lower():
            run_with_wait_window(
                self._root,
                "Exporting to HDF5 format.",
                lambda: self._hdf5_export(self.measurement_selection, output_dir)
            )
        elif ".csv" in output_ff_str.lower():
            run_with_wait_window(
                self._root,
                "Exporting to CSV format.",
                lambda: self._csv_export(self.measurement_selection, output_dir)
            )

        self._meas_window.destroy()

    def _hdf5_export(self, measurement_list, output_directory):
        """Implementation of export in HDF5 format.

        Parameters
        ----------
        measurement_list : list
            List of all measurements to be exported.
        """
        self.logger.error('Export as hdf5 is not yet implemented. Please choose another option.')
        raise NotImplementedError()

    def _csv_export(self, measurement_selection, output_directory):
        """ Implementation of export in CSV format. """
        file_names = []
        for measurement in measurement_selection:
            # get output directory and check for overwriting
            orig_json_name = basename(measurement['file_path_known'])
            oup_name = join(output_directory, orig_json_name) + ".csv"
            if exists(oup_name):
                self.logger.warning("Not exporting {:s} due to existing target file.".format(oup_name))
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
        self.logger.info('Exported %s files as .csv: %s', len(file_names), file_names)
