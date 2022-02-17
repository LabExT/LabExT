#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.View.StageCalibration.StageCalibrationView import StageCalibrationView
from LabExT.Movement.Calibration import CalibrationError


class StageCalibrationController:
    def __init__(self, experiment_manager, mover, parent=None) -> None:
        # Precondition: Mover has connected stages
        if not mover.has_connected_stages:
            raise AssertionError(
                "Cannot calibrate mover without any connected stage. ")

        self.experiment_manager = experiment_manager
        self.mover = mover
        self.view = StageCalibrationView(
            parent, experiment_manager, self, self.mover) if parent else None

    def save_coordinate_system(self, axes_rotations):
        """
        Saves for each calibration the axes rotation.
        """
        errors = {}

        for calibration, axes_rotation in axes_rotations.items():
            try:
                calibration.fix_coordinate_system(axes_rotation)
            except CalibrationError as e:
                errors.update({calibration: e})

        if errors:
            raise CalibrationError(errors)

        if self.experiment_manager:
            self.experiment_manager.main_window.refresh_context_menu()

        return True
