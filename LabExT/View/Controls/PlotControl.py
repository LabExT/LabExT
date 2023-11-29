#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import queue
import threading
from functools import wraps, partial
from tkinter import Frame, BOTH, TOP

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure

from LabExT.ViewModel.Utilities.ObservableList import ObservableList


class PlotData(object):
    """This holds the data for a plot. It contains the x and y values as well as the type of plot.
    Keeps track of changes: If x or y change it will alert the plot to update."""
    _x = None

    @property
    def color(self):
        return  self._color

    @color.setter
    def color(self, val):
        self._color = val

    @property
    def x(self):
        """Gets the x values of the plot."""
        return self._x

    @x.setter
    def x(self, value):
        """Sets the x values of the plot and updates them."""
        if type(self._x) is ObservableList:  # if the old value was observable stop listening for changes
            self._x.item_added.remove(self.__item_changed__)
            self._x.item_removed.remove(self.__item_changed__)

        if type(value) is ObservableList:  # if the value it observable start listening for changes
            value.item_added.append(self.__item_changed__)
            value.item_removed.append(self.__item_changed__)

        self._x = value
        self.__update__()

    _y = None

    @property
    def y(self):
        """Gets the y values of the plot."""
        return self._y

    @y.setter
    def y(self, value):
        """Sets the y values of the plot and updates them."""
        if type(self._y) is ObservableList:  # if the old value was observable stop listening for changes
            self._y.item_added.remove(self.__item_changed__)
            self._y.item_removed.remove(self.__item_changed__)

        if type(value) is ObservableList:  # if the value is observable start listening for changes
            value.item_added.append(self.__item_changed__)
            value.item_removed.append(self.__item_changed__)

        self._y = value
        self.__update__()

    def __init__(self, x=None, y=None, plot_type='plot', color=None, **plot_args):
        self.data_changed = list()
        self.x = x
        self.y = y
        self.plot_type = plot_type
        self.line_handle = None
        self.plot_args = plot_args
        self.plot_control = None
        self._color = color

    def __item_changed__(self, item):
        """Gets called in case that x and y are observable and one of them has changed"""
        self.__update__()

    def __update__(self):
        for callback in self.data_changed:
            callback(self)


def execute_in_plotting_thread(func):
    """ This wrapper is used inside PlotControl to force execution
     of the function inside the thread which created the plot. """
    @wraps(func)
    def decorator(plot_control, *args, **kwargs):
        if threading.current_thread() == plot_control.plotting_thread:
            # if the caller of this function is already in the plotting thread, we execute the function directly
            return func(plot_control, *args, **kwargs)
        else:
            # the caller is NOT in the plotting thread, send the function to the plotting thread for execution
            # functools.partial creates a "standalone" object of this function which can be sent via a queue
            # also we are using a threading.Lock such that only one foreign thread can execute something in the
            # plotting thread at the same time
            with plot_control.foreign_exec_lock:
                plot_control.send_queue.put(partial(func, plot_control, *args, **kwargs))
                return_values = plot_control.return_queue.get(True)  # blocking call
                return return_values
    return decorator


