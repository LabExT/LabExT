#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import List
from os.path import exists as os_path_exists

from LabExT.Wafer.Device import Device


class Chip:
    """Chip is the implementation of a chip with devices."""

    def __init__(self, name: str = None, path: str = None, devices: List[Device] = None):
        """Constructor.

        Parameters
        ----------
        name : string, optional
            Name of the Chip.
        devices : List[Device], optional
            Holds all devices objects
        """
        self._logger = logging.getLogger()
        self._logger.debug('Initialised Chip with name: %s', name)

        self._path = path
        if self._path is not None:
            if not os_path_exists(self._path):
                raise ValueError("File indicated in argument 'path' does not exist.")

        self._name = name

        if devices is not None:
            self._devices = devices
            assert isinstance(self._devices, list), "Argument 'devices' is not a list."
            for dev in self._devices:
                assert isinstance(dev, Device), "An element in devices is not of type Device."
        else:
            self._devices = list()
        self._logger.debug('Number of devices in chip: %s', len(self._devices))

    @property
    def path(self) -> str:
        """ Return the filepath of the chip file. """
        return self._path

    @property
    def name(self) -> str:
        """ Return the name of the chip. """
        return self._name

    @property
    def devices(self) -> dict:
        """ Return a dictionary of all devices with device ID as keys. """
        return {device.id: device for device in self._devices}
