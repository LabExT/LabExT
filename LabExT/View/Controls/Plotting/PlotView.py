#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import _Cursor, _Relief, _ScreenUnits, _TakeFocusValue, Misc
from typing import TYPE_CHECKING, Any

import tkinter as tk
from typing_extensions import Literal

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

if TYPE_CHECKING:
    from matplotlib.figure import Figure
else:
    Figure = None


class PlotView:
    """The view corresponding to a plotting visualization.

    Manages the widgets and so on.
    """

    def __init__(self, master: tk.Widget, figure: Figure, row: int = 0, column: int = 1, pad: int = 10) -> None:
        """Initializes a new `PlotView` object

        The plotting frame will be placed at the specified coordinates.

        Args:
            master: The parent of the plotting frame (e.g. the main window Tk instance)
            figure: A matplotlib figure used to visualize the data. Provided by `PlotModel`.
            row: row coordinate in the parent
            column: column coordinate in the parent
            pad: padding in x and y direction
        """
        self._plotting_frame = PlottingFrame(master=master, figure=figure)
        self._plotting_frame.grid(row=row, column=column, padx=pad, pady=pad, sticky="nsew")


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


class PlottingSettingsFrame(tk.LabelFrame):
    """This frame contains the widgets used to control the displayed visualization of the data"""

    def __init__(self, master: tk.Widget, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
