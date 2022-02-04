#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import sys
import json
import time
import ctypes as ct
from enum import Enum
from tkinter import TclError
from typing import List

from LabExT.Movement.Stage import Stage, StageMeta, StageError, assert_stage_connected, assert_driver_loaded
from LabExT.Movement.Calibration import Axis
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog

sys_path_changed = False
try:
    settings_path = get_configuration_file_path('mcsc_module_path.txt')
    with open(settings_path, 'r') as fp:
        module_path = json.load(fp)
    sys.path.insert(0, module_path)
    sys_path_changed = True
    import MCSControl_PythonWrapper.MCSControl_PythonWrapper as MCSC
    MCS_LOADED = True
except (ImportError, OSError, FileNotFoundError):
    MCSC = object()
    MCS_LOADED = False
finally:
    if sys_path_changed:
        del sys.path[0]


class MovementType(Enum):
    """Enumerate different movement modes."""
    RELATIVE = 0,
    ABSOLUTE = 1


class Stage3DSmarAct(Stage):
    """Implementation of a SmarAct stage. Communication with the devices using the driver version 1.

    Attributes
    ----------
    handle : ctypes long
        MCS handle object
    channels : dict
        Dict of channel objects
    """

    driver_loaded = MCS_LOADED
    driver_path_dialog = None
    meta = StageMeta(
        description='SmarAct Modular Control System',
        driver_specifiable=True
    )

    @classmethod
    def load_driver(cls, parent) -> bool:
        """
        Loads driver for SmarAct by open a dialog to specifiy the driver path. This method will be invoked by the MovementWizardController.
        """
        if cls.driver_path_dialog is not None:
            try:
                cls.driver_path_dialog.deiconify()
                cls.driver_path_dialog.lift()
                cls.driver_path_dialog.focus_set()

                parent.wait_window(cls.driver_path_dialog)
                return cls.driver_path_dialog.path_has_changed
            except TclError:
                pass

        cls.driver_path_dialog = DriverPathDialog(
            parent,
            settings_file_path="mcsc_module_path.txt",
            title="Stage Driver Settings",
            label="SmarAct MCSControl driver module path",
            hint="Specify the directory where the module MCSControl_PythonWrapper is found.\nThis is external software,"
            "provided by SmarAct GmbH and is available from them. See https://smaract.com.")
        parent.wait_window(cls.driver_path_dialog)

        return cls.driver_path_dialog.path_has_changed

    @classmethod
    @assert_driver_loaded
    def find_stage_addresses(cls) -> List[str]:
        """
        Returns a list of SmarAct stage addresses
        """
        out_buffer = ct.create_string_buffer(4096)
        buffer_size = ct.c_ulong(4096)
        if cls._exit_if_error(
            MCSC.SA_FindSystems(
                '',
                out_buffer,
                buffer_size)):
            if buffer_size != ct.c_ulong(0):
                return out_buffer.value.decode().split()

        return []

    class _Channel:
        """Implementation of one SmarAct synchronous channel. One channel represents one axis.

        Attributes
        ----------
        name : str
            Human-readable description of the channel
        status : int
            Current channel status
        humanized_status : str
            Current channel status translated to string
        sensor : int
            Channel sensor
        is_sensor_linear : bool
            Tells if sensor is linear
        position : int
            Current absolute position in micrometer
        speed : float
            speed setting of channel in micrometers/seconds
        acceleration : float
            acceleration setting of channel in micrometers/seconds^2
        movement_mode : MovementType
            Movement type of the channel, either relative or absolute

        Methods
        -------
        move(diff, mode):
            Moves the channel with the specified movement type by the value "diff
        find_reference_mark():
            Finds reference mark of channel
        """

        STATUS_CODES = {
            MCSC.SA_STOPPED_STATUS: 'SA_STOPPED_STATUS',
            MCSC.SA_STEPPING_STATUS: 'SA_STEPPING_STATUS',
            MCSC.SA_SCANNING_STATUS: 'SA_SCANNING_STATUS',
            MCSC.SA_HOLDING_STATUS: 'SA_HOLDING_STATUS',
            MCSC.SA_TARGET_STATUS: 'SA_TARGET_STATUS',
            MCSC.SA_MOVE_DELAY_STATUS: 'SA_MOVE_DELAY_STATUS',
            MCSC.SA_CALIBRATING_STATUS: 'SA_CALIBRATING_STATUS',
            MCSC.SA_FINDING_REF_STATUS: 'SA_FINDING_REF_STATUS',
            MCSC.SA_OPENING_STATUS: 'SA_OPENING_STATUS'
        } if MCS_LOADED else {}

        LINEAR_SENSORS = [
            MCSC.SA_S_SENSOR_TYPE,
            MCSC.SA_M_SENSOR_TYPE,
            MCSC.SA_SC_SENSOR_TYPE,
            MCSC.SA_SP_SENSOR_TYPE,
            MCSC.SA_SD_SENSOR_TYPE,
            MCSC.SA_SC500_SENSOR_TYPE,
            MCSC.SA_SCD_SENSOR_TYPE,
            MCSC.SA_MD_SENSOR_TYPE
        ] if MCS_LOADED else []

        def __init__(self, stage, index, name='Channel') -> None:
            """Constructs all necessary attributes of the channel object.
            Creates c-long object with channel index and sets all default values.

            Parameters
            ----------
            stage : Stage
                stage object, to which this channel belongs
            index : int
                Channel index
            name : str
                (Optional) Human-readable description of channel
            """
            self.name = name
            self._stage = stage
            self._handle = ct.c_ulong(index)
            self._status = None
            self._movement_mode = MovementType.RELATIVE
            self._position = None
            self._sensor = None
            self._speed = 0
            self._acceleration = 0

        @property
        def status(self) -> int:
            """Returns current channel status specified by SA_GetStatus_S"""
            status_code = ct.c_ulong()
            self._stage._exit_if_error(
                MCSC.SA_GetStatus_S(
                    self._stage.handle,
                    self._handle,
                    status_code))

            self._status = status_code.value

            return self._status

        @property
        def humanized_status(self) -> str:
            """Translates current status to string"""
            status_code = self.status
            return self.STATUS_CODES.get(
                status_code, "Unknown status code: " + str(status_code))

        @property
        def sensor(self) -> int:
            """Returns channel sensor specified by SA_GetSensorType_S"""
            sensor_type = ct.c_ulong()
            if self._stage._exit_if_error(
                MCSC.SA_GetSensorType_S(
                    self._stage.handle,
                    self._handle,
                    sensor_type)):
                self._sensor = sensor_type.value
            return self._sensor

        @property
        def is_sensor_linear(self) -> bool:
            """Returns a decision wheter the sensor is linear"""
            return self.sensor in self.LINEAR_SENSORS

        @property
        def position(self):
            """Returns current position of channel in micrometers specified by SA_GetPosition_S"""
            system_position = ct.c_int()
            if self._stage._exit_if_error(
                MCSC.SA_GetPosition_S(
                    self._stage.handle,
                    self._handle,
                    system_position)):
                self._position = self._to_micrometer(system_position.value)

            return self._position

        @property
        def speed(self) -> float:
            """Returns speed setting of channel in micrometers/seconds specified by SA_GetClosedLoopMoveSpeed_S"""
            system_speed = ct.c_int()
            if self._stage._exit_if_error(
                MCSC.SA_GetClosedLoopMoveSpeed_S(
                    self._stage.handle,
                    self._handle,
                    system_speed)):
                self._speed = self._to_micrometer(system_speed.value)

            return self._speed

        @speed.setter
        def speed(self, umps: float) -> None:
            """Sets speed of channel in micrometers/seconds by calling SA_SetClosedLoopMoveSpeed_S

            Parameters
            ----------
            umps : float
                Speed measured in um/s
            """
            if self._stage._exit_if_error(MCSC.SA_SetClosedLoopMoveSpeed_S(
                self._stage.handle,
                self._handle,
                ct.c_int(int(self._to_nanometer(umps)))
            )):
                self._speed = umps

        @property
        def acceleration(self) -> float:
            """Returns acceleration of channel in micrometers/seconds^2 specified by SA_GetClosedLoopMoveAcceleration_S"""
            system_acceleration = ct.c_int()
            if self._stage._exit_if_error(
                MCSC.SA_GetClosedLoopMoveAcceleration_S(
                    self._stage.handle,
                    self._handle,
                    system_acceleration)):
                self._acceleration = system_acceleration.value

            return self._acceleration

        @acceleration.setter
        def acceleration(self, umps2: float) -> None:
            """Sets acceleration of channel in micrometers/seconds^2 by calling SA_SetClosedLoopMoveAcceleration_S

            Parameters
            ----------
            umps2 : float
                Acceleration measured in um/s^2
            """
            if (self._stage._exit_if_error(
                    MCSC.SA_SetClosedLoopMoveAcceleration_S(
                        self._stage.handle,
                        self._handle,
                        ct.c_int(int(umps2))
                    ))):
                self._acceleration = umps2

        @property
        def movement_mode(self) -> MovementType:
            """Returns movement mode of channel: Either RELATIVE or ABSOLUTE"""
            return self._movement_mode

        @movement_mode.setter
        def movement_mode(self, mode: MovementType) -> None:
            """Set movement mode of channel: Either RELATIVE or ABSOLUTE"""
            if mode.value not in MovementType._value2member_map_:
                raise ValueError("Invalid movement mode {}".format(str(mode)))
            self._movement_mode = mode

        # Channel control

        def stop(self) -> None:
            """Stops all movement of this channel"""
            self._stage._exit_if_error(
                MCSC.SA_Stop_S(
                    self._stage.handle,
                    self._handle
                ))

        # Movement

        def move(
                self,
                diff: float,
                mode: MovementType,
                wait_for_stopping=True) -> None:
            """Moves the channel with the specified movement type by the value diff

            Parameters
            ----------
            diff : float
                Channel movement measured in micrometers.
            mode : MovementType
                Channel movement type
            """
            self.movement_mode = mode
            if self.movement_mode == MovementType.RELATIVE:
                self._move_relative(diff, wait_for_stopping)
            elif self.movement_mode == MovementType.ABSOLUTE:
                self._move_absolute(diff, wait_for_stopping)

        def find_reference_mark(self):
            """Moves the channel to a known physical position, by searching for the reference mark"""
            self._stage._exit_if_error(
                MCSC.SA_FindReferenceMark_S(
                    self._stage.handle,
                    self._handle,
                    MCSC.SA_BACKWARD_DIRECTION,
                    0,
                    MCSC.SA_AUTO_ZERO
                ))

        # Helper functions

        def _move_relative(self, diff: float, wait_for_stopping: bool):
            self._stage._exit_if_error(
                MCSC.SA_GotoPositionRelative_S(
                    self._stage.handle,
                    self._handle,
                    ct.c_int(int(self._to_nanometer(diff))),
                    0
                ))
            if wait_for_stopping:
                self._wait_for_stopping()

        def _move_absolute(self, pos: float, wait_for_stopping: bool):
            self._stage._exit_if_error(
                MCSC.SA_GotoPositionAbsolute_S(
                    self._stage.handle,
                    self._handle,
                    ct.c_int(int(self._to_nanometer(pos))),
                    0
                ))
            if wait_for_stopping:
                self._wait_for_stopping()

        def _wait_for_stopping(self):
            while True:
                time.sleep(0.05)
                if self.status == MCSC.SA_STOPPED_STATUS:
                    break

        def _to_nanometer(self, um: float) -> int:
            return um * 1e3

        def _to_micrometer(self, nm: int) -> float:
            return nm * 1e-3

    # Setup and initialization

    def __init__(self, address):
        """Constructs all necessary attributes of the Stage3DSmarAct object.

        Calls stage super class to complete initialization.
        """
        self.handle = None
        self.channels = {}

        # LEGACY: stage lift
        self._z_lift = 20
        self._stage_lifted_up = False
        self._z_axis_direction = 1
        super().__init__(address.encode('utf-8'))

    def __str__(self) -> str:
        return "SmarAct Piezo-Stage at {}".format(str(self.address_string))

    @property
    def address_string(self) -> str:
        return self.address.decode('utf-8')

    @assert_driver_loaded
    def connect(self) -> bool:
        """Connects to stage by calling SA_OpenSystem and initializes a system handle.
        Creates Channel objects for X, Y and Z axis and checks if each sensor is linear. Raise error otherwise.
        Sets channel default values.
        """
        if self.connected:
            self._logger.debug('Stage is already connected.')
            return True

        self.handle = self._open_system()
        if self.handle is not None:
            for ch in Axis:
                self.channels[ch] = self._Channel(self, ch.value, ch.name)

            try:
                self._raise_if_sensor_non_linear()

                self.connected = True

                self.set_speed_xy(300)
                self.set_speed_z(20)
                self.set_acceleration_xy(0)

                self._logger.info(
                    'PiezoStage at {} initialised successfully.'.format(
                        self.address))
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
    def disconnect(self):
        """Disconnects stage by calling SA_CloseSystem"""
        if self._exit_if_error(MCSC.SA_CloseSystem(self.handle)):
            self.connected = False
            self.handle = None

    # Properties

    @property
    def z_axis_direction(self):
        return self._z_axis_direction

    @z_axis_direction.setter
    def z_axis_direction(self, newdir):
        if newdir not in [-1, 1]:
            raise ValueError("Z axis direction can only be 1 or -1.")
        self._z_axis_direction = newdir

    @property
    def stage_lifted_up(self):
        return self._stage_lifted_up

    # Stage settings method
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
    def get_speed_xy(self) -> float:
        """Returns the speed set at the stage for x and y direction in um/s."""
        x_speed = self.channels[Axis.X].speed
        y_speed = self.channels[Axis.Y].speed

        if(x_speed != y_speed):
            self._logger.info(
                "Speed settings of x and y channel are not equal.")

        return x_speed

    @assert_driver_loaded
    @assert_stage_connected
    def get_speed_z(self):
        """Returns the speed set at the stage for z direction in um/s."""
        return self.channels[Axis.Z].speed

    @assert_driver_loaded
    @assert_stage_connected
    def set_acceleration_xy(self, umps2):
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
        """Returns the acceleration set at the stage for x and y direction in um/s^2."""
        x_acceleration = self.channels[Axis.X].acceleration
        y_acceleration = self.channels[Axis.Y].acceleration

        if(x_acceleration != y_acceleration):
            self._logger.info(
                'Acceleration settings of x and y channel are not equal.')

        return x_acceleration

    @assert_driver_loaded
    @assert_stage_connected
    def get_status(self) -> tuple:
        """Returns the channel status codes translated to strings as tuple for each channel. """
        return tuple(ch.humanized_status for ch in self.channels.values())

    def invert_z_axis(self):
        """
        toggles the _z_axis_direction between -1 and +1
        """
        self._z_axis_direction = -self._z_axis_direction

    # Movement methods

    @assert_driver_loaded
    @assert_stage_connected
    def wiggle_z_axis_positioner(self):
        """
        Wiggles the z axis positioner in order to enable the user to set the correct direction of the z movement

        Should first move "up" i.e. into direction of _z_axis_direction, then "down", i.e. against _z_axis_direction.
        """
        z_channel = self.channels[Axis.Z]

        previous_speed = self.get_speed_z()
        self.set_speed_z(1e3)

        # Move up relative
        z_channel.move(
            diff=self.z_axis_direction * 1e3,
            mode=MovementType.RELATIVE)

        time.sleep(1)

        # Move down relative
        z_channel.move(
            diff=-self.z_axis_direction * 1e3,
            mode=MovementType.RELATIVE)

        self.set_speed_z(previous_speed)

    @assert_driver_loaded
    @assert_stage_connected
    def lift_stage(self):
        """Lifts the stage up in the z direction by the amount defined in self._z_lift
        """
        if self._stage_lifted_up:
            self._logger.warning(
                "Stage already lifted up. Not executing lift.")
            return

        self.channels[Axis.Z].move(
            diff=self._z_axis_direction * self._z_lift,
            mode=MovementType.RELATIVE
        )

        self._stage_lifted_up = True

    @assert_driver_loaded
    @assert_stage_connected
    def lower_stage(self):
        """Lowers the stage in the z direction by the amount defined by self._z_lift
        """
        if not self._stage_lifted_up:
            self._logger.warning(
                "Stage already lowered down. Not executing lowering.")
            return

        self.channels[Axis.Z].move(
            diff=-self._z_axis_direction * self._z_lift,
            mode=MovementType.RELATIVE
        )

        self._stage_lifted_up = False

    def get_lift_distance(self):
        """Returns the set value of how much the stage moves up

        :return: how much the stage moves up [um]
        """
        return self._z_lift

    def set_lift_distance(self, height):
        """Sets the value of how much the stage moves up

        :param height: how much the stage moves up [um]
        """
        height = float(height)
        assert height >= 0.0, "Lift distance must be non-negative."
        self._z_lift = height

    @assert_driver_loaded
    @assert_stage_connected
    def get_current_position(self) -> list:
        """Get current position of the stages in micrometers.

        Returns
        -------
        list
            Returns current position in [x,y] format in units of um.
        """
        return [
            self.channels[Axis.X].position,
            self.channels[Axis.Y].position
        ]

    @assert_driver_loaded
    @assert_stage_connected
    def move_relative(self, x, y):
        """Performs a relative movement by x and y. Specified in units of micrometers.

        Parameters
        ----------
        x : int
            Movement in x direction by x measured in um.
        y : int
            Movement in y direction by y measured in um.
        """
        self._logger.debug(
            'Want to relative move %s to x = %s um and y = %s um',
            self.address,
            x,
            y)

        self.channels[Axis.X].move(diff=x, mode=MovementType.RELATIVE)
        self.channels[Axis.Y].move(diff=y, mode=MovementType.RELATIVE)

    @assert_driver_loaded
    @assert_stage_connected
    def move_absolute(self, pos):
        """Performs an absolute movement to the specified position in units of micrometers.

        Parameters
        ----------
        position : list
            Position in [x,y] format measured in um
        """
        self._logger.debug(
            'Want to absolute move %s to x = %s um and y = %s um',
            self.address,
            pos[0],
            pos[1])

        self.channels[Axis.X].move(
            diff=pos[0], mode=MovementType.ABSOLUTE)
        self.channels[Axis.Y].move(
            diff=pos[1], mode=MovementType.ABSOLUTE)

    # Stage control

    @assert_driver_loaded
    @assert_stage_connected
    def stop(self):
        for channel in self.channels.values():
            channel.stop()

    # Helper methods

    @classmethod
    def _exit_if_error(self, status: int) -> bool:
        if(status == MCSC.SA_OK):
            return True

        error_message = ct.c_char_p()
        MCSC.SA_GetStatusInfo(status, error_message)

        if error_message:
            error_message = 'MCSControl Error: {}'.format(
                error_message.value[:].decode('utf-8'))
        else:
            error_message = 'MCSControl Error: Undefined error occurred.'

        raise StageError(error_message)

    def _open_system(self):
        handle = ct.c_ulong()
        if self._exit_if_error(
            MCSC.SA_OpenSystem(
                handle,
                self.address,
                bytes('sync', 'utf-8'))):
            return handle
        return None

    def _raise_if_sensor_non_linear(self) -> None:
        for index, channel in self.channels.items():
            if not channel.is_sensor_linear:
                raise StageError(
                    'Channel {} of stage {} has no supported linear sensor!'.format(
                        index.name, self.address))
        self._logger.debug("Linear x, y and z sensor present")
