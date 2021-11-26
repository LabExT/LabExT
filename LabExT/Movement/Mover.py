#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
import pickle
import sys
import time
from tkinter import Toplevel, messagebox

import numpy as np

from LabExT.Movement.Stage3DSmarAct import Stage3DSmarAct
from LabExT.Movement.StageTrajectory import StageTrajectory
from LabExT.Utils import run_with_wait_window, get_configuration_file_path
from LabExT.View.ChooseStageWindow import ChooseStageWindow
from LabExT.View.MoveDeviceWindow import MoveDeviceWindow
from LabExT.transformations import Transformation2D

class Mover:
    """Handles everything related to the movement of the stages.

    Attributes
    ----------
    mover_enabled : bool
        If the mover is enabled at all. Is False if the Piezo Stage
        driver could not be loaded.
    trafo_enabled : bool
        Whether a coordinate transformation has been performed.
    num_stages : int
        Number of active stages
    left_stage : PiezoStage
        Left PiezoStage. Will move to inputs.
    right_stage : PiezoStage
        Right PiezoStage. Will move to outputs.
    """

    dimension_names_two_stages = ['Left X', 'Left Y', 'Right X', 'Right Y']
    dimension_names_one_stage = ['X', 'Y']

    def __init__(self, experiment_manager):
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager.
        """
        self.mover_enabled = Stage3DSmarAct.driver_loaded
        self.trafo_enabled = False

        self._experiment_manager = experiment_manager

        self._transformer_left = None
        self._transformer_right = None

        self.num_stages = 0
        self.left_stage = None
        self.right_stage = None

        self.dimension_names = []

        self.savefilename_settings = get_configuration_file_path('stage_settings.pkl')
        self.savefilename_transformation = get_configuration_file_path('coordinate_transformer.pkl')

        self.logger = logging.getLogger()
        self.logger.debug('Initialised Mover with experiment_manager:%s', experiment_manager)

    #
    # initialization and status reporting
    #

    def init_stages(self):
        """Initialises the stages.
        """
        if not self.mover_enabled:
            msg = "Linked library for stage movement not loaded." + \
                  " Any movement through LabExT will be deactivated."
            self.logger.error(msg)
            raise RuntimeError(msg)

        # release stages if already configured
        if self.left_stage is not None or self.right_stage is not None:
            msg = "One or more stages already initialized. To re-initialize Stages if needed, restart LabExT."
            self.logger.error(msg)
            raise RuntimeError(msg)

        stages = Stage3DSmarAct.find_stages()
        if not stages:
            msg = 'Could not find any stages connected to the computer.'
            self.logger.error(msg)
            raise RuntimeError(msg)

        self.logger.info('Found stages: %s', stages)

        # make the user choose which stage is left and which is right
        new_window = Toplevel(self._experiment_manager.root)
        new_window.attributes('-topmost', 'true')
        stage_window = ChooseStageWindow(new_window, self._experiment_manager, '', stages)
        self._experiment_manager.root.wait_window(new_window)

        # if the user aborts and doesn't choose stages
        # it's as if there were none
        if stage_window.aborted:
            self.logger.debug('Aborted by user.')
            return

        # get selected addresses of stages
        self.num_stages = stage_window.num_stages
        left_stage_address = stage_window.left_choice
        right_stage_address = stage_window.right_choice

        def create_stages():
            self.left_stage = Stage3DSmarAct(left_stage_address.encode('utf-8'))
            self.left_stage.connect()
            if self.num_stages == 2:
                self.right_stage = Stage3DSmarAct(right_stage_address.encode('utf-8'))
                self.right_stage.connect()
            new_window.destroy()

        run_with_wait_window(self._experiment_manager.root,
                             'Please wait while stages are being initialised.',
                             create_stages)

        self.logger.info("Initialized {} piezo stages - left: {}, right: {}.".format(
            self.num_stages, left_stage_address, right_stage_address
        ))

        # update dimension names
        if self.num_stages == 2:
            self.dimension_names = self.dimension_names_two_stages.copy()
        elif self.num_stages == 1:
            self.dimension_names = self.dimension_names_one_stage.copy()
        else:
            raise RuntimeError("Number of stages reported from user selection window must be either 1 or 2!")

        settings = self._load_settings()
        self._apply_settings(settings)

    def _check_stage_status(self):
        """
        Checks all necessary stages status and initializes them if necessary
        """
        if self.num_stages == 1:
            if self.left_stage is None:
                self.init_stages()
            if self.left_stage is None:
                raise RuntimeError('Abort movement. Stage could not be initialised.')
        else:
            if (self.left_stage is None) or (self.right_stage is None):
                self.init_stages()
            if (self.left_stage is None) or (self.right_stage is None):
                raise RuntimeError('Abort movement. Stages could not be initialised.')

    def get_status_code(self):
        """Returns channel status code of x, y and z positioner for each stage

        Returns
        -------
        status_left: channel status codes for left stage
        status_right: channel status codes for right stage
        """
        self._check_stage_status()
        if self.num_stages == 1:
            status_left = self.left_stage.get_status()
            status_right = ['not connected'] * 3
        else:
            status_left = self.left_stage.get_status()
            status_right = self.right_stage.get_status()

        return status_left, status_right

    #
    # setter and getter of properties
    #

    def get_speed_of_stages_xy(self):
        """Returns the movement speed of stages in xy direction

        Returns
        -------
        speed : speed [um/s] of left stage(since both stages have the same speed settings
                it doesn't matter which one is called)
        """
        self._check_stage_status()
        speed_left = self.left_stage.get_speed_xy()
        if self.num_stages == 2:
            speed_right = self.right_stage.get_speed_xy()
            if speed_left != speed_right:
                self.logger.info("Left and right stage have different speed settings. " +
                                 "Setting right stage speed setting equal to left stage.")
                self.set_speed_of_stages_xy(speed_left)
        return speed_left

    def get_acceleration_of_stages_xy(self):
        """
        Returns the set movement acceleration of stages in xy direction.

        Returns
        -------
        acceleration: acceleration [um/s^2] of left stage (both stages are suppposed to have
        same acceleration).
        """
        self._check_stage_status()
        acc_left = self.left_stage.get_acceleration_xy()
        if self.num_stages == 2:
            acc_right = self.right_stage.get_acceleration_xy()
            if acc_left != acc_right:
                self.logger.info('Left and right stages have different acceleration settings. ' +
                                 'Setting right stage acceleration setting equal to lef stage.')
                self.set_acceleration_of_stages_xy(acc_left)

        return acc_left

    def set_acceleration_of_stages_xy(self, acc_umps2):
        """
        Sets the acceleration in x and y direction.
        :param acc_umps2: acceleration in um/s^2
        """
        self._check_stage_status()

        if self.num_stages == 1:
            self.left_stage.set_acceleration_xy(acc_umps2)
        else:
            self.left_stage.set_acceleration_xy(acc_umps2)
            self.right_stage.set_acceleration_xy(acc_umps2)

    def get_z_axis_direction_left(self):
        """Returns the z axis direction of the left stage

        Returns
        -------
        z_axis_direction : direction of the z axis, either -1 or 1
        """

        z_axis_direction = self.left_stage.z_axis_direction
        return z_axis_direction

    def get_z_axis_direction_right(self):
        """Returns the z axis direction of the right stage

        Returns
        -------
        z_axis_direction : direction of the z axis, either -1 or 1
        """

        z_axis_direction = self.right_stage.z_axis_direction
        return z_axis_direction

    def set_speed_of_stages_xy(self, speed_umps):
        """Sets the speed in xy direction of both stages

        Parameters
        ----------
        speed_umps : speed with which the stages will move in xy direction [um/s]
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.set_speed_xy(speed_umps)
        else:
            self.left_stage.set_speed_xy(speed_umps)
            self.right_stage.set_speed_xy(speed_umps)

    def set_speed_of_stages_z(self, speed_umps):
        """Sets the speed in z direction of both stages

        Parameters
        ----------
        speed_umps : speed with which the stages will move in z direction [um/s]
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.set_speed_z(speed_umps)
        else:
            self.left_stage.set_speed_z(speed_umps)
            self.right_stage.set_speed_z(speed_umps)

    def get_speed_of_stages_z(self):
        """Returns the movement speed of stages in z direction

        Returns
        -------
        speed : speed [nm/s] of left stage(since both stages have the same speed settings
                it doesn't matter which one is called)
        """
        self._check_stage_status()
        speed_left = self.left_stage.get_speed_z()
        if self.num_stages == 2:
            speed_right = self.right_stage.get_speed_z()
            if speed_left != speed_right:
                self.logger.info("Left and right stage have different speed settings. " +
                                 "Setting right stage speed setting equal to left stage.")
                self.set_speed_of_stages_z(speed_left)
        return speed_left

    def get_z_lift(self):
        """Returns how much the stage moves up in z direction before it moves to a device

        Returns
        -------
        _z_lift: how much the stage moves up in [nm]
        """
        self._check_stage_status()
        z_lift = self.left_stage.get_lift_distance()
        return z_lift

    def set_z_lift(self, height):
        """Sets how much the stage moves up in z direction before it moves to a device

        Parameters
        ----------
        height: how much the stage moves up [um]
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.set_lift_distance(height)
        else:
            self.left_stage.set_lift_distance(height)
            self.right_stage.set_lift_distance(height)

    #
    # z-direction movement for lifting / lowering stages
    #

    def lift_stages(self):
        """
        Lifts the stages up by the amount defined in set_z_lift.
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.lift_stage()
        else:
            self.left_stage.lift_stage()
            self.right_stage.lift_stage()

    def lower_stages(self):
        """
        Deactivates the z movement before the stage moves to the target position
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.lower_stage()
        else:
            self.left_stage.lower_stage()
            self.right_stage.lower_stage()

    #
    # lateral x-y movement
    #

    def move_to_device(self, device):
        """Moves to a specific device on the chip.

        Parameters
        ----------
        device : Device
            Device to move to.

        Raises
        ------
        RuntimeError
            If no 2D transformation has been done beforehand.
        """
        self.logger.debug('Device to move to: %s', device)

        # only allow automatic movement if transformation done beforehand
        if not self.trafo_enabled:
            raise RuntimeError('Automatic movement disabled, no 2D Transformation done.')

        self._check_stage_status()

        # get transformed in- and outputs
        in_ = self._transformer_left.chip_to_stage_coord(device._in_position)
        if self.num_stages == 2:
            out_ = self._transformer_right.chip_to_stage_coord(device._out_position)
        else:
            out_ = None

        self.logger.debug('Positions after transformation: input:%s output:%s', in_, out_)

        # execute absolute movement
        if self.num_stages == 2:
            self.move_absolute(in_[0], in_[1], out_[0], out_[1], safe_movement=True, lift_z_dir=True)
        else:
            self.move_absolute(in_[0], in_[1], lift_z_dir=True)

        # save to log
        self.logger.debug('Moved to device successfully.')

    def move_relative(self, *args, lift_z_dir=False):
        """Perform a relative movement of the stages.

            You need to provide 4 coordinates if two stages are enabled,
            and 2 coordinates if only one stage is enabled.

            args = [lx, ly, rx, ry] for 2 stages
            args = [lx, ly] for 1 stage

        Parameters
        ----------
        *args :
            coordinates where to move to in stage coordinates
        lift_z_dir:
            if true, stages temporarily raise a bit in z direction before lateral movement

        Raises
        ------
        RuntimeError
            If stages could not be initialised.
            If safe_movement is true but transformation wasn't done yet.
        """
        self._check_stage_status()

        if len(args) != len(self.dimension_names):
            raise RuntimeError("Given number of coordinates does not match configured dimensions.")

        self.logger.debug('Move relative by: %s', args)

        stages_up = False
        # if the x movement of stage 1 is positive: move stage 2 first. Otherwise vice versa.
        if self.num_stages == 1:
            # move left stage
            if not (np.isclose(float(args[0]), 0.0) and np.isclose(float(args[1]), 0.0)):
                if lift_z_dir:
                    self.lift_stages()
                    stages_up = True
                t0 = time.time()
                self.left_stage.move_relative(float(args[0]), float(args[1]))
                t1 = time.time()
                print(t1 - t0)
        else:
            if float(args[0])<=0:
                # move left stage
                if not (np.isclose(float(args[0]), 0.0) and np.isclose(float(args[1]), 0.0)):
                    if lift_z_dir:
                        self.lift_stages()
                        stages_up = True
                    self.left_stage.move_relative(float(args[0]), float(args[1]))
                # move right stage
                if not (np.isclose(float(args[2]), 0.0) and np.isclose(float(args[3]), 0.0)):
                    if lift_z_dir and not stages_up:
                        self.lift_stages()
                        stages_up = True
                    self.right_stage.move_relative(-float(args[2]), -float(args[3]))
            else:
                # move right stage
                if not (np.isclose(float(args[2]), 0.0) and np.isclose(float(args[3]), 0.0)):
                    if lift_z_dir and not stages_up:
                        self.lift_stages()
                        stages_up = True
                    self.right_stage.move_relative(-float(args[2]), -float(args[3]))
                # move left stage
                if not (np.isclose(float(args[0]), 0.0) and np.isclose(float(args[1]), 0.0)):
                    if lift_z_dir:
                        self.lift_stages()
                        stages_up = True
                    self.left_stage.move_relative(float(args[0]), float(args[1]))

        if lift_z_dir and stages_up:
            self.lower_stages()

        self.logger.debug("Moved relative by %s.", args)

    def move_absolute(self, *args, safe_movement=False, lift_z_dir=False):
        """Move the stages to absolute coordinates given in micrometers.

            You need to provide 4 coordinates if two stages are enabled,
            and 2 coordinates if only one stage is enabled.

            args = [lx, ly, rx, ry] for 2 stages
            args = [lx, ly] for 1 stage

        Parameters
        ----------
        *args :
            coordinates where to move to, in stage coordinates
        safe_movement:
            if true, algorithm for save movement is used, otherwise not
        lift_z_dir:
            if true, stages temporarily raise a bit in z direction before lateral movement

        Raises
        ------
        RuntimeError
            If stages could not be initialised.
            If safe_movement is true but transformation wasn't done yet.
        """
        self._check_stage_status()

        if len(args) != len(self.dimension_names):
            raise RuntimeError("Given number of coordinates does not match configured dimensions.")

        if lift_z_dir:
            self.lift_stages()

        if self.num_stages == 1:
            self.left_stage.move_absolute([args[0], args[1]])
        else:
            if safe_movement:
                if self.trafo_enabled:
                    move_safe = StageTrajectory()
                    move_safe.move_on_safe_trajectory(args[0], args[1], args[2], args[3], self)
                else:
                    raise RuntimeError("Can't execute safe movement, because transformation is not done.")
            else:
                self.left_stage.move_absolute([args[0], args[1]])
                self.right_stage.move_absolute([args[2], args[3]])

        if lift_z_dir:
            self.lower_stages()

        loc_str = " x ".join(["{:.3f}um".format(p) for p in args])
        self.logger.debug('Moved absolute to %s.', loc_str)

    #
    # reading coordinates
    #

    def get_absolute_stage_coords(self):
        """Read stage positions in all two resp. four dimensions in um.

           return format for 2 stages is [lx, ly, rx, ry]
           return format for 1 stage is [lx, ly]

        Returns
        ----------
        list of double
            current absolute stage coordinates of all configured dimensions

        Raises
        ------
        RuntimeError
            If stages could not be initialised.
        """
        self._check_stage_status()

        coords = self.left_stage.get_current_position()
        if self.num_stages == 2:
            coords += self.right_stage.get_current_position()

        self.logger.debug("Current absolute positions read: %s".format(coords))

        return coords

    def get_absolute_chip_coords(self):
        """Read chip positions in all two resp. four dimensions in um.

           return format for 2 stages is [lx, ly, rx, ry]
           return format for 1 stage is [lx, ly]

        Returns
        ----------
        list of double
            current absolute chip coordinates of all configured dimensions
        """
        if not self.trafo_enabled:
            raise RuntimeError('Cannot get chip coordinates if no 2D Transformation is calibrated.')

        stage_coords = self.get_absolute_stage_coords()

        chip_coords = self._transformer_left.stage_to_chip_coord(stage_pos=stage_coords[0:2])
        if self.num_stages == 2:
            chip_coords += self._transformer_right.stage_to_chip_coord(stage_pos=stage_coords[2:4])

        return chip_coords

    #
    # reading from and writing to savefiles
    #

    def save_settings(self):
        """
        Saves the current settings in a pkl file
        """
        if self.num_stages == 2:
            settings = {'xy_speed': self.get_speed_of_stages_xy(),
                        'z_speed': self.get_speed_of_stages_z(),
                        'xyz_speed_unit': 'um/s',
                        'z_lift': self.get_z_lift(),
                        'left_z_direction': self.left_stage.z_axis_direction,
                        'right_z_direction': self.right_stage.z_axis_direction}
        else:
            settings = {'xy_speed': self.get_speed_of_stages_xy(),
                        'z_speed': self.get_speed_of_stages_z(),
                        'z_lift': self.get_z_lift(),
                        'xyz_speed_unit': 'um/s',
                        'left_z_direction': self.left_stage.z_axis_direction}
            settings_temp = self._load_settings()
            if 'right_z_direction' in settings_temp.keys():
                settings['right_z_direction'] = settings_temp['right_z_direction']

        with open(self.savefilename_settings, 'wb') as settings_file:
            pickle.dump(settings, settings_file)
            logging.debug('Piezo stage settings saved.')

    def check_for_saved_transformation(self):
        """
        Checks if there is a saved file containing the transformation and lets the user decide
        if he wants to load it or make a new transformation
        """
        try:
            with open(self.savefilename_transformation, 'rb') as transformer_file:
                date = time.ctime(os.path.getmtime(self.savefilename_transformation))
                transformer = pickle.load(transformer_file)
                chip_name = transformer[6]
                num_stages_old = transformer[7]
                # if there is a file ask user if he wants to load it
                title = "Found saved coordinate transformation"
                message = "A previously saved transformation is available. Do you want to load it?\n" \
                          "Last modified: " + date + "\n" + "Name of Chip: " + chip_name
                answer = messagebox.askyesno(title, message)

                if not answer:
                    self.make_transformation()
                    return

                if num_stages_old != self.num_stages:
                    message = ('The current number of stages ({}) is not equal to the number of stages ({}) ' \
                               + 'the old transformation was made for!\n' \
                               + 'Do you still want to continue?').format(self.num_stages, num_stages_old)
                    answer = messagebox.askyesno("Warning", message)
                    if not answer:
                        self.logger.info("Number of stages does not match. "
                                         "A new coordinate transformation needs to be done.")
                        self.make_transformation()
                        return

                self._transformer_left = Transformation2D(self)
                self._transformer_left._matrix = transformer[0]
                self._transformer_left._chip_offset = transformer[1]
                self._transformer_left._stage_offset = transformer[2]

                self._transformer_right = Transformation2D(self)
                self._transformer_right._matrix = transformer[3]
                self._transformer_right._chip_offset = transformer[4]
                self._transformer_right._stage_offset = transformer[5]

                # all good
                self.trafo_enabled = True
                self._experiment_manager.main_window.model.status_transformation_enabled.set(self.trafo_enabled)

                # inform user
                msg = "Saved calibration loaded. Automatic movement enabled."
                if self.num_stages == 2:
                    msg += " All non relative movements will be run with stage collision avoidance algorithm."
                self.logger.info(msg)
                messagebox.showinfo("Calibration", msg)

        except FileNotFoundError:
            self.logger.info("No saved transformation was found. A new coordinate transformation needs to be done.")
            self.make_transformation()

    def _load_settings(self):
        """
        Load piezo stage settings from pickle file.
        :return: settings
        """
        # load stage settings
        piezo_warning = False
        settings = {}
        try:
            with open(self.savefilename_settings, 'rb') as settings_file:
                settings = pickle.load(settings_file)
                if type(settings) is not dict:
                    settings = {}
                    raise TypeError('Settings loaded from piezo stage settings file are not a dict')
                self.logger.debug("Settings loaded from piezo stage settings file are not a dict")
        except (FileNotFoundError, TypeError):
            self.logger.debug("No settings file was found. Using default values.")
        return settings

    def _apply_settings(self, settings):
        """
        Applies settings dict to the piezo stages. Raises and manages relevant errors in order to ensure safe operation
        :param settings: dict as returned from _load_settings.
        """
        piezo_warning = False
        try:
            # make sure that the loaded settings are in the "new format", i.e. um/s for speeds
            # the flag xy_in_mus indicates whether we are in the "new format" (True) or not.
            if 'xyz_speed_unit' in settings.keys() and 'um/s' in settings['xyz_speed_unit']:
                xyz_speed_conversion_fac = 1  # [um] = [um]
            else:
                # if unit is not saved, save files are in "old format", i.e. nm/s
                xyz_speed_conversion_fac = 1e-3  # [um] = [nm] * 1e-3
            if 'xy_speed' in settings.keys():
                # convert xy speed to um/s if necessary
                self.set_speed_of_stages_xy(settings['xy_speed'] * xyz_speed_conversion_fac)
            else:
                self.logger.debug("XY Speed not found in piezo settings file")
            if 'z_speed' in settings.keys():
                # convert z_speed to um/s if necessary
                self.set_speed_of_stages_z(settings['z_speed'] * xyz_speed_conversion_fac)
            else:
                self.logger.debug("Z Speed not found in piezo settings file")
            if 'z_lift' in settings.keys():
                self.set_z_lift(settings['z_lift'])
            else:
                self.logger.debug("Z lift distance not found in piezo settings file")
            if 'left_z_direction' in settings.keys():
                self.left_stage.z_axis_direction = settings['left_z_direction']
            else:
                self.logger.warning("Left z axis orientation not found in piezo settings file")
                piezo_warning = True

            if self.num_stages == 2:
                if 'right_z_direction' in settings.keys():
                    self.right_stage.z_axis_direction = settings['right_z_direction']
                else:
                    self.logger.warning("Right z axis orientation not found in piezo settings file")
                    piezo_warning = True
        except AttributeError:
            piezo_warning = True
            self.logger.debug("Loaded Piezo settings not dicts, but other data type. Use default values.")
        if piezo_warning:
            piezo_warning_text = "Please go to stage configuration window and define direction of stages properly." \
                                 + "\nA fiber movement in the wrong direction can destroy the fiber." \
                                 + "\n\nAsk for help if you are not entirely sure how to configure the axis direction."
            messagebox.showwarning("Direction of left piezo stage not defined",
                                   piezo_warning_text)

    #
    # calibration
    #

    def find_reference_mark_all(self):
        """
        Moves the stages to a known physical position, by searching for the reference mark.
        DANGEROUS! NEEDS ENOUGH FREE ROOM FOR ALL STAGES TO MOVE!
        """
        self._check_stage_status()
        if self.num_stages == 1:
            self.left_stage.find_reference_mark()
        else:
            self.left_stage.find_reference_mark()
            self.right_stage.find_reference_mark()

    def make_transformation(self):
        """Perform a coordinate transformation.

        Raises
        ------
        Exception
            If no stages are initialised.
        RuntimeError
            If aborted by user.
        """
        self._check_stage_status()
        self.trafo_enabled = False
        # both stages have different coordinate systems,
        # so we need two transformations
        self._transformer_right = Transformation2D(self)
        self._transformer_left = Transformation2D(self)

        if self.num_stages == 1:
            msg = 'Please select a device above and couple to that device using the stage. ' + \
                  'Move the stage to the device input coordinates.' + \
                  'Only then click on continue.'
        else:
            msg = 'Please select a device above and couple to that device using both stages: ' + \
                  'Move the left stage to device input coordinate and the right stage to device output coordinate. ' + \
                  'Only then click on continue.'

        # order the user to move the stages to the first device
        new_window = Toplevel(self._experiment_manager.root)
        new_window.attributes('-topmost', 'true')
        d = MoveDeviceWindow(new_window, self._experiment_manager, msg)
        self._experiment_manager.root.wait_window(new_window)

        device = d.selection
        first_device_id = device._id
        if device is None:
            raise RuntimeError('Aborted by user')

        # query position of stage
        pos_1_stage_left = self.left_stage.get_current_position()
        if self.num_stages == 2:
            pos_1_stage_right = self.right_stage.get_current_position()

        # position of first device
        pos_1_chip_in = device._in_position
        pos_1_chip_out = device._out_position

        # order the user to move the stages to the second device
        while True:
            new_window = Toplevel(self._experiment_manager.root)
            new_window.attributes('-topmost', 'true')
            d = MoveDeviceWindow(new_window, self._experiment_manager, msg)
            self._experiment_manager.root.wait_window(new_window)

            device = d.selection
            if device is None:
                raise RuntimeError('Aborted by user')

            if device._id == first_device_id:
                messagebox.showerror('Coordinate transformation error!',
                                     'You selected the same device as first and second calibration device. ' +
                                     'You must select two different devices for calibration!')
            else:
                break

        # query position of stage
        pos_2_stage_left = self.left_stage.get_current_position()
        if self.num_stages == 2:
            pos_2_stage_right = self.right_stage.get_current_position()

        # position of second device
        pos_2_chip_in = device._in_position
        pos_2_chip_out = device._out_position

        self.logger.debug(
            'Transformation about to begin left with: ' +
            'pos_1_stage_left:%s pos_1_chip_in:%s pos_2_stage_left:%s pos_2_chip_in:%s',
            pos_1_stage_left, pos_1_chip_in, pos_2_stage_left, pos_2_chip_in)

        self._transformer_left.trafo_algorithm(pos_1_stage_left, pos_1_chip_in,
                                               pos_2_stage_left, pos_2_chip_in)

        if self.num_stages == 2:
            self.logger.debug(
                'Transformation about to begin right with: ' +
                'pos_1_stage_right:%s pos_1_chip_out:%s pos_2_stage_right:%s pos_2_chip_out:%s',
                pos_1_stage_right, pos_1_chip_out, pos_2_stage_right, pos_2_chip_out)

            self._transformer_right.trafo_algorithm(pos_1_stage_right, pos_1_chip_out,
                                                    pos_2_stage_right, pos_2_chip_out)
        else:
            self.logger.debug("Skipping right transformation, mover configured for single stage operation.")

        # save the transformation
        transform = [self._transformer_left._matrix,
                     self._transformer_left._chip_offset,
                     self._transformer_left._stage_offset,
                     self._transformer_right._matrix,
                     self._transformer_right._chip_offset,
                     self._transformer_right._stage_offset,
                     self._chip._name,
                     self.num_stages]
        with open(self.savefilename_transformation, 'wb') as transformer_file:
            pickle.dump(transform, transformer_file)

        # all good
        self.trafo_enabled = True
        self._experiment_manager.main_window.model.status_transformation_enabled.set(self.trafo_enabled)

        # inform user
        msg = "Calibration successful. Automatic movement enabled."
        if self.num_stages == 2:
            msg += " All non relative movements will be run with stage collision avoidance algorithm."
        self.logger.info(msg)
        messagebox.showinfo("Calibration", msg)
