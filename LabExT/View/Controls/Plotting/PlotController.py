#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable

from LabExT.View.Controls.Plotting.PlotModel import PlotModel
from LabExT.View.Controls.Plotting.PlotView import PlotView
from LabExT.View.Controls.Plotting.PlottableDataHandler import PlottableDataHandler
from LabExT.View.Controls.Plotting.PlotConstants import *
from LabExT.View.MeasurementTable import SelectionChangedEvent

from functools import reduce

import numpy as np

if TYPE_CHECKING:
    from tkinter import Widget
    from LabExT.View.Controls.Plotting.PlottableDataHandler import PlottableData
else:
    Widget = None
    PlottableData = None


class PlotController:
    """This is the controller of a data-plot visualization.

    This controller holds a reference to the needed model storing the variables and state of the
    visualization. It also contains a reference to the view needed to display the data.
    """

    def __init__(self, master: Widget) -> None:
        """Creates a new `PlotController` and initializes the corresponding model and view.

        Args:
            master: The master widget of the view (e.g. main window `Tk`)
        """

        self._model = PlotModel()
        self._view = PlotView(master=master, plot_model=self._model)

        self._settings_frame = self._view._settings_frame

        self._data_handler = PlottableDataHandler()

        self._plottable_data: PlottableData = None
        """The data is updated, when the user selection changes. (see `self._plottable_data_changed_callback`)"""

        self._settings_frame.add_settings_changed_callback(self._plot_settings_changed_callback)
        self._data_handler.add_plottable_data_changed_listener(self._plottable_data_changed_callback)

    def show(self, row: int = 0, column: int = 1, width: int = 2, height: int = 2, pad: int = 10) -> None:
        """Places the corresponding gui elements in a grid in the parent widget according to the arguments.

        Args:
            row: row coordinate of view in master
            column: column coordinate of view in master
            width: columnspan of view in master
            height: rowspan of view in master
            pad: padding in x and y direction
        """
        self._view.show(row, column, width, height, pad)

    def hide(self) -> None:
        """Removes the corresponding gui elements from the parent."""
        self._view.hide()

    @property
    def selection_changed_listener(self) -> Callable[[SelectionChangedEvent], None]:
        """The event listener that needs to be passed to `MeasurementTable`."""
        return self._data_handler.measurement_selection_changed_callback

    def _plottable_data_changed_callback(self, data: PlottableData) -> None:
        """This callback is notified when the user changes the selected data."""
        self._plottable_data = data
        self.__redraw_settings_frame()
        self.__redraw_axes()

    def _plot_settings_changed_callback(self) -> None:
        """Called by any of the `_settings_frame`'s component, when the user makes a change."""
        # redraw settings
        self.__redraw_settings_frame()
        # redraw plot
        self.__redraw_axes()

    def __redraw_axes(self) -> None:
        # clear
        self._model.figure.clear()

        # query settings and set axes
        if self._model.plot_type.get() == LINE_PLOT:
            self.__draw_axes_line_plot(self._model.axis_x_key_name.get(), self._model.axis_y_key_name.get())
        elif self._model.plot_type.get() in [CONTOUR, CONTOUR_F]:
            self.__draw_axes_contour_plot()

        # redraw canvas
        self._view._plotting_frame.data_changed_callback()

    def __draw_axes_line_plot(self, axis_x_key: str, axis_y_key: str) -> None:
        plot = self._model.figure.add_subplot(1, 1, 1)
        for meas_hash in self._plottable_data.keys():
            measurement = self._plottable_data[meas_hash]
            plot.plot(measurement["values"][axis_x_key], measurement["values"][axis_y_key])

        plot.set_xlabel(axis_x_key)
        plot.set_ylabel(axis_y_key)

    def __draw_axes_contour_plot(self) -> None:
        """Creates a contour or contourf plot on the plotting frame."""
        if len(self._plottable_data) < 2:
            # for a contour plot we need at least 2 selected measurements
            return

        plot = self._model.figure.add_subplot(1, 1, 1)

        # shorthand so we don't have to type so much
        x_key = self._model.axis_x_key_name.get()
        y_key = self._model.axis_y_key_name.get()
        z_key = self._model.axis_z_key_name.get()

        # x data can be easily extracted from the first item, because all selected measurements should
        # be from the same sweep, i.e. have the same x-values
        x_data = np.array(self._plottable_data[self._plottable_data.keys()[0]]["values"][x_key])

        # we want the y-values to be sorted by the swept parameter. In order to match the sorting of the z-values
        # this crazy thing is necessary
        y_z_data = [
            (meas["measurement_params"][y_key], meas["values"][z_key]) for meas in self._plottable_data.values()
        ]
        y_z_data.sort(key=lambda pair: pair[0])
        y_data, z_data = (np.array(t) for t in zip(*y_z_data))  # seperate the list of pairs

        x_data, y_data = np.meshgrid(x_data, y_data)

        if self._model.plot_type.get() == CONTOUR:
            plot_method = plot.contour
        else:
            plot_method = plot.contourf
        contour = plot_method(x_data, y_data, z_data)

        self._model.figure.colorbar(contour)

        plot.set_xlabel(x_key)
        plot.set_ylabel(y_key)

    def __redraw_settings_frame(self) -> None:
        if self._plottable_data is None:
            self._settings_frame.__setup__()
        else:
            self._settings_frame.__setup__(
                shared_params=self._plottable_data.common_params,
                shared_values=self._plottable_data.common_values,
            )
