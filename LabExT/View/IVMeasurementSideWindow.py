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


class IVMeasurementSideWindow:
    """
    Opens a side window with extra plots
    """

    def __init__(self, measurement, parent):
        """
        Constructor

        Parameters
        ----------
        measurement : IVMeasurement
            The IVMeasurement which displays its data on this plot
        parent : Tk
            TKinter window parent.
        """

        # set the root window
        self._root = parent
        # The measurement which displays its data on this plot
        self.meas = measurement
        # path where .json settings file is put
        self.settings_file_name = 'IVMeasurementSideWindow_settings.json'

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
        self.logger.debug("Opening Side Window.")

        # Create our own window
        self.cur_window = Toplevel(self._root)
        # Set the title to the measurement name
        self.cur_window.title(self.meas.get_name_with_id())

        # arrays with length (self.rows x self.cols) which store our tkinter objects
        self._plots = []

        # start GUI
        self.__setup__()

    def __setup__(self):
        # Set number of rows and columns
        dimension_setter = Frame(self.cur_window)
        dimension_setter.grid(row=0, column=0, sticky='we')

        # Select number of rows
        num_rows_selector_label = Label(dimension_setter, text='Number of Rows')
        num_rows_selector_label.grid(row=0, column=0, sticky='w')

        self.num_rows_choice = StringVar(self._root)
        self.num_rows_choice.set(str(self.rows))
        self.num_rows_choice.trace('w', self._dimensions_changed)

        num_rows_selector = OptionMenu(dimension_setter, self.num_rows_choice, "1", "2", "3", "4")
        num_rows_selector.grid(row=0, column=1, sticky='w')

        # Select number of columns
        num_cols_selector_label = Label(dimension_setter, text='Number of Columns')
        num_cols_selector_label.grid(row=0, column=2, sticky='w')

        self.num_cols_choice = StringVar(self._root)
        self.num_cols_choice.set(str(self.cols))
        self.num_cols_choice.trace('w', self._dimensions_changed)

        num_cols_selector = OptionMenu(dimension_setter, self.num_cols_choice, "1", "2", "3", "4")
        num_cols_selector.grid(row=0, column=3, sticky='w')

        self.plot_grid_frame = PlotGridControl(self.cur_window,
                                               {self.meas.get_name_with_id(): self.meas.values},
                                               polling_time=0.5,
                                               settings=self.load_settings())
        self.plot_grid_frame.grid(row=1, column=0, sticky='we')

        self.cur_window.rowconfigure(1, weight=1)
        self.cur_window.columnconfigure(0, weight=1)

        self.cur_window.lift()
        self.cur_window.protocol("WM_DELETE_WINDOW", self.__on_close__)

    def __on_close__(self):
        """If user presses 'x', exit the LiveViewer.
        """
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
        settings_file_path = get_configuration_file_path(self.settings_file_name)
        with open(settings_file_path, "w+") as f:
            json.dump(settings, f)

    def load_settings(self):
        """Loads the settings from its setting file.

        Returns
        -------
        settings : dict
            A dictionary containing the settings if the file exists, otherwise None
        """
        settings_file_path = get_configuration_file_path(self.settings_file_name)
        if os.path.exists(settings_file_path):
            with open(settings_file_path, "r") as f:
                settings = json.load(f)
            return settings
        else:
            return None
