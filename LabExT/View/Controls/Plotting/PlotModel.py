#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from matplotlib.figure import Figure
from matplotlib.axes import Axes

import tkinter as tk


class PlotModel:
    """The model part of the model-view-controller architecture for plotting"""

    def __init__(self) -> None:
        self.figure: Figure = Figure(figsize=(6, 5), dpi=100)
        self.axes: Axes = self.figure.add_subplot()

        self.plot_type = tk.StringVar()
        """Stores the type of plot currently being shown. See `PlotConstants.PLOT_TYPES`."""
        self.contour_interpolation_type = tk.StringVar()
        """Stores the type of interpolation to use for missing values in contour plot. See `PlotConstants.INTERPOLATION_TYPES`."""

        self.axis_x_key_name = tk.StringVar()
        """Stores the name of the key that populates the x-values of the plot."""
        self.axis_y_key_name = tk.StringVar()
        """Stores the name of the key that populates the y-values of the plot."""
        self.axis_z_key_name = tk.StringVar()
        """Stores the name of the key that populates the z-values of the plot (if this exists, e.g. contour)."""
        self.contour_bucket_count = tk.IntVar()
        """Stores the number of buckets used for the contour plot."""

        self.legend_elements: list[str] = []
        """Stores the names of the elements selected for the legend."""

        # default values
        self.contour_bucket_count.set(10)
