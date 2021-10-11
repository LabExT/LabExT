#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
from pathlib import Path
from tkinter import Toplevel, Label, Button, Entry
from tkinter.messagebox import showinfo

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame


class StageDriverSettingsDialog:
    """
    Modify stage driver loading location.
    """

    def __init__(self, parent):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.

        """
        self._root = parent
        self.logger = logging.getLogger()

        self.settings_file_path = get_configuration_file_path('mcsc_module_path.txt')
        self.stage_driver_path = ""
        self.get_stage_driver_module_path()

        # draw GUI
        self.__setup__()

    def __setup__(self):
        """
        Setup to toplevel GUI
        """
        #
        # top level window
        #
        self.wizard_window = Toplevel(self._root)
        self.wizard_window.title("Stage Driver Settings")
        # self.wizard_window.geometry('%dx%d+%d+%d' % (900, 400, 300, 300))
        self.wizard_window.rowconfigure(1, weight=1)
        self.wizard_window.columnconfigure(0, weight=1)
        self.wizard_window.focus_force()

        #
        # top level hint
        #
        hint = "Here you can configure the paths to the externally provided driver libraries for motorized stages.\n" \
               "You must restart LabExT for any changes to take effect."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        #
        # addon path mutliline text field
        #
        addon_paths_frame = CustomFrame(self.wizard_window)
        addon_paths_frame.title = "  SmarAct MCSControl driver module path  "
        addon_paths_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        addon_paths_frame.columnconfigure(0, weight=1)
        addon_paths_frame.rowconfigure(0, weight=1)

        # place hint
        hint = "Specify the directory where the module MCSControl_PythonWrapper is found.\nThis is external software," \
               "provided by SmarAct GmbH and is available from them. See https://smaract.com."
        top_hint = Label(addon_paths_frame, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # add paths loaded into experiment manager
        self.driver_path_entry = Entry(addon_paths_frame)
        self.driver_path_entry.insert(0, self.get_stage_driver_module_path())
        self.driver_path_entry.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')

        #
        # bottom row buttons
        #
        quit_button = Button(self.wizard_window,
                             text="Discard and Close",
                             command=self.close_dialog,
                             width=30,
                             height=1)
        quit_button.grid(row=2, column=0, padx=5, pady=5, sticky='sw')
        save_button = Button(self.wizard_window,
                             text="Save and Close",
                             command=self.save_and_close,
                             width=30,
                             height=1)
        save_button.grid(row=2, column=0, padx=5, pady=5, sticky='se')

    def get_stage_driver_module_path(self):
        try:
            with open(self.settings_file_path, 'r') as fp:
                module_path = json.load(fp)
        except FileNotFoundError:
            module_path = 'fill me...'
        self.stage_driver_path = module_path
        return module_path

    def save_and_close(self, *args):
        # here we get the user entered text and do some entry cleaning on them
        user_given_path = str(self.driver_path_entry.get())
        cleaned_path = str(Path(user_given_path.strip()))  # this formats the path properly
        # save the cleaned path here and to file
        self.stage_driver_path = cleaned_path
        with open(self.settings_file_path, 'w') as fp:
            json.dump(cleaned_path, fp)

        # as addons are only loaded on LabExT startup, user needs to restart LabExT for new addons to load
        showinfo('restart required',
                 'Stage Driver path saved. Please restart LabExT to apply changes.',
                 parent=self.wizard_window)

        self.close_dialog()

    def close_dialog(self, *args):
        self.wizard_window.destroy()
