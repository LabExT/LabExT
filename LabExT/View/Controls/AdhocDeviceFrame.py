#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import os
from tkinter import Label, Entry, Button, StringVar

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.Wafer.Device import Device


class AdhocDeviceFrame(CustomFrame):
    """A control that allows to specify a device."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._root = parent

        # custom parameter fields
        self._entry_id = None
        self._entry_type = None
        self._entry_inp_x = None
        self._entry_inp_y = None
        self._entry_oup_x = None
        self._entry_oup_y = None
        self._extra_parameter_vars = []
        self._counter = 4  # row counter

        self.__setup__()

    def __setup__(self):
        """setup GUI elements"""

        Label(self, text='Device ID number (*):').grid(row=0, column=0, padx=5, sticky='w')
        self._entry_id = self.add_widget(Entry(self), row=0, column=1, padx=5, sticky='we', columnspan=3)
        Label(self, text='Required: integer >= 0').grid(row=0, column=4, padx=5, sticky='w')

        Label(self, text='Type (*):').grid(row=1, column=0, padx=5, sticky='w')
        self._entry_type = self.add_widget(Entry(self), row=1, column=1, padx=5, sticky='we', columnspan=3)
        Label(self, text='Required: string').grid(row=1, column=4, padx=5, sticky='w')

        Label(self, text='Input position:').grid(row=2, column=0, padx=5, sticky='w')
        self._entry_inp_x = self.add_widget(Entry(self), row=2, column=1, padx=(5, 0), sticky='we')
        Label(self, text=',').grid(row=2, column=2)
        self._entry_inp_y = self.add_widget(Entry(self), row=2, column=3, padx=(0, 5), sticky='we')
        Label(self, text='x, y coordinate of input [um]').grid(row=2, column=4, padx=5, sticky='w')

        Label(self, text='Output position:').grid(row=3, column=0, padx=5, sticky='w')
        self._entry_oup_x = self.add_widget(Entry(self), row=3, column=1, padx=(5, 0), sticky='we')
        Label(self, text=',').grid(row=3, column=2)
        self._entry_oup_y = self.add_widget(Entry(self), row=3, column=3, padx=(0, 5), sticky='we')
        Label(self, text='x, y coordinate of output [um]').grid(row=3, column=4, padx=5, sticky='w')

        self._counter = 4
        self.__setup_extra_params__()

        # the window can max. support 100 input fields
        self._more_parameters_button = self.add_widget(
            Button(self, text='add more parameters', command=self._more_parameter),
            row=100, column=0, padx=5, pady=5, sticky='we')

        # size columns
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        # column 2 omitted on purpose for nicer commas between coordinate fields
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=1)

    def __setup_extra_params__(self):
        """setup GUI elements for the custom parameters"""
        for kv, vv in self._extra_parameter_vars:
            self.add_widget(Entry(self, textvariable=kv),
                            row=self._counter, column=0, columnspan=3, padx=5, sticky='we')
            self.add_widget(Entry(self, textvariable=vv),
                            row=self._counter, column=1, columnspan=3, padx=5, sticky='we')
            self._counter += 1

    def _more_parameter(self):
        """Adds new parameter fields to the window for custom
        parameters.
        """
        if self._counter >= 99:
            return

        param_key = StringVar()
        param_value = StringVar()
        self._extra_parameter_vars.append((param_key, param_value))

        self.add_widget(Entry(self, textvariable=param_key),
                        row=self._counter, column=0, columnspan=3, padx=5, sticky='we')
        self.add_widget(Entry(self, textvariable=param_value),
                        row=self._counter, column=1, columnspan=3, padx=5, sticky='we')
        self._counter += 1

    def get_custom_device(self):
        """
        Reads all current entries, does data validation, and converts it to a Device object.
        """
        _id = self._entry_id.get()
        if len(_id) < 1:
            raise ValueError("Device ID cannot be empty.")
        _id = int(_id)
        if _id < 0:
            raise ValueError("Device ID must be non-negative.")

        _type = self._entry_type.get()
        if len(_type) < 1:
            raise ValueError("Type cannot be empty.")

        _inp_x = self._entry_inp_x.get()
        _inp_y = self._entry_inp_y.get()
        if len(_inp_x) > 0 or len(_inp_y) > 0:
            _inp_x = float(_inp_x)
            _inp_y = float(_inp_y)
        else:
            _inp_x = 0
            _inp_y = 0

        _oup_x = self._entry_oup_x.get()
        _oup_y = self._entry_oup_y.get()
        if len(_oup_x) > 0 or len(_oup_y) > 0:
            _oup_x = float(_oup_x)
            _oup_y = float(_oup_y)
        else:
            _oup_x = 0
            _oup_y = 0

        params = {kv.get(): vv.get() for kv, vv in self._extra_parameter_vars}

        return Device(_id, [_inp_x, _inp_y], [_oup_x, _oup_y], _type, params)

    def load_existing_device(self, device: Device):
        """Loads existing device information from an existing device object."""

        self._entry_id.insert(0, device._id)
        self._entry_type.insert(0, device._type)
        self._entry_inp_x.insert(0, device._in_position[0])
        self._entry_inp_y.insert(0, device._in_position[1])
        self._entry_oup_x.insert(0, device._out_position[0])
        self._entry_oup_y.insert(0, device._out_position[1])

        # do not save empty extra parameters
        self._extra_parameter_vars = [(StringVar(value=kv), StringVar(value=vv))
                                      for kv, vv in device._parameters.items()]
        self.__setup_extra_params__()

    def serialize(self, file_name):
        """Serializes data in table to json."""
        data = {
            "_id": self._entry_id.get(),
            "_inp_x": self._entry_inp_x.get() or 0,
            "_inp_y": self._entry_inp_y.get() or 0,
            "_oup_x": self._entry_oup_x.get() or 0,
            "_oup_y": self._entry_oup_y.get() or 0,
            "_type": self._entry_type.get()
        }
        data['extra_parameter'] = {kv.get(): vv.get() for kv, vv in self._extra_parameter_vars}
        settings_path = get_configuration_file_path(file_name)
        with open(settings_path, 'w') as json_file:
            json_file.write(json.dumps(data))

    def deserialize(self, file_name):
        """Deserializes the table data from a given file and loads it
        into the cells."""
        settings_path = get_configuration_file_path(file_name)
        if not os.path.isfile(settings_path):
            return
        with open(settings_path, 'r') as json_file:
            data = json.loads(json_file.read())

        self._entry_id.insert(0, data["_id"])
        self._entry_type.insert(0, data["_type"])
        self._entry_inp_x.insert(0, data["_inp_x"])
        self._entry_inp_y.insert(0, data["_inp_y"])
        self._entry_oup_x.insert(0, data["_oup_x"])
        self._entry_oup_y.insert(0, data["_oup_y"])

        # do not save empty extra parameters
        self._extra_parameter_vars = [(StringVar(value=kv), StringVar(value=vv)) for kv, vv in
                                      data["extra_parameter"].items() if len(kv) > 0 or len(vv) > 0]
        self.__setup_extra_params__()
