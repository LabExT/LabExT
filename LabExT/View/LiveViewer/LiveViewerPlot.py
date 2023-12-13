#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


from queue import Empty
import time
from tkinter import Event, Frame, TOP, BOTH
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
    from matplotlib.text import Text
else:
    Tk = None
    LiveViewerModel = None
    Animation = None
    Figure = None
    Axis = None
    Text = None


class LiveViewerPlot(Frame):
    def __init__(self, parent: Tk, model: LiveViewerModel):
        super().__init__(parent, highlightbackground="grey", highlightthickness=1)
        self._root: Tk = parent

        self.model: LiveViewerModel = model

        # some constants
        self._figsize: Tuple[int, int] = (6, 4)
        self._title: str = "Live Plot"
        self._animate_interval_ms: int = 33

        # internal bookkeeping
        self._saved_xlim = 0.0
        self._saved_ylim = (np.inf, -np.inf)

        # plot object refs
        self._ani: Animation = None
        self._toolbar: NavigationToolbar2Tk = None
        self._canvas: FigureCanvasTkAgg = None
        self._fig: Figure = None
        self._ax: Axis = None
        self._ax_bar: Axis = None

        self._fps_counter: Text = None
        self._last_draw_time: float = None

        self.__setup__()

        # configure timed updating, starts automatically
        self._ani = animation.FuncAnimation(
            self._fig, self.animation_tick, interval=self._animate_interval_ms, cache_frame_data=False, blit=True
        )

    def __setup__(self):
        if self._canvas is not None:
            self._canvas.get_tk_widget().pack_forget()
        if self._toolbar is not None:
            self._toolbar.pack_forget()

        self._fig, (self._ax, self._ax_bar) = subplots(
                nrows=1,
                ncols=2,
                sharey="all",
                gridspec_kw={
                    "width_ratios": (6, 1),
                    "left": 0.12,
                    "bottom": 0.088,
                    "right": 0.93,
                    "top": 0.93,
                    "wspace": 0.0,
                    "hspace": 0.0,
                },
                figsize=self._figsize,
            )

        self._fig.suptitle(self._title)

        self._ax.grid(color="gray", linestyle="-", linewidth=0.5)
        self._ax.set_xlabel("elapsed time [s]")
        self._ax.set_ylabel("Power [dBm]")

        self._ax_bar.axis('off')

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

    def start_animation(self):
        self._ani.resume()

    def stop_animation(self):
        self._ani.pause()

    def animation_tick(self, _):

        do_full_redraw = False

        for _, card in self.model.cards:
            try:
                while True:
                    plot_data_point: PlotDataPoint = card.data_to_plot_queue.get_nowait()

                    trace_key = (card, plot_data_point.trace_name)

                    # line delete flag is set, remove line from axis and delete internal data structure
                    if plot_data_point.delete_trace and (trace_key in self.model.traces_to_plot):
                        self.model.traces_to_plot[trace_key].line_handle.remove()  # removes this line from axis
                        self.model.traces_to_plot[trace_key].annotation_handle.remove()
                        self.model.traces_to_plot.pop(trace_key, None)
                        continue

                    # we got a new trace name, setup internal data structure and put line onto axis
                    if trace_key not in self.model.traces_to_plot:
                        color_index = self.model.get_next_plot_color_index()
                        line_label = f"{card.instance_title:s}: {plot_data_point.trace_name:s}"
                        (line,) = self._ax.plot(
                            [], [], color=LIVE_VIEWER_PLOT_COLOR_CYCLE[color_index], animated=True
                        )
                        annotation = self._ax_bar.annotate(
                            text="n/a", xy=(0, 0), xytext=(10,0), xycoords='data', textcoords='offset points', annotation_clip=False, ha="left", va="center", arrowprops=dict(arrowstyle="->", connectionstyle="arc3", color=LIVE_VIEWER_PLOT_COLOR_CYCLE[color_index]), animated=True
                        )
                        legend = self._ax.annotate(
                            text="n/a", xy=(15, 15+15*color_index), xytext=(40,0), xycoords='axes points', textcoords='offset points', annotation_clip=False, ha="left", va="center", arrowprops=dict(arrowstyle="-", connectionstyle="arc3", color=LIVE_VIEWER_PLOT_COLOR_CYCLE[color_index]), animated=True
                        )
                        self.model.traces_to_plot[trace_key] = PlotTrace(
                            timestamps=[plot_data_point.timestamp],
                            y_values=[plot_data_point.y_value],
                            line_handle=line,
                            annotation_handle=annotation,
                            legend_handle=legend,
                            line_label=line_label,
                            color_index=color_index
                        )
                        continue

                    # append new data point to internal datastructure
                    self.model.traces_to_plot[trace_key].add_plot_data_point(plot_data_point)

            except Empty:
                # jumps to next card if no more plot values left to process
                continue

        changed_artists = []

        # update underlying line data, even if no new data is present, the delta-time changes
        for plot_trace in self.model.traces_to_plot.values():
            plot_trace.delete_older_than(self.model.plot_cutoff_seconds)
            plot_trace.update_line_label()
            changed_artists.append(plot_trace.legend_handle)
            plot_trace.update_line_data()
            changed_artists.append(plot_trace.line_handle)
            plot_trace.update_annotation(n_avg=self.model.averaging_arrow_height)
            changed_artists.append(plot_trace.annotation_handle)

        # update FPS counter
        if self.model.show_fps_counter:
            self._fps_counter.set_text(f"FPS: {1/(time.time()-(self._last_draw_time or float('inf'))):.2f}Hz")
        else:
            self._fps_counter.set_text(f"")
        changed_artists.append(self._fps_counter)
        self._last_draw_time = time.time()

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
        margin_data = (y_max - y_min) * 0.1
        y_min -= margin_data
        y_max += margin_data
        # make sure to adhere to the user-defined minimum y-range
        dy_with_margin = y_max - y_min
        if dy_with_margin < self.model.min_y_span:
            incr_by = self.model.min_y_span - dy_with_margin
            y_min -= incr_by / 2
            y_max += incr_by / 2
        dy_final = y_max - y_min

        # only update y-axis if we are actually out of range
        if (y_min < self._saved_ylim[0]) or (y_min > self._saved_ylim[0] + 0.2 * dy_final) or (y_max > self._saved_ylim[1]) or (y_max < self._saved_ylim[1] - 0.2 * dy_final):            
            self._ax.set_ylim((y_min, y_max))
            self._saved_ylim = (y_min, y_max)
            do_full_redraw = True

        # do x-axis re-scaling of plot only if changed
        requested_x_min = -self.model.plot_cutoff_seconds
        if requested_x_min != self._saved_xlim:
            self._ax.set_xlim([requested_x_min, 0.0])
            self._saved_xlim = requested_x_min
            do_full_redraw = True

        if do_full_redraw:
            # call a full redraw, s.t. axes limits update - this excludes all artists that have animate=True
            self._fig.canvas.draw()

        # Weird observation: if we use blitting and we don't have return animated artists to show, 
        # matplotlib gets extremely slow. Make sure that changed_artists is not empty!
        assert len(changed_artists) > 0

        return changed_artists
