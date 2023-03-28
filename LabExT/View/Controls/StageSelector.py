#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Label, OptionMenu, StringVar, font, NORMAL

from LabExT.View.Controls.CustomFrame import CustomFrame


class StageRole(object):
    """Container class representing a set of stage descriptor dictionaries."""

    def __init__(self, parent, choices, choice=None, channel=None):
        """
        Container class representing a set of instrument descriptor dictionaries.

        :param parent: Tk parent object
        :param choices: list of instrument descriptor dictionaries
        :param choice: (optional) integer defining the selected instrument
        :param channel: (optional) integer defining the selected channel
        """
        self._root = parent  # keep reference to the ui root
        self._choices = choices
        self.selected_stage = StringVar(parent,
                                        self.choices_human_readable_desc[0] if choice is None else
                                        self.choices_human_readable_desc[choice])  # selection variable for option menu

    def create_and_set(self, stage_dict):
        """
        Sets the selection of the role according to the given dictionary.
        """
        stage_cls = stage_dict.get("class")
        stage_id = stage_dict.get("identifier")
        calibration = next((
            c for c in self._choices
            if c.stage.identifier == stage_id and c.stage.__class__.__name__ == stage_cls
        ), None)

        try:
            stage_idx = self._choices.index(calibration)
        except Exception:
            stage_idx = 0

        self.selected_stage.set(self.choices_human_readable_desc[stage_idx])

    @property
    def choices_human_readable_desc(self):
        """formatting instrument descriptor dicts for user happens here"""
        stage_desc_human_readable = []
        for idx, calibration in enumerate(self._choices):
            # we add the index number to all of the strings to find the index of the selected instrument
            # later in choice()
            stage_desc_human_readable.append(
                str(idx + 1) + ": "
                + str(calibration))
        return stage_desc_human_readable

    @property
    def choice(self):
        """ returns the raw instrument descriptor as given in instruments.config """
        # get index of selection, conveniently stored before the first : in the
        # string of the dropdown selection
        selected_idx = int(self.selected_stage.get().split(":")[0].strip()) - 1
        return self._choices[selected_idx]


class StageSelector(CustomFrame):
    """A control that lists a set of stage roles that can be assigned
    to a list of stages."""

    def can_execute(self, flag):
        self._can_execute = flag
        self.__setup__()

    @property
    def stages_source(self):
        """Gets the source list of stages roles."""
        return self._stages_source

    @stages_source.setter
    def stages_source(self, source):
        """Sets the source list of stag roles."""
        self._stages_source = source
        self.__setup__()  # redraw the control with the new data

    def __init__(self, parent, *args, **kwargs):

        # call the parent class constructor
        super().__init__(parent, *args, **kwargs)

        # descriptor dictionary as in instruments.config file,
        # but type filtered so only interesting devices are shown
        self._stages_source = {}

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

        if self.stages_source is None:
            return

        # create all ui elements
        r = 0
        for stage_type, role in self._stages_source.items():
            # add label with role name
            self.add_widget(
                Label(self, text='{}:'.format(stage_type)),
                row=r, column=0, padx=2, pady=2, sticky='we')
            # add drop down option menu to choose devices
            menu = self.add_widget(
                OptionMenu(
                    self,
                    role.selected_stage,
                    *role.choices_human_readable_desc),
                row=r,
                column=1,
                padx=2,
                pady=2,
                sticky='we')
            self.__set_width__(role.choices_human_readable_desc, menu)
            menu.config(state=self._can_execute)
            # register callback to adapt selection of channels
            role.selected_stage.trace(
                'w', self._create_choice_changed_callback(role))
            # make row scalable
            self.rowconfigure(r, weight=1)
            r += 1

        # make columns x-dir stretchable
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
