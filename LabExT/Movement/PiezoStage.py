#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import sys
import time

import numpy as np

from LabExT.Utils import get_configuration_file_path

#
# import the MCSControl software, separately provided by SmarAct GmbH
# currently, the path to this external module must be saved as JSON string
# in the settings file 'mcsc_module_path.txt'
#
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
    MCS_LOADED = False
finally:
    if sys_path_changed:
        del sys.path[0]


def status_code_to_string(code):
    if code == MCSC.SA_STOPPED_STATUS:
        return 'SA_STOPPED_STATUS'
    elif code == MCSC.SA_STEPPING_STATUS:
        return 'SA_STEPPING_STATUS'
    elif code == MCSC.SA_SCANNING_STATUS:
        return 'SA_SCANNING_STATUS'
    elif code == MCSC.SA_HOLDING_STATUS:
        return 'SA_HOLDING_STATUS'
    elif code == MCSC.SA_TARGET_STATUS:
        return 'SA_TARGET_STATUS'
    elif code == MCSC.SA_MOVE_DELAY_STATUS:
        return 'SA_MOVE_DELAY_STATUS'
    elif code == MCSC.SA_CALIBRATING_STATUS:
        return 'SA_CALIBRATING_STATUS'
    elif code == MCSC.SA_FINDING_REF_STATUS:
        return 'SA_FINDING_REF_STATUS'
    elif code == MCSC.SA_OPENING_STATUS:
        return 'SA_OPENING_STATUS'
    else:
        return "Unknown status code: " + str(code)


