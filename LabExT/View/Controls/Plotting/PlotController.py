#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, Callable

from LabExT.View.Controls.Plotting.PlotModel import PlotModel
from LabExT.View.Controls.Plotting.PlotView import PlotView
from LabExT.View.Controls.Plotting.PlottableDataHandler import PlottableDataHandler
from LabExT.View.MeasurementTable import SelectionChangedEvent

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

    def __init__(self, master: Widget) -> None:
        """Creates a new `PlotController` and initializes the corresponding model and view.

        Args:
            master: The master widget of the view (e.g. main window `Tk`)
        """

        self._model = PlotModel()
        self._view = PlotView(master=master, figure=self._model._figure)

        self._data_handler = PlottableDataHandler()

    def show(self, row: int = 0, column: int = 1, width: int = 2, height: int = 2, pad: int = 10) -> None:
        """Places the corresponding gui elements in a grid in the parent widget according to the arguments.

        Args:
            row: row coordinate of view in master
            column: column coordinate of view in master
            width: columnspan of view in master
            height: rowspan of view in master
            pad: padding in x and y direction
        """
        self._view.show(row, column, width, height, pad)

    def hide(self) -> None:
        """Removes the corresponding gui elements from the parent."""
        self._view.hide()

    @property
    def selection_changed_listener(self) -> Callable[[SelectionChangedEvent], None]:
        """The event listener that needs to be passed to `MeasurementTable`."""
        return self._data_handler.measurement_selection_changed_callback
