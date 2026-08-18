#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import sys
import json
import time
import numpy as np

from enum import Enum

from pylablib.devices import Thorlabs
# import py_thorlabs_ctrl.kinesis as KCUBE
# from System import Decimal

from LabExT.Movement.config import Axis
from LabExT.Movement.Stage import Stage, StageError, assert_stage_connected, assert_driver_loaded
from LabExT.Utils import get_configuration_file_path, try_to_lift_window
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog

sys_path_changed = False
try:
    settings_path = get_configuration_file_path('kcube_module_path.txt')
    with open(settings_path, 'r') as fp:
        module_path = json.load(fp)
    # sys.path.insert(0, module_path)
    # KCUBE.init(module_path)
    sys_path_changed = True
    # from Thorlabs import KinesisMotor
    # from pylablib.devices import Thorlabs
    KCUBE_LOADED = True
except (ImportError, OSError, FileNotFoundError):
    KCUBE = object()
    KCUBE_LOADED = False
finally:
    if sys_path_changed:
        del sys.path[0]

class MovementType(Enum):
    """Enumerate different movement modes."""
    RELATIVE = 0,
    ABSOLUTE = 1

# Empirically measured mechanical backlash of the Z825B actuators, in micrometers.
# Configured once per channel via the Kinesis controller's own native backlash
# compensation (KinesisMotor.setup_gen_move) so the firmware applies it automatically,
# and only on the axis that actually reverses direction. Adjust if a different stage
# model with different backlash is used.
BACKLASH_DISTANCE_UM = 10.0

# Position differences below this are treated as "already there" and no move is
# issued - avoids spurious real movement for floating-point noise while still allowing
# genuinely small deliberate moves.
MIN_MOVE_DISTANCE_UM = 1e-3

