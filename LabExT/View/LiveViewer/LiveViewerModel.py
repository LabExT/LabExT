#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from dataclasses import dataclass

from LabExT.Measurements.MeasAPI import MeasParamFloat


@dataclass
class PlotDataPoint:
    """ use this object to transfer data to the live plotter """
    trace_name: str
    timestamp: float = float('nan')
    y_value: float = float('nan')
    delete_trace: bool = False


class LiveViewerModel:
    """
    Model class for the live viewer. Contains all data needed for the operation of the liveviewer.
    """

    def __init__(self, root):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window.
        """

        # these are the general settings
        self.general_settings = {
            # number of points kept
            'time range to display': MeasParamFloat(value=20.0, unit='s'),
            'minimum y-axis span': MeasParamFloat(value=4.0),
        }

        # the options when selecting a new card
        # this is dynamically filled in during start of the live viewer
        self.lvcards_classes = {}

        # the cards list
        self.cards = []
        self.next_card_index = 1

        # the currently plotted traces in the live viewer plot
        self.traces_to_plot = {}

        # the color index to be used for the next trace
        self.new_color_idx = 0

        # only keep this many seconds in the live plot
        self.plot_cutoff_seconds = 20.0

        # the minimum y span
        self.min_y_span = 4.0
