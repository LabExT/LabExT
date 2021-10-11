#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
from tkinter import DoubleVar, StringVar, BooleanVar, IntVar, Label, Entry, Checkbutton, filedialog, Button, \
    OptionMenu, TclError

from LabExT.Measurements.MeasAPI import *
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame


class ConfigParameter(object):
    """Handles parameters for parameter tables.
    As a basis the tkinter.Variables are used which notify the ui
    about changes automatically.
    """

    @property
    def value(self):
        """Gets the current value of the parameter."""
        return self.variable.get()

    @value.setter
    def value(self, v):
        """Sets the current value of the parameter."""
        # if needed, update origin
        # this is an artifact since we need to support stateless measurements
        self.variable.set(v)

    def __init__(self, parent, value=0,
                 unit=None, parameter_type='number_float', allow_user_changes=True, origin_var=None, ddvar=None):
        # initialize the parameter either as a number or as text
        if parameter_type == 'number_int':
            self.variable = IntVar(parent, value)
        elif parameter_type == 'number_float':
            self.variable = DoubleVar(parent, value)
        elif parameter_type == 'bool':
            self.variable = BooleanVar(parent, value)
        elif parameter_type == 'dropdown':
            self.variable = StringVar(parent, value[0] if ddvar is None else ddvar)
            self.options = value
        else:
            self.variable = StringVar(parent, value)
        self.unit = unit
        self.parameter_type = parameter_type
        self.parent = parent
        self.allow_user_changes = allow_user_changes

        self.origin_var = origin_var

    def browse_folders(self):
        result = filedialog.askdirectory(initialdir=self.value)
        if result is not None and result != '':
            self.value = result

    def browse_files(self):
        result = filedialog.asksaveasfilename(initialdir=self.value)
        if result is not None and result != '':
            self.value = result

    def browse_files_open(self):
        result = filedialog.askopenfilename(initialdir=self.value)
        if result is not None and result != '':
            self.value = result

    def as_dict(self):
        d = {'value': self.value}
        if self.unit is not None:
            d.update({'unit': self.unit})
        return d


