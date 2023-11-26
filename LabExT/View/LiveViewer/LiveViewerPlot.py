#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time
from dataclasses import dataclass, field
from queue import Empty
from tkinter import Tk, Frame, TOP, BOTH
from typing import List, TYPE_CHECKING

import matplotlib.animation as animation
import matplotlib.lines
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.pyplot import subplots

from LabExT.View.LiveViewer.LiveViewerModel import PlotDataPoint

if TYPE_CHECKING:
    from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel
else:
    LiveViewerModel = None


LIVE_VIEWER_PLOT_COLOR_CYCLE = {
    0: "#1f77b4",
    1: "#ff7f0e",
    2: "#2ca02c",
    3: "#d62728",
    4: "#9467bd",
    5: "#8c564b",
    6: "#e377c2",
    7: "#7f7f7f",
    8: "#bcbd22",
    9: "#17becf",
}


@dataclass
class PlotTrace:
    """stores data and ax/line references for a trace to plot"""

    timestamps: List[float] = field(default_factory=list)
    y_values: List[float] = field(default_factory=list)
    line_handle: matplotlib.lines.Line2D = None
    bar_index: int = None

    @property
    def delta_time_to_now(self):
        return np.array(self.timestamps) - time.time()

    @property
    def finite_y_values(self):
        return np.array(self.y_values)[np.isfinite(self.y_values)]

    def delete_older_than(self, cutoff_s):
        deltas = self.delta_time_to_now
        n_elems_older_than_cutoff = np.count_nonzero(np.abs(deltas) > np.abs(cutoff_s)) - 1
        if n_elems_older_than_cutoff > 0:
            self.timestamps[:n_elems_older_than_cutoff] = []
            self.y_values[:n_elems_older_than_cutoff] = []

    def add_plot_data_point(self, pdp: PlotDataPoint):
        self.timestamps.append(pdp.timestamp)
        self.y_values.append(pdp.y_value)

    def update_line_data(self):
        x = np.hstack((self.delta_time_to_now, 1))
        y = np.hstack((self.y_values, self.y_values[-1]))
        self.line_handle.set_data(x, y)


