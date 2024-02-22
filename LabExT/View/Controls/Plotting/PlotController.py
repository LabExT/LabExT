#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable, Iterable, TypeVar

from LabExT.View.Controls.Plotting.PlotModel import PlotModel
from LabExT.View.Controls.Plotting.PlotView import PlotView
from LabExT.View.Controls.Plotting.PlottableDataHandler import PlottableDataHandler
from LabExT.View.Controls.Plotting.PlotConstants import *
from LabExT.View.MeasurementTable import SelectionChangedEvent

import numpy as np

if TYPE_CHECKING:
    from tkinter import Widget
    from LabExT.View.Controls.Plotting.PlottableDataHandler import PlottableData
else:
    Widget = None
    PlottableData = None

T = TypeVar("T")


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

        def _print_sorted_error(key: str):
            plot.text(
                0.5, 0.5, f"The values given by '{key}' are not sorted!", color="red", horizontalalignment="center"
            )

        # shorthand so I don't have to type so much
        x_key = self._model.axis_x_key_name.get()
        y_key = self._model.axis_y_key_name.get()
        z_key = self._model.axis_z_key_name.get()

        # get all x-values that are contained in the measurements
        x_data = self._plottable_data.values()[0]["values"][x_key]
        if not PlotController.__is_sorted(x_data):
            _print_sorted_error(x_key)
            return

        for meas in self._plottable_data.values()[1:]:
            if not PlotController.__is_sorted(meas["values"][x_key]):
                _print_sorted_error(x_key)
                return
            x_data = PlotController.__merge_union_sorted(x_data, meas["values"][x_key])

        # Here we get the y and z-values corresponding to the x-values (we pad with NaN)
        y_z_data = list()
        for meas in self._plottable_data.values():
            y_values = meas["measurement_params"][y_key]
            z_values = list()
            z_iterator = iter(meas["values"][z_key])
            for x in x_data:
                z_values.append(next(z_iterator) if x in meas["values"][x_key] else np.nan)
            y_z_data.append((y_values, z_values))

        # We sort the list of pairs by the swept param (i.e. the y-value)
        y_z_data.sort(key=lambda pair: pair[0])

        # seperate the list of pairs
        y_data, z_data = (np.array(list(t)) for t in zip(*y_z_data))

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

    def __is_sorted(a: Iterable) -> bool:
        """Checks if an iterable is sorted and returns True or False accordingly.

        The elements of a need to support the < operation.
        """
        a = iter(a)
        end_iteration = object()
        e = next(a, end_iteration)
        while e != end_iteration:
            _e = next(a, end_iteration)
            if _e == end_iteration:
                break
            if e > _e:
                return False
            e = _e
        return True

    def __merge_union_sorted(a: Iterable[T], b: Iterable[T]) -> list[T]:
        """Calculates the merge of the two sorted iterables a and b without keeping duplicates.

        Args:
            a: A sorted iterable. The entries need to support the <= operation with the elements of b.
            b: A sorted iterable. The entries need to support the > operation with the elements of a.

        Returns:
            A sorted list of unique values contained in the first and second argument.
        """
        res = list()

        a = iter(a)
        b = iter(b)

        end_iteration = object()

        # go through both arrays as long as they have values left
        a_elem = next(a, end_iteration)
        b_elem = next(b, end_iteration)
        while a_elem != end_iteration and b_elem != end_iteration:
            if a_elem <= b_elem:
                if a_elem not in res:
                    res.append(a_elem)
                a_elem = next(a, end_iteration)
            else:
                if b_elem not in res:
                    res.append(b_elem)
                b_elem = next(b, end_iteration)

        # clean up the argument with elements left
        while a_elem != end_iteration:
            if a_elem not in res:
                res.append(a_elem)
            a_elem = next(a, end_iteration)
        while b_elem != end_iteration:
            if b_elem not in res:
                res.append(b_elem)
            b_elem = next(b, end_iteration)

        return res
