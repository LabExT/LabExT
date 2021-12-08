#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import importlib
import sys
from typing import Type
from tkinter import Tk

from LabExT.Movement.Stage import StageError, Stage
from LabExT.View.ApplicationController import ApplicationController
from LabExT.View.MovementWizard.MovementWizardView import MovementWizardView
from LabExT.Movement.MoverNew import MoverNew


class MovementWizardController(ApplicationController):
    def __init__(self, parent: Type[Tk], experiment_manager) -> None:
        super().__init__(parent, experiment_manager)
        self.mover: Type[MoverNew] = experiment_manager.mover_new
        self.view = MovementWizardView(parent, self, self.mover)

    #
    # View Controller methods
    #

    def new(self):
        """
        Creates View to configure stages
        """
        self.view.driver_frame()
        self.view.connection_frame()

        if not self.mover.all_disconnected:
            self.view.configuration_frame()

    def save_mover(
        self,
        speed_xy=None,
        speed_z=None,
        z_lift=None
    ):
        """
        Saves mover configuration
        """
        if speed_xy == 0:
            self.view.warning = "Setting a xy speed of 0 will turn the speed control OFF! \n" \
                                "The stage will now move as fast as possible. Set a different speed if " \
                                "this is not intended."
        if speed_z == 0:
            self.view.warning = "Setting a z speed of 0 will turn the speed control OFF! \n" \
                                "The stage will now move as fast as possible. Set a different speed if " \
                                "this is not intended."
        try:
            self.mover.speed_xy = speed_xy
        except StageError as exce:
            self.view.error = "Error during stage configuration, xy speed not set: \n {}".format(
                exce)

        try:
            self.mover.speed_z = speed_z
        except StageError as exce:
            self.view.error = "Error during stage configuration, z speed not set: \n {}".format(
                exce)

        self.mover.z_lift = z_lift

        self.new()

    def save_stage(
        self,
        stage,
        invert_z=None
    ):
        """
        Saves stage configurtion
        """
        pass

    #
    # Driver Management methods
    #

    def load_driver_and_reload(self, stage_class: Type[Stage]):
        importlib.reload(sys.modules.get(stage_class.__module__))
        self.new()

    #
    # Stage Management methods
    #

    def connect_to_all_stages(self):
        try:
            self.mover.connect()
            self.view.info = "Successfully connected to {} stages.".format(
                len(self.mover.stages))
        except StageError as exce:
            self.view.error = """Connection establishment to the stages failed: \n {} \n
							     Please check if all drivers are loaded and all stages are connected correctly.
							  """.format(exce)
        finally:
            self.new()

    def connect_to_single_stage_by_poll_index(self, stage_idx: int):
        try:
            self.mover.connect_stage_by_index(stage_idx)
            self.view.info = "Successfully connected to stage {}.".format(
                stage_idx)
        except (StageError, KeyError) as exce:
            self.view.error = """Connection establishment to stage {} failed: \n {} \n
							     Please check if all drivers are loaded and all stages are connected correctly.
							  """.format(stage_idx, exce)
        finally:
            self.new()

    def disconnect_to_all_stages(self):
        try:
            self.mover.disconnect()
            self.view.info = "Successfully disconnected {} stages.".format(
                len(self.mover.stages))
        except StageError as exce:
            self.view.error = """Connection teardown for stages failed: \n {} \n
							     Please check if all drivers are loaded and all stages are connected correctly.
							  """.format(exce)
        finally:
            self.new()

    def disconnect_to_single_stage_by_poll_index(self, stage_idx: int):
        try:
            self.mover.disconnect_stage_by_index(stage_idx)
            self.view.info = "Successfully disconnected stage {}.".format(
                stage_idx)
        except (StageError, KeyError) as exce:
            self.view.error = """Connection teardown for stage {} failed: \n {} \n
							     Please check if all drivers are loaded and all stages are connected correctly.
							  """.format(stage_idx, exce)
        finally:
            self.new()
