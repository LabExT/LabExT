#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Movement.Stage import Stage, StageMeta


class DummyStage(Stage):
    """
    Simple Stage implementation for testing purposes.
    """

    #
    #   Class description and properties
    #

    driver_loaded = True
    meta = StageMeta(
        description="Dummy Stage Vendor",
        driver_specifiable=False
    )

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
        self._z_lift = None
        self._z_axis_direction = 1

    def __str__(self) -> str:
        return "Dummy Stage at {}".format(self.address_string)

    @property
    def address_string(self) -> str:
        return self.address

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> bool:
        self.connected = False
        return True

    @property
    def z_axis_direction(self):
        return self._z_axis_direction

    @property
    def z_axis_inverted(self):
        return self.z_axis_direction == -1

    @z_axis_direction.setter
    def z_axis_direction(self, newdir):
        if newdir not in [-1, 1]:
            raise ValueError("Z axis direction can only be 1 or -1.")
        self._z_axis_direction = newdir

    def toggle_z_axis_direction(self):
        self.z_axis_direction *= -1

    @property
    def z_axis_inverted(self):
        return self.z_axis_direction == -1

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

    def wiggle_z_axis_positioner(self):
        pass

    def lift_stage(self):
        pass

    def lower_stage(self):
        pass

    def set_lift_distance(self, um: float):
        self._z_lift = um

    def get_lift_distance(self) -> float:
        return self._z_lift

    def get_current_position(self):
        return [0, 0]

    def move_relative(self, x, y):
        pass

    def move_absolute(self, pos):
        pass
