#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from abc import ABC, abstractmethod


class StageError(RuntimeError):
    pass


class Stage(ABC):
    _logger = logging.getLogger()
    driver_loaded = False

    @classmethod
    def find_stages(cls):
        raise NotImplementedError

    @abstractmethod
    def __init__(self, address):
        self.address = address
        self.connected = False

    def __del__(self):
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
