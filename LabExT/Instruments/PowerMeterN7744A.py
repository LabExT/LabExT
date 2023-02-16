#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Instruments.InstrumentAPI import InstrumentException
from LabExT.Instruments.PowerMeterGenericKeysight import PowerMeterGenericKeysight


class PowerMeterN7744A(PowerMeterGenericKeysight):
    """
    ## PowerMeterN7744A

    This class extends the [PowerMeterGenericKeysight](./PowerMeterGenericKeysight.md)
    class by the `autogain` property only present on the newer N77xxA models of power meters.

    This class was tested with the Keysight N7744A and N7745C power meters, and is very likely working with most other
    multichannel N77xx power meters from keysight, too.

    #### Properties

    handbook page refers to: Keysight N77xx Series Programming Guide (9018-02434.pdf)

    | property type | datatype | read/write | page in handbook | unit | description                                 |
    |---------------|----------|------------|------------------|------|---------------------------------------------|
    | autogain      | bool     | rw         | 134/135          |      | activate or deactivate the autogain feature |

    """

    def __init__(self, *args, **kwargs):
        """
        Constructor for the optical power meter. This class can be used if a N7744A optical power meter is attached
        via ethernet.
        """
        # call Instrument constructor, creates VISA instrument
        super().__init__(*args, **kwargs)
       
        # the N7744A is smart and returns sweep data in the chosen unit
        self._always_returns_sweep_in_Watt = False

        # instrument parameter on network, add to this list all object properties which should get freshly fetched
        # and added to self.instrument_paramters on each get_instrument_parameter() call
        self.networked_instrument_properties.extend([
            'autogain'
        ])

    def open(self):
        super().open()
        # observation by Marco: The N7744A has much faster polling when we call the setup to the logging function once
        self.logging_setup(n_measurement_points=1000)

    @property
    def autogain(self):
        """
        Query automatic gain setting.
        """
        resp = self.request_channel(':SENS', ':POW:GAIN:AUTO?').strip().lower()
        if '1' in resp or 'on' in resp:
            return True
        elif '0' in resp or 'off' in resp:
            return False
        else:
            raise InstrumentException('Power meter returned something not understandable: ' + str(resp))

    @autogain.setter
    def autogain(self, new_state):
        """
        Set automatic gain setting.
        """
        if new_state:
            self.command_channel(':SENS', ':POW:GAIN:AUTO 1')
        else:
            self.command_channel(':SENS', ':POW:GAIN:AUTO 0')