class LiveViewerPlot(Frame):
    def __init__(self, parent: Tk, model: LiveViewerModel):
        super().__init__(parent, highlightbackground="grey", highlightthickness=1)
        self._root = parent

        self.model = model

        # some constants
        self._figsize = (6, 4)
        self._title = "Live Plot"
        self._animate_interval_ms = 100

        # plot object refs
        self._ani = None
        self._toolbar = None
        self.canvas = None
        self.fig = None
        self.ax = None
        self.ax_bar = None
        self.bar_collection = []
        self.bar_collection_labels = []

        self.__setup__()

    def __setup__(self):
        if self._ani is not None:
            self.stop_animation()
        if self.canvas is not None:
            self.canvas.get_tk_widget().pack_forget()
        if self._toolbar is not None:
            self._toolbar.pack_forget()

        if self.model.show_bar_plots:
            self.fig, (self.ax, self.ax_bar) = subplots(
                nrows=1,
                ncols=2,
                sharey="all",
                gridspec_kw={
                    "width_ratios": (4, 1),
                    "left": 0.12,
                    "bottom": 0.088,
                    "right": 0.93,
                    "top": 0.93,
                    "wspace": 0.0,
                    "hspace": 0.0,
                },
                figsize=self._figsize,
            )
        else:
            self.fig, self.ax = subplots(
                nrows=1,
                ncols=1,
                sharey="all",
                gridspec_kw={"left": 0.12, "bottom": 0.088, "right": 0.93, "top": 0.93, "wspace": 0.0, "hspace": 0.0},
                figsize=self._figsize,
            )
            self.ax_bar = None

        self.fig.suptitle(self._title)

        # self.ax = self.fig.add_subplot(1, 2, 1)
        self.ax.grid(color="gray", linestyle="-", linewidth=0.5)
        self.ax.set_xlabel("elapsed time [s]")
        self.ax.set_ylabel("Power [dBm]")

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self._toolbar = NavigationToolbar2Tk(self.canvas, self)
        self._toolbar.update()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

        self.canvas.draw()

        # configure timed updating, starts automatically
        self._ani = animation.FuncAnimation(
            self.fig, self.animation_tick, interval=self._animate_interval_ms, cache_frame_data=False
        )

    def start_animation(self):
        self._ani.resume()

    def stop_animation(self):
        self._ani.pause()

    def animation_tick(self, _):
        if (self.ax_bar is not None) != self.model.show_bar_plots:
            # show/hiding bar plot changed, we need to start anew with the plot setup
            for trace in self.model.traces_to_plot.values():
                trace.line_handle.remove()
            self.model.traces_to_plot.clear()
            self.__setup__()
            # setup started a new animation loop, return here
            return

        redraw_bars = False

        for _, card in self.model.cards:
            try:
                while True:
                    plot_data_point: PlotDataPoint = card.data_to_plot_queue.get_nowait()

                    trace_key = (card, plot_data_point.trace_name)

                    # line delete flag is set, remove line from axis and delete internal data structure
                    if plot_data_point.delete_trace and (trace_key in self.model.traces_to_plot):
                        self.model.traces_to_plot[trace_key].line_handle.remove()  # removes this line from axis
                        self.model.traces_to_plot.pop(trace_key, None)
                        redraw_bars = True
                        continue

                    # we got a new trace name, setup internal data structure and put line onto axis
                    if trace_key not in self.model.traces_to_plot:
                        # figure out which color to use for the line
                        color = LIVE_VIEWER_PLOT_COLOR_CYCLE[self.model.new_color_idx]
                        self.model.new_color_idx = (self.model.new_color_idx + 1) % len(LIVE_VIEWER_PLOT_COLOR_CYCLE)

                        line_label = f"{card.instance_title:s}: {plot_data_point.trace_name:s}"
                        (line,) = self.ax.plot([], [], color=color, label=line_label)
                        self.model.traces_to_plot[trace_key] = PlotTrace(
                            timestamps=[plot_data_point.timestamp],
                            y_values=[plot_data_point.y_value],
                            line_handle=line,
                            bar_index=-1,
                        )
                        redraw_bars = True
                        continue

                    # append new data point to internal datastructure
                    self.model.traces_to_plot[trace_key].add_plot_data_point(plot_data_point)

            except Empty:
                # jumps to next card if no more plot values left to process
                continue

        # update the line data for all traces
        for plot_trace in self.model.traces_to_plot.values():
            plot_trace.delete_older_than(self.model.plot_cutoff_seconds)
            plot_trace.update_line_data()

        # do y-axis re-scaling of plot
        # get current max/min of all traces
        y_min = []
        y_max = []
        for plot_trace in self.model.traces_to_plot.values():
            y_values = plot_trace.finite_y_values
            if len(y_values) > 0:
                y_min.append(min(y_values))
                y_max.append(max(y_values))
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

        # do x-axis re-scaling of plot
        self.ax.set_xlim([-self.model.plot_cutoff_seconds, 0.0])

        # update bar data
        if redraw_bars and (self.ax_bar is not None):
            for b in self.bar_collection:
                b.remove()
            for l in self.bar_collection_labels:
                l.remove()
            self.bar_collection_labels.clear()

            x = []
            height = []
            colors = []
            labels = []
            for tidx, (_, plot_trace) in enumerate(self.model.traces_to_plot.items()):
                plot_trace.bar_index = tidx
                y_values = plot_trace.finite_y_values
                if len(y_values) > 0:
                    y_val = y_values[-1]
                else:
                    y_val = float("nan")
                height.append(y_val - y_min)
                x.append(tidx)
                colors.append(plot_trace.line_handle.get_color())
                labels.append(plot_trace.line_handle.get_label())
                self.bar_collection_labels.append(
                    self.ax_bar.text(x=tidx, y=y_min, s=f"{y_val:.3f}\n", va="bottom", ha="center")
                )

            self.bar_collection = self.ax_bar.bar(x, height, bottom=y_min, color=colors)

            self.ax_bar.set_xlim([-0.6, len(x) - 0.4])
            self.ax_bar.set_xticks([i for i in range(len(x))])
            self.ax_bar.set_xticklabels(labels, rotation=90, va="bottom")
            self.ax_bar.tick_params(axis="x", length=0.0, pad=-35.0, direction="in")

        else:
            for _, plot_trace in self.model.traces_to_plot.items():
                y_values = plot_trace.finite_y_values
                if len(y_values) > 0:
                    self.bar_collection[plot_trace.bar_index].set_height(y_values[-1] - y_min)
                    self.bar_collection[plot_trace.bar_index].set_y(y_min)
                    self.bar_collection_labels[plot_trace.bar_index].set_text(f"{y_values[-1]:.3f}\n")
                    self.bar_collection_labels[plot_trace.bar_index].set_y(y_min)
                else:
                    self.bar_collection_labels[plot_trace.bar_index].set_text("N/A")
