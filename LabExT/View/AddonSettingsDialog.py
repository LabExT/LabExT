#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from os.path import basename
from pathlib import Path
from tkinter import Toplevel, Label, Button, END
from tkinter.messagebox import showinfo, showerror
from tkinter.scrolledtext import ScrolledText

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable


class AddonSettingsDialog:
    """
    Modify plugin loading settings with this dialog.
    """

    def __init__(self, parent, experiment_manager):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.

        """
        self._root = parent
        self._exp_mgr = experiment_manager
        self._exp = self._exp_mgr.exp
        self.logger = logging.getLogger()

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
        self.wizard_window.title("Addon Settings")
        self.wizard_window.geometry('%dx%d+%d+%d' % (900, 900, 300, 300))
        self.wizard_window.rowconfigure(3, weight=1)
        self.wizard_window.rowconfigure(4, weight=1)
        self.wizard_window.rowconfigure(5, weight=1)
        self.wizard_window.columnconfigure(0, weight=1)
        self.wizard_window.focus_force()

        #
        # top level hint
        #
        hint = "Addons in LabExT are additional Instrument or Measurement sub-classes loaded from anywhere on" \
               " your harddrive."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        #
        # addon path mutliline text field
        #
        addon_paths_frame = CustomFrame(self.wizard_window)
        addon_paths_frame.title = " addon paths "
        addon_paths_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        addon_paths_frame.columnconfigure(0, weight=1)
        addon_paths_frame.rowconfigure(0, weight=1)
        addon_paths_frame.rowconfigure(1, weight=1)

        # place hint
        hint = "Add all paths which you want LabExT to search for addon classes here. One path per line.\n" \
               "Your addon classes must be in a package below the given path, i.e. in a sub-folder" \
               " with an __init__.py file.\n" \
               "You must restart LabExT for any changes to take effect."
        top_hint = Label(addon_paths_frame, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # add paths loaded into experiment manager
        self.addon_path_text_area = ScrolledText(addon_paths_frame, height=5, width=100, wrap='none')
        self.addon_path_text_area.insert("1.0", self._get_addon_search_paths_string())
        self.addon_path_text_area.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')

        #
        # explanation on tables below
        #

        # place hint
        hint = "The following two tables show the names and module path of all loaded Measurement and Instrument " \
               "sub-classes."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=2, column=0, padx=5, pady=5, sticky='nswe')

        #
        # table with paths to all loaded measurements
        #
        loaded_meas_frame = CustomFrame(self.wizard_window)
        loaded_meas_frame.title = " currently loaded Measurement classes "
        loaded_meas_frame.grid(row=3, column=0, padx=5, pady=5, sticky='nswe')
        loaded_meas_frame.columnconfigure(0, weight=1)
        loaded_meas_frame.rowconfigure(0, weight=1)

        CustomTable(parent=loaded_meas_frame,
                    columns=('Measurement class', 'imported from'),
                    rows=self._get_loaded_measurements_and_paths(),
                    selectmode='none')  # custom table inserts itself into the parent frame

        #
        # table with paths to all loaded instruments
        #
        loaded_instr_frame = CustomFrame(self.wizard_window)
        loaded_instr_frame.title = " currently loaded Instrument classes "
        loaded_instr_frame.grid(row=4, column=0, padx=5, pady=5, sticky='nswe')
        loaded_instr_frame.columnconfigure(0, weight=1)
        loaded_instr_frame.rowconfigure(0, weight=1)

        CustomTable(parent=loaded_instr_frame,
                    columns=('Instrument class', 'imported from'),
                    rows=self._get_loaded_instruments_and_paths(),
                    selectmode='none')  # custom table inserts itself into the parent frame

        #
        # table with paths to all loaded live viewer cards
        #
        loaded_lvcards_frame = CustomFrame(self.wizard_window)
        loaded_lvcards_frame.title = " currently loaded CardFrame (live viewer cards) classes "
        loaded_lvcards_frame.grid(row=5, column=0, padx=5, pady=5, sticky='nswe')
        loaded_lvcards_frame.columnconfigure(0, weight=1)
        loaded_lvcards_frame.rowconfigure(0, weight=1)

        CustomTable(parent=loaded_lvcards_frame,
                    columns=('CardFrame class', 'instrument type', 'imported from'),
                    rows=self._get_loaded_lvcards_and_paths(),
                    selectmode='none')  # custom table inserts itself into the parent frame

        #
        # bottom row buttons
        #
        quit_button = Button(self.wizard_window,
                             text="Discard and Close",
                             command=self.close_dialog,
                             width=30,
                             height=1)
        quit_button.grid(row=6, column=0, padx=5, pady=5, sticky='sw')
        save_button = Button(self.wizard_window,
                             text="Save and Close",
                             command=self.save_and_close,
                             width=30,
                             height=1)
        save_button.grid(row=6, column=0, padx=5, pady=5, sticky='se')

    def _get_addon_search_paths_string(self):
        return "\n".join(self._exp_mgr.addon_settings['addon_search_directories'])

    def _get_loaded_measurements_and_paths(self):
        ret_list = []
        for k, v in self._exp.measurements_classes.items():
            ret_list.append((k, ''))
            for vi in v.PluginLoader_module_path:
                ret_list.append(('    ->', vi))
        return ret_list

    def _get_loaded_instruments_and_paths(self):
        ret_list = []
        for k, v in self._exp_mgr.instrument_api.instruments.items():
            ret_list.append((k, ''))
            for vi in v.PluginLoader_module_path:
                ret_list.append(('    ->', vi))
        return ret_list

    def _get_loaded_lvcards_and_paths(self):
        ret_list = []
        for k, v in self._exp_mgr.live_viewer_cards.items():
            ret_list.append((v.__name__, k, ''))
            for vi in v.PluginLoader_module_path:
                ret_list.append(('    ->', '', vi))
        return ret_list

    def save_and_close(self, *args):
        # here we get the user entered text and do some entry cleaning on them
        user_given_paths = str(self.addon_path_text_area.get("1.0", END))
        stripped_paths = [p.strip() for p in  # delete extra whitespace
                          user_given_paths.splitlines(keepends=False)]  # split user text into lines
        cleaned_paths = [Path(p) for p in stripped_paths if p]  # filter out empty lines and make to path objects
        for cp in cleaned_paths:
            # a dot is not allowed in the last level directory, otherwise Python will not be able to import it
            if '.' in basename(cp):
                showerror('period not allowed',
                          'The last directory name of your path can not contain a period due to'
                          ' the way the addon import system works! Please rename or remove the'
                          ' path: ' + str(cp),
                          parent=self.wizard_window)
                return
        cleaned_path_strs = [str(cp) for cp in cleaned_paths]

        # finally we save the changed addon paths back to the experiment manager and trigger saving to file
        self._exp_mgr.addon_settings['addon_search_directories'] = list(set(cleaned_path_strs))  # uniquify
        self._exp_mgr.save_addon_settings()

        # as addons are only loaded on LabExT startup, user needs to restart LabExT for new addons to load
        showinfo('restart required',
                 'Addon paths saved. Please restart LabExT to apply changes.',
                 parent=self.wizard_window)

        self.close_dialog()

    def close_dialog(self, *args):
        self.wizard_window.destroy()
