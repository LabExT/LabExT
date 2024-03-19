#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from matplotlib.figure import Figure
from matplotlib.axes import Axes

import tkinter as tk

from LabExT.View.Controls.Plotting.PlotConstants import COLOR_MAPS


class PlotModel:
    """The model part of the model-view-controller architecture for plotting"""

    def __init__(self) -> None:
        self.figure: Figure = Figure(figsize=(6, 5), dpi=100)
        self.axes: Axes = self.figure.add_subplot()

        self.plot_type = tk.StringVar()
        """Stores the type of plot currently being shown. See `PlotConstants.PLOT_TYPES`."""
        self.contour_interpolation_type = tk.StringVar()
        """Stores the type of interpolation to use for missing values in contour plot. See `PlotConstants.INTERPOLATION_TYPES`."""
        self.color_map_name = tk.StringVar()
        """Stores the name of the colormap used to color the graphs."""

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
        self.axis_bounds: list[tuple[float, float]] = [(0, 0), (0, 0)]
        """Stores the lower and upper bounds for the x- and y- axis.
           The format is `[(x_low, x_high), (y_low, y_high)]`"""
        self.axis_bound_types = tk.StringVar()
        """What type of bounds should be used."""

        # default values
        self.color_map_name.set(COLOR_MAPS[0])
        self.contour_bucket_count.set(10)
        self.axis_bound_types.set("Auto")
