#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable, Optional

import tkinter as tk
import tktooltip as tktt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.Plotting.PlotConstants import *

import re


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
            buckets_count_var=plot_model.contour_bucket_count,
            interpolation_type_var=plot_model.contour_interpolation_type,
            axis_bound_type_var=plot_model.axis_bound_types,
            axis_bounds=plot_model.axis_bounds,
            data_bound_var=plot_model.data_bound_set,
            data_bounds=plot_model.data_bounds,
            color_map_var=plot_model.color_map_name,
            legend_elements=plot_model.legend_elements,
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
        buckets_count_var: tk.IntVar,
        interpolation_type_var: tk.StringVar,
        axis_bounds: list[tuple[float, float]],
        axis_bound_type_var: tk.StringVar,
        data_bound_var: tk.BooleanVar,
        data_bounds: list[tuple[float, float]],
        color_map_var: tk.StringVar,
        legend_elements: list[str],
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

        # plot options
        self._bucket_count_entry = tk.Entry(self)
        self._bucket_count_var = buckets_count_var
        self._interpolation_var = interpolation_type_var
        self._axis_bounds = axis_bounds
        self._axis_bound_types = axis_bound_type_var
        self._data_bounds = data_bounds
        self._use_data_bounds = data_bound_var
        self._color_map = color_map_var

        # legend options
        self._legend_options = legend_elements
        self._legend_changed_callbacks: list[Callable[[None], None]] = []

        self.__set_vars_trace_method(
            [
                self._plot_type_var,
                self._axis_x_var,
                self._axis_y_var,
                self._axis_z_var,
                self._interpolation_var,
                self._axis_bound_types,
                self._color_map,
            ]
        )

        # temporaries
        self._last_shared_params: list[str] = []
        self._last_shared_values: list[str] = []
        self._last_unequal_params: list[str] = []

    def __set_vars_trace_method(self, variables: list[tk.Variable]):
        for var in variables:
            var.trace_add("write", self.__notify_settings_changed_callbacks)

    def _draw_general(self):
        general_window = CustomFrame(self)
        general_window.title = "General Settings"

        self._plot_selector = tk.OptionMenu(general_window, self._plot_type_var, *PLOT_TYPES)
        plot_label = tk.Label(general_window, anchor="w", text="Plot Type:")

        general_window.add_widget(plot_label, column=0, row=0, ipadx=10, ipady=0, sticky="we")
        general_window.add_widget(self._plot_selector, column=1, row=0, ipadx=10, ipady=0, sticky="ew")
        general_window.columnconfigure(0, weight=1)
        general_window.columnconfigure(1, weight=1)

        self.add_widget(general_window, row=0, column=0, ipadx=10, ipady=0, sticky="we")

    def __setup__(
        self,
        current_plot_type: Optional[str] = None,
        shared_params: Optional[list[str]] = None,
        shared_values: Optional[list[str]] = None,
        unequal_params: Optional[list[str]] = None,
    ):
        """Redraw the needed widgets for the currently selected plot type.

        Args:
            current_plot_type: This parameter can be used to override the user's selection. If it is `None`
                the value currently stored in the corresponding `PlotModel.plot_type: tk.StringVar` is used.
            shared_params: A list of the names of the parameters shared by all currently selected measurements.
            shared_values: A list of the names of the measured values shared by all currently selected measurements.
            unequal_params: A list of the names of the parameters unequal across the currently selected measurements.
        """
        # remove all widgets
        self.clear()

        self._logger.debug("Redrawing settings frame")

        # set default values
        if shared_params is None:
            shared_params = self._last_shared_params
        else:
            self._last_shared_params = shared_params.copy()

        self._logger.debug(f"Shared parameters: {shared_params}")

        if shared_values is None:
            shared_values = self._last_shared_values
        else:
            self._last_shared_values = shared_values.copy()

        self._logger.debug(f"Shared values: {shared_values}")

        if unequal_params is None:
            unequal_params = self._last_unequal_params
        else:
            self._last_unequal_params = unequal_params

        self._logger.debug(f"Unequal parameters: {unequal_params}")

        if current_plot_type is not None:
            self._plot_type_var.set(current_plot_type)
        else:
            current_plot_type = self._plot_type_var.get()

        # start setup
        self._draw_general()

        # This is needed for correct width and placement of widgets
        self.columnconfigure(0, weight=1)
        for i in range(10):
            self.rowconfigure(i, weight=1)
            self.rowconfigure(i, pad=0)

        if current_plot_type == LINE_PLOT:
            lowest_row = self.__setup_line_plot(shared_values=shared_values, unequal_params=unequal_params)
        elif current_plot_type == CONTOUR or current_plot_type == CONTOUR_F:
            lowest_row = self.__setup_contour_plot(shared_values=shared_values, unequal_params=unequal_params)
        else:
            lowest_row = 0

        if lowest_row == 0:
            return

        self.__setup_design(lowest_row + 1)

    def __setup_line_plot(self, shared_values: list[str], unequal_params: list[str], base_row: int = 2) -> int:
        """Sets up the components needed for a line-plot.

        Args:
            shared_values: A list of the names of the values shared by all selected measurements.
            unequal_params: A list of the names of the parameters unequal across all selected measurements.
            base_row: In which row of the parent grid the setting widgets are drawn.
        Returns:
            The index of the lowest used row
        """
        if len(shared_values) == 0:
            # If there are no shared values, there really isn't anything to plot, so we don't draw any settings
            self.__show_value_error(base_row=base_row)
            return 0

        self.__setup_axes_settings(values=[shared_values, shared_values], base_row=base_row)

        self.__setup_legend(base_row=base_row + 1, unequal_params=unequal_params)

        return base_row + 1

    def __setup_contour_plot(self, shared_values: list[str], unequal_params: list[str], base_row: int = 2) -> int:
        """Sets up the components needed for a contour-plot.

        Args:
            shared_values: A list of the names of the values shared by all selected measurements.
            unequal_params: A list of the names of the parameters unequal across all selected measurements.
            base_row: In which row of the parent grid the setting widgets are drawn.
        Returns:
            The index of the lowest used row or 0 if nothing was drawn
        """
        if len(shared_values) == 0:
            # If there are no shared values, there really isn't anything to plot, so we don't draw any settings
            self.__show_value_error(base_row=base_row)
            return 0

        if len(unequal_params) == 0:
            # If there are no shared parameters, we can't use a contour plot (maybe we somehow change this in the future,
            # to allow values instead of parameters to be the y-axis)
            self.__show_value_error(base_row=base_row, parameter=True)
            return 0

        self.__setup_axes_settings(
            values=[shared_values, unequal_params, shared_values], base_row=base_row, with_z=True
        )

        self.__setup_interpolation(base_row + 1)

        return base_row + 1

    def __show_value_error(self, base_row: int, parameter: bool = False):
        """Shows an error message about non-matching values or parameters in the selected measurements."""
        error_message = tk.Label(
            self,
            anchor="s",
            text="Please select measurements whose \n"
            + ("parameters " if parameter else "measured values ")
            + "share at least 1 key"
            + (" (e.g. a sweep)." if parameter else ".")
            + (
                "\nMake sure there is at least one parameter\nwhose values differ in at least one measurement."
                if parameter
                else ""
            ),
        )
        self.add_widget(error_message, column=0, row=base_row, rowspan=2, ipadx=10, ipady=0, sticky="snwe")
        self._axis_x_var.set("")
        self._axis_y_var.set("")
        self._axis_z_var.set("")

    def __setup_interpolation(self, base_row: int):
        interp_container = CustomFrame(self)
        interp_container.title = "Contour Settings"

        if self._interpolation_var.get() == "":
            # set default value
            self._interpolation_var.set(INTERPOLATE_TYPES[0])

        interpolation_label = tk.Label(interp_container, anchor="w", text="Interpolation Type:")
        interpolation_menu = tk.OptionMenu(interp_container, self._interpolation_var, *INTERPOLATE_TYPES)
        interp_container.add_widget(interpolation_label, column=0, row=0, sticky="we")
        interp_container.add_widget(interpolation_menu, column=1, row=0, sticky="ew")
        interp_container.rowconfigure(0, weight=0)
        tktt.ToolTip(
            interpolation_label,
            msg="This option controls what to do if some measurements have a more densely populated x-axis than others.",
            delay=1.0,
        )
        if self._interpolation_var.get() == INTERPOLATE_NAN:
            msg = "Fill missing values with NAN.\nThis will result in a white color."
        else:
            msg = "Lineraly interpolate between\nthe next two closest existing values."
        tktt.ToolTip(interpolation_menu, msg=msg, delay=1.0)

        buckets_label = tk.Label(interp_container, anchor="w", text="No of Buckets:")
        self._bucket_count_entry = tk.Entry(
            interp_container,
            textvariable=self._bucket_count_var,
            validate="key",
            validatecommand=(self.register(self._validate_positive_non_empty_int), "%d", "%P"),
            invalidcommand=(self.register(self._on_invalid), "%P"),
            justify="right",
        )

        self._bucket_count_entry.bind("<FocusOut>", lambda *_: self.__notify_settings_changed_callbacks())
        self._bucket_count_entry.bind("<Return>", lambda *_: self.focus())
        interp_container.add_widget(buckets_label, column=0, row=1, sticky="we")
        interp_container.add_widget(self._bucket_count_entry, column=1, row=1, sticky="ew")
        interp_container.rowconfigure(1, weight=0)

        self.add_widget(interp_container, column=0, row=base_row, sticky="we")
        interp_container.columnconfigure(0, weight=1)
        interp_container.columnconfigure(1, weight=1)

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

        axis_container = CustomFrame(self)
        axis_container.title = "Data Settings"

        axis_x_label = tk.Label(axis_container, anchor="w", text="X-Axis:")
        axis_y_label = tk.Label(axis_container, anchor="w", text="Y-Axis:")
        axis_z_label = tk.Label(axis_container, anchor="w", text="Z-Axis:")

        # set default values for option menus
        if self._axis_x_var.get() == "" or self._axis_x_var.get() not in values[0]:
            self._axis_x_var.set(values[0][0])
        if self._axis_y_var.get() == "" or self._axis_y_var.get() not in values[1]:
            # because it's quite rare for someone to want to plot the same values on the x- and y-axis,
            # the y-axis selector is set to the second entry of the values if it exists
            self._axis_y_var.set(values[1][0 if values[0] != values[1] else 1])
        if with_z and (self._axis_z_var.get() == "" or self._axis_z_var.get() not in values[2]):
            self._axis_z_var.set(values[2][0 if values[0] != values[2] else 1])

        self._axis_x_selector = tk.OptionMenu(axis_container, self._axis_x_var, *values[0])
        self._axis_y_selector = tk.OptionMenu(axis_container, self._axis_y_var, *values[1])
        if with_z:
            self._axis_z_selector = tk.OptionMenu(axis_container, self._axis_z_var, *values[2])

        axis_container.add_widget(axis_x_label, column=0, row=0, sticky="we")
        axis_container.add_widget(self._axis_x_selector, column=1, row=0, sticky="ew")
        axis_container.rowconfigure(0, weight=0)

        axis_container.add_widget(axis_y_label, column=0, row=1, sticky="we")
        axis_container.add_widget(self._axis_y_selector, column=1, row=1, sticky="ew")
        axis_container.rowconfigure(1, weight=0)

        if with_z:
            axis_container.add_widget(axis_z_label, column=0, row=2, sticky="we")
            axis_container.add_widget(self._axis_z_selector, column=1, row=2, sticky="ew")
            axis_container.rowconfigure(2, weight=0)

        axis_container.columnconfigure(0, weight=1)
        axis_container.columnconfigure(1, weight=1)

        self.add_widget(axis_container, column=0, row=base_row, sticky="we")

    def __setup_legend(self, base_row: int, unequal_params: list[str]):
        legend_container = CustomFrame(self)
        legend_container.title = "Legend Settings"

        legend_label = tk.Label(legend_container, anchor="w", text="Legend elements:")
        legend_container.add_widget(legend_label, row=0, column=0, ipadx=10, ipady=0, sticky="we")

        legend_options = ["Measurement name", "Measurement ID"] + unequal_params
        checkbox_variables = [tk.IntVar() for _ in range(len(legend_options))]

        def _on_legend_change():
            self._legend_options.clear()
            self._legend_options += [
                option for option, var in zip(legend_options, checkbox_variables) if var.get() == 1
            ]
            for callback in self._legend_changed_callbacks:
                callback()

        for i, (option, var) in enumerate(zip(legend_options, checkbox_variables)):
            checkbox = tk.Checkbutton(
                legend_container, text=option, variable=var, onvalue=1, offvalue=0, command=_on_legend_change
            )
            legend_container.add_widget(checkbox, row=1 + i, column=1, sticky="w", ipadx=10, ipady=0)
            legend_container.rowconfigure(i + 1, pad=0)
            legend_container.rowconfigure(i + 1, weight=0)

        self.add_widget(legend_container, column=0, row=base_row, sticky="we")
        legend_container.columnconfigure(0, weight=1)
        legend_container.columnconfigure(1, weight=1)

    @property
    def legend_changed_callbacks(self):
        return self._legend_changed_callbacks

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

    def _validate_positive_non_empty_int(self, mode: str, text: str) -> bool:
        """Allows only ints in the text field.

        Args:
            mode: an integer specifying the type of change ('%d' in tk)
            text: the new value of the entry after the change ('%P' in tk)

        Returns:
            false if there was an invalid insertion, true otherwise
        """
        if int(mode) == 0:
            # mode == 0 means deletion
            return text != ""  # uncomment this line if the entry shouldn't be emptyable
            # return True # uncomment this line if the entry should be emptyable
        elif int(mode) == 1:
            # mode == 1 means insertion
            pattern = r"[0-9]*"
            return re.fullmatch(pattern, text) is not None
        else:
            return True

    def _validate_float(self, mode: str, text: str) -> bool:
        """Allows only ints and floats in the text field.

        Args:
            mode: an integer specifying the type of change ('%d' in tk)
            text: the new value of the entry after the change ('%P' in tk)

        Returns:
            false if there was an invalid insertion, true otherwise
        """
        if int(mode) == 1:
            # mode == 1 means insertion
            optional_fraction = r"[0-9]+(?:[.][0-9]*)?"
            optional_whole = r"[.][0-9]+"
            pattern = r"[+-]?(" + optional_fraction + "|" + optional_whole + r")"
            ret = re.fullmatch(pattern, text)
            return ret is not None
        else:
            return True

    def _on_invalid(self, text: str) -> None:
        """Is executed if an illegal string would be placed inside the entry

        Args:
            text: the new value of the entry if the change had happened ('%P' in tk)
        """
        if text == "":
            # we first insert and then delete because otherwise the validation function would return
            # False again which would result in an endless recursion
            self._bucket_count_entry.insert(0, "0")
            self._bucket_count_entry.delete(1, "end")
            # because we changed the value of entry inside the validation or invalid function, validate
            # is set to 'none', so we reset it here.
            self._bucket_count_entry.config(validate="key")

    def __setup_design(self, base_row: int):
        design_container = CustomFrame(self)
        design_container.title = "Design Settings"

        color_label = tk.Label(design_container, anchor="w", text="Colormap for plots:")
        color_menu = tk.OptionMenu(design_container, self._color_map, *COLOR_MAPS)
        design_container.add_widget(color_label, column=0, row=0, ipadx=10, ipady=0, sticky="we")
        design_container.add_widget(color_menu, column=1, row=0, ipadx=10, ipady=0, sticky="ew")

        bound_label = tk.Label(design_container, anchor="w", text="Axis bounds type:")
        bound_menu = tk.OptionMenu(design_container, self._axis_bound_types, *AXIS_BOUND_TYPES)
        design_container.add_widget(bound_label, column=0, row=1, ipadx=10, ipady=0, sticky="we")
        design_container.add_widget(bound_menu, column=1, row=1, ipadx=10, ipady=0, sticky="ew")

        design_container.rowconfigure(0, weight=0)
        design_container.rowconfigure(1, weight=0)

        if self._axis_bound_types.get() == AXIS_BOUND_CUSTOM:

            def set_new_data_bounds(zmin, zmax):
                z_old = self._data_bounds[0]
                self._data_bounds.clear()
                self._data_bounds.append(
                    (zmin if zmin is not None else z_old[0], zmax if zmax is not None else z_old[1])
                )

            def set_new_axis_bounds(xmin, xmax, ymin, ymax):
                x_old = self._axis_bounds[0]
                y_old = self._axis_bounds[1]
                self._axis_bounds.clear()
                self._axis_bounds.append(
                    (xmin if xmin is not None else x_old[0], xmax if xmax is not None else x_old[1])
                )
                self._axis_bounds.append(
                    (ymin if ymin is not None else y_old[0], ymax if ymax is not None else y_old[1])
                )

            validate = (self.register(self._validate_float), "%d", "%P")
            text_width = 8

            msg = "Define the lowest and highest coordinate yourself."
            x_frame = tk.Frame(design_container)
            x_frame.columnconfigure(0, weight=1)
            x_frame.columnconfigure(1, weight=1)

            x_min_var = tk.StringVar()
            x_min_var.set(f"{self._axis_bounds[0][0]:.1f}")
            x_min_frame = tk.Frame(x_frame)
            x_min_frame.columnconfigure(0, weight=1)
            x_min_frame.columnconfigure(1, weight=1)
            x_min_label = tk.Label(x_min_frame, text="x-min", anchor="w")
            x_min_entry = tk.Entry(
                x_min_frame,
                textvariable=x_min_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            x_min_label.grid(column=0, row=0, sticky="we")
            x_min_entry.grid(column=1, row=0, sticky="ew")

            x_max_var = tk.StringVar()
            x_max_var.set(f"{self._axis_bounds[0][1]:.1f}")
            x_max_frame = tk.Frame(x_frame)
            x_max_frame.columnconfigure(0, weight=1)
            x_max_frame.columnconfigure(1, weight=1)
            x_max_label = tk.Label(x_max_frame, text="x-max", anchor="w")
            x_max_entry = tk.Entry(
                x_max_frame,
                textvariable=x_max_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            x_max_label.grid(column=0, row=0, sticky="we")
            x_max_entry.grid(column=1, row=0, sticky="ew")

            x_min_frame.grid(column=0, row=0)
            x_max_frame.grid(column=1, row=0)

            y_frame = tk.Frame(design_container)
            y_frame.columnconfigure(0, weight=1)
            y_frame.columnconfigure(1, weight=1)

            y_min_frame = tk.Frame(y_frame)
            y_min_frame.columnconfigure(0, weight=1)
            y_min_frame.columnconfigure(1, weight=1)
            y_min_var = tk.StringVar()
            y_min_var.set(f"{self._axis_bounds[1][0]:.1f}")
            y_min_label = tk.Label(y_min_frame, text="y-min", anchor="w")
            y_min_entry = tk.Entry(
                y_min_frame,
                textvariable=y_min_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            y_min_label.grid(column=0, row=0, sticky="we")
            y_min_entry.grid(column=1, row=0, sticky="ew")

            y_max_frame = tk.Frame(y_frame)
            y_max_frame.columnconfigure(0, weight=1)
            y_max_frame.columnconfigure(1, weight=1)
            y_max_var = tk.StringVar()
            y_max_var.set(f"{self._axis_bounds[1][1]:.1f}")
            y_max_label = tk.Label(y_max_frame, text="y-max", anchor="w")
            y_max_entry = tk.Entry(
                y_max_frame,
                textvariable=y_max_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            y_max_label.grid(column=0, row=0, sticky="we")
            y_max_entry.grid(column=1, row=0, sticky="ew")

            y_min_frame.grid(column=0, row=0)
            y_max_frame.grid(column=1, row=0)

            z_frame = tk.Frame(design_container)
            z_frame.columnconfigure(0, weight=1)
            z_frame.columnconfigure(1, weight=1)

            z_min_var = tk.StringVar()
            z_min_var.set(f"{self._data_bounds[0][0]:.1f}")
            z_min_frame = tk.Frame(z_frame)
            z_min_frame.columnconfigure(0, weight=1)
            z_min_frame.columnconfigure(1, weight=1)
            z_min_label = tk.Label(z_min_frame, text="z-min", anchor="w")
            z_min_entry = tk.Entry(
                z_min_frame,
                textvariable=z_min_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            z_min_label.grid(column=0, row=0, sticky="we")
            z_min_entry.grid(column=1, row=0, sticky="ew")

            z_max_var = tk.StringVar()
            z_max_var.set(f"{self._data_bounds[0][1]:.1f}")
            z_max_frame = tk.Frame(z_frame)
            z_max_frame.columnconfigure(0, weight=1)
            z_max_frame.columnconfigure(1, weight=1)
            z_max_label = tk.Label(z_max_frame, text="z-max", anchor="w")
            z_max_entry = tk.Entry(
                z_max_frame,
                textvariable=z_max_var,
                justify="right",
                validate="key",
                validatecommand=validate,
                width=text_width,
            )
            z_max_label.grid(column=0, row=0, sticky="we")
            z_max_entry.grid(column=1, row=0, sticky="ew")

            z_min_frame.grid(column=0, row=0)
            z_max_frame.grid(column=1, row=0)

            use_z_checkbox = tk.Checkbutton(
                design_container,
                text="Constrain z-axis",
                variable=self._use_data_bounds,
                onvalue=True,
                offvalue=False,
                command=lambda *_: self.__setup__(),
            )

            update_button = tk.Button(
                design_container,
                text="Update Settings",
                command=lambda *_: self.__notify_settings_changed_callbacks(),
            )

            design_container.add_widget(x_frame, column=0, row=2, sticky="we")
            design_container.add_widget(y_frame, column=1, row=2, sticky="ew")
            design_container.add_widget(use_z_checkbox, column=0, row=3, sticky="w")
            button_row = 3
            if self._use_data_bounds.get():
                design_container.add_widget(z_frame, column=1, row=3, sticky="ew")
                button_row += 1
            design_container.add_widget(update_button, column=1, row=button_row, sticky="we")
            design_container.rowconfigure(2, weight=0)

            x_min_var.trace_add(
                "write",
                lambda *_: set_new_axis_bounds(
                    float(x_min_var.get()) if x_min_var.get() != "" else None, None, None, None
                ),
            )
            x_max_var.trace_add(
                "write",
                lambda *_: set_new_axis_bounds(
                    None, float(x_max_var.get()) if x_max_var.get() != "" else None, None, None
                ),
            )
            y_min_var.trace_add(
                "write",
                lambda *_: set_new_axis_bounds(
                    None, None, float(y_min_var.get()) if y_min_var.get() != "" else None, None
                ),
            )
            y_max_var.trace_add(
                "write",
                lambda *_: set_new_axis_bounds(
                    None, None, None, float(y_max_var.get()) if y_max_var.get() != "" else None
                ),
            )
            z_min_var.trace_add(
                "write",
                lambda *_: set_new_data_bounds(float(z_min_var.get()) if z_min_var.get() != "" else None, None),
            )
            z_max_var.trace_add(
                "write",
                lambda *_: set_new_data_bounds(None, float(z_max_var.get()) if z_max_var.get() != "" else None),
            )

        else:
            msg = "Let matplotlib figure out the coordinates."
        tktt.ToolTip(bound_menu, msg=msg, delay=0.5)

        self.add_widget(design_container, column=0, row=base_row, sticky="we")
        design_container.columnconfigure(0, weight=1)
        design_container.columnconfigure(1, weight=1)
