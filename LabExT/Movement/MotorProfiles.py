#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import numpy as np
from scipy.interpolate import interp1d


def trapezoidal_velocity_profile_by_integration(start_position_m,
                                                stop_position_m,
                                                max_speed_mps,
                                                const_acceleration_mps2,
                                                dt_integration=1e-5,
                                                n_output_points=None):
    """
    Calculates the positions, the velocity, and the accelerations over time for a constant-acceleration positioning
    motor. This is for motors using a trapezoidal velocity profile and automatically takes care of the case when
    saturation velocity is not reached (see e.g. Maxon Motor EPOS4 Firmware Specification, p3-21).

    Parameters
    ----------
    start_position_m, stop_position_m: start and stop position of the movement in [m]
    max_speed_mps: saturation speed of the motor (>0) in [m/s]
    const_acceleration_mps2: constant acceleration for speeding up or slowing down (>0) in [m/s^2]
    dt_integration: what is the time resolution on which the numerical integration should be done? Make sure that this
    is sufficiently small.
    n_output_points: optional, if given, will resample all output vectors, s.t. they include N_output_points samples.
    The time vectors starts at 0 and includes the maximum time as its last sample.

    Returns
    -------
    t_vec: the time vector, sampled at the interval dt_integration (default 10us) in units of [s].
    x_vec: the position vector, i.e. the position x at each time in t_vec [m].
    xd_vec: the velocity vector, i.e. the velocity dx/dt at each time in t_vec [m/s].
    xdd_vec: the acceleration vector, i.e. the acceleration d^2x/dt^2 at each time in t_vec [m/s^2].
    """

    # movement profile parameters
    # convert all values from [nm] to [um], [um/s] to [nm/s], [um/s^2] to [nm/s^2]
    x = start_position_m  # [m]
    y = stop_position_m  # [m]
    d = y - x  # total distance [m]
    v = max_speed_mps  # [m/s]
    assert v > 0, "saturation velocity must be positive"
    a = const_acceleration_mps2  # [m/s^2]
    assert a > 0, "constant acceleration must be positive"
    dt = dt_integration  # time resolution for simulation [s]

    # create movement profile by defining acceleration curves (xdd_vec) manually
    if np.abs(d) / v - v / a > 0:
        # case: long enough drive to get into saturation velocity
        t = np.abs(d) / v + v / a  # time for total movement, trapecoidal profile
        t_vec = np.arange(0, t, dt)
        xdd_vec = np.zeros_like(t_vec)
        xdd_vec[t_vec < v / a] = np.sign(d) * a
        xdd_vec[t_vec > t - v / a] = -1 * np.sign(d) * a
    else:
        # case: we never run into maximum velocity
        t = np.sqrt(4 * np.abs(d) / a)  # time for total movement, triangular profile
        t_vec = np.arange(0, t, dt)
        xdd_vec = np.zeros_like(t_vec)
        xdd_vec[t_vec < t / 2] = np.sign(d) * a
        xdd_vec[t_vec > t / 2] = -1 * np.sign(d) * a

    # integrate to get location (x_vec)
    xd_vec = np.cumsum(xdd_vec) * dt
    x_vec = np.cumsum(xd_vec) * dt + x

    if n_output_points is not None:
        sampling_times = np.linspace(0, t, num=n_output_points, endpoint=True)
        x_vec = interp1d(
            t_vec, x_vec, kind='quadratic', bounds_error=False, fill_value=(x_vec[0], x_vec[-1]))(sampling_times)
        xd_vec = interp1d(
            t_vec, xd_vec, kind='linear', bounds_error=False, fill_value=0.0)(sampling_times)
        xdd_vec = interp1d(
            t_vec, xdd_vec, kind='linear', bounds_error=False, fill_value=0.0)(sampling_times)
        t_vec = sampling_times

    return t_vec, x_vec, xd_vec, xdd_vec
