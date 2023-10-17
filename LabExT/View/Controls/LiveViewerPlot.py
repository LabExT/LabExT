#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import time
from dataclasses import dataclass, field
from queue import Empty
from tkinter import Tk, Frame, TOP, BOTH

import matplotlib.animation as animation
import matplotlib.lines
import numpy as np
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from LabExT.View.LiveViewer.Cards import CardFrame
from LabExT.View.LiveViewer.LiveViewerModel import PlotDataPoint


LIVE_VIWER_PLOT_COLOR_CYCLE = {
    0: '#1f77b4',
    1: '#ff7f0e',
    2: '#2ca02c',
    3: '#d62728',
    4: '#9467bd',
    5: '#8c564b',
    6: '#e377c2',
    7: '#7f7f7f',
    8: '#bcbd22',
    9: '#17becf'
}


@dataclass
class PlotTrace:
    """ stores data and ax/line references for a trace to plot """
    timestamps: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    line_handle: matplotlib.lines.Line2D = None
    card_handle: CardFrame = None

    @property
    def delta_time_to_now(self):
        return np.array(self.timestamps) - time.time()

    def delete_older_than(self, cutoff_s):
        deltas = self.delta_time_to_now
        n_elems_older_than_cutoff = np.count_nonzero(np.abs(deltas) > np.abs(cutoff_s))
        self.timestamps[:n_elems_older_than_cutoff] = []
        self.y_values[:n_elems_older_than_cutoff] = []

    def add_plot_data_point(self, pdp: PlotDataPoint):
        self.timestamps.append(pdp.timestamp)
        self.y_values.append(pdp.y_value)

    def update_line_data(self):
        self.line_handle.set_data(self.delta_time_to_now, self.y_values)


class LiveViewerPlot(Frame):

    def __init__(self, parent: Tk):
        super().__init__(parent, highlightbackground='grey', highlightthickness=1)
        self._root = parent

        self.model = None

        self._ani = None

        # some constants
        self._figsize = (6, 4)
        self._title = 'Live Plot'
        self._animate_interval_ms = 200

        self.__setup__()

        # configure timed updating, starts automatically
        self._ani = animation.FuncAnimation(self.fig, self.animation_tick, interval=self._animate_interval_ms)

    def __setup__(self):
        self.fig = Figure(figsize=self._figsize)

        self.ax = self.fig.add_subplot(111)

        self.ax.set_title(self._title)
        self.ax.set_xlabel('elapsed time [s]')
        self.ax.set_ylabel('Power [dBm]')

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

        self._toolbar = NavigationToolbar2Tk(self.canvas, self)
        self._toolbar.update()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

        self.canvas.draw()

        # ToDo: different instruments might have different units?

    def animation_tick(self, _):

        for cidx, (card_type, card) in enumerate(self.model.cards):
            try:
                while True:
                    plot_data_point: PlotDataPoint = card.data_to_plot_queue.get_nowait()

                    card_trace_prefix = str(card_type) + " " + str(cidx) + ": "
                    fqtn = card_trace_prefix + plot_data_point.trace_name  # "fully qualified trace name"

                    # line delete flag is set, remove line from axis and delete internal data structure
                    if plot_data_point.delete_trace and (fqtn in self.model.traces_to_plot):
                        self.model.traces_to_plot[fqtn].line_handle.remove()  # removes this line from axis
                        self.model.traces_to_plot.pop(fqtn, None)
                        continue

                    # we got a new trace name, setup internal data structure and put line onto axis
                    if fqtn not in self.model.traces_to_plot:
                        # figure out which color to use for the line
                        color = LIVE_VIWER_PLOT_COLOR_CYCLE[self.model.new_color_idx]
                        self.model.new_color_idx = (self.model.new_color_idx + 1) % len(LIVE_VIWER_PLOT_COLOR_CYCLE)

                        line, = self.ax.plot([], [], color=color)
                        self.model.traces_to_plot[fqtn] = PlotTrace(timestamps=[plot_data_point.timestamp],
                                                              y_values=[plot_data_point.y_value],
                                                              line_handle=line,
                                                              card_handle=card)
                        continue

                    # append new data point to internal datastructure
                    self.model.traces_to_plot[fqtn].add_plot_data_point(plot_data_point)

            except Empty:
                # jumps to next card if no more plot values left to process
                continue

        # update the line data for all traces
        for fqtn, plot_trace in self.model.traces_to_plot.items():
            plot_trace.delete_older_than(self.model.plot_cutoff_seconds)
            plot_trace.update_line_data()

        # do re-scaling of the plot
        # get current max/min of all traces
        y_min = []
        y_max = []
        for plot_trace in self.model.traces_to_plot.values():
            if plot_trace.y_values:
                y_min.append(min(plot_trace.y_values))
                y_max.append(max(plot_trace.y_values))
        y_min = min(y_min) if y_min else 0.0
        y_max = max(y_max) if y_max else 0.0
        # make sure that we have a small margin
        dy = y_max - y_min
        y_min -= dy * 0.1
        y_max += dy * 0.1
        # make sure to adhere to the user-defined minimum y-range
        dy_scaled = y_max - y_min
        if dy_scaled < self.model.min_y_span:
            incr_by = self.model.min_y_span - dy_scaled
            y_min -= incr_by / 2
            y_max += incr_by / 2
        self.ax.set_ylim([y_min, y_max])

        self.ax.set_xlim([-self.model.plot_cutoff_seconds, 0.0])
