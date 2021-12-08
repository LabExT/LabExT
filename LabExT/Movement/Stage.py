#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from functools import wraps
from abc import ABC, abstractmethod


class StageError(RuntimeError):
    pass


def assert_stage_connected(func):
    """
    Use this decorator to assert that any method of a stage is only executed
    when the stage is connected and all drivers are loaded.
    """

    @wraps(func)
    def wrapper(stage, *args, **kwargs):
        if not stage.driver_loaded:
            raise StageError(
                "Stage driver not loaded: Function {} requires previously loaded drivers.".format(
                    func.__name__))
        if not stage.connected:
            raise StageError(
                "Stage not connected: Function {} requires an active stage connection. Make sure that you have called connect() before.".format(
                    func.__name__))

        return func(stage, *args, **kwargs)
    return wrapper


class Stage(ABC):
    _logger = logging.getLogger()
    driver_loaded = False

    _META_DESCRIPTION = ''
    _META_CONNECTION_TYPE = ''

    @classmethod
    def discovery(cls):
        stages = []
        for stage_class in cls.__subclasses__():
            stages += stage_class.find_stages()
        return stages

    @classmethod
    def find_stages(cls):
        raise NotImplementedError

    @abstractmethod
    def __init__(self, address):
        self.address = address
        self.connected = False

    def __del__(self):
        if self.connected:
            self.disconnect()

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        pass

    @abstractmethod
    def set_speed_xy(self, umps: float):
        pass

    @abstractmethod
    def set_speed_z(self, umps: float):
        pass

    @abstractmethod
    def get_speed_xy(self) -> float:
        pass

    @abstractmethod
    def get_speed_z(self) -> float:
        pass

    @abstractmethod
    def set_acceleration_xy(self):
        pass

    @abstractmethod
    def get_acceleration_xy(self) -> float:
        pass

    @abstractmethod
    def get_status(self) -> tuple:
        pass

    @abstractmethod
    def wiggle_z_axis_positioner(self):
        pass

    @abstractmethod
    def lift_stage(self):
        pass

    @abstractmethod
    def lower_stage(self):
        pass

    @abstractmethod
    def get_current_position(self):
        pass

    @abstractmethod
    def move_relative(self, x, y):
        pass

    @abstractmethod
    def move_absolute(self, pos):
        pass
