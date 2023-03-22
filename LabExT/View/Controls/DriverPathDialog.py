#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import os
import logging

from pathlib import Path
from tkinter import Toplevel, Label, Button, Entry, messagebox

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame


class DriverPathDialog(Toplevel):
    """
    Dialog to change a driver path to be saved in a specified file.
    """

    def __init__(
        self,
        parent,
        settings_file_path,
        title=None,
        label=None,
        hint=None
    ) -> None:
        """
        Constructor.

        settings_file_path must be relative to the LabExT settings folder.
        """
        Toplevel.__init__(self, parent)
        self.title(title)

        self.logger = logging.getLogger()

        self._label = label
        self._hint = hint
        self._settings_file_path = get_configuration_file_path(
            settings_file_path)
        self._driver_path = None
        self._path_has_changed = False

        self._driver_path_entry = None

        self.__setup__()

    def __setup__(self):
        """
        Builds Dialog.
        """
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        path_frame = CustomFrame(self)
        path_frame.title = self._label
        path_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        path_frame.columnconfigure(0, weight=1)
        path_frame.rowconfigure(0, weight=1)

        Label(
            path_frame,
            text=self._hint
        ).grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        self._driver_path_entry = Entry(path_frame)
        self._driver_path_entry.insert(0, self.driver_path)
        self._driver_path_entry.grid(
            row=1, column=0, padx=5, pady=5, sticky='nswe')

        self._cancel_button = Button(
            self,
            text="Discard and Close",
            command=self.destroy,
            width=30,
            height=1
        )
        self._cancel_button.grid(row=2, column=0, padx=5, pady=5, sticky='sw')

        self._save_button = Button(
            self,
            text="Save and Close",
            command=self._save,
            width=30,
            height=1
        )
        self._save_button.grid(row=2, column=0, padx=5, pady=5, sticky='se')

    def _save(self) -> None:
        """
        Callback, when user wants to save the Path.
        """
        if not self._driver_path_entry:
            return

        user_given_path = str(self._driver_path_entry.get())
        self.driver_path = str(Path(user_given_path.strip()))

        self.destroy()

    @property
    def driver_path(self) -> str:
        """
        Returns current driver path.

        If None, the path is read from the settings file.
        """
        if not self._driver_path:
            self._driver_path = self._get_driver_path_from_file(
                default="/path/to/module")

        return self._driver_path

    @property
    def path_has_changed(self) -> bool:
        """
        Returns True, if driver path has changed and False otherwise
        """
        return self._path_has_changed

    @driver_path.setter
    def driver_path(self, path) -> None:
        """
        Saves the given driver path in the settings file if it is not equal to the current path.
        """
        if path == self.driver_path:
            return

        try:
            with open(self._settings_file_path, 'w') as f:
                json.dump(path, f)
            self._path_has_changed = True
            self._driver_path = path
        except Exception as e:
            messagebox.showerror(
                "Error", "Could not save driver path: {}".format(e))

    def _get_driver_path_from_file(
        self,
        default: str = None
    ) -> str:
        """
        Reads the current driver path from settings path.

        If file does not exists or is not readable,
        the default value will be returned.
        """
        if not os.path.exists(self._settings_file_path):
            return default

        try:
            with open(self._settings_file_path, 'r') as f:
                try:
                    return json.load(f)
                except ValueError as err:
                    self.logger.error(
                        f"Failed to load JSON from {self._settings_file_path}: {err}")
                    return default

        except IOError as err:
            self.logger.error(
                f"Failed to load driver settings file {self._settings_file_path}: {err}")
            return default
