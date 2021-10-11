#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
import time

import numpy as np
from scipy.optimize import curve_fit

from LabExT.Measurements.MeasAPI import *
from LabExT.Movement.MotorProfiles import trapezoidal_velocity_profile_by_integration
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.ViewModel.Utilities.ObservableList import ObservableList


class PeakSearcher(Measurement):
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

    def __init__(self, *args, mover=None, parent=None, **kwargs):
        """Constructor

        Parameters
        ----------
        mover : Mover
            Reference to the Mover class for Piezo stages.
        """
        super().__init__(*args, **kwargs)  # calling parent constructor

        self._parent = parent
        self.name = "SearchForPeak-2DGaussianFit"
        self.settings_filename = "PeakSearcher_settings.json"
        self.mover = mover

        self.logger = logging.getLogger()

        # gather all plots for the plotting GUIs
        self.plots_left = ObservableList()
        self.plots_right = ObservableList()

        # chosen instruments for IL measurement
        self.instr_laser = None
        self.instr_powermeter = None
        self.initialized = False

        self.logger.info('Initialized Search for Peak with method: ' + str(self.name))

    @property
    def settings_path_full(self):
        return get_configuration_file_path(self.settings_filename)

    def set_experiment(self, experiment):
        """Helper function to keep all initializations in the right order
        This line cannot be included in __init__
        """
        self._experiment = experiment

    @staticmethod
    def _gaussian(xdata, a, mu, sigma, offset):
        return a * np.exp(-(xdata - mu) ** 2 / (2 * sigma ** 2)) + offset

    @staticmethod
    def _gaussian_param_initial_guess(x_data, y_data):
        """
        Crudely estimates initial parameters for a gaussian fitting on 2-dimensional data.
        """
        a_init = y_data.max() - y_data.min()
        # mu_init = np.sum(x_data * y_data) / np.sum(y_data)
        mu_init = x_data[np.argmax(y_data)]
        # sigma_init = np.sqrt(np.sum(y_data * (x_data - mu_init) ** 2 / np.sum(y_data)))
        sigma_init = x_data.max() - x_data.min()  # assume that sigma spans the sampled interval
        offset_init = y_data.min()

        return [a_init, mu_init, sigma_init, offset_init]

    def fit_gaussian(self, x_data, y_data):
        """Fits a gaussian function of four parameters to the given x and y data.

        Parameters
        ----------
        x_data : np.ndarray
            the set of independent data points
        y_data : np.ndarray
            the set of dependent data points

        Returns
        -------
        popt: 4-tuple
            a (amplitude of gauss peak), mu (mean of gauss), sigma (std dev of gauss), offset (y-axis offset baseline)
        perr_std_dev: np.ndarray
            a 4-vector giving the estimated std deviations of the parameters, the lower the better

        Raises
        ------
        RuntimeError: when the fitting fails to converge.
        """

        # make sure the input data is in numpy arrays
        x_data = np.array(x_data)
        y_data = np.array(y_data)

        # we cannot fit on empty vectors
        assert len(x_data) > 0
        assert len(y_data) > 0

        pinit = PeakSearcher._gaussian_param_initial_guess(x_data, y_data)

        # define bounds for the fitting parameters
        a_bounds = (0, np.inf)  # allow only positive gaussians, i.e. hills, not valleys
        mu_bounds = (-np.inf, np.inf)
        sigma_bounds = (0, np.inf)
        offset_bounds = (-np.inf, np.inf)

        lower_bounds = (a_bounds[0], mu_bounds[0], sigma_bounds[0], offset_bounds[0])
        upper_bounds = (a_bounds[1], mu_bounds[1], sigma_bounds[1], offset_bounds[1])

        # fit a gaussian to the data
        popt, cov = curve_fit(PeakSearcher._gaussian,
                              x_data,
                              y_data,
                              p0=pinit,
                              bounds=(lower_bounds, upper_bounds),
                              ftol=1e-8,
                              maxfev=10000)

        self.logger.debug('Gaussian Fit:')
        self.logger.debug('a -- mu -- sigma -- offset')
        self.logger.debug(str(popt))

        perr_std_dev = np.sqrt(np.diag(cov))

        return popt, perr_std_dev

    @staticmethod
    def get_default_parameter():
        return {
            'Laser wavelength': MeasParamInt(value=1550, unit='nm'),
            'Laser power': MeasParamFloat(value=0.0, unit='dBm'),
            'Power Meter range': MeasParamFloat(value=0.0, unit='dBm'),
            'Search radius': MeasParamFloat(value=5.0, unit='um'),
            'SfP type': MeasParamList(options=['stepped SfP', 'swept SfP (FA & N7744a PM models only)']),
            '(stepped SfP only) Search step size': MeasParamFloat(value=0.5, unit='um'),
            '(stepped SfP only) Search fiber stabilization time': MeasParamInt(value=200, unit='ms'),
            '(swept SfP only) Search time': MeasParamFloat(value=2.0, unit='s'),
            '(swept SfP only) Number of points': MeasParamInt(value=500)
        }

    @staticmethod
    def get_wanted_instrument():
        return ['Laser', 'Power Meter']

    def search_for_peak(self):
        """Main Search For Peak routine
        Uses a 2D gaussian fit for all four dimensions.

        Returns
        -------
        dict
            A dict containing the parameters used for the SFP, the estimated through power,
            and gaussian fitting information.
        """
        # double check if mover is actually enabled
        if not self.mover.mover_enabled:
            raise RuntimeError('Mover class is disabled! Cannot do automatic search for peak.')

        # load laser and powermeter
        self.instr_powermeter = self.get_instrument('Power Meter')
        self.instr_laser = self.get_instrument('Laser')

        # double check if instruments are initialized, otherwise throw error
        if self.instr_powermeter is None:
            raise RuntimeError('Search for Peak Power Meter not yet defined!')
        if self.instr_laser is None:
            raise RuntimeError('Search for Peak Laser not yet defined!')

        # initialize plotting
        self.plots_left.clear()
        self.plots_right.clear()

        # open connection to instruments
        self.instr_laser.open()
        self.instr_powermeter.open()

        self.logger.debug('Executing Search for Peak with the following parameters: {:s}'.format(
            "\n".join([str(name) + " = " + str(param.value) + " " + str(param.unit) for name, param in
                       self.parameters.items()])
        ))

        # setup results dictionary and save all parameters
        results = {
            'name': self.name,
            'parameter': {},
            'start location': None,
            'start through power': None,
            'optimized location': None,
            'optimized through power': None,
            'fitting information': {}
        }
        for param_name, cfg_param in self.parameters.items():
            results['parameter'][param_name] = str(cfg_param.value) + str(cfg_param.unit)

        # send user specified parameters to instruments
        self.instr_laser.wavelength = self.parameters['Laser wavelength'].value
        self.instr_laser.power = self.parameters['Laser power'].value
        self.instr_powermeter.unit = 'dBm'
        self.instr_powermeter.wavelength = self.parameters['Laser wavelength'].value
        self.instr_powermeter.range = self.parameters['Power Meter range'].value

        # get stage speed for later reference
        v0 = self.mover.get_speed_of_stages_xy()
        acc0 = self.mover.get_acceleration_of_stages_xy()

        # stop all previous logging
        self.instr_powermeter.logging_stop()

        # switch on laser
        with self.instr_laser:

            # read parameters for SFP
            sfp_type = self.parameters.get('SfP type').value
            radius_us = self.parameters.get('Search radius').value

            # parameters specifically for stepped sfp
            stepsize_us = self.parameters['(stepped SfP only) Search step size'].value
            pause_time_ms = self.parameters['(stepped SfP only) Search fiber stabilization time'].value

            # parameters specifically for swept SfP
            t_sweep = self.parameters.get('(swept SfP only) Search time').value
            no_points = int(self.parameters.get('(swept SfP only) Number of points').value)

            # define parameters
            # the sweep velocity is the distance passed (twice the search radius) divided by the sweep time
            v_sweep_ums = 2 * radius_us / t_sweep
            avg_time = t_sweep / float(no_points)
            unit = 'dBm'
            # find the current positions of the stages as starting point for SFP
            start_coordinates = self.mover.get_absolute_stage_coords()
            current_coordinates = start_coordinates.copy()
            estimated_through_power = -99.0

            # get start statistics
            results['start location'] = start_coordinates.copy()
            results['start through power'] = self.instr_powermeter.power

            # do sweep for every dimension
            color_strings = ['C' + str(i) for i in range(10)]  # color cycle strings for matplotlib
            for dimidx, p_start in enumerate(start_coordinates):

                dimension_name = self.mover.dimension_names[dimidx]

                # create new plotting dataset for measurement
                meas_plot = PlotData(ObservableList(), ObservableList(),
                                     'scatter', color=color_strings[dimidx])
                fit_plot = PlotData(ObservableList(), ObservableList(),
                                    color=color_strings[dimidx], label=dimension_name)
                opt_pos_plot = PlotData(ObservableList(), ObservableList(),
                                        marker='x', markersize=10, color=color_strings[dimidx])
                if dimidx < len(start_coordinates) / 2:
                    self.plots_left.append(meas_plot)
                    self.plots_left.append(fit_plot)
                    self.plots_left.append(opt_pos_plot)
                else:
                    self.plots_right.append(meas_plot)
                    self.plots_right.append(fit_plot)
                    self.plots_right.append(opt_pos_plot)

                # differentiate between the two types of SfP
                if sfp_type == 'swept SfP (FA & N7744a PM models only)':
                    allowed_pm_classes = ['PowerMeterN7744A', 'PowerMeterSimulator']
                    # complain if user selects a Power Meter that is not compatible with new Search for Peak
                    if self.instr_powermeter.__class__.__name__ not in allowed_pm_classes :
                        raise RuntimeError(
                            'swept SfP is only compatible with Keysight N7744A PM models, not {}'.format(
                            self.instr_powermeter.__class__.__name__)
                        )
                    # move stage to initial position and setup
                    current_coordinates[dimidx] = p_start - radius_us
                    self.mover.move_absolute(*current_coordinates, safe_movement=False, lift_z_dir=False)
                    # setup power meter logging feature
                    self.instr_powermeter.autogain = False  # autogain attribute exists only for N7744A, no effect on other
                    self.instr_powermeter.range = self.parameters['Power Meter range'].value
                    self.instr_powermeter.unit = unit
                    self.instr_powermeter.averagetime = avg_time
                    self.instr_powermeter.logging_setup(n_measurement_points=no_points,
                                                        triggered=True,
                                                        trigger_each_meas_separately=False)
                    self.instr_powermeter.logging_start()

                    # take a tiny break
                    time.sleep(0.1)

                    current_coordinates[dimidx] = p_start + radius_us
                    # empirically determined acceleration
                    acc_umps2 = 50
                    self.mover.set_speed_of_stages_xy(v_sweep_ums)
                    self.mover.set_acceleration_of_stages_xy(acc_umps2)
                    # start logging at powermeter
                    self.instr_powermeter.trigger()
                    # mover_time_lower = time.time()
                    self.mover.move_absolute(*current_coordinates, safe_movement=False, lift_z_dir=False)
                    # mover_time_upper = time.time()

                    while self.instr_powermeter.logging_busy():
                        time.sleep(0.1)
                    pm_data = self.instr_powermeter.logging_get_data()

                    # pay attention to unit here
                    IL_meas = pm_data

                    # calculate the estimated movement profile, given constant acceleration of the stages
                    _, d_range, _, _ = trapezoidal_velocity_profile_by_integration(start_position_m=-radius_us,
                                                                                   stop_position_m=radius_us,
                                                                                   max_speed_mps=v_sweep_ums,
                                                                                   const_acceleration_mps2=acc_umps2,
                                                                                   n_output_points=len(IL_meas))

                    # plot it
                    meas_plot.x = d_range
                    meas_plot.y = IL_meas

                elif sfp_type == 'stepped SfP':
                    #  create range of N measurement points from x-Delta to x+Delta
                    d_range = np.arange(-radius_us, radius_us + stepsize_us, stepsize_us)

                    # go through all measurement points for this coordinate and record IL
                    IL_meas = np.empty(len(d_range))

                    for measidx, d_current in enumerate(d_range):
                        # move stages to currently probed coordinate
                        current_coordinates[dimidx] = d_current + p_start
                        self.mover.move_absolute(*current_coordinates, safe_movement=False, lift_z_dir=False)

                        # take a break to let fiber-vibration die off
                        time.sleep(pause_time_ms / 1000)

                        # take IL measurement
                        loss = self.instr_powermeter.power

                        # save data
                        meas_plot.x.extend([d_current])  # do not trigger plot update just yet
                        meas_plot.y.append(loss)

                        IL_meas[measidx] = loss

                else:
                    raise ValueError('invalid SfP type given! Options are `stepped SfP` or `swept SfP`.')

                self.logger.debug('SFP results:')
                self.logger.debug('coordinates:' + str(d_range))
                self.logger.debug('IL: ' + str(IL_meas))

                # default assignments before SFP decision
                optimized_target = 0
                popt = None
                perr_std_dev = None
                fit_msg = None
                sfp_msg = None

                # 1st decision: did the power meter always return useful data?
                if ~np.all(np.isfinite(IL_meas)):
                    sfp_msg = f'SFP failed on dimension {dimension_name} because not all measured IL values are finite.' + \
                              ' Change of power meter range required. Moving back to start point.'
                    self.logger.warning(sfp_msg)
                else:
                    # 2nd decision: fit the gauss and see if it works
                    try:
                        popt, perr_std_dev = self.fit_gaussian(d_range, IL_meas)
                        fit_msg = "Gauss fitting successful."
                    except RuntimeError:  # thrown from scipy optimizer if algorithm did not converge
                        # if convergence fails, we estimate the parameters crudly, i.e. just get the point with
                        # maximum transmission
                        popt = PeakSearcher._gaussian_param_initial_guess(d_range, IL_meas)
                        fit_msg = "Gauss fitting did not converge. Using point with maximum transmission."
                        self.logger.warning(fit_msg)

                    # 3rd decision: judge feasibility of gaussian fit
                    a_best, d_best = popt[0:2]
                    if abs(d_best) > 1.5 * radius_us:
                        sfp_msg = 'Movement would be more than 1.5x search radius. Moving back to start point.'
                        self.logger.warning(sfp_msg)
                    else:
                        optimized_target = d_best
                        sfp_msg = f'Moving to optimized fiber location.'

                    # plot the gaussian, if gaussian was successfully fitted
                    if perr_std_dev is not None:
                        # interpolate between the fitted values to get a nice smooth line
                        d_range_highres = np.linspace(d_range.min(), d_range.max(), num=len(meas_plot.x) * 5)
                        IL_fit_fctn = PeakSearcher._gaussian(d_range_highres, *popt)
                        # plot fit data
                        fit_plot.x.extend(d_range_highres)
                        fit_plot.y.extend(IL_fit_fctn[0:-1])
                        fit_plot.y.append(IL_fit_fctn[-1])  # trigger plot update

                    # mark the point where we move to in any case
                    estimated_through_power = self._gaussian(optimized_target, *popt)
                    opt_pos_plot.x.extend([optimized_target])  # do not trigger plot update just yet
                    opt_pos_plot.y.append(estimated_through_power)

                # inform user and store the fitting information
                self.logger.debug(f"Search for peak for dimension {dimension_name} finished. "
                                  f"Fitter message: {fit_msg} -- SFP decision: {sfp_msg} "
                                  f"Moving to location: {optimized_target:.3f}um with estimated through power"
                                  f" of {estimated_through_power:.1f}dBm.")

                results['fitting information'][dimension_name] = {
                    'optimized parameters': list(popt) if popt is not None else None,
                    'parameter estimation error std dev': list(perr_std_dev) if perr_std_dev is not None else None,
                    'fitter message': str(fit_msg),
                    'sfp decision': str(sfp_msg)
                }

                # reset speed and acceleration to original
                self.mover.set_speed_of_stages_xy(v0)
                self.mover.set_acceleration_of_stages_xy(acc0)

                # final move of fiber in this dimensions final decision
                current_coordinates[dimidx] = optimized_target + p_start
                self.mover.move_absolute(*current_coordinates)

        # close instruments
        self.instr_laser.close()
        self.instr_powermeter.close()

        # save final result to log
        loc_str = " x ".join(["{:.3f}um".format(p) for p in current_coordinates])
        self.logger.info(f"Search for peak finished: maximum estimated output power of {estimated_through_power:.1f}dBm"
                         f" at {loc_str:s}.")

        # save end result and return
        results['optimized location'] = current_coordinates.copy()
        results['optimized through power'] = estimated_through_power

        return results

    def update_params_from_savefile(self):
        if not os.path.isfile(self.settings_path_full):
            self.logger.info("SFP Parameter save file at {:s} not found. Using default parameters.".format(
                self.settings_path_full
            ))
            return
        with open(self.settings_path_full, 'r') as json_file:
            data = json.loads(json_file.read())
        for parameter_name in data:
            self.parameters[parameter_name].value = data[parameter_name]
        self.logger.info("SearchForPeak parameters loaded from file: {:s}.".format(self.settings_path_full))

    def algorithm(self, device, data, instruments, parameters):
        raise NotImplementedError()
