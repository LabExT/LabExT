#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import importlib
import sys
from typing import Type

from LabExT.Movement.Stage import Stage, StageError
from LabExT.View.MovementWizard.MovementWizardView import MovementWizardView
from LabExT.Movement.MoverNew import MoverError, MoverNew


class MovementWizardController:
    def __init__(self, experiment_manager, mover, parent=None) -> None:
        self.experiment_manager = experiment_manager
        self.mover: Type[MoverNew] = mover
        self.view = MovementWizardView(
            parent, self, self.mover) if parent else None

    def save(
        self,
        stage_assignment: dict,
        speed_xy: float = MoverNew.DEFAULT_SPEED_XY,
        speed_z: float = MoverNew.DEFAULT_SPEED_Z,
        acceleration_xy: float = MoverNew.DEFAULT_ACCELERATION_XY,
    ):
        """
        Saves mover configuration.

        Throws ValueError if speed or acceleration is not in the valid range.
        Throws MoverError and/or StageError if stage assignment or stage connection did not work.
        """
        # Tell mover to use the assigned stage. Can throw MoverError,
        # StageError and ValueError
        for stage, assignment in stage_assignment.items():
            try:
                orientation, port = assignment
                calibration = self.mover.add_stage_calibration(
                    stage, orientation, port)
                calibration.connect_to_stage()
            except (ValueError, MoverError, StageError) as e:
                self.mover.reset()
                raise e

        # Setting speed and acceleration values. Can throw StageError and
        # ValueError.
        if self.mover.has_connected_stages:
            self.mover.speed_xy = speed_xy
            self.mover.speed_z = speed_z
            self.mover.acceleration_xy = acceleration_xy

        # Refresh Context Menu
        if self.experiment_manager:
            self.experiment_manager.main_window.refresh_context_menu()

    def load_driver(self, stage_class: Type[Stage]):
        """
        Invokes the load_driver function of some Stage class.

        If successful, it reloads the Stage module and the wizard.
        """
        if not stage_class.meta.driver_specifiable:
            return

        if stage_class.load_driver(parent=self.view):
            importlib.reload(sys.modules.get(stage_class.__module__))
            self.mover.reload_stage_classes()
            self.mover.reload_stages()
            self.view.__reload__()

    def reload_stage_classes(self):
        """
        Callback, when user wants to reload stage classes.
        """
        self.mover.reload_stage_classes()
        self.view.__reload__()
