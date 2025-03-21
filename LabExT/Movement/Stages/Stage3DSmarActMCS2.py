#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2024  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import time
from typing import List

from LabExT.Movement.config import Axis
from LabExT.Movement.Stage import Stage, assert_driver_loaded, StageError, assert_stage_connected
from LabExT.Movement.Stages.ChannelMCS2 import ChannelMCS2
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog

from LabExT.Utils import try_to_lift_window

try:
    import smaract.ctl as ctl
    MCS_LOADED = True
except (ImportError, OSError):
    MCS_LOADED = False

class Stage3DSmarActMCS2(Stage):
    """Implementation of a SmarAct stage. Communication with the devices using the driver version 2.

    Attributes
    ----------
    handle : int
        MCS handle
        
    """

    driver_loaded = MCS_LOADED
    driver_specifiable = False
    description = "SmarAct Modular Control System for one 3D stage (driver version 2)"

    @classmethod
    @assert_driver_loaded
    def find_stage_addresses(cls) -> List[str]:
        """
        Returns a list of SmarAct stage addresses
        """
        buffer = ctl.FindDevices()
        if buffer:
            locators = buffer.split('\n')
            def is_one_module(locator):
                d_handle = ctl.Open(locator)
                result = ctl.GetProperty_i32(d_handle, 0, ctl.Property.NUMBER_OF_BUS_MODULES) == 1
                ctl.Close(d_handle)
                return result
            return [locator for locator in locators if is_one_module(locator)]
        return []

    # Setup and initialization

    def __init__(self, address):
        """Constructs all necessary attributes of the Stage3DSmarActMCS2 object.
        Calls stage super class to complete initialization.
        """
        self.handle = None
        self.channels = {}
        super().__init__(address)

    def __str__(self) -> str:
        return f'SmarAct Piezo-Stage at {str(self.address_string)}'

    @property
    def address_string(self) -> str:
        return self.address
    
    @property
    def identifier(self) -> str:
        """
        Returns the address as identifier for a SmartAct stage
        """
        return self.address_string

    @assert_driver_loaded
    def connect(self) -> bool:
        """Connects to stage by calling ctl.Open and initializes a system handle.
        Creates Channel objects for X, Y and Z axis and checks if each sensor is linear. Raise error otherwise.
        Sets channel default values.
        """
        if self.connected:
            self._logger.debug('Stage is already connected.')
            return True

        self.handle = self._open_system()
        if self.handle is not None:
            for ch in Axis:
                self.channels[ch] = ChannelMCS2(self, ch.value, ch.name)
            try:
                self._raise_if_sensor_non_linear()
                self.connected = True
                self.set_speed_xy(300)
                self.set_speed_z(20)
                self.set_acceleration_xy(0)
                self._logger.info(f'PiezoStage at {self.address} initialized successfully.')
            except Exception as e:
                self.connected = False
                self.handle = None
                self.channels = {}
                raise e
        else:
            self.connected = False

        return self.connected

    @assert_driver_loaded
    @assert_stage_connected
    def disconnect(self) -> None:
        """Disconnects stage by calling ctl.Close"""
        ctl.Close(self.handle)
        self.connected = False
        self.handle = None

    # Stage settings methods

    @assert_driver_loaded
    @assert_stage_connected
    def find_reference_mark(self):
        for channel in self.channels.values():
            channel.find_reference_mark()

    @assert_driver_loaded
    @assert_stage_connected
    def set_speed_xy(self, umps: float):
        """Sets the xy speed of a stage.

        Parameters
        ----------
        umps : speed with which the stage will move in xy direction [um/s]
                valid range: 0...1e5 um/s
        """
        self.channels[Axis.X].speed = umps
        self.channels[Axis.Y].speed = umps

    @assert_driver_loaded
    @assert_stage_connected
    def get_speed_xy(self) -> float:
        """Returns the speed set at the stage for x and y direction in um/s."""
        x_speed = self.channels[Axis.X].speed
        y_speed = self.channels[Axis.Y].speed

        if (x_speed != y_speed):
            self._logger.info('Speed settings of x and y channel are not equal.')

        return x_speed

    @assert_driver_loaded
    @assert_stage_connected
    def set_speed_z(self, umps: float):
        """Sets the z speed of a stage.

        Parameters
        ----------
        umps : speed with which the stage will move in z direction [um/s]
                valid range: 0...1e5 um/s
        """
        self.channels[Axis.Z].speed = umps

    @assert_driver_loaded
    @assert_stage_connected
    def get_speed_z(self) -> float:
        """Returns the speed set at the stage for z direction in um/s."""
        return self.channels[Axis.Z].speed

    @assert_driver_loaded
    @assert_stage_connected
    def set_acceleration_xy(self, umps2) -> None:
        """Set the acceleration at the stage for the x and y direction.

        Parameters
        ----------
        umps2 : float
            Acceleration measured in um/s^2
        """
        self.channels[Axis.X].acceleration = umps2
        self.channels[Axis.Y].acceleration = umps2

    @assert_driver_loaded
    @assert_stage_connected
    def get_acceleration_xy(self) -> float:
        """Returns the acceleration set at the stage for the x and y direction in um/s^2. """
        x_acceleration = self.channels[Axis.X].acceleration
        y_acceleration = self.channels[Axis.Y].acceleration

        if (x_acceleration != y_acceleration):
            self._logger.info(
                'Acceleration settings of x and y channel are not equal.')

        return x_acceleration

    @assert_driver_loaded
    @assert_stage_connected
    def get_status(self) -> tuple:
        """Returns the channel status codes translated into strings as tuple for each channel."""
        return tuple(ch.humanized_status for ch in self.channels.values())
    
    @property
    @assert_driver_loaded
    @assert_stage_connected
    def is_stopped(self) -> bool:
        """
        Returns true if all axis are stopped.
        """
        return not any('ACTIVELY_MOVING' in status for status in self.get_status())

    # Movement Methods

    @assert_driver_loaded
    @assert_stage_connected
    def get_position(self) -> list:
        """Get current position of the stage in micrometers.

        Returns
        -------
        list
            Returns current position in [x,y,z] format in units of um.
        """
        # return [ch.position for ch in self.channels.values()]
        return [
            self.channels[Axis.X].position,
            self.channels[Axis.Y].position,
            self.channels[Axis.Z].position
        ]

    @assert_driver_loaded
    @assert_stage_connected
    def move_relative(self, x: float, y: float, z: float = 0, wait_for_stopping: bool = True) -> None:
        """Performs a relative movement by x and y. Specified in unity of micrometers.

        Parameters
        ----------
        x : float
            Movement in x direction by x measured in um.
        y : float
            Movement in y direction by y measured in um.
        z : float
            Movement in z direction by z measured in um.
        wait_for_stopping : bool
            Wait until all aces have stopped.
        """
        self._logger.debug(f'Want to relative move {self.address} to x = {x}, y = {y}, z = {z}')
        self.channels[Axis.X].move(value=x, mode=ctl.MoveMode.CL_RELATIVE)
        self.channels[Axis.Y].move(value=y, mode=ctl.MoveMode.CL_RELATIVE)
        self.channels[Axis.Z].move(value=z, mode=ctl.MoveMode.CL_RELATIVE)

        if wait_for_stopping:
            self._wait_for_stopping()

    @assert_driver_loaded
    @assert_stage_connected
    def move_absolute(self, x: float = None, y: float = None, z: float = None, wait_for_stopping: bool = True) -> None:
        """
        Performs an absolute movement to the specified position in units of micrometers.
        """
        self._logger.debug(f'Want to absolute move {self.address} to x = {x}, y = {y}, z = {z}')

        if x is not None:
            self.channels[Axis.X].move(value=x, mode=ctl.MoveMode.CL_ABSOLUTE)
        if y is not None:
            self.channels[Axis.Y].move(value=y, mode=ctl.MoveMode.CL_ABSOLUTE)
        if z is not None:
            self.channels[Axis.Z].move(value=z, mode=ctl.MoveMode.CL_ABSOLUTE)

        if wait_for_stopping:
            self._wait_for_stopping()

    # Helper Methods

    def _open_system(self):
        handle = ctl.Open(self.address)
        if handle:
            return handle
        return None

    def _raise_if_sensor_non_linear(self) -> None:
        for index, channel in self.channels.items():
            if not channel.is_sensor_linear:
                raise StageError(f'Channel {index.name} of stage {self.address} has no supported linear sensor!')
            self._logger.debug('Linear x, y and z sensor present.')

    def _wait_for_stopping(self, delay=0.05) -> None:
        """Blocks until all channels have stopped moving."""
        while True:
            time.sleep(delay)

            if self.is_stopped:
                break
