#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame

from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.Wafer.Chip import Chip
from LabExT.Wafer.Device import Device


class DeviceTable(Frame):
    """
    Frame which contains a table to select a device from the loaded chip file.
    """

    def __init__(self, parent, chip: Chip):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            Window in which frame will be placed.
        chip : Chip
            Instance of current imported Chip.
        """
        super(DeviceTable, self).__init__(parent)
        self.logger = logging.getLogger()
        self._devices = chip.devices.copy()

        self.__setup__()

    def __setup__(self):
        """
        Set up the CustomTable containing all devices
        """
        # set up columns so that they contain all parameters
        def_columns = ["ID", "In", "Out", "Type"]
        columns = set()
        for device in self._devices.values():
            for param in device.parameters:
                columns.add(str(param))
        def_columns.extend(list(columns))

        self.logger.debug('Columns in table: %s', (def_columns + list(columns)))

        # fill parameters in devices as empty values if not specified
        devs = list()
        for d in self._devices.values():
            tup = (d.id, d.in_position, d.out_position, d.type)
            for param in columns:
                val = d.parameters.get(param, '')
                # we unpack the tuple, append the value of the new parameter
                # and make a tuple again, if parameter not specified on device
                # its just empty
                tup = (*tup, val)
            devs.append(tup)

        self.logger.debug('Number of rows in table: %d', len(devs))
        # make new table
        self._device_table = CustomTable(parent=self, columns=def_columns, rows=devs, col_width=20, selectmode='browse')

    def get_selected_device(self) -> Device or None:
        """
        Return the currently selected device object.
        """
        selected_iid = self._device_table.focus()
        if not selected_iid:
            return None
        dev_id = self._device_table.set_by(selected_iid, 0)
        return self._devices[dev_id]

    def set_selected_device(self, device_id):
        """
        Set the current selected entry by the device id.
        """
        self._device_table.select_by(device_id, 0)
