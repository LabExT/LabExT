#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from functools import wraps
from abc import ABC, abstractmethod
from os.path import dirname, join

from LabExT.PluginLoader import PluginLoader


class StageError(RuntimeError):
    pass


def assert_stage_connected(func):
    """
    Use this decorator to assert that any method of a stage is only executed
    when the stage is connected.
    """

    @wraps(func)
    def wrapper(stage, *args, **kwargs):
        if not stage.connected:
            raise StageError(
                "Stage not connected: Function {} requires an active stage connection. Make sure that you have called connect() before.".format(
                    func.__name__))

        return func(stage, *args, **kwargs)
    return wrapper


def assert_driver_loaded(func):
    """
    Use this decorator to assert that any method of a stage is only executed
    when the drivers are loaded.
    """

    @wraps(func)
    def wrapper(stage, *args, **kwargs):
        if not stage.driver_loaded:
            raise StageError(
                "Stage driver not loaded: Function {} requires previously loaded drivers.".format(
                    func.__name__))

        return func(stage, *args, **kwargs)
    return wrapper


class Stage(ABC):
    _logger = logging.getLogger()
    driver_loaded = False

    @classmethod
    def find_stage_classes(cls, subdir="Stages") -> list:
        """
        Returns a list of all classes which inherit from this class.

        Needs to import Stages module first.
        """
        search_path = join(dirname(__file__), subdir)
        plugin_loader = PluginLoader()

        return [*plugin_loader.load_plugins(search_path, cls).values()]

    @classmethod
    def find_available_stages(cls):
        """
        Returns a list of stage objects. Each object represents a found stage.

        Note: The stage is not yet connected.
        """
        stages = []
        for stage_class in cls.find_stage_classes():
            try:
                addresses = stage_class.find_stage_addresses()
            except StageError:
                continue
            for address in addresses:
                stages.append(stage_class(address))

        return stages

    @classmethod
    def find_stage_addresses(cls) -> list:
        """
        Returns a list of stage locators.
        """
        return []

    @classmethod
    def load_driver(cls, parent=None) -> bool:
        """
        Stage specific method to load any missing drivers.

        Returns True, if successfully loaded and False otherwise.

        Needs to be overwritten.
        """
        raise NotImplementedError

    @abstractmethod
    def __init__(self, address):
        self.address = address
        self.connected = False

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def address_string(self) -> str:
        raise NotImplementedError

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
