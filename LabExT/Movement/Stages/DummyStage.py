#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Movement.Stage import Stage


class DummyStage(Stage):
    """
    Simple Stage implementation for testing purposes.
    """

    #
    #   Class description and properties
    #

    driver_loaded = True
    driver_specifiable = False
    description = "Dummy Stage Vendor"

    @classmethod
    def find_stage_addresses(cls):
        return [
            'tcp:192.168.0.42:1234',
            'tcp:192.168.0.123:7894'
        ]

    @classmethod
    def load_driver(cls):
        pass

    def __init__(self, address):
        super().__init__(address)

        self._speed_xy = None
        self._speed_z = None
        self._acceleration_xy = None

    def __str__(self) -> str:
        return "Dummy Stage at {}".format(self.address_string)

    @property
    def address_string(self) -> str:
        return self.address

    @property
    def identifier(self) -> str:
        return self.address_string

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> bool:
        self.connected = False
        return True

    def set_speed_xy(self, umps: float):
        self._speed_xy = umps

    def set_speed_z(self, umps: float):
        self._speed_z = umps

    def get_speed_xy(self) -> float:
        return self._speed_xy

    def get_speed_z(self) -> float:
        return self._speed_z

    def set_acceleration_xy(self, umps2):
        self._acceleration_xy = umps2

    def get_acceleration_xy(self) -> float:
        return self._acceleration_xy

    def get_status(self) -> tuple:
        return ('STOP', 'STOP', 'STOP')

    @property
    def is_stopped(self) -> bool:
        return all(s == 'STOP' for s in self.get_status())

    def get_position(self) -> list:
        return [0, 0, 0]

    def move_relative(
            self,
            x: float = 0,
            y: float = 0,
            z: float = 0,
            wait_for_stopping: bool = True) -> None:
        pass

    def move_absolute(
            self,
            x: float = None,
            y: float = None,
            z: float = None,
            wait_for_stopping: bool = True) -> None:
        pass
