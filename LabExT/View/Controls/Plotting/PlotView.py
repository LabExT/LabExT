#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.Plotting.PlotConstants import *


if TYPE_CHECKING:
    from LabExT.View.Controls.Plotting.PlotModel import PlotModel
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
else:
    PlotModel = None
    Figure = None
    Axes = None


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
        *args,
        **kwargs,
    ) -> None:
        super().__init__(master, *args, **kwargs)

        self._settings_changed_callbacks: list[callable] = []
        """These callbacks are performed when the user makes a change to the settings."""

        # plot type selection
        self._plot_selector = tk.OptionMenu(self, plot_type_var, *PLOT_TYPES)
        self._plot_type_var = plot_type_var
        self._plot_type_var.set(LINE_PLOT)

        # axis selection
        self._axis_x_selector = tk.OptionMenu(self, axis_x_var, "")
        self._axis_y_selector = tk.OptionMenu(self, axis_y_var, "")
        self._axis_x_var = axis_x_var
        self._axis_y_var = axis_y_var

        self.__set_vars_trace_method([self._plot_type_var, self._axis_x_var, self._axis_y_var])

    def __set_vars_trace_method(self, variables: list[tk.Variable]):
        for var in variables:
            var.trace_add("write", self.__notify_settings_changed_callbacks)

    def __setup__(
        self, current_plot_type: str = None, shared_params: list[str] = None, shared_values: list[str] = None
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
        elif current_plot_type == CONTOUR:
            pass
        else:
            pass

    def __setup_line_plot(self, shared_values: list[str], base_row: int = 2):
        """Sets up the components needed for a line-plot.

        Args:
            shared_values: A list of the names of the values shared by all selected measurements.
        """
        if len(shared_values) == 0:
            error_message = tk.Label(
                self,
                anchor="s",
                text="Please select measurements whose \n" + "measured values share at least 1 key.",
            )
            self.add_widget(
                error_message, column=0, row=base_row, columnspan=2, rowspan=2, ipadx=10, ipady=0, sticky="snwe"
            )
            self._axis_x_var.set("")
            self._axis_y_var.set("")
            return

        axis_x_label = tk.Label(self, anchor="w", text="X-Axis:")
        axis_y_label = tk.Label(self, anchor="w", text="Y-Axis:")

        if self._axis_x_var.get() == "":
            self._axis_x_var.set(shared_values[0])
        if self._axis_y_var.get() == "":
            self._axis_y_var.set(shared_values[0 if len(shared_values) == 1 else 1])

        self._axis_x_selector = tk.OptionMenu(self, self._axis_x_var, *shared_values)
        self._axis_y_selector = tk.OptionMenu(self, self._axis_y_var, *shared_values)

        self.add_widget(axis_x_label, column=0, row=base_row, sticky="we")
        self.add_widget(axis_y_label, column=0, row=base_row + 1, sticky="we")
        self.add_widget(self._axis_x_selector, column=1, row=base_row, sticky="ew")
        self.add_widget(self._axis_y_selector, column=1, row=base_row + 1, sticky="ew")

        self.rowconfigure(base_row, weight=0)
        self.rowconfigure(base_row + 1, weight=0)

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
