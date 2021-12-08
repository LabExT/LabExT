#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
from pathlib import Path
from tkinter import Toplevel, Label, Button, Entry, messagebox

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame


class DriverPathDialog:
    """
    Modify stage driver loading location.
    """

    def __init__(self, parent, title=None, label=None, hint=None):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.

        """
        self.parent = parent
        self.dialog = None
        self.logger = logging.getLogger()

        self._settings_file_path = None
        self._settings_path = None
        self._path_has_changed = False
        self._title = title
        self._label = label
        self._hint = hint
        self._driver_path_entry = None

    def show(self):
        self.dialog = Toplevel(self.parent)
        self.dialog.title(self._title)
        self.dialog.rowconfigure(1, weight=1)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.focus_force()

        path_frame = CustomFrame(self.dialog)
        path_frame.title = self._label
        path_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        path_frame.columnconfigure(0, weight=1)
        path_frame.rowconfigure(0, weight=1)

        Label(
            path_frame,
            text=self._hint).grid(
            row=0,
            column=0,
            padx=5,
            pady=5,
            sticky='nswe')

        self._driver_path_entry = Entry(path_frame)
        self._driver_path_entry.insert(
            0, self.settings_path if self.settings_path else "/path/to/module")
        self._driver_path_entry.grid(
            row=1, column=0, padx=5, pady=5, sticky='nswe')

        Button(
            self.dialog,
            text="Discard and Close",
            command=self.dialog.destroy,
            width=30,
            height=1
        ).grid(row=2, column=0, padx=5, pady=5, sticky='sw')

        Button(
            self.dialog,
            text="Save and Close",
            command=self.save_and_close,
            width=30,
            height=1
        ).grid(row=2, column=0, padx=5, pady=5, sticky='se')

    def save_and_close(self, *_):
        user_given_path = str(self._driver_path_entry.get())
        self.settings_path = str(Path(user_given_path.strip()))

        messagebox.showinfo(
            parent=self.parent,
            title='Success',
            message='Stage Driver path saved. Module will be reloaded.',
        )

        self.dialog.destroy()

    @property
    def settings_path_file(self):
        return self._settings_file_path

    @settings_path_file.setter
    def settings_path_file(self, path):
        self._settings_file_path = get_configuration_file_path(path)

    @property
    def settings_path(self):
        try:
            with open(self.settings_path_file, 'r') as f:
                try:
                    self._settings_path = json.load(f)
                except ValueError:
                    raise ValueError(
                        '{} is not valid JSON.'.format(
                            self.settings_path_file))
        except IOError:
            raise IOError('{} does not exist.'.format(self.settings_path_file))

        return self._settings_path

    @settings_path.setter
    def settings_path(self, path):
        self._path_has_changed = path != self.settings_path

        try:
            with open(self.settings_path_file, 'w') as f:
                json.dump(path, f)
            self._settings_path = path
        except Exception as exce:
            self.logger.error(exce)

    @property
    def path_has_changed(self):
        return self._path_has_changed
