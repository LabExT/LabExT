#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging


class Device:
    """Implements a device on a chip.
    """

    def __init__(self, identifier, in_p, out_p, typ, parameters=None):
        """Constructor.

        Parameters
        ----------
        identifier : int
            Device ID.
        in_p : list
            Input position of device.
        out_p : list
            Output position of device.
        typ : string
            Type of device.
        parameters : dict, optional
            Any additional parameters, as written in the chip file.
        """

        self.logger = logging.getLogger()
        self.logger.debug('Initialise device with ID: %s input: %s output: %s type: %s parameters: %s',
                          identifier, in_p, out_p, typ, parameters)

        self._id = identifier
        self._in_position = in_p
        self._out_position = out_p
        if parameters is not None:
            self._parameters = parameters
        else:
            self._parameters = dict()
        self._type = typ

    def __str__(self):
        """Overrides the print() function for devices.

        Returns
        -------
        string
            String representation of the device.
        """
        rep = "Device ID: " + str(self._id) + "\n"
        rep += "Input-position on chip: " + str(self._in_position) + "\n"
        rep += "Output-position on chip: " + str(self._out_position) + "\n"
        rep += "Type: " + self._type
        rep += "Parameters:\n"
        if self._parameters is not None:
            for k, v in self._parameters.items():
                rep += "\t"
                rep += str(k) + " = " + str(v) + "\n"
        return rep

    def short_str(self, add_params=False):
        """
        Same as __str__(), but a short text version.
        """
        rep = "ID: " + str(self._id) + " " + \
              "type: " + str(self._type) + " " + \
              "out: " + str(self._out_position) + " " + \
              "in: " + str(self._in_position)
        if add_params and self._parameters is not None:
            for k, v in self._parameters.items():
                rep += " "
                rep += str(k) + "=" + str(v)
        return rep

    def get_device_data(self):
        """Returns all information on the device as a dictionary.

        Returns
        -------
        dict
            A dictionary containing all data on the device.
        """
        data = {}
        data['id'] = self._id
        data['in_position'] = self._in_position
        data['out_position'] = self._out_position
        data['type'] = self._type
        data.update(self._parameters)

        self.logger.debug('Requested data of device: %s', data)
        return data
