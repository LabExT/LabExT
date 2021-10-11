#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame

from LabExT.View.Controls.CustomTable import CustomTable


class DeviceTable(Frame):
    """
    Frame which contains a table to select a device from the loaded chip file.
    """

    def __init__(self, parent, experiment_manager):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            Window in which frame will be placed.
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager.
        """
        super(DeviceTable, self).__init__(parent)

        self.logger = logging.getLogger()

        self._experiment_manager = experiment_manager

        self._devices = self._experiment_manager.chip._devices.copy()
        self.logger.debug('Found %d devices.', len(self._devices))

        self.__setup__()

    def __setup__(self):
        """
        Setup the CustomTable containing all devices
        """

        # setup columns so that they contains all parameters
        def_columns = ["ID", "In", "Out", "Type"]
        columns = set()
        for device in self._devices.values():
            for param in device._parameters:
                columns.add(str(param))

        self.logger.debug('Columns in table: %s', (def_columns + list(columns)))

        # fill parameters in devices as empty values if not specified
        devs = list()
        for d in self._devices.values():
            tup = (d._id, d._in_position, d._out_position, d._type)
            for param in columns:
                val = d._parameters.get(param, '')
                # we unpack the tuple, append the value of the new parameter
                # and make a tuple again, if parameter not specified on device
                # its just empty
                tup = (*tup, val)
            devs.append(tup)

        self.logger.debug('Number of rows in table: %d', len(devs))
        # make new table
        self._device_table = CustomTable(self, (def_columns + list(columns)), devs, 20, 'browse')

    def get_selected_device(self):
        """
        Return the currently selected device object.
        """
        selected_iid = self._device_table._tree.focus()
        self.logger.debug('Selected iid: %s', selected_iid)
        if not selected_iid:
            return None
        dev_id = int(self._device_table._tree.set(selected_iid, 0))
        self.logger.debug('Selected device ID: %s', dev_id)
        selection = self._devices[dev_id]
        self.logger.debug('Device selected: %s', selection)
        return selection

    def set_selected_device(self, device_id):
        """
        Set the current selected entry by the device id.
        """
        self._device_table.select_by_id(device_id)
