#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import StringVar, OptionMenu, Label, Frame

from LabExT.View.Controls.PlotControl import PlotControl
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.ViewModel.Utilities.ObservableList import ObservableList


class PlotGridControl(Frame):
    """This controls a grid of plots. The number of rows and columns in the grid can be changed"""

    def __init__(self, parent, data, rows=2, cols=2, polling_time=None, add_legend=False, settings=None):
        """
        Constructor for the plot grid control.

        :param parent : tkinter.Frame
            The parent frame.
        :param data : dict
            A dict filled with dictionaries containing the data we want to plot. The dictionary should contain the name
            for the data rows as a key and the according data in an list as a value. These lists should be an
            ObservableList if the polling time is None.
            Example:
            {"measurement1":{"Voltage":[0,1,3],"Current":[3,2,1]},"measurement2":{"Voltage":[3,4,5],"Time":[0,1,2]}}
        :param rows : int
            The number of rows our gird should have. Gets overwritten if a settings dict is passed.
        :param cols : int
            The number of columns our gird should have. Gets overwritten if a settings dict is passed.
        :param polling_time : float
            The time the plots should wait between polling for new data. If this is set to None, polling is disabled
            and the plots update live, as long as the data is provided in an ObservableList.
        :param add_legend : bool
            Whether a legend should be added or not
        :param settings : dict
            A Dictionary containing the settings for this plot grid. The settings contain the dimensions of the grid
            as well as the data and scale choices for the individual plots.
        """
        super(PlotGridControl, self).__init__(parent)  # call the parent controls constructor
        self._polling_time = polling_time  # How long the plot waits between polling.s$
        self._data = data
        self._plot_cells = []
        self.settings = settings
        self._rows = 0
        self._cols = 0
        self._root = parent
        self._add_legend = add_legend
        if settings is None:
            self.set_dimensions(rows, cols)
        else:
            self.apply_settings(settings)

    def get_index(self, row, col):
        """Returns the plot index for a given row and column

        Parameters
        ----------
        :param row : int
            The row we want to get the index for
        :param row: int
            The column we want to get the index for

        :returns The index of the plot located at the given row and column
        """
        return row * self.cols + col

    def get_settings(self):
        """Returns a settings array according to the current state of the plot cells
        :returns An array containing all of the settings of our cells.
        """

        if self.settings is None:
            self.settings = {"dimensions": {},
                             "cell_settings": []}

        cell_settings = self.settings["cell_settings"]
        for r in range(self.rows):
            for c in range(self.cols):
                settings_index = self.get_index(r, c)
                if settings_index < len(self._plot_cells):
                    if settings_index < len(cell_settings):
                        cell_settings[settings_index] = self._plot_cells[settings_index].get_settings()
                    else:
                        cell_settings.append(self._plot_cells[settings_index].get_settings())

        self.settings["cell_settings"] = cell_settings
        self.settings["dimensions"]["rows"] = self.rows
        self.settings["dimensions"]["cols"] = self.cols
        return self.settings

    def apply_settings(self, settings):
        """Applies a settings dict to our grid.

        Parameters
        ----------
        :param settings : dict
            A Dictionary containing the settings for this plot grid. The settings contain the dimensions of the grid
            as well as the data and scale choices for the individual plots.

        :except Throws ValueError if the given settings dictionary is malformed.
        """
        if settings is None:
            pass
        else:
            try:
                self.set_dimensions(settings["dimensions"]["rows"], settings["dimensions"]["cols"])

                cell_settings = settings["cell_settings"]
                for r in range(self.rows):
                    for c in range(self.cols):
                        cell_index = self.get_index(r, c)
                        if len(cell_settings) <= cell_index:
                            return
                        self._plot_cells[cell_index].apply_settings(cell_settings[cell_index])
            except KeyError as e:
                raise ValueError("The PlotGridCell settings are wrongly formatted: {} {}".format(e, settings))
        self.settings = settings

    def _redraw_grid(self):
        """
        Redraws the plot grid, creating new cells if necessary and deleting the unused cells
        """
        for r in range(self.rows):
            for c in range(self.cols):
                cell_index = self.get_index(r, c)
                # If the cell already exists, reuse the old one
                if cell_index < len(self._plot_cells):
                    cell = self._plot_cells[cell_index]
                # Otherwise create a new one
                else:
                    cell = PlotGridCell(self, self.data, add_legend=self._add_legend, polling_time=self._polling_time)
                    self._plot_cells.append(cell)
                    if self.settings is not None and cell_index < len(self.settings["cell_settings"]):
                        cell.apply_settings(self.settings["cell_settings"][cell_index])
                cell.grid(row=r, column=c, sticky='nswe')
        # We can reuse some of the cells by just moving them to their new place.
        # However if the new dimension is smaller than the old one, we do not need as many cells as we had before,
        # so we have to destroy the extra cells
        first_unused = self.get_index(self.rows - 1, self.cols - 1) + 1
        for cell in self._plot_cells[first_unused:]:
            cell.destroy()
        self._plot_cells = self._plot_cells[:first_unused]

    def set_dimensions(self, new_rows, new_cols):
        """Set the girds dimension. Updates row and columns and redraws grid.

        Parameters
        ----------
        :param new_rows : int
                The new number of rows our grid should have.
        :param new_cols : int
                The new number of columns our grid should have.
        """
        self._update_row_weights(self.rows, new_rows)
        self._update_col_weights(self.cols, new_cols)
        self._rows = new_rows
        self._cols = new_cols
        self._redraw_grid()

    def _update_row_weights(self, old_rows, new_rows):
        """Update the row weights so that the plot still scales correctly

        Parameters
        ----------
        :param old_rows : int
                The number or rows our grid previously had.
        :param new_rows : int
                The new number of rows our grid should have.
        """
        for r in range(max([old_rows, new_rows])):
            if r < new_rows:
                self.rowconfigure(r, weight=1)  # set the weight to 1 if the current row is within our grid
            elif new_rows <= r < old_rows:
                self.rowconfigure(r, weight=0)  # otherwise set the weight to 0

    def _update_col_weights(self, old_cols, new_cols):
        """Update the column weights so that the plot still scales correctly

        Parameters
        ----------
        :param old_cols : int
                The number or columns our grid previously had.
        :param new_cols : int
                The new number of columns our grid should have.
        """
        for r in range(max([old_cols, new_cols])):
            if r < new_cols:
                self.columnconfigure(r, weight=1)  # set the weight to 1 if the current column is within our grid
            elif new_cols <= r < old_cols:
                self.columnconfigure(r, weight=0)  # otherwise set the weight to 0

    @property
    def rows(self):
        """Property containing the number of rows in our grid.

        :returns The number of rows in our grid
        """
        return self._rows

    @rows.setter
    def rows(self, new_rows):
        """Update number of rows in our grid and redraw the grid.

        Parameters
        ----------
        :param new_rows : int
                The new number of rows in our grid.
        """
        self._update_row_weights(self._rows, new_rows)
        self._rows = new_rows
        self._redraw_grid()

    @property
    def cols(self):
        """Property containing the number of columns in our grid.

        :returns The number of columns in our grid
        """
        return self._cols

    @cols.setter
    def cols(self, new_cols):
        """Update number of columns in our grid and redraw the grid.

        Parameters
        ----------
        :param new_cols : int
                The new number of columns in our grid.
        """
        self._update_col_weights(self._rows, new_cols)
        self._cols = new_cols
        self._redraw_grid()

    @property
    def data(self):
        """Property containing the number of columns in our grid.

        :returns The number of columns in our grid
        """
        return self._data

    @data.setter
    def data(self, new_data):
        """Update number of columns in our grid and redraw the grid.

        Parameters
        ----------
        :param new_cols : int
                The new number of columns in our grid.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                index = self.get_index(r, c)
                self._plot_cells[index].data = new_data
        self._data = new_data


class PlotGridCell(Frame):
    """This is a single cell in our plot grid for which we can choose the data that should be displayed"""

    def __init__(self, parent, data, add_legend=False, polling_time=None):
        """
        Constructor for a plot grid cell.

        :param parent : tkinter.Frame
            The parent frame.
        :param data : dict
            A dict filled with dictionaries containing the data we want to plot. The dictionary should contain the name
            for the data rows as a key and the according data in an list as a value. These lists should be an
            ObservableList if the polling time is None.
            Example:
            {"measurement1":{"Voltage":[0,1,3],"Current":[3,2,1]},"measurement2":{"Voltage":[3,4,5],"Time":[0,1,2]}}
        :param add_legend : bool
            Whether a legend should be added or not
        :param polling_time : int
            The time the plots should wait between polling for new data. If this is set to None, polling is disabled
            and the plots update live, as long as the data is provided in an ObservableList.
        """
        super(PlotGridCell, self).__init__(parent)  # call the parent controls constructor
        self._root = parent
        self._polling = (polling_time is not None)  # Whether the plot should update live or poll for changes
        self._add_legend = add_legend
        self._polling_time = polling_time  # How long the plot waits between polling.s$
        self._data = data
        self.__setup__()

    def __setup__(self):
        """Draws the plot and the configuration buttons"""

        choices = self._get_choices()
        self._scales = ["linear", "log(|x|)"]
        #
        # Plot
        #
        self._plot = PlotControl(self,
                                 add_toolbar=True,
                                 figsize=(5, 4),
                                 autoscale_axis=True,
                                 add_legend=self._add_legend,
                                 polling_time_s=self._polling_time
                                 )
        # Set the data to an empty list for now
        self._plot.data_source = ObservableList([])
        # Show grid
        self._plot.show_grid = True
        # Place plot in our window
        self._plot.grid(row=0, column=0, padx=10, pady=10, sticky='nswe')

        self.rowconfigure(0, weight=1)
        # self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        config_frame = Frame(self)  # Create a new frame holding all plot configurations
        config_frame.grid(row=1, column=0, sticky='nswe')

        # config_frame.rowconfigure(0, weight=1)
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)

        #
        # Plot Data Choice
        #
        data_choice_frame = Frame(config_frame)  # Create a new frame holding the data choice for a plot
        data_choice_frame.grid(row=0, column=0, sticky='nswe')

        # Data selection for x and y axis
        x_data_label = Label(data_choice_frame, text='Set data for x-axis:')
        x_data_label.grid(row=1, column=0, sticky='we')
        y_data_label = Label(data_choice_frame, text='Set data for y-axis:')
        y_data_label.grid(row=0, column=0, sticky='we')

        # Variable where choice for x axis is stored
        self._x_data_choice = StringVar()
        self._x_data_choice.trace('w', self._plot_settings_changed)

        # Variable where choice for y axis is stored
        self._y_data_choice = StringVar()
        self._y_data_choice.trace('w', self._plot_settings_changed)

        # The actual selectors
        self.x_data_selector = OptionMenu(data_choice_frame, self._x_data_choice, *choices)
        self.x_data_selector.grid(row=1, column=1, sticky='we')
        self.y_data_selector = OptionMenu(data_choice_frame, self._y_data_choice, *choices)
        self.y_data_selector.grid(row=0, column=1, sticky='we')

        # scaling of data choice frame
        # data_choice_frame.rowconfigure(0, weight=1)
        # data_choice_frame.rowconfigure(1, weight=1)
        data_choice_frame.columnconfigure(0, weight=1)
        data_choice_frame.columnconfigure(1, weight=1)

        #
        # Plot Scale Choice
        #
        scale_choice_frame = Frame(config_frame)  # Create a new frame holding the scale choice for a plot
        scale_choice_frame.grid(row=0, column=1, sticky='nswe')
        # Scale selection for x and y axis
        x_scale_label = Label(scale_choice_frame, text='Set scale for x-axis:')
        x_scale_label.grid(row=1, column=0, sticky='we')
        y_scale_label = Label(scale_choice_frame, text='Set scale for y-axis:')
        y_scale_label.grid(row=0, column=0, sticky='we')

        # Choice for x axis
        self._x_scale_choice = StringVar()
        self._x_scale_choice.set('linear')
        self._x_scale_choice.trace('w', self._plot_settings_changed)

        # Choice for y axis
        self._y_scale_choice = StringVar()
        self._y_scale_choice.set('linear')
        self._y_scale_choice.trace('w', self._plot_settings_changed)

        # The actual selectors
        x_scale_selector = OptionMenu(scale_choice_frame, self._x_scale_choice, *self._scales)
        x_scale_selector.grid(row=1, column=1, sticky='we')
        y_scale_selector = OptionMenu(scale_choice_frame, self._y_scale_choice, *self._scales)
        y_scale_selector.grid(row=0, column=1, sticky='we')

        # scaling of scale selectors
        # scale_choice_frame.rowconfigure(0, weight=1)
        # scale_choice_frame.rowconfigure(1, weight=1)
        scale_choice_frame.columnconfigure(0, weight=1)
        scale_choice_frame.columnconfigure(1, weight=1)

    def _get_choices(self):
        """Gets all axis choices for the current data.

        :returns A list of axis choices
        """
        choices = set()
        for name, data in self.data.items():
            choices |= set(data.keys())
        if len(choices) == 0:
            choices = [""]
        return sorted(list(choices))

    def _plot_settings_changed(self, *args):
        """Called by tkinter the axis or data for the plot have changed.
        Repaints the selected measurement plot.

        Parameters
        ----------
        *args
            Tkinter arguments, not used
        """
        # Set the axis scale for the x axis
        x_scale = self._x_scale_choice.get()
        if x_scale != '':
            # Prevent negative axis values for log scales
            if x_scale == 'log(|x|)':
                x_min, x_max = self._plot.ax.get_xlim()
                x_min = max(.1, x_min)
                self._plot.ax.set_xlim(x_min, x_max)
                self._plot.ax.set_xscale('log')
            else:
                self._plot.ax.set_xscale(x_scale)

        # Set the axis scale for the y axis
        y_scale = self._y_scale_choice.get()
        if y_scale != '':
            # Prevent negative axis values for log scales
            if y_scale == 'log(|x|)':
                y_min, y_max = self._plot.ax.get_ylim()
                y_min = max(.1, y_min)
                self._plot.ax.set_ylim(y_min, y_max)
                self._plot.ax.set_yscale('log')
            else:
                self._plot.ax.set_yscale(y_scale)

        # Get the dictionary keys that allow us to access the correct data from our measurement
        x_key = self._x_data_choice.get()
        y_key = self._y_data_choice.get()

        # We are only going to plot all of the data where both the x_key and the y_key are part of the data
        relevant_data = [(name, data) for name, data in self.data.items() if x_key in data and y_key in data]
        for i, (name, data) in enumerate(relevant_data):
            # Set axes names
            self._plot.set_axes(x_key, y_key)
            # Change data on plot
            data_x = data[x_key]
            data_y = data[y_key]

            # Take absolute value if we are using log plots
            if x_scale == 'log(|x|)':
                data_x = [abs(x) for x in data_x]
            if y_scale == 'log(|x|)':
                data_y = [abs(y) for y in data_y]


            if len(relevant_data) > 1:
                label = name
            else:
                label = None

            # Change the data of the most recently added plot.
            if i < len(self._plot.data_source):
                self._plot.data_source[i].plot_args['label'] = label
                self._plot.data_source[i].x = data_x
                self._plot.data_source[i].y = data_y
            else:
                if i < len(self._plot.data_source):
                    self._plot.data_source[i].plot_args['label'] = label
                    self._plot.data_source[i].x = data_x
                    self._plot.data_source[i].y = data_y
                else:
                    self._plot.data_source.append(PlotData(data_x, data_y, label=label))

        # Remove all other plots.
        for i in range(len(relevant_data), len(self._plot.data_source)):
            self._plot.data_source[i].plot_args['label'] = None
            self._plot.data_source[i].x = ObservableList()
            self._plot.data_source[i].y = ObservableList()

    def destroy(self):
        """
        Destroys this Frame and stops the plots from polling.
        """
        if self._polling:
            self._plot.stop_polling()
        super().destroy()

    def get_settings(self):
        """
        Gets the current settings for this plot cell
        :return: the settings for this plot cell
        """
        return {
            "data": {
                "x": self._x_data_choice.get(),
                "y": self._y_data_choice.get()
            },
            "scale": {
                "x": self._x_scale_choice.get(),
                "y": self._y_scale_choice.get()
            },
        }

    def apply_settings(self, settings):
        """
        Applies settings from a dictionary to this plot cell.
        """
        self._x_data_choice.set(settings["data"]["x"])
        self._y_data_choice.set(settings["data"]["y"])
        self._x_scale_choice.set(settings["scale"]["x"])
        self._y_scale_choice.set(settings["scale"]["y"])

    @property
    def data(self):
        """Property containing the number of columns in our grid.

        :returns The number of columns in our grid
        """
        return self._data

    @data.setter
    def data(self, new_data):
        """Update number of columns in our grid and redraw the grid.

        Parameters
        ----------
        :param new_cols : int
                The new number of columns in our grid.
        """
        self._data = new_data
        choices = self._get_choices()

        x_selector = self.x_data_selector["menu"]
        y_selector = self.y_data_selector["menu"]

        x_selector.delete(0, "end")
        y_selector.delete(0, "end")
        for choice in choices:
            x_selector.add_command(label=choice, command=lambda value=choice: self._x_data_choice.set(value))
            y_selector.add_command(label=choice, command=lambda value=choice: self._y_data_choice.set(value))
        self._plot_settings_changed()
