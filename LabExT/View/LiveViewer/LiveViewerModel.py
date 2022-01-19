#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Measurements.MeasAPI import MeasParamInt, MeasParamFloat

from LabExT.ViewModel.Utilities.ObservableList import ObservableList


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
            'number of points kept': MeasParamInt(value=100),
            'minimum y-axis span': MeasParamFloat(value=4.0),
        }

        # the plot collection, which is used for the plotting frame
        self.plot_collection = ObservableList()

        # the options when selecting a new card
        # this is dynamically filled in during start of the live viewer
        self.options = {}

        # the cards list
        self.cards = []
        # the old parameters, used when loading from an existing instance of the liveviewer
        self.old_params = []
        self.old_instr = []

        # the current live plot
        self.live_plot = None

        # the number of points kept
        self.plot_size = 100

        # the minimum y span
        self.min_y_span = 4.0
