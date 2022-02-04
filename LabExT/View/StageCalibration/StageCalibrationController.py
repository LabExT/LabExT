#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Movement.Calibration import Calibration, DevicePort, Orientation, Axis
from LabExT.View.StageCalibration.StageCalibrationView import StageCalibrationView


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

        self.experiment_manager = experiment_manager
        self.mover = mover
        self.view = StageCalibrationView(
            parent, experiment_manager, self, self.mover) if parent else None

    def save_coordinate_system(self, axes_rotations):
        """
        Saves axes calibration.
        """
        for calibration, axes_rotation in axes_rotations.items():
            try:
                calibration.fix_coordinate_system(axes_rotation)
            except Exception as e:
                self.view.set_error("Calibration failed: {}".format(e))
                return False

        self.experiment_manager.main_window.refresh_context_menu()
        return True
