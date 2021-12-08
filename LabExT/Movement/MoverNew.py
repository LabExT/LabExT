#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import Type, List
from functools import wraps

from LabExT.Movement.Stage import Stage


def assert_connected_stages(func):
    """
    Use this decorator to assert that the mover has at least one connected stage,
    when calling methods, which require connected stages.
    """

    @wraps(func)
    def wrapper(mover, *args, **kwargs):
        if mover.all_disconnected:
            raise MoverError(
                "Function {} needs at least one connected stage. Please use the connection functions beforehand".format(
                    func.__name__))

        return func(mover, *args, **kwargs)
    return wrapper


class MoverError(RuntimeError):
    pass


class MoverNew:
    DEFAULT_SPEED_XY = 200
    DEFAULT_SPPED_Z = 20
    DEFAULT_Z_LIFT = 20

    def __init__(self, experiment_manager):
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager.
        """
        self.experiment_manager = experiment_manager
        self.logger = logging.getLogger()

        self._stages: List[Type[Stage]] = Stage.discovery()
        self._stage_classes: List[Stage] = Stage.get_all_stage_classes()

        self._speed_xy = self.DEFAULT_SPEED_XY
        self._speed_z = self.DEFAULT_SPPED_Z
        self._z_lift = self.DEFAULT_Z_LIFT

    def __del__(self):
        """Collects all settings and stores them in a file"""
        pass

    @property
    def stage_classes(self):
        return self._stage_classes

    @property
    def stages(self):
        return self._stages

    @property
    def connected_stages(self):
        return list(filter(lambda s: s.connected, self.stages))

    @property
    def disconnected_stages(self):
        return list(filter(lambda s: not s.connected, self.stages))

    @property
    def all_connected(self):
        if len(self.stages) == 0:
            return False
        return len(self.connected_stages) == len(self.stages)

    @property
    def all_disconnected(self):
        if len(self.stages) == 0:
            return True
        return len(self.disconnected_stages) == len(self.stages)

    #
    #   Connectivity methods
    #

    def connect(self):
        if not self.stages:
            raise MoverError(
                "No stages found to connect. Please check your devices.")

        for stage in self.stages:
            stage.connect()

    def connect_stage_by_index(self, stage_idx: int):
        if not self.stages:
            raise MoverError(
                "No stages found to connect. Please check your devices.")

        self.stages[stage_idx].connect()

    @assert_connected_stages
    def disconnect(self):
        for stage in self.connected_stages:
            stage.disconnect()

    @assert_connected_stages
    def disconnect_stage_by_index(self, stage_idx: int):
        if not self.stages[stage_idx].connected:
            return

        self.stages[stage_idx].disconnect()
