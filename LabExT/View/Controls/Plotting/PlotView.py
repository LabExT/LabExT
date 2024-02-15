#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable, Optional

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.Plotting.PlotConstants import *


if TYPE_CHECKING:
    from LabExT.View.Controls.Plotting.PlotModel import PlotModel
    from matplotlib.figure import Figure
else:
    PlotModel = None
    Figure = None


class PlotView:
    """The view corresponding to a plotting visualization.

    Manages the widgets and so on.
    """

    def __init__(self, master: tk.Widget, plot_model: PlotModel) -> None:
        """Initializes a new `PlotView` object

        The plotting frame will be placed at the specified coordinates and the settings window will be placed
        one column to the right.

        Args:
            master: The parent of the plotting frame (e.g. the main window Tk instance)
            plot_model: The `PlotModel` holding the variables used to store the settings to.
        """

        self._paned_frame = tk.PanedWindow(master=master, orient=tk.HORIZONTAL, sashrelief="ridge")
        """Holds the subwindows."""

        self._plotting_frame = PlottingFrame(master=self._paned_frame, figure=plot_model.figure)

        self._settings_frame = PlottingSettingsFrame(
            master=self._paned_frame,
            plot_type_var=plot_model.plot_type,
            axis_x_var=plot_model.axis_x_key_name,
            axis_y_var=plot_model.axis_y_key_name,
            axis_z_var=plot_model.axis_z_key_name,
        )
        self._settings_frame.title = "Plot Settings"

    def show(self, row: int = 0, column: int = 1, width: int = 2, height=2, pad: int = 10) -> None:
        """Places this element in a grid in the parent widget according to the arguments.

        Args:
            row: row coordinate in the parent
            width: columnspan in master
            height: rowspan in master
            column: column coordinate in the parent
            pad: padding in x and y direction
        """
        self._paned_frame.add(self._plotting_frame, padx=pad, pady=pad, minsize=400, width=700)
        self._paned_frame.add(self._settings_frame, padx=pad, pady=pad, minsize=200)

        self._paned_frame.grid(
            row=row, column=column, columnspan=width, rowspan=height, padx=pad, pady=pad, sticky="nsew"
        )

    def hide(self) -> None:
        """Removes this element from the parent grid."""
        self._paned_frame.remove(self._plotting_frame)
        self._paned_frame.remove(self._settings_frame)
        self._paned_frame.grid_forget()


class PlottingFrame(tk.Frame):
    """This frame contains the widgets created by the matplotlib tk backend"""

    def __init__(self, master: tk.Widget, figure: Figure, *args, **kwargs) -> None:
        """Initializes a new `PlottingWidget`

        Args:
            master: The parent this widget should be placed in
            figure: The figure used to plot the data (provided by model)
        """
        super().__init__(master, *args, **kwargs)

        self._canvas = FigureCanvasTkAgg(figure=figure, master=self)
        self._canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self._canvas, self)
        toolbar.pack()

    def data_changed_callback(self) -> None:
        """This method should be called if the axes object was changed, such that the necessary updates can be performed."""
        self._canvas.draw()


