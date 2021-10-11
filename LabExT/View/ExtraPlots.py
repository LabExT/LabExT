#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os.path
from tkinter import Toplevel, StringVar, OptionMenu, Label, Frame

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.PlotGridControl import PlotGridControl


class ExtraPlots:
    """
    Opens a side window with extra plots
    """

    def __init__(self, measurement_table, parent):
        """
        Constructor

        Parameters
        ----------
        measurement_table : MeasurementTable
            The Measurement Table holding our data
        parent : Tk
            TKinter window parent.
        """

        # set the root window
        self._root = parent
        # The measurement table which displays its data on this plot
        self.meas_table = measurement_table
        # path where .json settings file is put
        self.settings_file_name = 'ExtraPlots_settings.json'

        # Dimensions
        settings = self.load_settings()
        if settings is not None:
            self.rows = settings["dimensions"]["rows"]
            self.cols = settings["dimensions"]["cols"]
        else:
            self.rows = 2
            self.cols = 2

        # Logging
        self.logger = logging.getLogger()
        self.logger.debug("Opening Extra Plots.")

        # Create our own window
        self.cur_window = Toplevel(self._root)
        # Set the title to the measurement name
        self.cur_window.title("Extra Plots")

        # array with length (self.rows x self.cols) which store our tkinter objects
        self._plots = []

        # start GUI
        self.__setup__()

    def __setup__(self):
        """Draws the window"""
        # Set number of rows and columns
        dimension_setter = Frame(self.cur_window)
        dimension_setter.grid(row=0, column=0, sticky='we')

        # Select number of rows
        num_rows_selector_label = Label(dimension_setter, text='Number of Rows')
        num_rows_selector_label.grid(row=0, column=0, sticky='w')

        self.num_rows_choice = StringVar()
        self.num_rows_choice.set(str(self.rows))
        self.num_rows_choice.trace('w', self._dimensions_changed)

        num_rows_selector = OptionMenu(dimension_setter, self.num_rows_choice, "1", "2", "3", "4")
        num_rows_selector.grid(row=0, column=1, sticky='w')

        # Select number of columns
        num_cols_selector_label = Label(dimension_setter, text='Number of Columns')
        num_cols_selector_label.grid(row=0, column=2, sticky='w')

        self.num_cols_choice = StringVar()
        self.num_cols_choice.set(str(self.cols))
        self.num_cols_choice.trace('w', self._dimensions_changed)

        num_cols_selector = OptionMenu(dimension_setter, self.num_cols_choice, "1", "2", "3", "4")
        num_cols_selector.grid(row=0, column=3, sticky='w')

        data = self.get_selected_data()
        self.plot_grid_frame = PlotGridControl(self.cur_window,
                                               data,
                                               add_legend=True,
                                               settings=self.load_settings())

        self.plot_grid_frame.grid(row=1, column=0, sticky='nswe')

        self.cur_window.rowconfigure(1, weight=1)
        self.cur_window.columnconfigure(0, weight=1)

        self.cur_window.lift()
        self.cur_window.protocol("WM_DELETE_WINDOW", self.__on_close__)

    def get_selected_data(self):
        """Gets the data for all of the rows selected in the finished measurements table."""
        data = {}
        for meas_iid, meas in self.meas_table.selected_measurements.items():
            measurement_name = "{id} - {timestamp}".format(id=meas["device"]["id"], timestamp=meas["timestamp_known"])
            data[measurement_name] = meas["values"]
        return data

    def axis_options_changed(self):
        """Gets called by the Finished Measurements Table if the user selected a different subset of data."""
        self.plot_grid_frame.data = self.get_selected_data()

    def is_opened(self):
        """Checks if the window is currently opened.

        :returns True if the window is opened, False otherwise."""
        return self.cur_window is not None

    def __on_close__(self):
        """If user presses 'x', exit the LiveViewer."""
        self.save_settings()
        self.cur_window.destroy()
        self.cur_window = None

    def _dimensions_changed(self, *args):
        """Called when dimensions changed for current window

        Parameters
        ----------
        *args
            Tkinter arguments, not used
        """
        self.save_settings()
        self.rows = int(self.num_rows_choice.get())
        self.cols = int(self.num_cols_choice.get())
        self.plot_grid_frame.set_dimensions(self.rows, self.cols)

    def save_settings(self):
        """Saves the current settings from the tkinter objects into a json file.
        """
        settings = self.plot_grid_frame.get_settings()
        settings_path = get_configuration_file_path(self.settings_file_name)
        with open(settings_path, "w+") as f:
            json.dump(settings, f)

    def load_settings(self):
        """Loads the settings from its setting file.

        Returns
        -------
        settings : dict
            A dictionary containing the settings if the file exists, otherwise None
        """
        settings_path = get_configuration_file_path(self.settings_file_name)
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                settings = json.load(f)
            return settings
        else:
            return None
