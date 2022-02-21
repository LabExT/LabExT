#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.View.StageCalibration.StageCalibrationView import StageCalibrationView
from LabExT.Movement.Calibration import CalibrationError, DevicePort, Orientation


class StageCalibrationController:
    def __init__(self, experiment_manager, mover, parent=None) -> None:
        # REMOVE ME
        for idx, stage in enumerate(mover.available_stages):
            mover.add_stage_calibration(
                stage,
                Orientation(
                    idx + 1),
                DevicePort(
                    idx + 1))
            stage.connect()

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

    def save_single_point_fixation(self, fixations):
        """
        Saves for each calibration the single point fixation.
        """
        errors = {}

        for calibration, fixation in fixations.items():
            try:
                calibration.fix_single_point(fixation)
            except CalibrationError as e:
                errors.update({calibration: e})

        if errors:
            raise CalibrationError(errors)

        if self.experiment_manager:
            self.experiment_manager.main_window.refresh_context_menu()

        return True

    def save_full_calibration(self, rotations):
        """
        Saves for each calibration the Kabsch rotation.
        """