#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import Type
from tkinter import SUNKEN, Frame, Label

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
        for idx, axis in enumerate(Axis):
            Label(
                self,
                text="{}:".format(axis.name)
            ).grid(row=0, column=idx * 2)
            Label(
                self,
                text="{:.2f}".format(coordinate_list[axis.value]),
                borderwidth=1,
                relief=SUNKEN
            ).grid(row=0, column=idx * 2 + 1, ipadx=5, padx=(0, 5))

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

    def __init__(self, parent, calibration: Type[Calibration]):
        """
        Constructor.

        Calls CoordinateWidget with current position.
        """
        self.calibration = calibration
        with calibration.perform_in_system(CoordinateSystem.STAGE):
            super().__init__(parent, calibration.get_position())

        self._register_refresh_job()

    def __del__(self):
        """
        Deconstructor.

        Cancels refreshing job.
        """
        if self._refresh_position_job:
            self.after_cancel(self._refresh_position_job)

    def __setup__(self):
        super().__setup__()

        if self.calibration.supports_live_position:
            Label(
                self,
                text="(Updates automatically)"
            ).grid(row=0, column=len(Axis) * 2)
        else:
            Label(
                self,
                text="(Does not update automatically)"
            ).grid(row=0, column=len(Axis) * 2)

    def _register_refresh_job(self) -> None:
        """
        Registers a job to refresh the stage position.
        """
        self._refresh_position_job = None
        if self.calibration.supports_live_position:
            self._refresh_position_job = self.after(
                self.calibration.stage.live_position_refreshing_rate,
                self._refresh_position)

    def _refresh_position(self):
        """
        Refreshes Stage Position.
        Kills update job, if an error occurred.
        """
        try:
            with self.calibration.perform_in_system(CoordinateSystem.STAGE):
                self.coordinate = self.calibration.get_position()
        except Exception as exc:
            self.after_cancel(self._refresh_position_job)
            raise RuntimeError(exc)

        self._register_refresh_job()
