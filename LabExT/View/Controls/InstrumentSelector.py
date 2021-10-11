#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import os
from copy import deepcopy
from tkinter import Label, OptionMenu, StringVar, font, NORMAL, END, _setit

from LabExT.Utils import find_dict_with_ignore, get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame


class InstrumentRole(object):
    """Container class representing a set of instrument descriptor dictionaries."""

    def __init__(self, parent, choices, choice=None, channel=None):
        """
        Container class representing a set of instrument descriptor dictionaries.

        :param parent: Tk parent object
        :param choices: list of instrument descriptor dictionaries
        :param choice: (optional) integer defining the selected instrument
        :param channel: (optional) integer defining the selected channel
        """
        self._root = parent  # keep reference to the ui root
        self._choices = deepcopy(choices)
        self.selected_instr = StringVar(parent,
                                        self.choices_human_readable_desc[0] if choice is None else
                                        self.choices_human_readable_desc[choice])  # selection variable for option menu
        self.selected_channel = StringVar(parent,
                                          str(channel) if channel is not None else
                                          self.choices_available_channels[0])  # selection variable for channel

    def create_and_set(self, instr_dict):
        """
        Sets the selection of the role according to the given dictionary.
        """

        if 'channel' in instr_dict:
            chan = instr_dict['channel']
            if chan is None:
                chan = '-'
        else:
            chan = instr_dict.get('channels', ['-'])[0]

        existing_idx = find_dict_with_ignore(instr_dict, self._choices, ['channel', 'channels'])

        if existing_idx is None:
            self._choices.append(instr_dict)
            self.selected_instr.set(self.choices_human_readable_desc[-1])
        else:
            self.selected_instr.set(self.choices_human_readable_desc[existing_idx])

        self.selected_channel.set(str(chan))

    @property
    def choices_human_readable_desc(self):
        """formatting instrument descriptor dicts for user happens here"""
        inst_desc_human_readable = []
        for inst_idx, inst_desc in enumerate(self._choices):
            # we add the index number to all of the strings to find the index of the selected instrument
            # later in choice()
            inst_desc_human_readable.append(
                str(inst_idx + 1) + ": "
                + str(inst_desc['class'])
                + ' at ' + str(inst_desc['visa'])
            )
        return inst_desc_human_readable

    @property
    def choices_available_channels(self):
        """get a list of the available channels for each instrument"""
        inst_dict = self._raw_choice
        if 'channels' in inst_dict:
            lst = inst_dict['channels']
            if not lst:
                return ['-']
            else:
                return lst  # list of available channels
        elif 'channel' in inst_dict:
            return [inst_dict['channel']]  # only one channel available, make 1 element list
        else:
            return ['-']  # put a dash when you cannot select channels

    @property
    def _raw_choice(self):
        """ returns the raw instrument descriptor as given in instruments.config """
        # get index of selection, conveniently stored before the first : in the string of the dropdown selection
        selected_idx = int(self.selected_instr.get().split(":")[0].strip()) - 1
        return self._choices[selected_idx]

    @property
    def choice(self):
        """ returns the instrument description dictionary for the selected instrument """
        inst_descriptor = deepcopy(self._raw_choice)
        # fill channel key
        inst_descriptor['channel'] = self.choice_channel
        return inst_descriptor

    @property
    def choice_channel(self):
        """ returns the currently chosen channel """
        c = self.selected_channel.get()
        if c == '-':
            return None
        else:
            return int(c)


class InstrumentSelector(CustomFrame):
    """A control that lists a set of device roles that can be assigned
    to a list of devices."""

    def can_execute(self, flag):
        self._can_execute = flag
        self.__setup__()

    @property
    def instrument_source(self):
        """Gets the source list of device roles."""
        return self._instrument_source

    @instrument_source.setter
    def instrument_source(self, source):
        """Sets the source list of device roles."""
        self._instrument_source = source
        self.__setup__()  # redraw the control with the new data

    def __init__(self, parent, *args, **kwargs):

        # call the parent class constructor
        super().__init__(parent, *args, **kwargs)

        # descriptor dictionary as in instruments.config file,
        # but type filtered so only interesting devices are shown
        self._instrument_source = {}

        self._root = parent  # save reference to ui root
        self._can_execute = NORMAL
        self.__setup__()  # draw the control

    def __set_width__(self, stringList, element):
        """Sets the width of the option menus according to the longest
        string."""
        f = font.nametofont(element.cget("font"))  # get font of ui element
        zerowidth = f.measure("0")  # get string width
        w = int(max([f.measure(i)
                     for i in stringList]) / zerowidth)  # calculate max width
        element.config(width=w)  # set width of control

    def __setup__(self):
        # remove all currently rendered controls inside the instrument selector
        self.clear()

        if self.instrument_source is None:
            return

        # create all ui elements
        r = 0
        for instrument_type in self._instrument_source:
            role = self._instrument_source[instrument_type]  # get instrument role
            # add label with role name
            self.add_widget(
                Label(self, text='{}:'.format(instrument_type)),
                row=r, column=0, padx=2, pady=2, sticky='we')
            # add drop down option menu to choose devices
            menu = self.add_widget(
                OptionMenu(self, role.selected_instr, *role.choices_human_readable_desc),
                row=r, column=1, padx=2, pady=2, sticky='we')
            self.__set_width__(role.choices_human_readable_desc, menu)
            menu.config(state=self._can_execute)
            # add label for channel selection
            self.add_widget(
                Label(self, text='channel'),
                row=r, column=2, padx=2, pady=2, sticky='we')
            # add drop down option menu to choose devices
            channel_menu = self.add_widget(
                OptionMenu(self, role.selected_channel, *role.choices_available_channels),
                row=r, column=3, padx=2, pady=2, sticky='we')
            channel_menu.config(state=self._can_execute)
            # register callback to adapt selection of channels
            role.selected_instr.trace('w', self._create_choice_changed_callback(role, channel_menu))
            # make row scalable
            self.rowconfigure(r, weight=1)
            r += 1

        # make columns x-dir stretchable
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)

    def _create_choice_changed_callback(self, role, channel_menu):
        """ creates the callback to change the channel menu options """
        def fn(*args):
            m = channel_menu['menu']
            m.delete(0, END)  # delete all existing entries
            if not role.choices_available_channels:
                # instrument without channels
                role.selected_channel.set("-")
                return
            # instrument with channels, set default selected, and add all channel number to dropdown menu
            role.selected_channel.set(role.choices_available_channels[0])
            for c in role.choices_available_channels:
                m.add_command(label=str(c), command=_setit(role.selected_channel, str(c)))
        return fn

    def serialize(self, file_name):
        """Serializes data in table to json."""
        if self._instrument_source is None:
            return
        settings_path = get_configuration_file_path(file_name)
        if os.path.isfile(settings_path):
            with open(settings_path, 'r') as json_file:
                data = json.loads(json_file.read())
        else:
            data = {}
        for role_name in self._instrument_source:
            data[role_name] = self._instrument_source[role_name].choice
        with open(settings_path, 'w') as json_file:
            json_file.write(json.dumps(data))

    def deserialize(self, file_name):
        """Deserializes the table data from a given file and loads it
        into the cells."""
        settings_path = get_configuration_file_path(file_name)
        if self._instrument_source is None or not os.path.isfile(settings_path):
            return
        with open(settings_path, 'r') as json_file:
            data = json.loads(json_file.read())
        for role_name in data:
            if role_name in self._instrument_source:
                self._instrument_source[role_name].create_and_set(data[role_name])
        self.__setup__()