class ParameterTable(CustomFrame):
    """A ui control that creates a table from a given set of
    parameters so they can easily be set from the ui."""

    @property
    def parameter_source(self):
        """Gets the currently set parameter list."""
        return self._parameter_source

    @parameter_source.setter
    def parameter_source(self, source):
        """Sets the parameter list."""
        self.new_source = source

        if len(source) == 0:
            return
        # little hack to access the first element
        # this is needed since source is a dict and we want the first
        if type(next(iter(source.values()))) is ConfigParameter:
            # treat as ConfigParam
            self.set_from_meas_param = False
            self._parameter_source = source
            self.__setup__()  # redraw the control with the new parameter source
        else:
            # Treat as MeasParam
            self.set_from_meas_param = True
            self.setup_measparam()
            self.__setup__()

    def __init__(self, parent, customwidth=20, store_callback=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._parameter_source = None
        self._root = parent  # keep reference to the ui parent
        self._customwidth = customwidth
        self.set_from_meas_param = False
        self.new_source = []
        self.store_callback = store_callback
        self.__setup__()  # draw the table

    def __setup__(self):
        self.clear()  # remove all existing ui controls from the table

        if self.parameter_source is None:
            return

        # add the fields for all the parameters
        r = 0
        for parameter_name in self.parameter_source:
            parameter = self.parameter_source[parameter_name]  # get the next parameter
            self.add_widget(Label(self, text='{}:'.format(parameter_name)),
                            row=r,
                            column=0,
                            padx=5,
                            sticky='w')  # add parameter name
            self.rowconfigure(r, weight=1)
            self.columnconfigure(0, weight=1)

            if parameter.parameter_type == 'bool':
                self.add_widget(Checkbutton(self,
                                            variable=parameter.variable,
                                            state='normal' if parameter.allow_user_changes else 'disabled'),
                                row=r,
                                column=1,
                                padx=5,
                                sticky='we')
            elif parameter.parameter_type == 'dropdown':
                if not isinstance(parameter.options, list) and not isinstance(parameter.options, tuple):
                    raise ValueError(
                        "Dropdown options has to be a list or tuple, got {} instead.".format(type(parameter.options)))
                self.add_widget(OptionMenu(self,
                                           parameter.variable,
                                           *parameter.options),
                                row=r,
                                column=1,
                                sticky='we')
            else:
                self.add_widget(Entry(self,
                                      textvariable=parameter.variable,
                                      width=self._customwidth,
                                      state='normal' if parameter.allow_user_changes else 'disabled'),
                                row=r,
                                column=1,
                                padx=5,
                                sticky='we')
                self.columnconfigure(1, weight=2)

            if parameter.unit is not None:
                self.add_widget(Label(self, text='[{}]'.format(parameter.unit)),
                                row=r,
                                column=2,
                                padx=5,
                                sticky='we')  # add unit description

            # add browse button for files and folders
            if parameter.parameter_type == 'folder':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_folders),
                                row=r,
                                column=2,
                                padx=5,
                                sticky='we')
            if parameter.parameter_type == 'file':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_files),
                                row=r,
                                column=2,
                                padx=5,
                                sticky='we')
            if parameter.parameter_type == 'openfile':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_files_open),
                                row=r,
                                column=2,
                                padx=5,
                                sticky='we')
            r += 1

    def setup_measparam(self):
        # set the table to be a meas param table (we need translation)
        self.set_from_meas_param = True
        self._parameter_source = {}
        # fill self.parameter_source with translated paremters
        for meas_param_key in self.new_source:
            meas_param_inst = self.new_source[meas_param_key]
            if type(meas_param_inst) is MeasParamList:
                type_m = 'dropdown'
                par = ConfigParameter(parent=None,
                                      value=meas_param_inst.options,
                                      unit=meas_param_inst.unit,
                                      parameter_type=type_m,
                                      origin_var=meas_param_inst,
                                      ddvar=meas_param_inst.value)
                self._parameter_source[meas_param_key] = par
            else:
                if type(meas_param_inst) is MeasParamString:
                    if meas_param_inst.extra_type is not None:
                        type_m = meas_param_inst.extra_type
                    else:
                        type_m = 'string'
                elif type(meas_param_inst) is MeasParamInt:
                    type_m = 'number_int'
                elif type(meas_param_inst) is MeasParamFloat:
                    type_m = 'number_float'
                else:
                    type_m = 'bool'
                par = ConfigParameter(parent=None,
                                      value=meas_param_inst.value,
                                      unit=meas_param_inst.unit,
                                      parameter_type=type_m,
                                      origin_var=meas_param_inst)
                self._parameter_source[meas_param_key] = par

    def make_json_able(self):
        """Returns all the parameters of this table as one dict containing all selections. This is in such a format
        pythons built in json function can work with it."""
        if self._parameter_source is None:
            return {}
        data = {}
        for parameter_name in self._parameter_source:
            data[parameter_name] = self._parameter_source[parameter_name].value
        return data

    def serialize(self, file_name):
        """Serializes data in table to json. Takes the filename as parameter and first converts all the data
        of this parameter table to json-able format and then writes this to the provided file, as json"""
        if self._parameter_source is None:
            return False
        data = self.make_json_able()
        file_path = get_configuration_file_path(file_name)
        with open(file_path, 'w') as json_file:
            json_file.write(json.dumps(data))
        return True

    def deserialize(self, file_name):
        """Deserializes the table data from a given file and loads it
        into the cells."""
        file_path = get_configuration_file_path(file_name)
        if self._parameter_source is None or not os.path.isfile(file_path):
            return False
        with open(file_path, 'r') as json_file:
            data = json.loads(json_file.read())
        for parameter_name in data:
            try:
                self._parameter_source[parameter_name].value = data[parameter_name]
            except KeyError:
                self._logger.warning("Unknown key in save file: " + str(parameter_name) + ". Ignoring this parameter.")
        self.__setup__()
        return True

    def check_parameter_validity(self):
        """
        Calls the value on all ConfigParameters. Tk raises a TclError on wrong user inputs. We catch all mistaken inputs
        and raise a ValueError if we got any converion errors.
        """
        if not self.set_from_meas_param:
            return
        error_texts = []
        for k, v in self._parameter_source.items():
            try:
                _ = v.value
            except TclError as e:
                error_texts.append('"' + str(k) + '" got wrong value type: ' + str(e))
        if error_texts:
            raise ValueError("\n".join(error_texts))

    def to_meas_param(self):
        """
        Converts the parameters with values to meas_params
        """
        if self._parameter_source is None:
            return None
        to_ret = {}
        for k, v in self._parameter_source.items():
            if v.parameter_type == 'dropdown':
                to_ret[k] = MeasParamAuto(value=v.options, selected=v.value, unit=v.unit, extra_type=v.parameter_type)
            else:
                to_ret[k] = MeasParamAuto(value=v.value, unit=v.unit, extra_type=v.parameter_type)
        return to_ret

    def writeback_meas_values(self, event=None):
        """
        Gets called on destroy. Writes the values, if coming from meas param, back to the field.
        """
        if self.set_from_meas_param and self._parameter_source is not None:
            if self.store_callback is not None:
                self.store_callback(self.to_meas_param())

    def destroy(self):
        try:
            self.check_parameter_validity()
            self.writeback_meas_values()
        except ValueError as e:
            logging.getLogger().warning(
                "Encountered invalid parameter values! Did not save changed parameters! Full Errors:\n" + str(e))
        CustomFrame.destroy(self)