class PlottingSettingsFrame(CustomFrame):
    """This frame contains the widgets used to control the displayed visualization of the data.

    Because this is a "View"-component it does not handle *any* of the logic. It does not even
    refresh the view (using the `__setup__` method), when the user interacts. It only calls the
    registered callbacks, one of which (the "Controller") is responsible for calling the `__setup__`
    method.
    """

    def __init__(
        self,
        master: tk.Widget,
        plot_type_var: tk.StringVar,
        axis_x_var: tk.StringVar,
        axis_y_var: tk.StringVar,
        axis_z_var: tk.StringVar,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(master, *args, **kwargs)

        self._settings_changed_callbacks: list[Callable[[], None]] = []
        """These callbacks are performed when the user makes a change to the settings."""

        # plot type selection
        self._plot_selector = tk.OptionMenu(self, plot_type_var, *PLOT_TYPES)
        self._plot_type_var = plot_type_var
        self._plot_type_var.set(LINE_PLOT)

        # axis selection
        self._axis_x_selector = tk.OptionMenu(self, axis_x_var, "")
        self._axis_y_selector = tk.OptionMenu(self, axis_y_var, "")
        self._axis_z_selector = tk.OptionMenu(self, axis_z_var, "")
        self._axis_x_var = axis_x_var
        self._axis_y_var = axis_y_var
        self._axis_z_var = axis_z_var

        self.__set_vars_trace_method(
            [
                self._plot_type_var,
                self._axis_x_var,
                self._axis_y_var,
                self._axis_z_var,
            ]
        )

    def __set_vars_trace_method(self, variables: list[tk.Variable]):
        for var in variables:
            var.trace_add("write", self.__notify_settings_changed_callbacks)

    def __setup__(
        self,
        current_plot_type: Optional[str] = None,
        shared_params: Optional[list[str]] = None,
        shared_values: Optional[list[str]] = None,
    ):
        """Redraw the needed widgets for the currently selected plot type.

        Args:
            current_plot_type: This parameter can be used to override the user's selection. If it is `None`
                the value currently stored in the corresponding `PlotModel.plot_type: tk.StringVar` is used.
            shared_params: A list of the names of the parameters shared by all currently selected measurements.
            shared_values: A list of the names of the measured values shared by all currently selected measurements.
        """
        # remove all widgets
        self.clear()

        self._logger.debug("Redrawing settings frame")

        # set default values
        if shared_params is None:
            shared_params = []

        self._logger.debug(f"Shared parameters: {shared_params}")

        if shared_values is None:
            shared_values = []

        self._logger.debug(f"Shared values: {shared_values}")

        if current_plot_type is not None:
            self._plot_type_var.set(current_plot_type)
        else:
            current_plot_type = self._plot_type_var.get()

        # start setup
        self._plot_selector = tk.OptionMenu(self, self._plot_type_var, *PLOT_TYPES)

        plot_label = tk.Label(self, anchor="w", text="Plot Type:")
        self.add_widget(plot_label, column=0, row=0, ipadx=10, ipady=0, sticky="we")
        self.add_widget(self._plot_selector, column=1, row=0, ipadx=10, ipady=0, sticky="ew")

        # This is needed for correct width and placement of widgets
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        for i in range(10):
            self.rowconfigure(i, weight=1)
            self.rowconfigure(i, pad=0)

        if current_plot_type == LINE_PLOT:
            self.__setup_line_plot(shared_values=shared_values)
        elif current_plot_type == CONTOUR or current_plot_type == CONTOUR_F:
            self.__setup_contour_plot(shared_values=shared_values, shared_params=shared_params)
        else:
            pass

    def __show_value_error(self, base_row: int, parameter: bool = False):
        """Shows an error message about non-matching values or parameters in the selected measurements."""
        error_message = tk.Label(
            self,
            anchor="s",
            text="Please select measurements whose \n"
            + ("parameters " if parameter else "measured values ")
            + "share at least 1 key"
            + ("(e.g. a sweep)." if parameter else "."),
        )
        self.add_widget(
            error_message, column=0, row=base_row, columnspan=2, rowspan=2, ipadx=10, ipady=0, sticky="snwe"
        )
        self._axis_x_var.set("")
        self._axis_y_var.set("")

    def __setup_axes_settings(self, values: list[list[str]], base_row: int, with_z: bool = False):
        """Adds the x- and y-axis selection widgets to the parent component.

        If the variables storing the axis selections are set to the empty string they will be set to
        the first and if available second element of the `shared_values` parameter.

        Args:
            values: A list of lists of possible values the axis selectors can take. The first list is used for
                the x-axis, the second list is used for the y-axis and if `with_z` is `True` the third list is
                used for the z-axis.
            base_row: In which row the elements should start to be placed in the parent grid.
            with_z: If `True` then the selector for the z-axis will be added as well.

        Raises:
            AssertionError if `values` has less than the required number of entries.
        """
        if with_z:
            assert len(values) >= 3
            assert len(values[2]) > 0
        else:
            assert len(values) >= 2
        assert len(values[0]) > 0 and len(values[1]) > 0

        axis_x_label = tk.Label(self, anchor="w", text="X-Axis:")
        axis_y_label = tk.Label(self, anchor="w", text="Y-Axis:")
        axis_z_label = tk.Label(self, anchor="w", text="Z-Axis:")

        if self._axis_x_var.get() == "" or self._axis_x_var.get() not in values[0]:
            self._axis_x_var.set(values[0][0])
        if self._axis_y_var.get() == "" or self._axis_y_var.get() not in values[1]:
            # because it's quite rare for someone to want to plot the same values on the x- and y-axis,
            # the y-axis selector is set to the second entry of the values if it exists
            self._axis_y_var.set(values[1][0 if values[0] != values[1] else 1])
        if with_z and (self._axis_z_var.get() == "" or self._axis_z_var.get() not in values[2]):
            self._axis_z_var.set(values[2][0 if values[0] != values[2] else 1])

        self._axis_x_selector = tk.OptionMenu(self, self._axis_x_var, *values[0])
        self._axis_y_selector = tk.OptionMenu(self, self._axis_y_var, *values[1])
        if with_z:
            self._axis_z_selector = tk.OptionMenu(self, self._axis_z_var, *values[2])

        self.add_widget(axis_x_label, column=0, row=base_row, sticky="we")
        self.add_widget(self._axis_x_selector, column=1, row=base_row, sticky="ew")
        self.rowconfigure(base_row, weight=0)

        self.add_widget(axis_y_label, column=0, row=base_row + 1, sticky="we")
        self.add_widget(self._axis_y_selector, column=1, row=base_row + 1, sticky="ew")
        self.rowconfigure(base_row + 1, weight=0)

        if with_z:
            self.add_widget(axis_z_label, column=0, row=base_row + 2, sticky="we")
            self.add_widget(self._axis_z_selector, column=1, row=base_row + 2, sticky="ew")
            self.rowconfigure(base_row + 1, weight=0)

    def __setup_contour_plot(self, shared_values: list[str], shared_params: list[str], base_row: int = 2):
        """Sets up the components needed for a contour-plot.

        Args:
            shared_values: A list of the names of the values shared by all selected measurements.
            shared_params: A list of the names of the parameters shared by all selected measurements.
            base_row: In which row of the parent grid the setting widgets are drawn.
        """
        if len(shared_values) == 0:
            # If there are no shared values, there really isn't anything to plot, so we don't draw any settings
            self.__show_value_error(base_row=base_row)
            return

        if len(shared_params) == 0:
            # If there are no shared parameters, we can't use a contour plot (maybe we somehow change this in the future,
            # to allow values instead of parameters to be the y-axis)
            self.__show_value_error(base_row=base_row, parameter=True)
            return

        self.__setup_axes_settings(
            values=[shared_values, shared_params, shared_values], base_row=base_row, with_z=True
        )

    def __setup_line_plot(self, shared_values: list[str], base_row: int = 2):
        """Sets up the components needed for a line-plot.

        Args:
            shared_values: A list of the names of the values shared by all selected measurements.
            base_row: In which row of the parent grid the setting widgets are drawn.
        """
        if len(shared_values) == 0:
            # If there are no shared values, there really isn't anything to plot, so we don't draw any settings
            self.__show_value_error(base_row=base_row)
            return

        self.__setup_axes_settings(values=[shared_values, shared_values], base_row=base_row)

    def add_settings_changed_callback(self, callback: Callable[[], None]):
        """Adds a callback being notified when a setting is changed by the user.

        If the callback was already added previously, nothing happens.
        """
        if callback not in self._settings_changed_callbacks:
            self._settings_changed_callbacks.append(callback)

    def remove_settings_changed_callback(self, callback: Callable[[], None]):
        """Removes a callback previously added using `add_settings_changed_callback`.

        If the given callback was not previously added, nothing happens.
        """
        if callback in self._settings_changed_callbacks:
            self._settings_changed_callbacks.remove(callback)

    def __notify_settings_changed_callbacks(self, *_) -> None:
        self._logger.debug("Plot-settings changed: Notifying callbacks.")
        for callback in self._settings_changed_callbacks:
            callback()
