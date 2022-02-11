#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Button, NORMAL, DISABLED, StringVar

from LabExT.View.Controls.CustomFrame import CustomFrame


class ControlCommand(object):
    """Data handle for a button.

    Attributes
    ----------
    can_execute : bool
        If the button can be clicked on.
    command : func
        Function to be called when button is clicked on.
    name : str
        Text on the button
    """

    _can_execute = True

    @property
    def can_execute(self):
        return self._can_execute

    @can_execute.setter
    def can_execute(self, b):
        self._can_execute = b
        if not self._button_handle is None:
            self._button_handle.config(
                state=NORMAL if self._can_execute else DISABLED)

    _button_handle = None

    @property
    def button_handle(self):
        return self._button_handle

    @button_handle.setter
    def button_handle(self, handle):
        self._button_handle = handle
        self.can_execute = self._can_execute

    def __init__(self, command, parent, name='', can_execute=True):
        """Constructor.

        Parameters
        ----------
        command : func
            Function to be called when button is clicked.
        parent : Tk
            Tkinter parent window.
        name : str, optional
            Text of button.
        can_execute : bool, optional
            Whether or not the button can be clicked.
        """
        self.name = StringVar(parent)
        self.name.set(name)
        self.command = command
        self._can_execute = can_execute


class ControlPanel(CustomFrame):
    """Frame holding buttons and handling appearance.
    """

    _command_source = None

    @property
    def command_source(self):
        return self._command_source

    @command_source.setter
    def command_source(self, source):
        self._command_source = source
        self.__setup__()

    _button_width = None

    @property
    def button_width(self):
        return self._button_width

    @button_width.setter
    def button_width(self, width):
        self._button_width = width
        self.__setup__()

    def __init__(self, parent, *args, **kwargs):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        *args
            Arguments, forwarded to superclass
        **kwargs
            Names, forwarded to superclass
        """
        super().__init__(parent, *args, **kwargs)
        self._root = parent
        self.__setup__()

    def __setup__(self):
        """Clears current frame and adds all widgets back to it.
        """
        self.clear()

        if self._command_source is None:
            return

        for cidx, command in enumerate(self._command_source):

            # only x-pad first and last button
            if cidx == 0:
                padx = (5, 0)
            elif cidx == len(self._command_source) - 1:
                padx = (0, 5)
            else:
                padx = (0, 0)

            command.button_handle = self.add_widget(
                Button(
                    self, textvariable=command.name, command=command.command),
                column=cidx,
                row=0, sticky='nswe', padx=padx, pady=5)

            if self._button_width is not None:
                command.button_handle.config(width=self._button_width)
                command.button_handle.rowconfigure(0, weight=1)
                command.button_handle.columnconfigure(cidx, weight=1)
