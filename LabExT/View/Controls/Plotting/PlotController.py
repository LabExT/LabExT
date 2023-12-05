#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING

from LabExT.View.Controls.Plotting.PlotModel import PlotModel
from LabExT.View.Controls.Plotting.PlotView import PlotView

if TYPE_CHECKING:
    from tkinter import Tk, Widget
else:
    Tk = None
    Widget = None


class PlotController:
    """This is the controller of a data-plot visualization.

    This controller holds a reference to the needed model storing the variables and state of the
    visualization. It also contains a reference to the view needed to display the data.
    """

    def __init__(self, master: Widget, row: int = 0, column: int = 1, pad: int = 10) -> None:
        """Creates a new `PlotController` and initializes the corresponding model and view.

        Args:
            master: The master widget of the view (e.g. main window `Tk`)
            row: row coordinate of view in master
            column: column coordinate of view in master
            pad: padding in x and y direction
        """

        self._model = PlotModel()
        self._view = PlotView(master=master, figure=self._model._figure, row=row, column=column, pad=pad)

        import numpy as np
        data = np.linspace(0, 10, 50)
        self._model._axes.plot(data, data**2)
