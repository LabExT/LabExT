#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
from os.path import dirname, join
import time
from typing import Type
import datetime

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from LabExT.Measurements.MeasAPI import *
from LabExT.Movement.MotorProfiles import trapezoidal_velocity_profile_by_integration
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.config import CoordinateSystem
from LabExT.Movement.Transformations import StageCoordinate
from LabExT.Utils import get_configuration_file_path
from LabExT.Utils import make_filename_compliant
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.ViewModel.Utilities.ObservableList import ObservableList
from LabExT.Experiments.AutosaveDict import AutosaveDict


class EdgeSearcher(Measurement):
    """
    ## Search for Peak

    Executes a Search for Peak for a standard IL measurement with one or two stages (left and right) and only x and y coordinates.
    This Measurement is NOT a 'normal' measurement and should NOT be used in an experiment routine.

    #### Details
    An optical signal generated at an optical source passes through the DUT and into a power meter. The optical fibers carrying said signal are mounted onto
    remotely controllable stages (in our case SmarAct Piezo Stages). In this routine, these stages mechanically sweep over a given range, the insertion loss is measured in regular intervals.
    The sweep is conducted in x and y direction separately.

    The Search for Peak measurement routine relies on the assumption that around the transmission maximum of a grating coupler, the transmission forms a 2D gaussian (w.r.t x and y position).
    Thus after having collected data for each axis, a 1D gaussian is fitted to the data and the stages are moved to the maximum of the gaussian.

    There are two types of Search for Peak available:
    - **stepped SfP**: suitable for all types of fibers/fiber arrays and all power meter models. The given range is mechanically stepped over, the measurement
    stops at each point given by the `search step size` parameter, waits the time given by the `search fiber stabilization time` parameter to let fiber vibrations
    dissipate and then records a data point. This type is universally applicable but also very slow.
    - **fast SfP**: suitable only for fiber arrays and the Keysight N7744a power meter models. The given range is mechanically continuously sweeped over, the power meter
    collects regular data points (amount is given by `Number of points`). Those data points are then related to a physical position taking into account the acceleration
    of the stages. This type of Search for Peak is significantly faster than the stepped SfP and provides the user with a massively increased amount of data.
    At the moment, this type only works with the Keysight N7744a power meter. Usage with single mode fibers is possible, but untested.


    #### Example Setup

    ```
    Laser -in-> DUT -out-> Power Meter
    ```
    The `-xx->` arrows denote where the remotely controllable stages are placed. In the case of a fiber array, `-in->` and `-out->` denote the same stage, as both input and output of the DUT are
    included in the fiber array. In the case of two single fibers, `-in->` and `-out->` denote two separate stages.

    ### Parameters

    #### Laser Parameters
    - **Laser wavelength**: wavelength of the laser in [nm].
    - **Laser power**: power of the laser in [dBm].

    #### Power Meter Parameters
    - **Power Meter range**: range of the power in [dBm].

    #### Stage Parameters
    - **Search radius**: Radius arond the current position the algorithm sweeps over in [um].
    - **SfP type**: Type of Search for Peak to use. Options are `stepped SfP` and `swept SfP`, see above for more detail.
    - **(stepped SfP only) Search step size**: Distance between every data point in [um].
    - **(stepped SfP only) Search fiber stabilization time**: Idle time between the stage having reached the target position and the measurement start. Meant to allow fiber oscillations to dissipate.
    - **(swept SfP only) Search time**: Time the mechanical movement across the set measurement range should take in [s].
    - **(swept SfP only) Number of points**: Number of points to collect at the power meter for each separate sweep.

    All parameters labelled `stepped SfP only` are ignored when choosing the swept SfP, all parameters labelled `swept SfP only` are ignored when choosing the stepped SfP.
    """

    DIMENSION_NAMES_TWO_STAGES = ['Left X', 'Left Y', 'Left Z', 'Right X', 'Right Y', 'Right Z']
    DIMENSION_NAMES_SINGLE_STAGE = ['X', 'Y', 'Z']

    def __init__(
        self,
        *args,
        mover: Type[MoverNew] = None,
        parent=None,
        **kwargs
    ) -> None:
        """Constructor

        Parameters
        ----------
        mover : Mover
            Reference to the Mover class for Piezo stages.
        """
        super().__init__(*args, **kwargs)  # calling parent constructor

        self._parent = parent
        self.name = "EdgeSearcher"
        self.settings_filename = "EdgeSearcher_settings.json"
        self.mover = mover

        self.logger = logging.getLogger()

        # gather all plots for the plotting GUIs
        self.plots_left = ObservableList()
        self.plots_right = ObservableList()

        # chosen instruments for IL measurement
        self.instr_laser = None
        self.instr_powermeter = None
        self.initialized = False

        self.logger.info(
            'Initialized Search for Peak with method: ' + str(self.name))

    @property
    def settings_path_full(self):
        return get_configuration_file_path(self.settings_filename)

    def set_experiment(self, experiment):
        """Helper function to keep all initializations in the right order
        This line cannot be included in __init__
        """
        self._experiment = experiment

    @staticmethod
    def get_default_parameter():
        return {
            'Laser wavelength': MeasParamFloat(value=1300.0, unit='nm'),
            'Laser power': MeasParamFloat(value=0.0, unit='dBm'),
            'output path': MeasParamString(value=""),
            'file str': MeasParamString(value=""),
            'Motor X increment': MeasParamFloat(value=0.0, unit="um"),
            'Motor Y increment': MeasParamFloat(value=0.0, unit="um"),
            'Motor Z increment': MeasParamFloat(value=0.0, unit="um"),
            'Max motor increment': MeasParamFloat(value=50.0, unit="um"),
        }

    @staticmethod
    def get_wanted_instrument():
        return ['Laser', 'Power Meter', 'Camera']
    
    def prepare_instruments(self):
         # double check if mover is actually enabled
        if self.mover.left_calibration is None and self.mover.right_calibration is None:
            raise RuntimeError(
                "The Search for Peak requires at least one left or right stage configured.")

        if self.mover.left_calibration and self.mover.right_calibration:
            self._dimension_names = self.DIMENSION_NAMES_TWO_STAGES
        else:
            self._dimension_names = self.DIMENSION_NAMES_SINGLE_STAGE

        # load laser and powermeter
        self.instr_powermeter = self.get_instrument('Power Meter')
        self.instr_laser = self.get_instrument('Laser')
        self.camera = self.get_instrument('Camera')

        # double check if instruments are initialized, otherwise throw error
        if self.instr_powermeter is None:
            raise RuntimeError('Search for Peak Power Meter not yet defined!')
        if self.instr_laser is None:
            raise RuntimeError('Search for Peak Laser not yet defined!')
        if self.camera is None:
            raise RuntimeError('Search for Peak Laser not yet defined!')

        # initialize plotting
        self.plots_left.clear()
        self.plots_right.clear()

        # open connection to instruments
        self.instr_laser.open()
        self.instr_powermeter.open()
        self.camera.open()

        self.logger.debug('Executing Search for Peak with the following parameters: {:s}'.format(
            "\n".join([str(name) + " = " + str(param.value) + " " + str(param.unit) for name, param in
                       self.parameters.items()])
        ))

        # setup results dictionary and save all parameters
        now = datetime.datetime.now()
        ts = str('{date:%Y-%m-%d_%H%M%S}'.format(date=now))
        save_file_name = f"{self.parameters.get('file str').value}_{ts}"
        save_file_name = make_filename_compliant(save_file_name)
        self.save_file_path = f"{self.parameters.get('output path').value}//{save_file_name}"

        os.mkdir(self.save_file_path)

        self.results =  AutosaveDict(freq=50, file_path=f"{self.save_file_path}\\results.json")
        self.results['name'] = self.name
        self.results['parameter'] = {}
        self.results['start location'] = None
        self.results['measured location'] = []
        self.results['measured power'] = []
        self.results['measurement time'] = []
        self.captured_img = []

        for param_name, cfg_param in self.parameters.items():
            self.results['parameter'][param_name] = str(cfg_param.value) + str(cfg_param.unit)

        # send user specified parameters to instruments
        self.instr_laser.wavelength = self.parameters.get('Laser wavelength').value
        self.instr_laser.power = self.parameters.get('Laser power').value
        self.instr_powermeter.unit = 'dBm'
        self.instr_powermeter.wavelength = self.parameters.get('Laser wavelength').value

        # stop all previous logging
        self.instr_powermeter.logging_stop()

         # turn laser on
        self.instr_laser.enable = True

        self.estimated_through_power = -99
        self.current_coordinates = []

        return

    def capture_data(self):
        """Main Search For Peak routine
        Uses a 2D gaussian fit for all four dimensions.

        Returns
        -------
        dict
            A dict containing the parameters used for the SFP, the estimated through power,
            and gaussian fitting information.
        """

        # switch on laser
        self.instr_laser.wavelength = self.parameters.get('Laser wavelength').value
        self.instr_laser.power = self.parameters.get('Laser power').value

        with self.instr_laser:
            with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
                # read parameters for SFP
                move__motor_x = self.parameters.get('Motor X increment').value
                move__motor_y = self.parameters.get('Motor Y increment').value
                move__motor_z = self.parameters.get('Motor Z increment').value
                max_motor_increment = self.parameters.get('Max motor increment').value

                for axis_name, increment in (('X', move__motor_x), ('Y', move__motor_y), ('Z', move__motor_z)):
                    if not np.isfinite(increment):
                        raise ValueError(
                            f"Motor {axis_name} increment is {increment!r}, not a finite number. Refusing to move stages."
                        )
                    if abs(increment) > max_motor_increment:
                        raise ValueError(
                            f"Motor {axis_name} increment of {increment}um exceeds the configured "
                            f"'Max motor increment' safety limit of {max_motor_increment}um. Refusing to move stages."
                        )

                # find the current positions of the stages as starting point for
                # SFP
                _left_start_coordinates = []
                _right_start_coordinates = []
                if self.mover.left_calibration:
                    _left_start_coordinates = self.mover.left_calibration.get_position().to_list()
                if self.mover.right_calibration:
                    _right_start_coordinates = self.mover.right_calibration.get_position().to_list()
                start_coordinates = _left_start_coordinates + _right_start_coordinates

                self.logger.debug(f"Start Position: {start_coordinates}")

                # get start statistics
                self.results['start location'] = start_coordinates.copy()
                self.results['start through power'] = self.instr_powermeter.power

                # move motors
                self._move_stages_relative([move__motor_x, move__motor_y, move__motor_z])
                self.logger.info(f"Move by: {[move__motor_x, move__motor_y, move__motor_z]}.")

                # Save location (post-move, i.e. the actual current position)
                self.current_coordinates = []
                if self.mover.left_calibration:
                    left_position = self.mover.left_calibration.get_position().to_list()
                    self.results['measured location'].append(left_position)
                    self.current_coordinates += left_position
                if self.mover.right_calibration:
                    right_position = self.mover.right_calibration.get_position().to_list()
                    self.results['measured location'].append(right_position)
                    self.current_coordinates += right_position

                # Save power
                self.results['measured power'].append(self.instr_powermeter.fetch_power())
                self.estimated_through_power = max(self.results['measured power'])

                # Save picture
                # self.results['captured image'].append(self.camera.snap_photo())
                self.captured_img.append(np.uint8(self.camera.snap_photo()))
                # plt.imshow(self.captured_img[-1])
                # plt.axis('off')
                # plt.savefig(f"{self.save_file_path}\\img_{np.size(self.results['measured power']):03}.png")
                # plt.show()
                now = datetime.datetime.now()
                ts = str('{date:%Y-%m-%d_%H%M%S}'.format(date=now))
                self.results['measurement time'].append(ts)
                self.results.save()
                
                plt.imsave(f"{self.save_file_path}\\img_{np.size(self.results['measured power']):03}.png", self.captured_img[-1], dpi=300)
                np.savez(f"{self.save_file_path}\\imgs.npz", images = self.captured_img)

                # Plot Power
                # color_strings = ['C' + str(i) for i in range(10)]
                meas_plot_left_x = PlotData(ObservableList(), ObservableList(), color = 'blue', marker='o', label="x")
                meas_plot_left_z = PlotData(ObservableList(), ObservableList(), color = 'red', marker='o', label="z")
                self.plots_left.append(meas_plot_left_x)
                self.plots_left.append(meas_plot_left_z)

                if len(self.results['measured power']) == 1:
                    meas_plot_left_x.x = [0.0]
                    meas_plot_left_x.y = self.results['measured power']
                    meas_plot_left_z.x = [0.0]
                    meas_plot_left_z.y = self.results['measured power']
                else:
                    meas_plot_left_x.x = [0.0] + [coord[0] - self.results['measured location'][0][0] for coord in self.results['measured location'][1:]]
                    meas_plot_left_x.y = self.results['measured power']
                    meas_plot_left_z.x = [0.0] + [coord[2] - self.results['measured location'][0][2] for coord in self.results['measured location'][1:]]
                    meas_plot_left_z.y = self.results['measured power']
                # print()
                # print('HELP')
                # print(type(meas_plot_left.plot_data))

                meas_plot_right = PlotData(x=None, y=None, plot_type='image', image = ObservableList())
                self.plots_right.append(meas_plot_right)
                # meas_plot_right.x = [coord[2] for coord in self.results['measured location']]
                # meas_plot_right.y = self.results['measured power']
                meas_plot_right.image = self.captured_img[-1]
                # print(type(meas_plot_right.image))
                # plt.imshow(self.captured_img[-1])
                # plt.show()
                # print(type(meas_plot_right.plot_data))

                
        return self.results
    
    def close_instruments(self):
        # turn laser off
        self.instr_laser.enable = False

        # close instruments
        self.instr_laser.close()
        self.instr_powermeter.close()
        self.camera.close()

        # save final result to log
        loc_str = " x ".join(["{:.3f}um".format(p)
                             for p in self.current_coordinates])
        self.logger.info(
            f"Search for peak finished: maximum estimated output power of {self.estimated_through_power:.1f}dBm"
            f" at {loc_str:s}.")

        # save end result and return
        self.results['optimized location'] = self.current_coordinates.copy()
        self.results['optimized through power'] = self.estimated_through_power

        return self.results
    
    def _move_stages_relative(self, coordinates: list):
        # self.mover.move_relative(coordinates)
        # return
        with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
            if self.mover.left_calibration and self.mover.right_calibration:
                self.mover.left_calibration.move_relative(
                    StageCoordinate.from_list(coordinates))
                self.mover.right_calibration.move_relative(
                    StageCoordinate.from_list(coordinates))
            elif self.mover.left_calibration:
                self.mover.left_calibration.move_relative(
                    StageCoordinate.from_list(coordinates))
            elif self.mover.right_calibration:
                self.mover.right_calibration.move_relative(
                    StageCoordinate.from_list(coordinates))
            else:
                raise RuntimeError()

    def update_params_from_savefile(self):
        if not os.path.isfile(self.settings_path_full):
            self.logger.info(
                "SFP Parameter save file at {:s} not found. Using default parameters.".format(
                    self.settings_path_full))
            return
        with open(self.settings_path_full, 'r') as json_file:
            data = json.loads(json_file.read())
        for parameter_name in data:
            self.parameters[parameter_name].value = data[parameter_name]
        self.logger.info(
            "SearchForPeak parameters loaded from file: {:s}.".format(
                self.settings_path_full))

    def algorithm(self, device, data, instruments, parameters):
        raise NotImplementedError()
