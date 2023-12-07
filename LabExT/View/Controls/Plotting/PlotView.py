#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable

import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from LabExT.View.Controls.CustomFrame import CustomFrame

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
else:
    Figure = None
    Axes = None


class PlotView:
    """The view corresponding to a plotting visualization.

    Manages the widgets and so on.
    """

    def __init__(
        self, master: tk.Widget, figure: Figure, row: int = 0, column: int = 1, width: int = 2, height=2, pad: int = 10
    ) -> None:
        """Initializes a new `PlotView` object

        The plotting frame will be placed at the specified coordinates and the settings window will be placed
        one column to the right.

        Args:
            master: The parent of the plotting frame (e.g. the main window Tk instance)
            figure: A matplotlib figure used to visualize the data. Provided by `PlotModel`.
            row: row coordinate in the parent
            width: columnspan in master
            height: rowspan in master
            column: column coordinate in the parent
            pad: padding in x and y direction
        """

        self._paned_frame = tk.PanedWindow(master=master, orient=tk.HORIZONTAL)
        """Holds the subwindows."""

        self._plotting_frame = PlottingFrame(master=self._paned_frame, figure=figure)
        self._paned_frame.add(self._plotting_frame, padx=pad, pady=pad, minsize=400, width=700)

        self._settings_frame = PlottingSettingsFrame(
            master=self._paned_frame, axes=figure.axes[0], on_data_change=self._plotting_frame.data_changed_callback
        )
        self._settings_frame.title = "Plot Settings"
        self._paned_frame.add(self._settings_frame, padx=pad, pady=pad, minsize=200)
        self._paned_frame.grid(
            row=row, column=column, columnspan=width, rowspan=height, padx=pad, pady=pad, sticky="nsew"
        )


class PlottingFrame(tk.Frame):
    """This frame contains the widgets created created by the matplotlib tk backend"""

    def __init__(self, master: tk.Widget, figure: Figure, *args, **kwargs) -> None:
        """Initializes a new `PlottingWidget`

        Args:
            master: The parent this widget should be placed in
            figure: The figure used to plot the data (provided by model)
        """
        super().__init__(master, *args, **kwargs)

        self._canvas = FigureCanvasTkAgg(figure=figure, master=self)
        self._canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def data_changed_callback(self) -> None:
        """This method should be called if the axes object was changed, such that the necessary updates can be performed."""
        self._canvas.draw()


class PlottingSettingsFrame(CustomFrame):
    """This frame contains the widgets used to control the displayed visualization of the data"""

    def __init__(self, master: tk.Widget, axes: Axes, on_data_change: Callable[[], None], *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)

        self._data_changed_callback = on_data_change

        self._value = 0
        self._axes = axes
        self._change_button = tk.Button(self, text="Click me", command=self.on_click)
        self._change_button.pack(side=tk.TOP, fill=tk.BOTH)

    def on_click(self):
        self._axes.clear()
        import numpy as np

        data = np.linspace(0, 10, 10)
        self._axes.plot(data, data**self._value)
        self._value += 1

        self._data_changed_callback()
