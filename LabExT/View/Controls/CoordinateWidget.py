#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import Type
from tkinter import LEFT, SUNKEN, Frame, Label

from LabExT.Movement.config import Axis, CoordinateSystem
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.Transformations import Coordinate


class CoordinateWidget(Frame):
    """
    Simple Widget to display a coordinate
    """

    def __init__(self, master, coordinate: Type[Coordinate]):
        super(CoordinateWidget, self).__init__(master)
        self._coordinate = coordinate

        self.__setup__()

    def __setup__(self):
        coordinate_list = self._coordinate.to_list()
        for axis in Axis:
            Label(self, text="{}:".format(axis.name)).pack(side=LEFT)
            Label(
                self,
                text="{:.2f}".format(coordinate_list[axis.value]),
                borderwidth=1,
                relief=SUNKEN
            ).pack(side=LEFT, ipadx=5, padx=(0, 5))

    @property
    def coordinate(self):
        self._coordinate

    @coordinate.setter
    def coordinate(self, coordinate):
        """
        Rerenders the the frame to display
        """
        self._coordinate = coordinate

        for c in self.winfo_children():
            c.forget()
        self.__setup__()


class StagePositionWidget(CoordinateWidget):
    """
    Widget, which display the current position of a stage.

    Updates automatically. (1000 ms refreshing rate)
    """

    REFRESHING_RATE = 1000  # [ms]

    def __init__(self, parent, calibration: Type[Calibration]):
        self.calibration = calibration

        with self.calibration.perform_in_system(CoordinateSystem.STAGE):
            super().__init__(parent, self.calibration.get_position())

        self._update_pos_job = self.after(
            self.REFRESHING_RATE, self._refresh_position)

    def __del__(self):
        """
        Deconstructor.

        Cancels refreshing job.
        """
        if self._update_pos_job:
            self.after_cancel(self._update_pos_job)

    def _refresh_position(self):
        """
        Refreshes Stage Position.
        Kills update job, if an error occurred.
        """
        try:
            with self.calibration.perform_in_system(CoordinateSystem.STAGE):
                self.coordinate = self.calibration.get_position()
        except Exception as exc:
            self.after_cancel(self._update_pos_job)
            raise RuntimeError(exc)

        self._update_pos_job = self.after(
            self.REFRESHING_RATE, self._refresh_position)
