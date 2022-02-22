#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import Type
from LabExT.Movement.Stage import Stage
from LabExT.View.Controls.CoordinateWidget import CoordinateWidget


class StagePositionWidget(CoordinateWidget):
    """
    Widget, which display the current position of a stage. Updates automatically.
    """

    REFRESHING_RATE = 1000  # [ms]

    def __init__(self, parent, stage: Type[Stage]):
        self.stage = stage

        super().__init__(parent, self.stage.get_current_position())

        self._update_pos_job = self.after(
            self.REFRESHING_RATE, self._refresh_position)

    def __del__(self):
        if self._update_pos_job:
            self.after_cancel(self._update_pos_job)

    def _refresh_position(self):
        """
        Refreshes Stage Position.

        Kills update job, if an error occurred.
        """
        try:
            self.coordinate = self.stage.get_current_position()
        except Exception as exc:
            self.after_cancel(self._update_pos_job)
            raise RuntimeError(exc)

        self.after(self.REFRESHING_RATE, self._refresh_position)
