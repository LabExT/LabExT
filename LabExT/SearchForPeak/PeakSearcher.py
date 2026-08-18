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
from typing import Type

import numpy as np
from scipy.optimize import curve_fit

from LabExT.Measurements.MeasAPI import *
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.config import CoordinateSystem
from LabExT.Movement.Transformations import StageCoordinate
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.ViewModel.Utilities.ObservableList import ObservableList

# If the measured dynamic range across a scan is below this, the scan is treated as
# having found no real peak (flat/noise-dominated response), and the stage is left at
# its start position rather than trusting the Gaussian fit's suggested location.
NO_PEAK_FOUND_DYNAMIC_RANGE_DB = 3.0

# A Gaussian fit whose optimum lands beyond this fraction of the search radius is
# treated as potentially clipped - the true peak may lie outside the scanned window,
# so the fitted centre is not trustworthy as an absolute reference. The move itself
# still happens (it is still an improvement); the result is only flagged as unfit for
# use as a chip-to-stage calibration reference point.
NEAR_EDGE_REJECT_FRACTION = 0.9


class PeakSearcher(Measurement):
    """
    ## Search for Peak

    Executes a Search for Peak for a standard IL measurement with one or two stages (left and right) and only x and y coordinates.
    This class does not implement the standard `Measurement.algorithm()` interface (it raises `NotImplementedError`), so it
    cannot be selected as a regular sweep-able measurement in the measurement wizard. It is instead used directly via
    `search_for_peak()` - either manually from the Search-for-Peak window, or automatically as a pre-measurement alignment
    step in `StandardExperiment` when "auto move stages" and "execute search for peak" are both enabled in the main window.

    #### Details
    An optical signal generated at an optical source passes through the DUT and into up to four power meters (the merit
    value at each measured point is the maximum reading across whichever power meters are configured). The optical fibers
    carrying said signal are mounted onto remotely controllable stages (in our case SmarAct Piezo Stages, or Thorlabs
    K-Cube stages). In this routine, these stages mechanically sweep over a given range, the insertion loss is measured in
    regular intervals. The sweep is conducted for each stage axis separately (Left X, Left Y, Right X, Right Y, or just X, Y
    for a single-stage setup).

    The Search for Peak measurement routine relies on the assumption that around the transmission maximum of a grating coupler, the transmission forms a 2D gaussian (w.r.t x and y position).
    Thus after having collected data for each axis, a 1D gaussian is fitted to the data and the stages are moved to the maximum of the gaussian.

    The given range is mechanically stepped over: the measurement stops at each point given by the `search step size`
    parameter, waits the time given by the `search fiber stabilization time` parameter to let fiber vibrations dissipate,
    and then records a data point. This is suitable for all types of fibers/fiber arrays and all power meter models.

    Up to three independently-configured passes ("First/Second/Third Peak Search") can be enabled, each re-running the
    full sweep over every axis using the position left by the previous pass as its new starting point - typically used to
    do a coarse pass with a larger radius/step size followed by one or two finer passes with a smaller radius/step size.

    An optional optical switch can be enabled ("Switch Flag") to route logical ports 1-4 (`M = 1`..`M = 4`) to power
    meters 1-4 before the search starts; it is connected once and is not reconfigured during the search itself.

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

    #### Switch Parameters
    - **Switch Flag**: whether to connect and use the optical switch before searching.
    - **M = 1** / **M = 2** / **M = 3** / **M = 4**: logical switch port routed to Power Meter 1/2/3/4 respectively (only used if `Switch Flag` is enabled).

    #### Stage Parameters (per pass - First/Second/Third Peak Search)
    - **Enable/Disable**: whether this pass runs at all.
    - **Search Radius**: Radius arond the current position the algorithm sweeps over in [um].
    - **Search step size**: Distance between every data point in [um].
    - **Search fiber stabilization time**: Idle time between the stage having reached the target position and the measurement start. Meant to allow fiber oscillations to dissipate.
    - **Power averaging time**: Duration in [s] to repeatedly sample and average each power meter at every scan point, to reduce point-to-point noise. 0 takes a single instantaneous reading (no averaging).

    #### Backlash Test Parameters
    Used by `test_backlash()` (also runnable from the "Test Backlash (X/Y)" button in the Search for Peak window) - a
    diagnostic that moves each stage's X and Y axis by a small amount and reverses direction repeatedly, checking that
    the actual position always lands within tolerance of the commanded target. Z is never moved. Always restores the
    exact starting position, including on error - safe to run on an already-aligned setup.
    - **Amplitude**: size of each test move in [um].
    - **Number of reversals**: number of forward/backward direction-reversal pairs to test per axis.
    - **Tolerance**: maximum acceptable position error (commanded vs. actual) for a pass, in [um].
    """

    DIMENSION_NAMES_TWO_STAGES = ['Left X', 'Left Y', 'Right X', 'Right Y']
    DIMENSION_NAMES_SINGLE_STAGE = ['X', 'Y']
    PASS_NAMES = ['First', 'Second', 'Third']

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
        self.name = "SearchForPeak-2DGaussianFit"
        self.settings_filename = "PeakSearcher_settings.json"
        self.mover = mover

        self.logger = logging.getLogger()

        # gather all plots for the plotting GUIs
        self.plots_left = ObservableList()
        self.plots_right = ObservableList()

        # chosen instruments for IL measurement
        self.instr_laser = None
        self.instr_powermeter1 = None
        self.instr_powermeter2 = None
        self.instr_powermeter3 = None
        self.instr_powermeter4 = None
        self.instr_switch = None
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
        # assume that sigma spans the sampled interval
        sigma_init = x_data.max() - x_data.min()
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

    def _read_averaged_power(self, averaging_time_s: float) -> list:
        """
        Reads all four power meters repeatedly for averaging_time_s seconds and returns
        their time-averaged readings, to reduce point-to-point noise in the scan trace.
        averaging_time_s=0 takes exactly one sample per meter (no averaging).

        Each sample triggers all four meters first, then fetches all four, instead of
        doing 4 sequential blocking trigger+read cycles (.power). On instruments where
        trigger() is a fire-and-forget "start acquisition" command (e.g. the Keysight
        SCPI power meters, via INIT:IMM) this lets their averaging windows overlap
        instead of stacking sequentially - fetch_power() then just reads back the
        already-triggered value instead of triggering (and waiting for) a new one. On
        instruments with no real acquisition delay to hide (e.g. PowerMeterKoheronPD10R,
        whose trigger() is a no-op and fetch_power() reads the same instantaneous value
        as .power) this is equivalent to the old behaviour - no regression either way.
        """
        meters = [self.instr_powermeter1, self.instr_powermeter2, self.instr_powermeter3, self.instr_powermeter4]
        samples = [[] for _ in meters]
        t_end = time.perf_counter() + averaging_time_s
        while True:
            for meter in meters:
                meter.trigger()
            for sample_list, meter in zip(samples, meters):
                sample_list.append(meter.fetch_power())
            if time.perf_counter() >= t_end:
                break
        return [float(np.mean(sample_list)) for sample_list in samples]

    @staticmethod
    def get_default_parameter():
        params = {
            'Switch Flag': MeasParamBool(value=False),
            'M = 1': MeasParamInt(value=1, unit='N Port'),
            'M = 2': MeasParamInt(value=2, unit='N Port'),
            'M = 3': MeasParamInt(value=3, unit='N Port'),
            'M = 4': MeasParamInt(value=4, unit='N Port'),
            'Laser wavelength': MeasParamInt(value=1550, unit='nm'),
            'Laser power': MeasParamFloat(value=0.0, unit='dBm'),
            'Power Meter range': MeasParamFloat(value=0.0, unit='dBm'),
        }
        for pass_name in PeakSearcher.PASS_NAMES:
            params.update({
                f'{pass_name} Peak Search: Enable/Disable': MeasParamBool(value=False),
                f'{pass_name} Peak Search: Search Radius': MeasParamFloat(value=5.0, unit='um'),
                f'{pass_name} Peak Search: Search step size': MeasParamFloat(value=0.5, unit='um'),
                f'{pass_name} Peak Search: Search fiber stabilization time': MeasParamInt(value=200, unit='ms'),
                f'{pass_name} Peak Search: Power averaging time': MeasParamFloat(value=0.25, unit='s'),
            })
        params.update({
            'Backlash Test: Amplitude': MeasParamFloat(value=3.0, unit='um'),
            'Backlash Test: Number of reversals': MeasParamInt(value=3, unit=''),
            'Backlash Test: Tolerance': MeasParamFloat(value=1.0, unit='um'),
        })
        return params

    @staticmethod
    def get_wanted_instrument():
        return ['Laser', 'Power Meter 1', 'Power Meter 2', 'Power Meter 3', 'Power Meter 4', 'Switch']

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
        if self.mover.left_calibration is None and self.mover.right_calibration is None:
            raise RuntimeError(
                "The Search for Peak requires at least one left or right stage configured.")

        if self.mover.left_calibration and self.mover.right_calibration:
            self._dimension_names = self.DIMENSION_NAMES_TWO_STAGES
        else:
            self._dimension_names = self.DIMENSION_NAMES_SINGLE_STAGE

        # load laser and powermeter
        self.instr_powermeter1 = self.get_instrument('Power Meter 1')
        self.instr_powermeter2 = self.get_instrument('Power Meter 2')
        self.instr_powermeter3 = self.get_instrument('Power Meter 3')
        self.instr_powermeter4 = self.get_instrument('Power Meter 4')
        self.instr_laser = self.get_instrument('Laser')
        self.instr_switch = self.get_instrument('Switch')

        # double check if instruments are initialized, otherwise throw error
        if self.instr_powermeter1 is None:
            raise RuntimeError('Search for Peak Power Meter 1 not yet defined!')
        if self.instr_powermeter2 is None:
            raise RuntimeError('Search for Peak Power Meter 2 not yet defined!')
        if self.instr_powermeter3 is None:
            raise RuntimeError('Search for Peak Power Meter 3 not yet defined!')
        if self.instr_powermeter4 is None:
            raise RuntimeError('Search for Peak Power Meter 4 not yet defined!')
        if self.instr_laser is None:
            raise RuntimeError('Search for Peak Laser not yet defined!')

        # initialize plotting
        self.plots_left.clear()
        self.plots_right.clear()

        # open connection to instruments
        self.instr_laser.open()
        self.instr_powermeter1.open()
        self.instr_powermeter2.open()
        self.instr_powermeter3.open()
        self.instr_powermeter4.open()
        if self.parameters['Switch Flag'].value:
            self.instr_switch = self.get_instrument('Switch')
            if self.instr_switch is None:
                raise RuntimeError('Search for Peak Switch not yet defined!')
            self.instr_switch.open()
            self.instr_switch.connect([(1, self.parameters['M = 1'].value), (2, self.parameters['M = 2'].value), (3, self.parameters['M = 3'].value), (4, self.parameters['M = 4'].value)])

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
        self.instr_powermeter1.unit = 'dBm'
        self.instr_powermeter1.wavelength = self.parameters['Laser wavelength'].value
        self.instr_powermeter1.range = self.parameters['Power Meter range'].value
        self.instr_powermeter2.unit = 'dBm'
        self.instr_powermeter2.wavelength = self.parameters['Laser wavelength'].value
        self.instr_powermeter2.range = self.parameters['Power Meter range'].value
        self.instr_powermeter3.unit = 'dBm'
        self.instr_powermeter3.wavelength = self.parameters['Laser wavelength'].value
        self.instr_powermeter3.range = self.parameters['Power Meter range'].value
        self.instr_powermeter4.unit = 'dBm'
        self.instr_powermeter4.wavelength = self.parameters['Laser wavelength'].value
        self.instr_powermeter4.range = self.parameters['Power Meter range'].value

        # get stage speed for later reference
        v0 = self.mover.speed_xy
        acc0 = self.mover.acceleration_xy

        # stop all previous logging
        self.instr_powermeter1.logging_stop()
        self.instr_powermeter2.logging_stop()
        self.instr_powermeter3.logging_stop()
        self.instr_powermeter4.logging_stop()

        # switch on laser
        num_peak_searches = [
            ps for ps, pass_name in enumerate(self.PASS_NAMES)
            if self.parameters.get(f'{pass_name} Peak Search: Enable/Disable').value
        ]
        for ps in num_peak_searches:
            with self.instr_laser:
                with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
                    # read parameters for SFP
                    pass_name = self.PASS_NAMES[ps]
                    radius_us = self.parameters.get(f'{pass_name} Peak Search: Search Radius').value
                    stepsize_us = self.parameters[f'{pass_name} Peak Search: Search step size'].value
                    pause_time_ms = self.parameters[f'{pass_name} Peak Search: Search fiber stabilization time'].value
                    power_averaging_time_s = self.parameters[f'{pass_name} Peak Search: Power averaging time'].value

                    # find the current positions of the stages as starting point for
                    # SFP
                    _left_start_coordinates = []
                    _right_start_coordinates = []
                    if self.mover.left_calibration:
                        _left_start_coordinates = self.mover.left_calibration.get_position().to_list()[
                            :2]
                    if self.mover.right_calibration:
                        _right_start_coordinates = self.mover.right_calibration.get_position().to_list()[
                            :2]
                    start_coordinates = _left_start_coordinates + _right_start_coordinates
                    current_coordinates = start_coordinates.copy()

                    self.logger.debug(f"Start Position: {start_coordinates}")

                    estimated_through_power = -99.0

                    # get start statistics
                    results['start location'] = start_coordinates.copy()
                    results['start through power'] = max(self._read_averaged_power(power_averaging_time_s))

                    # do sweep for every dimension
                    # color cycle strings for matplotlib
                    color_strings = ['C' + str(i) for i in range(10)]
                    for dimidx, p_start in enumerate(start_coordinates):

                        dimension_name = self._dimension_names[dimidx]

                        # create new plotting dataset for measurement
                        meas_plot = PlotData(ObservableList(), ObservableList(),
                                            'scatter', color=color_strings[dimidx])
                        meas_plot1 = PlotData(ObservableList(), ObservableList(),
                                            'scatter', color=color_strings[dimidx])
                        meas_plot2 = PlotData(ObservableList(), ObservableList(),
                                            'scatter', color=color_strings[dimidx])
                        meas_plot3 = PlotData(ObservableList(), ObservableList(),
                                            'scatter', color=color_strings[dimidx])
                        meas_plot4 = PlotData(ObservableList(), ObservableList(),
                                            'scatter', color=color_strings[dimidx])
                        fit_plot = PlotData(ObservableList(), ObservableList(),
                                            color=color_strings[dimidx], label=dimension_name)
                        opt_pos_plot = PlotData(ObservableList(), ObservableList(),
                                                marker='x', markersize=10, color=color_strings[dimidx])
                        if dimidx < len(start_coordinates) / 2:
                            self.plots_left.append(meas_plot)
                            self.plots_left.append(meas_plot1)
                            self.plots_left.append(meas_plot2)
                            self.plots_left.append(meas_plot3)
                            self.plots_left.append(meas_plot4)
                            self.plots_left.append(fit_plot)
                            self.plots_left.append(opt_pos_plot)
                        else:
                            self.plots_right.append(meas_plot)
                            self.plots_right.append(meas_plot1)
                            self.plots_right.append(meas_plot2)
                            self.plots_right.append(meas_plot3)
                            self.plots_right.append(meas_plot4)
                            self.plots_right.append(fit_plot)
                            self.plots_right.append(opt_pos_plot)

                        # create range of N measurement points from x-Delta to
                        # x+Delta
                        d_range = np.arange(-radius_us, radius_us +
                                            stepsize_us, stepsize_us)

                        # go through all measurement points for this coordinate and
                        # record IL
                        IL_meas = np.empty(len(d_range))

                        for measidx, d_current in enumerate(d_range):
                            # move stages to currently probed coordinate
                            current_coordinates[dimidx] = d_current + p_start
                            self._move_stages_absolute(current_coordinates)

                            # take a break to let fiber-vibration die off
                            time.sleep(pause_time_ms / 1000)

                            # take IL measurement, averaged over power_averaging_time_s
                            # to reduce point-to-point noise in the scan trace
                            p1, p2, p3, p4 = self._read_averaged_power(power_averaging_time_s)
                            loss = max(p1, p2, p3, p4)

                            # save data
                            # do not trigger plot update just yet
                            meas_plot.x.extend([d_current])
                            meas_plot.y.append(loss)
                            meas_plot1.x.extend([d_current])
                            meas_plot1.y.append(p1)
                            meas_plot2.x.extend([d_current])
                            meas_plot2.y.append(p2)
                            meas_plot3.x.extend([d_current])
                            meas_plot3.y.append(p3)
                            meas_plot4.x.extend([d_current])
                            meas_plot4.y.append(p4)

                            IL_meas[measidx] = loss

                        self.logger.debug('SFP results:')
                        self.logger.debug('coordinates:' + str(d_range))
                        self.logger.debug('IL: ' + str(IL_meas))

                        # default assignments before SFP decision
                        optimized_target = 0
                        popt = None
                        perr_std_dev = None
                        fit_msg = None
                        sfp_msg = None
                        # True only if a real peak was located and moved to. Used to
                        # decide whether this position is trustworthy enough to reuse
                        # as a chip-to-stage calibration reference point.
                        peak_found = False

                        # 1st decision: did the power meter always return useful data?
                        if ~np.all(np.isfinite(IL_meas)):
                            sfp_msg = f'SFP failed on dimension {dimension_name} because not all measured IL values are finite.' + \
                                    ' Change of power meter range required. Moving back to start point.'
                            self.logger.warning(sfp_msg)
                        else:
                            # 2nd decision: fit the gauss and see if it works
                            try:
                                popt, perr_std_dev = self.fit_gaussian(
                                    d_range, IL_meas)
                                fit_msg = "Gauss fitting successful."
                            except RuntimeError:  # thrown from scipy optimizer if algorithm did not converge
                                # if convergence fails, we estimate the parameters crudly, i.e. just get the point with
                                # maximum transmission
                                popt = PeakSearcher._gaussian_param_initial_guess(
                                    d_range, IL_meas)
                                fit_msg = "Gauss fitting did not converge. Using point with maximum transmission."
                                self.logger.warning(fit_msg)

                            # 3rd decision: judge feasibility of gaussian fit
                            a_best, d_best = popt[0:2]
                            if abs(d_best) > 1.5 * radius_us:
                                sfp_msg = 'Movement would be more than 1.5x search radius. Moving back to start point.'
                                self.logger.warning(sfp_msg)
                            elif (np.max(IL_meas) - np.min(IL_meas)) < NO_PEAK_FOUND_DYNAMIC_RANGE_DB:
                                optimized_target = 0
                                sfp_msg = (
                                    f'Dynamic range of {np.max(IL_meas) - np.min(IL_meas):.2f}dB is below the '
                                    f'{NO_PEAK_FOUND_DYNAMIC_RANGE_DB}dB no-peak-found threshold. '
                                    'No clear peak detected; staying at start point.'
                                )
                                self.logger.warning(sfp_msg)
                            else:
                                optimized_target = d_best
                                peak_found = True
                                sfp_msg = f'Moving to optimized fiber location.'

                            # plot the gaussian, if gaussian was successfully fitted
                            if perr_std_dev is not None:
                                # interpolate between the fitted values to get a nice
                                # smooth line
                                d_range_highres = np.linspace(
                                    d_range.min(), d_range.max(), num=len(
                                        meas_plot.x) * 5)
                                IL_fit_fctn = PeakSearcher._gaussian(
                                    d_range_highres, *popt)
                                # plot fit data
                                fit_plot.x.extend(d_range_highres)
                                fit_plot.y.extend(IL_fit_fctn[0:-1])
                                # trigger plot update
                                fit_plot.y.append(IL_fit_fctn[-1])

                            # mark the point where we move to in any case
                            estimated_through_power = self._gaussian(
                                optimized_target, *popt)
                            # do not trigger plot update just yet
                            opt_pos_plot.x.extend([optimized_target])
                            opt_pos_plot.y.append(estimated_through_power)

                        # inform user and store the fitting information
                        self.logger.debug(
                            f"Search for peak for dimension {dimension_name} finished. "
                            f"Fitter message: {fit_msg} -- SFP decision: {sfp_msg} "
                            f"Moving to location: {optimized_target:.3f}um with estimated through power"
                            f" of {estimated_through_power:.1f}dBm.")

                        # A fit whose optimum sits at the very edge of the scanned window
                        # may be clipped (true peak possibly outside the window), so the
                        # move still happens but the position is not trusted as an
                        # absolute calibration reference.
                        near_edge = bool(
                            peak_found and abs(optimized_target) > NEAR_EDGE_REJECT_FRACTION * radius_us)
                        if near_edge:
                            self.logger.warning(
                                f"Search for peak on dimension {dimension_name}: optimum at "
                                f"{optimized_target:.3f}um is beyond {NEAR_EDGE_REJECT_FRACTION:.0%} of the "
                                f"{radius_us:.3f}um search radius; the peak may be clipped by the scan window. "
                                "Still moving there, but not using this position as a calibration reference."
                            )

                        results['fitting information'][dimension_name] = {
                            'optimized parameters': list(popt) if popt is not None else None,
                            'parameter estimation error std dev': list(perr_std_dev) if perr_std_dev is not None else None,
                            'fitter message': str(fit_msg),
                            'sfp decision': str(sfp_msg),
                            'peak found': bool(peak_found),
                            'near search radius edge': near_edge}

                        # reset speed and acceleration to original
                        self.mover.speed_xy = v0
                        self.mover.acceleration_xy = acc0

                        # final move of fiber in this dimensions final decision
                        current_coordinates[dimidx] = optimized_target + p_start
                        self._move_stages_absolute(current_coordinates)

                        # verify the move with a real measurement rather than trusting
                        # the fit's prediction, and flag a net-negative outcome
                        verified_through_power = max(self._read_averaged_power(power_averaging_time_s))
                        results['fitting information'][dimension_name]['verified through power'] = verified_through_power
                        results['fitting information'][dimension_name]['verification passed'] = bool(
                            verified_through_power >= results['start through power'])
                        if verified_through_power < results['start through power']:
                            self.logger.warning(
                                f"Search for peak on dimension {dimension_name}: verified power "
                                f"{verified_through_power:.2f}dBm after the final move is WORSE than the "
                                f"pass start power {results['start through power']:.2f}dBm "
                                f"(fit estimated {estimated_through_power:.2f}dBm)."
                            )
                        else:
                            self.logger.debug(
                                f"Search for peak on dimension {dimension_name}: verified power "
                                f"{verified_through_power:.2f}dBm after the final move "
                                f"(fit estimated {estimated_through_power:.2f}dBm, "
                                f"pass start was {results['start through power']:.2f}dBm)."
                            )

        # close instruments
        self.instr_laser.close()
        self.instr_powermeter1.close()
        self.instr_powermeter2.close()
        self.instr_powermeter3.close()
        self.instr_powermeter4.close()
        if self.parameters['Switch Flag'].value:
            self.instr_switch.close()

        # save final result to log
        loc_str = " x ".join(["{:.3f}um".format(p)
                             for p in current_coordinates])
        self.logger.info(
            f"Search for peak finished: maximum estimated output power of {estimated_through_power:.1f}dBm"
            f" at {loc_str:s}.")

        # save end result and return
        results['optimized location'] = current_coordinates.copy()
        results['optimized through power'] = estimated_through_power

        # Summarise whether this search's end position is trustworthy enough to be
        # reused as a chip-to-stage calibration reference point. Note 'fitting
        # information' is keyed per dimension and overwritten by each enabled pass,
        # so this reflects the state after the final pass on every dimension.
        rejection_reasons = []
        if not results['fitting information']:
            rejection_reasons.append(
                'no search pass ran (all passes disabled)')
        for dimension_name, info in results['fitting information'].items():
            if not info.get('peak found'):
                rejection_reasons.append(
                    f"{dimension_name}: no peak found ({info.get('sfp decision')})")
            if info.get('near search radius edge'):
                rejection_reasons.append(
                    f"{dimension_name}: optimum at edge of search radius, fit may be clipped")
            if not info.get('verification passed'):
                rejection_reasons.append(
                    f"{dimension_name}: verified power after the final move was worse than the pass start power")

        results['search successful'] = not rejection_reasons
        results['calibration rejection reasons'] = rejection_reasons

        return results

    def _move_stages_absolute(self, coordinates: list):
        with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
            if self.mover.left_calibration and self.mover.right_calibration:
                leftz = self.mover.left_calibration.get_position().z
                rightz = self.mover.right_calibration.get_position().z
                assert len(coordinates) == 4
                self.mover.left_calibration.move_absolute(
                    StageCoordinate.from_list(coordinates[:2] + [leftz]))
                self.mover.right_calibration.move_absolute(
                    StageCoordinate.from_list(coordinates[2:] + [rightz]))
            elif self.mover.left_calibration:
                leftz = self.mover.left_calibration.get_position().z
                assert len(coordinates) == 2
                self.mover.left_calibration.move_absolute(
                    StageCoordinate.from_list(coordinates + [leftz]))
            elif self.mover.right_calibration:
                rightz = self.mover.right_calibration.get_position().z
                assert len(coordinates) == 2
                self.mover.right_calibration.move_absolute(
                    StageCoordinate.from_list(coordinates + [rightz]))
            else:
                raise RuntimeError()

    def _get_current_coordinates(self) -> list:
        """
        Returns the current [Left X, Left Y, Right X, Right Y] (or [X, Y] for a
        single-stage setup) stage coordinates, in the same ordering/slicing used
        throughout search_for_peak().
        """
        _left = self.mover.left_calibration.get_position().to_list()[:2] if self.mover.left_calibration else []
        _right = self.mover.right_calibration.get_position().to_list()[:2] if self.mover.right_calibration else []
        return _left + _right

    def test_backlash(self) -> dict:
        """
        Backlash / direction self-test for the X and Y stage axes (Z is never moved -
        _move_stages_absolute always holds Z fixed at its current value).

        For each axis, moves by 'Backlash Test: Amplitude' and back to the start
        position 'Backlash Test: Number of reversals' times, reading back the actual
        position after every move and comparing it to the commanded target. If the
        stage driver's backlash compensation (or direction handling) is broken, this
        shows up as a position error of roughly the mechanical backlash distance right
        after a direction reversal. Always restores the exact starting position,
        including if an error occurs partway through - safe to run on an
        already-aligned setup.

        Returns
        -------
        dict
            Per-axis-name -> {'max_error_um': float, 'passed': bool}
        """
        if self.mover.left_calibration is None and self.mover.right_calibration is None:
            raise RuntimeError("Backlash test requires at least one left or right stage configured.")

        amplitude_um = self.parameters.get('Backlash Test: Amplitude').value
        num_reversals = int(self.parameters.get('Backlash Test: Number of reversals').value)
        tolerance_um = self.parameters.get('Backlash Test: Tolerance').value

        dimension_names = (
            self.DIMENSION_NAMES_TWO_STAGES
            if self.mover.left_calibration and self.mover.right_calibration
            else self.DIMENSION_NAMES_SINGLE_STAGE
        )

        test_results = {}

        with self.mover.set_stages_coordinate_system(CoordinateSystem.STAGE):
            start_coordinates = self._get_current_coordinates()
            current_coordinates = start_coordinates.copy()
            self.logger.info(f"Backlash test: starting at {start_coordinates}")

            try:
                for dimidx, p_start in enumerate(start_coordinates):
                    dimension_name = dimension_names[dimidx]
                    max_error = 0.0
                    direction = 1
                    for rev in range(num_reversals * 2):
                        target = p_start + (amplitude_um if direction == 1 else 0.0)
                        current_coordinates[dimidx] = target
                        self._move_stages_absolute(current_coordinates)
                        actual = self._get_current_coordinates()[dimidx]
                        error = actual - target
                        max_error = max(max_error, abs(error))
                        self.logger.info(
                            f"Backlash test [{dimension_name}] reversal {rev + 1}/{num_reversals * 2}: "
                            f"target={target:.4f}um actual={actual:.4f}um error={error:+.4f}um"
                        )
                        direction *= -1

                    # return this axis to its exact start before testing the next axis
                    current_coordinates[dimidx] = p_start
                    self._move_stages_absolute(current_coordinates)
                    actual = self._get_current_coordinates()[dimidx]
                    error = actual - p_start
                    max_error = max(max_error, abs(error))

                    passed = max_error <= tolerance_um
                    test_results[dimension_name] = {'max_error_um': max_error, 'passed': passed}
                    self.logger.info(
                        f"Backlash test [{dimension_name}] finished: max error {max_error:.4f}um "
                        f"(tolerance {tolerance_um}um) -> {'PASS' if passed else 'FAIL'}"
                    )
            finally:
                # safety net: always try to restore the exact original position, even on error
                self._move_stages_absolute(start_coordinates.copy())
                final_coordinates = self._get_current_coordinates()
                self.logger.info(
                    f"Backlash test: restored position to {final_coordinates} (target was {start_coordinates})"
                )

        return test_results

    def update_params_from_savefile(self):
        if not os.path.isfile(self.settings_path_full):
            self.logger.debug(f"SFP Parameter save file at {self.settings_path_full} not found. "
                              f"Using default parameters.")
            return

        with open(self.settings_path_full, 'r') as json_file:
            data = json.loads(json_file.read())

        for param_name, param_value in data["data"].items():
            self.parameters[param_name].value = param_value

    def algorithm(self, device, data, instruments, parameters):
        raise NotImplementedError()