class ThorlabsKCube(Stage):
    """
    Simple Stage implementation for testing purposes.
    """

    #
    #   Class description and properties
    #

    driver_loaded = KCUBE_LOADED
    driver_path_dialog = None
    driver_specifiable = True
    description = "Thorlabs KCube Stages"

    @classmethod
    def load_driver(cls, parent):
        """
        Loads driver for SmarAct by open a dialog to specifiy the driver path. This method will be invoked by the StageWizard.
        """
        if try_to_lift_window(cls.driver_path_dialog):
            parent.wait_window(cls.driver_path_dialog)
            return cls.driver_path_dialog.path_has_changed

        cls.driver_path_dialog = DriverPathDialog(
            parent,
            settings_file_path="kcube_module_path.txt",
            title="Stage Driver Settings",
            label="Thorlabs driver module path",
            hint="Specify the directory where the Thorlabs blah blah blah")
        parent.wait_window(cls.driver_path_dialog)
        
        return cls.driver_path_dialog.path_has_changed

    @classmethod
    @assert_driver_loaded
    def find_stage_addresses(cls): #TODO
        devices = Thorlabs.list_kinesis_devices()
        return ["ThorlabsKCube"]
    
    class _Channel:
        def __init__(self, serial_number, name='Channel') -> None:
            self.name = name
            self._sn = serial_number
            self._stage = Thorlabs.KinesisMotor(self._sn, scale="Z825")
            self._stage.setup_gen_move(backlash_distance=BACKLASH_DISTANCE_UM * 1e-6)
            self._status = None
            self._movement_mode = MovementType.RELATIVE
            self._position = None
            self._sensor = None
            self._speed = 0
            self._acceleration = 0
        
        @property
        def status(self) -> int:
            """Returns current channel status"""
            self._status = self._stage.get_status()

            return self._status
        
        @property
        def position(self):
            """Returns current position of channel in micrometers"""
            self._position = self._stage.get_position() * 1e6

            return self._position
        
        @property
        def speed(self) -> float: #TODO
            """Returns maximum speed setting of channel in micrometers/seconds"""
            self._speed = self._stage.get_velocity_parameters()[2] * 1e6

            return self._speed
        
        @speed.setter
        def speed(self, umps: float) -> None:
            self._speed = self._stage.setup_velocity(max_velocity=umps*1e-6, acceleration=None)

        @property
        def acceleration(self) -> float: 
            """Returns acceleration of channel in micrometers/seconds^2"""
            self._acceleration = self._stage.get_velocity_parameters()[1] * 1e6

            return self._acceleration

        @acceleration.setter
        def acceleration(self, umps2: float, max_velocity=None) -> None:
            """Sets acceleration of channel in micrometers/seconds^2

            Parameters
            ----------
            umps2 : float
                Acceleration measured in um/s^2
            """
            accel = None if umps2 < 1e-8 else umps2/1e6
            self._acceleration = self._stage.setup_velocity(max_velocity=max_velocity, acceleration=accel)

        # Channel control
        def stop(self) -> None:
            """Stops all movement of this channel"""
            self._stage.stop(immediate=True)

        def is_moving(self) -> None:
            """Checks if the channel is moving"""
            return self._stage.is_moving()

        def move(
                self,
                diff: float,
                mode: MovementType) -> None:
            """Moves the channel with the specified movement type by the value diff.

            Backlash compensation is handled natively by the Kinesis controller
            (configured once in __init__ via setup_gen_move), which applies it
            automatically to move_by/move_to and only when direction actually reverses.

            Parameters
            ----------
            diff : float
                Channel movement measured in micrometers. In RELATIVE mode this is the
                signed distance to move; in ABSOLUTE mode this is the target position.
            mode : MovementType
                Channel movement type
            """
            if mode == MovementType.RELATIVE:
                if np.abs(diff) < MIN_MOVE_DISTANCE_UM:
                    return
                self._stage.move_by(diff * 1e-6)
                self._stage.wait_move()
            elif mode == MovementType.ABSOLUTE:
                if np.abs(diff - self.position) < MIN_MOVE_DISTANCE_UM:
                    return
                self._stage.move_to(diff * 1e-6)
                self._stage.wait_move()

        def wait_for_stopping(self) -> None:
            """Waits until the channel stops moving"""
            self._stage.wait_move()

    def __init__(self, address):
        super().__init__(address)
        self.channels = {}
        self.handle = None
        self._speed_z = None
        self._speed_xy = 0
        self.instr_cfg_path = get_configuration_file_path('instruments.config')
        self.axes = []
        self.sns = []

    def __str__(self) -> str:
        return "KCUBE Stage at {}".format(self.address_string)

    @property
    def address_string(self) -> str:
        return self.address

    @property
    def identifier(self) -> str:
        return self.address_string

    def connect(self) -> bool:
        if self.connected:
            self._logger.debug('Stage is already connected.')
            return True
    
        with open(self.instr_cfg_path, 'r') as fp:
            cfg_data = json.load(fp)
        self.motor_cfg = cfg_data['Mover']['ThorlabsKCube']

        for stage in self.motor_cfg:
            if stage["axis"] == "X":
                self.axes.append(Axis.X)
                self.sns.append(stage["sns"])
            elif stage["axis"] == "Y":
                self.axes.append(Axis.Y)
                self.sns.append(stage["sns"])
            elif stage["axis"] == "Z": # Modified so z is empty (we don't want labext to move the z stage)
                #self.axes.append(Axis.Z)
                self.sns.append(None)

        for sn, axis in zip(self.sns, self.axes):
            try:
                self.channels[axis] = self._Channel(serial_number=sn)
                self.connected = True

                self._logger.info(
                    'KCube at {} initialised successfully.'.format(
                        self.address))

            except Exception as e:
                self.connected = False
                self.handle = None
                self.channels = {}

                raise e
            
        return self.connected

    @assert_driver_loaded
    # @assert_stage_connected
    def disconnect(self) -> bool:
        for ch in self.channels:
            ch.close()
        self.connected = False

    @assert_driver_loaded
    # @assert_stage_connected
    def set_speed_xy(self, umps: float):
        self.channels[Axis.X].speed = umps
        self.channels[Axis.Y].speed = umps
        self._speed_xy = umps

    @assert_driver_loaded
    # @assert_stage_connected
    def set_speed_z(self, umps: float):
        # self.channels[Axis.Z].speed = umps
        self._speed_z = umps

    @assert_driver_loaded
    # @assert_stage_connected
    def get_speed_xy(self) -> float:
        x_speed = self.channels[Axis.X].speed
        y_speed = self.channels[Axis.Y].speed
        if (x_speed != y_speed):
            self._logger.info(
                "Speed settings of x and y channel are not equal.")
            
        return x_speed

    @assert_driver_loaded
    # @assert_stage_connected
    def get_speed_z(self) -> float:
        return self._speed_z

    @assert_driver_loaded
    # @assert_stage_connected
    def set_acceleration_xy(self, umps2):
        self.channels[Axis.X].acceleration = umps2
        self.channels[Axis.Y].acceleration = umps2

    @assert_driver_loaded
    # @assert_stage_connected
    def get_acceleration_xy(self) -> float:
        x_acceleration = self.channels[Axis.X].acceleration
        y_acceleration = self.channels[Axis.Y].acceleration

        if (x_acceleration != y_acceleration):
            self._logger.info(
                'Acceleration settings of x and y channel are not equal.')

        return x_acceleration

    @assert_driver_loaded
    # @assert_stage_connected
    def get_status(self) -> tuple: #TODO
        return tuple(ch.status for ch in self.channels.values())

    def is_stopped(self, channel, stop_pos_um) -> bool: #TODO
        return all(not s for s in self.is_moving())

    @assert_driver_loaded
    # @assert_stage_connected
    def get_position(self) -> list:
        """ Returns position in (um)
        """
        return [
            self.channels[Axis.X].position,
            self.channels[Axis.Y].position,
            0 #self.channels[Axis.Z].position,
        ]

    @assert_driver_loaded
    # @assert_stage_connected
    def move_relative(
            self,
            x: float = 0,
            y: float = 0,
            z: float = 0,
            wait_for_stopping: bool = True) -> None:
        
        self._logger.debug(
            'Want to relative move %s to x = %s um, y = %s um and z = %s um',
            self.address,
            x,
            y,
            z)
        self.channels[Axis.X].move(diff=x, mode=MovementType.RELATIVE)
        self.channels[Axis.Y].move(diff=y, mode=MovementType.RELATIVE)
        # self.channels[Axis.Z].move(diff=z, mode=MovementType.RELATIVE)
       
        if wait_for_stopping:
            self._wait_for_stopping(self.channels)

        pass

    def move_absolute(
            self,
            x: float = None,
            y: float = None,
            z: float = None,
            wait_for_stopping: bool = True) -> None:
        
        self._logger.debug(
            'Want to absolute move %s to x = %s um, y = %s um and z = %s um',
            self.address,
            x,
            y,
            z)

        if x is not None:
            self.channels[Axis.X].move(diff=x, mode=MovementType.ABSOLUTE)
        if y is not None:
            self.channels[Axis.Y].move(diff=y, mode=MovementType.ABSOLUTE)
        # if z is not None:
        #     self.channels[Axis.Z].move(diff=z, mode=MovementType.ABSOLUTE)
        
        if wait_for_stopping:
            self._wait_for_stopping(self.channels)

    def _wait_for_stopping(self, channels: list[_Channel]):
        """
        Blocks until all channels have 'SA_STOPPED_STATUS' status.
        """
        for axis, channel in channels.items():
            channel.wait_for_stopping()