class PiezoStage:
    """Implementation of a PiezoStage, suitable for SmarAct stages.
    All movement in z direction is disabled.

    Attributes
    ----------
    mcs_handle : ctypes long
        MCS handle object
    x_channel : ctypes long
        Channel for x movement
    y_channel : ctypes long
        Channel for y movement
    """

    NUM_DIMENSIONS = 2

    def __init__(self, address):

        # define allowed sensor types
        self.allowed_linear_sensor_types = [
            # see MCS Programmers Guide, p136
            MCSC.SA_S_SENSOR_TYPE,
            MCSC.SA_M_SENSOR_TYPE,
            MCSC.SA_SC_SENSOR_TYPE,
            MCSC.SA_SP_SENSOR_TYPE,
            MCSC.SA_SD_SENSOR_TYPE,
            MCSC.SA_SC500_SENSOR_TYPE,
            MCSC.SA_SCD_SENSOR_TYPE,
            MCSC.SA_MD_SENSOR_TYPE
        ]

        self.logger = logging.getLogger()
        self.logger.debug('Initialise PiezoStage with address: %s', address)

        self.mcs_handle = MCSC.ct.c_ulong()
        self.address_string = address
        self.exit_if_error(
            MCSC.SA_OpenSystem(self.mcs_handle, address, bytes('sync', "utf-8")))

        # our stages have three channels, x y z
        self.x_channel = MCSC.ct.c_ulong(0)
        self.y_channel = MCSC.ct.c_ulong(1)
        self.z_channel = MCSC.ct.c_ulong(2)

        # check sensor availability on x channel
        sensor_type = MCSC.ct.c_ulong()
        self.exit_if_error(
            MCSC.SA_GetSensorType_S(self.mcs_handle, self.x_channel, sensor_type))
        if sensor_type.value in self.allowed_linear_sensor_types:
            self.logger.debug("Linear x sensor present")
        else:
            raise RuntimeError('X axis of stage {:s} has no supported linear sensor!'.format(self.address_string))

        # check sensor availability on y channel
        self.exit_if_error(
            MCSC.SA_GetSensorType_S(self.mcs_handle, self.y_channel, sensor_type))
        if sensor_type.value in self.allowed_linear_sensor_types:
            self.logger.debug("Linear y sensor present")
        else:
            raise RuntimeError('Y axis of stage {:s} has no supported linear sensor!'.format(self.address_string))

        # Set default closed-loop speed to 300 um per second (xy) and 20 um per second (z).
        # Faster values risk to make the fiber oscillate and hit onto the chip surface
        # Set acceleration controll OFF (encoded by a value of 0)
        self.set_speed_xy(300)
        self.set_speed_z(20)
        self.set_acceleration_xy(0)

        # Value for upward movement in z direction when a stage moves to a device
        self._z_lift = 20  # [um]
        # variable to keep track if stage is lifted
        self._stage_lifted_up = False

        self._z_axis_direction = 1  # either 1 or -1 depending on how the z axis is configured

        self.logger.info('PiezoStage at {} initialised successfully.'.format(address))

    def __del__(self):
        self.close_system()

    #
    # USB communication system
    #

    def close_system(self):
        """Releases stage and closes communication channels.
        """
        self.logger.debug("Closing MCS connection to stage %s.".format(self.address_string))
        self.exit_if_error(MCSC.SA_CloseSystem(self.mcs_handle))

    def exit_if_error(self, status):
        """Prints an Error, if occured with stages.

        Parameters
        ----------
        status : str
            Status returned by the stages.
        """
        # init error_msg variable
        error_msg = MCSC.ct.c_char_p()
        if status != MCSC.SA_OK:
            MCSC.SA_GetStatusInfo(status, error_msg)
            self.logger.error('MCS error: {}'.format(error_msg.value[:].decode('utf-8')))
        return

    #
    # calibration
    #

    def find_reference_mark(self):
        """Moves the positioner to a known physical position, by searching for the reference mark

        :return:
        """
        MCSC.SA_FindReferenceMark_S(self.mcs_handle, self.x_channel, MCSC.SA_BACKWARD_DIRECTION, 0, MCSC.SA_AUTO_ZERO)
        MCSC.SA_FindReferenceMark_S(self.mcs_handle, self.y_channel, MCSC.SA_BACKWARD_DIRECTION, 0, MCSC.SA_AUTO_ZERO)
        MCSC.SA_FindReferenceMark_S(self.mcs_handle, self.z_channel, MCSC.SA_BACKWARD_DIRECTION, 0, MCSC.SA_AUTO_ZERO)

    #
    # property setter / getters
    #

    def set_speed_xy(self, speed_xy_umps):
        """Sets the xy speed of a stage.
        See p. 40 of ´MCS ASCII Programming Interface.pdf´

        Parameters
        ----------
        speed_xy_umps : speed with which the stage will move in xy direction [um/s]
                valid range: 0...1e5 um/s
        """
        # convert speed from um/s to nm/s
        speed_xy_nmps = speed_xy_umps * 1e3
        speed_xy_nmps = MCSC.ct.c_int(int(speed_xy_nmps))

        self.exit_if_error(
            MCSC.SA_SetClosedLoopMoveSpeed_S(self.mcs_handle, self.x_channel, speed_xy_nmps))
        self.exit_if_error(
            MCSC.SA_SetClosedLoopMoveSpeed_S(self.mcs_handle, self.y_channel, speed_xy_nmps))

    def set_speed_z(self, speed_z_umps):
        """Sets the z speed of a stage.
        See p. 40 of ´MCS ASCII Programming Interface.pdf´

        Parameters
        ----------
        speed_z_umps : speed with which the stage will move in z direction [um/s]
                valid range: 0...1e5 um/s
        """
        # convert speed from um/s to nm/s
        speed_z_nmps = speed_z_umps * 1e3
        speed_z_nmps = MCSC.ct.c_int(int(speed_z_nmps))
        self.exit_if_error(
            MCSC.SA_SetClosedLoopMoveSpeed_S(self.mcs_handle, self.z_channel, speed_z_nmps))

    def get_speed_xy(self):
        """
        Returns the speed set at the stage for x and y direction in um/s.
        See p. 27 of ´MCS ASCII Programming Interface.pdf´.
        :return : speed in um/s
        """
        speed_x = MCSC.ct.c_int()
        speed_y = MCSC.ct.c_int()

        self.exit_if_error(
            MCSC.SA_GetClosedLoopMoveSpeed_S(self.mcs_handle, self.x_channel, speed_x))
        self.exit_if_error(
            MCSC.SA_GetClosedLoopMoveSpeed_S(self.mcs_handle, self.y_channel, speed_y))
        if speed_x.value != speed_y.value:
            self.logger.info("Speed settings of x and y channel are not equal.")

        # convert nm/s to um/s
        x_speed_umps = speed_x.value * 1e-3
        return x_speed_umps

    def get_speed_z(self):
        """
        Returns the speed set at the stage for z direction in um/s.
        See p. 27 of ´MCS ASCII Programming Interface.pdf´.
        :return : speed in um/s
        """
        speed_z = MCSC.ct.c_int()

        self.exit_if_error(
            MCSC.SA_GetClosedLoopMoveSpeed_S(self.mcs_handle, self.z_channel, speed_z))

        # convert nm/s to um/s
        z_speed_umps = speed_z.value * 1e-3
        return z_speed_umps

    def get_acceleration_xy(self):
        """
        Returns the acceleration set at the stage for x and y direction in um/s^2. See p. 26 of
        'MCS ASCII Programming Interface.pdf' for more detailled information.
        :return: acceleration of stage in um/s^2
        """
        acc_x = MCSC.ct.c_int()
        acc_y = MCSC.ct.c_int()

        self.exit_if_error(
            MCSC.SA_GetClosedLoopMoveAcceleration_S(self.mcs_handle, self.x_channel, acc_x)
        )
        self.exit_if_error(
            MCSC.SA_GetClosedLoopMoveAcceleration_S(self.mcs_handle, self.y_channel, acc_y)
        )
        if acc_x != acc_y:
            self.logger.info('Acceleration settings of x and y channel are not equal.')
        return acc_x.value

    def set_acceleration_xy(self, acc):
        """
        Set the acceleration at the stage for the x and y direction. See p. 38 of 'MCS ASCII Programming Interface.pdf'
        for more detailled information.
        :param acc: acceleration in um/s^2.
        """
        acc_xy = MCSC.ct.c_int(int(acc))

        self.exit_if_error(
            MCSC.SA_SetClosedLoopMoveAcceleration_S(self.mcs_handle, self.x_channel, acc_xy)
        )
        self.exit_if_error(
            MCSC.SA_SetClosedLoopMoveAcceleration_S(self.mcs_handle, self.y_channel, acc_xy)
        )

    def get_status(self):
        """Returns the channel status code (See MCS Programmer's guide page 135)

        Returns
        -------
        status_x.value, status_y.value : returns as tupel, each one containing a number between 0 and 8
        """
        code_x = MCSC.ct.c_ulong()
        code_y = MCSC.ct.c_ulong()
        code_z = MCSC.ct.c_ulong()

        self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.x_channel, code_x))
        self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.y_channel, code_y))
        self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.z_channel, code_z))

        status_x = status_code_to_string(code_x.value)
        status_y = status_code_to_string(code_y.value)
        status_z = status_code_to_string(code_z.value)

        return status_x, status_y, status_z

    #
    # lifting and lowering stages in z-direction
    #

    @property
    def z_axis_direction(self):
        return self._z_axis_direction

    @z_axis_direction.setter
    def z_axis_direction(self, newdir):
        if newdir not in [-1, 1]:
            raise ValueError("Z axis direction can only be 1 or -1.")
        self._z_axis_direction = newdir

    def invert_z_axis(self):
        """
        toggles the _z_axis_direction between -1 and +1
        """
        self._z_axis_direction = -self._z_axis_direction

    def wiggle_z_axis_positioner(self):
        """
        Wiggles the z axis positioner in order to enable the user to set the correct direction of the z movement

        Should first move "up" i.e. into direction of _z_axis_direction, then "down", i.e. against _z_axis_direction.
        """
        # current speed setting is saved and restored after the movement is performed
        tmp_speed = self.get_speed_z()
        # current speed setting is set to 1mm/s, so the following movement isn't performed to slow or to fast
        self.set_speed_z(1e3)
        # move up
        z_int = int(self._z_axis_direction * 1e6)  # +1mm
        z_cint = MCSC.ct.c_int(z_int)

        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.z_channel, z_cint, 0))

        status_z = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.z_channel, status_z))
            time.sleep(0.05)
            if status_z.value == MCSC.SA_STOPPED_STATUS:
                break

        # wait for one second so user has time to think
        time.sleep(1)

        # move down
        z_int = int(-self._z_axis_direction * 1e6)  # -1mm
        z_cint = MCSC.ct.c_int(z_int)

        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.z_channel, z_cint, 0))

        status_z = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.z_channel, status_z))
            time.sleep(0.05)
            if status_z.value == MCSC.SA_STOPPED_STATUS:
                break

        # set speed of movement back to old value
        self.set_speed_z(tmp_speed)
        
    @property
    def stage_lifted_up(self):
        return self._stage_lifted_up

    def lift_stage(self):
        """Lifts the stage up in the z direction by the amount defined in self._z_lift
        """
        if self._stage_lifted_up:
            self.logger.warning("Stage already lifted up. Not executing lift.")
            return

        z_int = int(self._z_axis_direction * self._z_lift * 1000)  # convert um to nm
        z_cint = MCSC.ct.c_int(z_int)

        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.z_channel, z_cint, 0))

        status_z = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.z_channel, status_z))
            time.sleep(0.05)
            if status_z.value == MCSC.SA_STOPPED_STATUS:
                break

        self._stage_lifted_up = True

    def lower_stage(self):
        """Lowers the stage in the z direction by the amount defined by self._z_lift
        """
        if not self._stage_lifted_up:
            self.logger.warning("Stage already lowered down. Not executing lowering.")
            return

        z_int = int(-self._z_axis_direction * self._z_lift * 1000)  # convert um to nm
        z_cint = MCSC.ct.c_int(z_int)

        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.z_channel, z_cint, 0))

        status_z = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.z_channel, status_z))
            time.sleep(0.05)
            if status_z.value == MCSC.SA_STOPPED_STATUS:
                break

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

    #
    # lateral x-y movement of piezo stage
    #

    def get_current_position(self):
        """Get current position of the stages in micrometers.

        Returns
        -------
        list
            Returns current position in [x,y] format in units of um.
        """
        # position in nm
        position = MCSC.ct.c_int()
        self.exit_if_error(
            MCSC.SA_GetPosition_S(self.mcs_handle, self.x_channel, position))
        x = position.value
        self.exit_if_error(
            MCSC.SA_GetPosition_S(self.mcs_handle, self.y_channel, position))
        y = position.value
        self.logger.debug('Current position of %s: x = %s nm, y = %s nm', self.address_string, x, y)
        return [x / 1000, y / 1000]  # convert from nm to um

    def move_relative(self, x, y):
        """Performs a relative movement by x and y. Specified in units of micrometers.

        Parameters
        ----------
        x : int
            Movement in x direction by x measured in um.
        y : int
            Movement in y direction by y measured in um.
        """
        x_int = int(x * 1000)  # convert um to nm
        y_int = int(y * 1000)  # convert um to nm
        # print('Type now: ', x_int)
        x_cint = MCSC.ct.c_int(x_int)
        y_cint = MCSC.ct.c_int(y_int)

        self.logger.debug('Want to relative move %s to x = %s nm with type %s and y = %s nm with type %s',
                          self.address_string, x_cint, type(x_cint), y_cint, type(y_cint))

        # command movements
        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.x_channel, x_cint, 0))
        self.exit_if_error(
            MCSC.SA_GotoPositionRelative_S(self.mcs_handle, self.y_channel, y_cint, 0))

        # wait until all movements performed
        # ToDo: Is this at all needed? We're using synchronous access above, which is probably breaking IO access.
        status_x = MCSC.ct.c_ulong()
        status_y = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.x_channel, status_x))
            self.exit_if_error(MCSC.SA_GetStatus_S(self.mcs_handle, self.y_channel, status_y))
            time.sleep(0.05)
            if (status_x.value == MCSC.SA_STOPPED_STATUS) and (status_y.value == MCSC.SA_STOPPED_STATUS):
                break

    def move_absolute(self, position):
        """Performs an absolute movement to the specified position in units of micrometers.

        Parameters
        ----------
        position : list
            Position in [x,y] format measured in um
        """
        x = position[0] * 1000  # convert um to nm
        y = position[1] * 1000  # convert um to nm

        x_int = int(x)
        y_int = int(y)

        x_cint = MCSC.ct.c_int(x_int)
        y_cint = MCSC.ct.c_int(y_int)

        self.logger.debug('Want to absolute move %s to x = %s nm with type %s and y = %s nm with type %s',
                          self.address_string, x_cint, type(x_cint), y_cint, type(y_cint))

        # command movements
        self.exit_if_error(
            MCSC.SA_GotoPositionAbsolute_S(self.mcs_handle, self.x_channel, x_cint, 0))
        self.exit_if_error(
            MCSC.SA_GotoPositionAbsolute_S(self.mcs_handle, self.y_channel, y_cint, 0))

        # wait until all movements performed
        # ToDo: Is this at all needed? We're using synchronous access above, which is probably breaking IO access.
        status_x = MCSC.ct.c_ulong()
        status_y = MCSC.ct.c_ulong()
        while True:
            self.exit_if_error(
                MCSC.SA_GetStatus_S(self.mcs_handle, self.x_channel, status_x))
            self.exit_if_error(
                MCSC.SA_GetStatus_S(self.mcs_handle, self.y_channel, status_y))
            time.sleep(0.05)
            if (status_x.value == MCSC.SA_STOPPED_STATUS) and (status_y.value == MCSC.SA_STOPPED_STATUS):
                curr_pos = np.array(self.get_current_position())
                distance = curr_pos - np.array(position)
                # Todo set correct margin
                if np.linalg.norm(distance) > 1:
                    raise RuntimeError('Target is out of mechanical range.')
                break
