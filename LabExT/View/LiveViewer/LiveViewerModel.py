#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from collections import OrderedDict
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, TYPE_CHECKING, Optional

import matplotlib.lines
import numpy as np

from LabExT.Measurements.MeasAPI import MeasParamFloat, MeasParamBool, MeasParamInt

if TYPE_CHECKING:
    from LabExT.View.LiveViewer.Cards import CardFrame
    from tkinter import Tk
    from LabExT.Measurements.MeasAPI.Measurement import MEAS_PARAMS_TYPE
else:
    CardFrame = None
    Tk = None
    MEAS_PARAMS_TYPE = None


LIVE_VIEWER_PLOT_COLOR_CYCLE = OrderedDict(
    [
        (0, "#1f77b4"),
        (1, "#ff7f0e"),
        (2, "#2ca02c"),
        (3, "#d62728"),
        (4, "#9467bd"),
        (5, "#8c564b"),
        (6, "#e377c2"),
        (7, "#7f7f7f"),
        (8, "#bcbd22"),
        (9, "#17becf"),
    ]
)


@dataclass
class PlotDataPoint:
    """use this object to transfer data to the live plotter"""

    trace_name: str
    timestamp: float = float("nan")
    y_value: float = float("nan")
    delete_trace: bool = False


@dataclass
class PlotTrace:
    """stores data and ax/line pointers for a trace to plot"""

    timestamps: List[float] = field(default_factory=list)
    y_values: List[float] = field(default_factory=list)
    line_handle: matplotlib.lines.Line2D = None
    reference_value: float = None
    color_index: int = None
    bar_index: int = None

    @property
    def delta_time_to_now(self):
        return np.array(self.timestamps) - time.time()

    @property
    def finite_y_values(self) -> np.ndarray:
        return np.array(self.y_values)[np.isfinite(self.y_values)] - (self.reference_value or 0.0)

    def delete_older_than(self, cutoff_s: float):
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
        y = np.hstack((self.y_values, self.y_values[-1])) - (self.reference_value or 0.0)
        self.line_handle.set_data(x, y)

    def reference_set(self, reference_value: Optional[float] = None):
        if reference_value is not None:
            self.reference_value = reference_value
        else:
            finite_vals = np.array(self.y_values)[np.isfinite(self.y_values)]
            if len(finite_vals) > 0:
                self.reference_value = finite_vals[-1]
            else:
                raise ValueError("No valid data in trace to set reference from")
    
    def reference_clear(self):
        self.reference_value = None


class LiveViewerModel:
    """
    Model class for the live viewer. Contains all data needed for the operation of the liveviewer.
    """

    def __init__(self, root: Tk):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window.
        """

        self.settings_file_name: str = "LiveViewerConfig.json"
        self.references_file_name: str = "LiveViewerReferences.json"

        # these are the general settings
        self.general_settings: MEAS_PARAMS_TYPE = {
            "time range to display": MeasParamFloat(value=20.0, unit="s"),
            "minimum y-axis span": MeasParamFloat(value=4.0),
            "show bar plots": MeasParamBool(value=True),
            "averaging in bar plot": MeasParamInt(value=20, unit="samples"),
        }

        # the options when selecting a new card
        # this is dynamically filled in during start of the live viewer
        self.lvcards_classes: Dict[str, type] = {}

        # the cards list
        self.cards: List[Tuple[str, CardFrame]] = []
        self.next_card_index: int = 1

        # the currently plotted traces in the live viewer plot
        self.traces_to_plot: Dict[Tuple[CardFrame, str], PlotTrace] = {}
        self.plotting_active: bool = True

        # the color index to be used for the next trace
        self.new_color_idx: int = 0

        # only keep this many seconds in the live plot
        self.plot_cutoff_seconds: float = 20.0

        # the minimum y span
        self.min_y_span: float = 4.0

        # if bar pot should be shown
        self.show_bar_plots: bool = True

        # averaging for bar plot
        self.averaging_bar_plot: int = 20

    def get_next_plot_color_index(self) -> int:
        """call this to get the next color for another trace to show"""
        occupied_color_indices = [t.color_index for t in self.traces_to_plot.values()]
        indices_in_ccycle = [k for k in LIVE_VIEWER_PLOT_COLOR_CYCLE.keys() if k not in occupied_color_indices]
        if indices_in_ccycle:
            return indices_in_ccycle[0]
        else:
            ret_idx = self.new_color_idx
            self.new_color_idx = (self.new_color_idx + 1) % len(LIVE_VIEWER_PLOT_COLOR_CYCLE)
            return ret_idx
