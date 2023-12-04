#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


from queue import Empty
import time
from tkinter import Frame, TOP, BOTH
from typing import TYPE_CHECKING, Tuple, List

import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.pyplot import subplots
import numpy as np

from LabExT.View.LiveViewer.LiveViewerModel import PlotDataPoint, PlotTrace, LIVE_VIEWER_PLOT_COLOR_CYCLE

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel
    from matplotlib.animation import Animation
    from matplotlib.figure import Figure
    from matplotlib.axis import Axis
    from matplotlib.container import BarContainer
    from matplotlib.text import Text
    from matplotlib.legend import Legend
else:
    Tk = None
    LiveViewerModel = None
    Animation = None
    Figure = None
    Axis = None
    BarContainer = None
    Text = None
    Legend = None


class LiveViewerPlot(Frame):
    def __init__(self, parent: Tk, model: LiveViewerModel):
        super().__init__(parent, highlightbackground="grey", highlightthickness=1)
        self._root: Tk = parent

        self.model: LiveViewerModel = model

        # some constants
        self._figsize: Tuple[int, int] = (6, 4)
        self._title: str = "Live Plot"
        self._animate_interval_ms: int = 33
        self._full_redraw_every_N_ticks: int = 10
        self._update_counter = 0

        # plot object refs
        self._ani: Animation = None
        self._toolbar: NavigationToolbar2Tk = None
        self._canvas: FigureCanvasTkAgg = None
        self._fig: Figure = None
        self._ax: Axis = None
        self._ax_bar: Axis = None
        self._bar_collection: BarContainer = []
        self._bar_collection_labels: List[Text] = []
        self._legend: Legend = None

        self._fps_counter: Text = None
        self._last_draw_time: float = None

        self.__setup__()

    def __setup__(self):
        if self._ani is not None:
            self.stop_animation()
        if self._canvas is not None:
            self._canvas.get_tk_widget().pack_forget()
        if self._toolbar is not None:
            self._toolbar.pack_forget()

        if self.model.show_bar_plots:
            self._fig, (self._ax, self._ax_bar) = subplots(
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
            self._fig, self._ax = subplots(
                nrows=1,
                ncols=1,
                sharey="all",
                gridspec_kw={"left": 0.12, "bottom": 0.088, "right": 0.93, "top": 0.93, "wspace": 0.0, "hspace": 0.0},
                figsize=self._figsize,
            )
            self._ax_bar = None

        self._fig.suptitle(self._title)

        # self.ax = self.fig.add_subplot(1, 2, 1)
        self._ax.grid(color="gray", linestyle="-", linewidth=0.5)
        self._ax.set_xlabel("elapsed time [s]")
        self._ax.set_ylabel("Power [dBm]")

        self._canvas = FigureCanvasTkAgg(self._fig, self)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self)
        self._toolbar.update()
        self._canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

        self._canvas.draw()

        # show fps counter
        self._fps_counter = self._ax.annotate("0",
                                            (1, 1),
                                            xycoords="axes fraction",
                                            xytext=(-10, -10),
                                            textcoords="offset points",
                                            ha="right",
                                            va="top",
                                            animated=True
                                            )

        # configure timed updating, starts automatically
        self._ani = animation.FuncAnimation(
            self._fig, self.animation_tick, interval=self._animate_interval_ms, cache_frame_data=False, blit=True
        )

    def start_animation(self):
        self._ani.resume()

    def stop_animation(self):
        self._ani.pause()

    def animation_tick(self, _):
        changed_artists = []

        if (self._ax_bar is not None) != self.model.show_bar_plots:
            # show/hiding bar plot changed, we need to start anew with the plot setup
            for trace in self.model.traces_to_plot.values():
                trace.line_handle.remove()
            self.model.traces_to_plot.clear()
            self.__setup__()
            # setup started a new animation loop, return here
            return changed_artists
        
        self._update_counter += 1
        if self._update_counter >= self._full_redraw_every_N_ticks:
            do_full_redraw = True
            self._update_counter = 0
        else:
            do_full_redraw = False

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
                        color_index = self.model.get_next_plot_color_index()
                        line_label = f"{card.instance_title:s}: {plot_data_point.trace_name:s}"
                        (line,) = self._ax.plot(
                            [], [], color=LIVE_VIEWER_PLOT_COLOR_CYCLE[color_index], label=line_label, animated=True
                        )
                        self.model.traces_to_plot[trace_key] = PlotTrace(
                            timestamps=[plot_data_point.timestamp],
                            y_values=[plot_data_point.y_value],
                            line_handle=line,
                            line_label=line_label,
                            color_index=color_index,
                            bar_index=-1,
                        )
                        redraw_bars = True
                        continue

                    # append new data point to internal datastructure
                    self.model.traces_to_plot[trace_key].add_plot_data_point(plot_data_point)

            except Empty:
                # jumps to next card if no more plot values left to process
                continue

        # update line data
        for plot_trace in self.model.traces_to_plot.values():
            plot_trace.update_line_data()
            changed_artists.append(plot_trace.line_handle)

        # delete old line data & update label only on full-redraw
        redraw_legend = False
        if do_full_redraw:
            for plot_trace in self.model.traces_to_plot.values():
                plot_trace.delete_older_than(self.model.plot_cutoff_seconds)
                redraw_legend = redraw_legend or plot_trace.update_line_label()

        # update FPS counter
        self._fps_counter.set_text(f"FPS: {1/(self._last_draw_time or float('nan')):.2f}Hz")

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
        self._ax.set_ylim([y_min, y_max])
        # self._ax.yaxis.set_animated(True)
        # changed_artists.append(self._ax.yaxis)

        # do x-axis re-scaling of plot
        self._ax.set_xlim([-self.model.plot_cutoff_seconds, 0.0])

        # handle legend: show legend only if there are traces to plot
        # only do changes to the legend if there are any changes to the shown traces
        if redraw_bars or redraw_legend:
            if self.model.traces_to_plot:
                self._legend = self._ax.legend(loc="upper left", frameon=False)
                changed_artists.extend(self._legend.legend_handles)
            else:
                if self._legend is not None:
                    self._legend.remove()
                    self._legend = None

        # update bar data
        if self._ax_bar is not None:
            if redraw_bars:
                for b in self._bar_collection:
                    b.remove()
                for l in self._bar_collection_labels:
                    l.remove()
                self._bar_collection_labels.clear()

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
                    self._bar_collection_labels.append(
                        self._ax_bar.text(x=tidx, y=y_min, s=f"{y_val:.3f}\n", va="bottom", ha="center", animated=True)
                    )

                self._bar_collection = self._ax_bar.bar(x, height, bottom=y_min, color=colors, animated=True)

                self._ax_bar.set_xlim([-0.6, len(x) - 0.4])
                self._ax_bar.set_xticks([i for i in range(len(x))])
                self._ax_bar.set_xticklabels(labels, rotation=90, va="bottom")
                self._ax_bar.tick_params(axis="x", length=0.0, pad=-35.0, direction="in")

            else:
                for _, plot_trace in self.model.traces_to_plot.items():
                    y_values = plot_trace.finite_y_values
                    if len(y_values) > 0:
                        self._bar_collection[plot_trace.bar_index].set_height(
                            np.mean(y_values[-self.model.averaging_bar_plot :]) - y_min
                        )
                        self._bar_collection_labels[plot_trace.bar_index].set_text(f"{y_values[-1]:.3f}\n")
                    else:
                        self._bar_collection[plot_trace.bar_index].set_height(0)
                        self._bar_collection_labels[plot_trace.bar_index].set_text("N/A\n")
                    self._bar_collection[plot_trace.bar_index].set_y(y_min)
                    self._bar_collection_labels[plot_trace.bar_index].set_y(y_min)

        changed_artists.extend(self._bar_collection)
        changed_artists.extend(self._bar_collection_labels)
        # if self._ax_bar is not None:
            # changed_artists.extend(self._ax_bar.get_xticklabels())
        
        # update FPS counter
        self._fps_counter.set_text(f"FPS: {1/(time.time()-(self._last_draw_time or float('nan'))):.2f}Hz")
        changed_artists.append(self._fps_counter)
        self._last_draw_time = time.time()

        return changed_artists