class PlotControl(Frame):
    """Displays a plot which can be controlled with a plot data collection."""

    #
    # setter and getters for: title, hold, show_grid, axis_limit_margin_fraction, data_source
    #

    @property
    def title(self):
        """Gets the title of the plot."""
        return self._title

    @title.setter
    @execute_in_plotting_thread
    def title(self, t):
        """Sets the title of the plot."""
        self._title = t
        if self.ax is not None:
            if self._title is not None:
                self.ax.set_title(self._title)
            else:
                self.ax.set_title('')

    @property
    def hold(self):
        """Gets if the plots should be overwritten when a new plot is added."""
        return self._hold

    @hold.setter
    @execute_in_plotting_thread
    def hold(self, h):
        """Sets if the plots should be overwritten when a new plot is added."""
        self._hold = h
        if self.ax is not None:
            self.ax.hold = h

    _show_grid = False

    @property
    def show_grid(self):
        """Gets if grid is being displayed."""
        return self._show_grid

    @show_grid.setter
    @execute_in_plotting_thread
    def show_grid(self, g):
        """Sets if grid is being displayed."""
        self._show_grid = g
        if self.ax is not None:
            if self._show_grid:
                self.ax.grid(color='k', linestyle='-', linewidth=0.5)
            else:
                self.ax.grid(color='k', linestyle='-', linewidth=0)

    _axis_limit_margin_fraction = 0.1

    @property
    def axis_limit_margin_fraction(self):
        """Gets the fraction of the axis span that is added before and after the data.
        (Only used if autoscale is enabled)"""
        return self._axis_limit_margin_fraction

    @axis_limit_margin_fraction.setter
    @execute_in_plotting_thread
    def axis_limit_margin_fraction(self, h):
        """Sets the fraction of the axis span that is added before and after the data.
                (Only used if autoscale is enabled)"""
        self._axis_limit_margin_fraction = h
        self.__handle_scaling__()

    @property
    def min_y_axis_span(self):
        """ Gets the current setting of the minimum y-axis span. (Only used if autoscale is enabled, overrides
        axis_limit_margin_fraction property). """
        return self._min_y_axis_span

    @min_y_axis_span.setter
    @execute_in_plotting_thread
    def min_y_axis_span(self, ydiff):
        """ Sets the current setting of the minimum y-axis span. (Only used if autoscale is enabled, overrides
        axis_limit_margin_fraction property)."""
        if ydiff is None:
            self._min_y_axis_span = None
        elif float(ydiff) > 0:
            self._min_y_axis_span = float(ydiff)
        else:
            raise ValueError("Minimum y axis span must be greater than 0 or None!")
        self.__handle_scaling__()

    _data_source = None

    @property
    def data_source(self):
        """Gets the plot data source of this plot."""
        return self._data_source

    @data_source.setter
    @execute_in_plotting_thread
    def data_source(self, source: ObservableList):
        """Sets the plot data source of this plot. (Will replace old plots if set)"""

        # if we replace an old data_source, we need to remove all callbacks in there
        if self._data_source is not None:
            self.__plot_clear__()
            for item in self._data_source:
                # disconnect callback method from items
                if not self._polling:
                    item.data_changed.remove(self.__plotdata_changed__)
            self._data_source.item_added.remove(self.__plotdata_added_to_ds__)
            self._data_source.item_removed.remove(self.__plotdata_removed_from_ds__)
            self._data_source.on_clear.remove(self.__ds_cleared__)

        if source is None:  # if the new source is none do nothing
            return

        # add callbacks when a new PlotData gets added to the data_source
        self._data_source = source  # set new source

        self._data_source.item_added.append(self.__plotdata_added_to_ds__)
        self._data_source.item_removed.append(self.__plotdata_removed_from_ds__)
        self._data_source.on_clear.append(self.__ds_cleared__)

        # register callback on every PlotData to listen for changes to it
        for item in self._data_source:
            if not self._polling:
                item.data_changed.append(self.__plotdata_changed__)
            item.plot_control = self

        self.__plot_setup__()  # plot the currently available data

    #
    # class methods
    #

    def __init__(self,
                 parent,
                 add_toolbar=False,
                 figsize=(5, 5),
                 dpi=100,
                 autoscale_axis=True,
                 add_legend=False,
                 polling_time_s=None,
                 onclick=None,
                 no_x_autoscale=False,
                 min_y_axis_span=None):
        """
        PlotControl: creates a frame with a plotting area in a Tkinter GUI environment.

        Example on how to create a plot and put it into a Tkinter grid somewhere:
        >> self._live_plot = PlotControl(parent=<parent>, add_toolbar=True, figsize=(5, 5), polling_time=.5)
        >> self._live_plot.title = 'Some Title'
        >> self._live_plot.show_grid = True
        >> self._live_plot.data_source = < an ObservableList containing PlotData >
        >> self._live_plot.grid(row=0, column=0, padx=10, pady=10, sticky='nswe')
        >> self._live_plot.rowconfigure(0, weight=1)
        >> self._live_plot.columnconfigure(0, weight=1)

        Parameters
        ----------
        parent
            the Tk parent
        add_toolbar
            (optional) boolean if you want the matplotlib toolbar
        figsize
            (optional) a 2-tuple of flaots giving the figure size of the plot in inches
        dpi
            (optional) int dpi of your figure
        autoscale_axis
            (optional) boolean if the axis should be automatically scaled or not
        add_legend
            (optional) if you want to show the legend, use the label="something" keyword argument on PlotData to specify
            the legend entry for this curve.
        polling_time_s
            (optional) float number in seconds what the redraw period of the plot is. Set to None for immediate
            redrawing on data changes (heavy on performance!)
        onclick
            (optional) function reference to callback to be executed on click onto plot
        no_x_autoscale
            (optional) defines whether the x axis should be autoscaled as well
        min_y_axis_span
            (optional) if given, the y-axis will never shrink below this span (this setting overrides the
            axis_limit_margin_fraction property). Must be positive float or None. Only applies to linear y-scales.
        """

        super(PlotControl, self).__init__(parent)  # call the parent controls constructor
        self._title = None
        self._hold = False
        self._root = parent  # keep a reference for the ui root
        self._enable_toolbar = add_toolbar  # member to store whether a plot toolbar should be added or not
        self._figsize = figsize  # figure size
        self._dpi = dpi  # dpi resolution
        self.autoscale_axis = autoscale_axis  # True = automatically calculate the axis limits to include all data
        self._enable_legend = add_legend  # should legend be added or not?
        self._onclick_cb = onclick  # Function that gets called when plot is clicked
        self._no_x_autoscale = no_x_autoscale
        self._min_y_axis_span = min_y_axis_span

        # set automatic updating time
        self._polling = (polling_time_s is not None)  # should the plot update on every change or poll for changes?
        if self._polling:
            # How long the plot waits between polling.
            self._polling_time_ms = int(polling_time_s * 1000)
        else:
            self._polling_time_ms = None
        self._polling_running = False  # flag to not start polling thread multiple times
        self._polling_kill_flag = False  # Gets set to true when the class is destroyed in order to stop polling

        # executing functions for foreign threads to make sure matplotlib is always accessed by the same thread
        self.plotting_thread = threading.current_thread()  # save reference to thread which owns the plots
        self.send_queue = queue.Queue()
        self.return_queue = queue.Queue()
        self.foreign_exec_lock = threading.Lock()
        self._root.after(self._foreign_function_execution_period_ms, self.__execute_foreign_functions__)

        self._x_label = "x"
        self._y_label = "y"

        self.__setup__()

    @execute_in_plotting_thread
    def __setup__(self):
        self._figure = Figure(figsize=self._figsize, dpi=self._dpi)  # define plot size
        self.ax = self._figure.add_subplot(111)  # add subplot and save reference
        self.ax.hold = self._hold

        self._canvas = FigureCanvasTkAgg(self._figure, self)  # add figure to canvas

        self._canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)  # place canvas
        self._canvas.draw()  # show canvas

        # draw toolbar if not switched off
        if self._enable_toolbar:
            self._toolbar = NavigationToolbar2Tk(self._canvas,self)  # enable plot toolbar
            self._toolbar.update()  # update toolbar
            self._canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)

        # connect _onclick function with button press event
        if self._onclick_cb is not None:
            self._canvas.mpl_connect('button_press_event', self._onclick)

        # start polling
        if self._polling and not self._polling_running:
            self._polling_kill_flag = False
            self._polling_running = True
            self._root.after(self._polling_time_ms, self.__polling__)

    @execute_in_plotting_thread
    def set_axes(self, x_ax_label, y_ax_label):
        self._x_label = x_ax_label
        self._y_label = y_ax_label
        self.__update_canvas__()

    #
    # timed redrawing functions, either because of data polling or function exeuctions by foreign threads
    #

    _foreign_function_execution_period_ms = 10

    def __execute_foreign_functions__(self):
        """
        Since matplotlib is NOT thread save, we must make sure that all functions which access matplotlib are
        actually executed from the same thread.
        This method periodically executes functions scheduled by other threads in the thread which created this plot.
        """
        try:
            foreign_function = self.send_queue.get(False)  # get function from queue, false=doesn't block
            return_parameters = foreign_function()  # run function from queue
            self.return_queue.put(return_parameters)
        except queue.Empty:
            pass
        # this reschedules this function to run again after 10ms
        self._root.after(self._foreign_function_execution_period_ms, self.__execute_foreign_functions__)

    def __polling__(self):
        """ Polls and updates data """
        if self._data_source is not None:
            for item in self._data_source:
                self.__plotdata_changed__(item)
        if not self._polling_kill_flag:
            # reschedule if not killed
            self._root.after(self._polling_time_ms, self.__polling__)
        else:
            # otherwise set running flag to false to signal completion
            self._polling_running = False

    def stop_polling(self):
        self._polling_kill_flag = True

    #
    # callbacks on plot_data or data_source changes
    #

    def _onclick(self, event):
        """
        Gets called when the user clicks on the plot. Runs the specified _onclick function if the user double-clicked
        the primary mouse button.

        :param event: The click event.
        """
        if event.dblclick and event.button == 1:
            self._onclick_cb()

    @execute_in_plotting_thread
    def __ds_cleared__(self):
        """Remove old plot"""
        if self._toolbar is not None:
            self._toolbar.pack_forget()
        self._canvas.get_tk_widget().pack_forget()

        # Setup new plot
        self.__setup__()

    @execute_in_plotting_thread
    def __plotdata_added_to_ds__(self, item: PlotData):
        """Gets called if a new plot data item is added to the plot data source."""
        self.__add_plot__(item)  # add plot to the canvas
        if not self._polling:
            item.data_changed.append(self.__plotdata_changed__)  # listen to data changes of this plot data item
        item.plot_control = self
        self.__update_canvas__()

    @execute_in_plotting_thread
    def __plotdata_removed_from_ds__(self, item: PlotData):
        """Gets called if a plot data item gets removed from the plot data source."""
        item.line_handle.remove()  # remove the plot from the canvas
        if not self._polling:
            item.data_changed.remove(self.__plotdata_changed__)  # stop listening to changes of this plot data item
        self.__update_canvas__()

    def sanitize_plot_data(self, plot_data: PlotData, sanitize_lengths=True):
        # do nothing if either the x or y data is set to None
        if plot_data.x is None or plot_data.y is None:
            return None, None
        # Copy our data into arrays that don't get updated by other threads anymore
        x_data = np.array([x for x in plot_data.x])  # get data for x axis
        y_data = np.array([y for y in plot_data.y])  # get data for y axis
        # If the shapes mismatch, we cut away the end of the longer list.
        if sanitize_lengths:
            if len(x_data) != len(y_data):
                min_len = min(len(x_data), len(y_data))
                x_data = x_data[:min_len]
                y_data = y_data[:min_len]
        # return sanitized lists
        return x_data, y_data

    @execute_in_plotting_thread
    def __plotdata_changed__(self, plot_data: PlotData):
        """Gets called if a plot data item gets changed. (e.g. the y collection is overwritten with new data)"""
        x_data, y_data = self.sanitize_plot_data(plot_data=plot_data)
        if x_data is None or y_data is None:
            return

        if type(plot_data.line_handle) is PathCollection:
            # case if plot is a scatter plot
            data = np.asarray([x_data, y_data]).transpose()  # prepare data such that it is compatible (2xN)
            plot_data.line_handle.set_offsets(data)  # update scatter plot with new data
        elif plot_data.line_handle is not None:
            # other plot types
            plot_data.line_handle.set_xdata(x_data)  # set x data
            plot_data.line_handle.set_ydata(y_data)  # set y data
            if plot_data.color is not None:
                plot_data.line_handle.set_color(plot_data.color)

        self.__update_canvas__()

    @execute_in_plotting_thread
    def __add_plot__(self, plot_data: PlotData):
        """Plots plot data according to their configuration."""

        x_data, y_data = self.sanitize_plot_data(plot_data=plot_data)
        if x_data is None or y_data is None:
            return

        if plot_data.plot_type == 'plot':
            if plot_data.color is None:
                plot_data.line_handle = self.ax.plot(x_data, y_data, **plot_data.plot_args)[0]
            else:
                plot_data.line_handle = self.ax.plot(x_data, y_data, color=plot_data.color, **plot_data.plot_args)[0]
        elif plot_data.plot_type == 'scatter':
            plot_data.line_handle = self.ax.scatter(x_data, y_data, **plot_data.plot_args)
        else:
            raise RuntimeError("Unknown plot type. Use either plot or scatter.")

        self.__update_canvas__()

    @execute_in_plotting_thread
    def __plot_clear__(self):
        """ Gets executed to clear all plots from the canvas. """
        for plot_data in self._data_source:
            lh = plot_data.line_handle
            if lh is not None:
                lh.remove()
        self.__update_canvas__()

    @execute_in_plotting_thread
    def __plot_setup__(self):
        """Gets executed to draw all the plots if a plot source has been specified.
        If plots are being done manually this method is not used."""
        if self.ax is None:  # do nothing if no base plot is present
            return
        for plot_data in self._data_source:
            self.__add_plot__(plot_data)  # plot all the given plot data
        self.__update_canvas__()

    #
    # helpers to redraw the canvas
    #

    @execute_in_plotting_thread
    def __update_canvas__(self):
        self.__handle_scaling__()  # setup proper axis scaling
        self.__handle_legend__()  # setup legend
        self.__handle_axes_labels__()  # setup axes labels
        assert threading.current_thread() == self.plotting_thread, "Cannot redraw canvas from other thread than plot " \
                                                                   "owner. This would result in a segfault. "
        self._canvas.draw()  # redraw canvas

    @execute_in_plotting_thread
    def __handle_scaling__(self):
        """If autoscaling is enabled this method defines the appropriate axis ranges."""
        if not self.autoscale_axis \
                or self.ax is None \
                or self._data_source is None \
                or len(self._data_source) == 0:
            return  # do nothing if either autoscaling is disabled, plot is none or the data source is none

        first_iteration = True  # used for initialization of the extrema variables
        x_min, x_max, y_min, y_max = -1, 1, -1, 1  # definition of extrema variables
        for plot_data in self._data_source:  # check each plot for its maximum and minimum values on both axis

            x_data, y_data = self.sanitize_plot_data(plot_data=plot_data)
            if x_data is None or y_data is None:
                continue  # skip the plot if its data is not valid because there is no data

            finite_x = np.array(x_data)[np.isfinite(x_data)]
            finite_y = np.array(y_data)[np.isfinite(y_data)]

            length_x = len(finite_x)
            length_y = len(finite_y)
            if length_x == 0 or length_y == 0:
                continue  # skip the plot if any of the lists do not contain finite points to plot

            cx_max = np.max(finite_x)  # get maximum x value
            cx_min = np.min(finite_x)  # get minimum x value
            cy_max = np.max(finite_y)  # get maximum y value
            cy_min = np.min(finite_y)  # get minimum y value

            # set all values in first iteration as comparison basis
            if cx_max > x_max or first_iteration:  # set new global maximum x value if the current value is higher
                x_max = cx_max
            if cx_min < x_min or first_iteration:  # set new global minimum x value if the current value is lower
                x_min = cx_min
            if cy_max > y_max or first_iteration:  # set new global maximum y value if the current value is higher
                y_max = cy_max
            if cy_min < y_min or first_iteration:  # set new global minimum y value if the current value is lower
                y_min = cy_min

            first_iteration = False  # now we aren't in the first iteration anymore

        x_scale = self.ax.get_xscale()
        if x_scale == 'linear':
            dx = x_max - x_min  # get x axis span
            if dx == 0:
                dx = 1 / self._axis_limit_margin_fraction  # if span is zero set it to a small margin
            x_min -= dx * self._axis_limit_margin_fraction  # add margin to x axis minimum
            x_max += dx * self._axis_limit_margin_fraction  # add margin to x axis maximum
        elif x_scale == 'log':
            x_min = np.fabs(x_min * (1.0 - self._axis_limit_margin_fraction))
            x_max = np.fabs(x_max * (1.0 + self._axis_limit_margin_fraction))
        else:
            raise ValueError("Unknown x-axis scale: " + x_scale)

        y_scale = self.ax.get_yscale()
        if y_scale == 'linear':
            dy = y_max - y_min  # get y axis span
            if dy == 0:
                dy = 1 / self._axis_limit_margin_fraction  # if span is zero set it to a small margin
            y_min -= dy * self._axis_limit_margin_fraction  # add margin to y axis minimum
            y_max += dy * self._axis_limit_margin_fraction  # add margin to y axis maximum
            # ensure the minimum span is adhered to:
            if self.min_y_axis_span is not None:
                dy_scaled = y_max - y_min
                if dy_scaled < self.min_y_axis_span:
                    incr_by = self.min_y_axis_span - dy_scaled
                    y_min -= incr_by / 2
                    y_max += incr_by / 2
        elif y_scale == 'log':
            y_min = np.fabs(y_min * (1.0 - self._axis_limit_margin_fraction))
            y_max = np.fabs(y_max * (1.0 + self._axis_limit_margin_fraction))
        else:
            raise ValueError("Unknown y-axis scale: " + y_scale)

        if not self._no_x_autoscale:
            self.ax.set_xlim([x_min, x_max])  # set x axis range including the defined margin before and after the data
        self.ax.set_ylim([y_min, y_max])  # set y axis range including the defined margin before and after the data

    @execute_in_plotting_thread
    def __handle_legend__(self):
        """Only draw legend, if data sources with labels are available."""
        if not self._enable_legend \
                or self.ax is None \
                or self._data_source is None \
                or len(self._data_source) == 0:
            return

        handles = []
        labels = []
        for plot_data in self.data_source:
            lbl = plot_data.plot_args.get('label', False)
            if lbl:
                handles.append(plot_data.line_handle)
                labels.append(lbl)

        if labels:
            if len(labels)<10:
                self.ax.legend(handles, labels,  loc="best")
            else:
                self.ax.legend(handles, labels, loc="lower right")
        elif self.ax.get_legend() is not None:
            self.ax.get_legend().remove()

    @execute_in_plotting_thread
    def __handle_axes_labels__(self):
        if self.ax is not None:
            if self._x_label is not None:
                self.ax.set_xlabel(self._x_label)
            if self._y_label is not None:
                self.ax.set_ylabel(self._y_label)
            if self._title is not None:
                self.ax.set_title(self._title)
