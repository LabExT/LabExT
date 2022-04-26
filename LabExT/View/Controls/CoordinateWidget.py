#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import LEFT, SUNKEN, Frame, Label
from LabExT.Movement.Calibration import Axis


class CoordinateWidget(Frame):
    """
    Simple Widget to display a coordinate
    """

    def __init__(self, parent, coordinate):
        super(CoordinateWidget, self).__init__(parent)
        self._coordinate = coordinate[:3]  # Use only first 3 values

        self.__setup__()

    def __setup__(self):
        for idx, value in enumerate(self._coordinate):
            Label(self, text="{}:".format(Axis(idx).name)).pack(side=LEFT)
            Label(
                self, text=value, borderwidth=1, relief=SUNKEN
            ).pack(side=LEFT, ipadx=5, padx=(0, 5))

    @property
    def coordinate(self):
        self._coordinate

    @coordinate.setter
    def coordinate(self, coordinate):
        """
        Rerenders the the frame to display
        """
        self._coordinate = coordinate[:3]

        for c in self.winfo_children():
            c.forget()
        self.__setup__()
