#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from os.path import basename
from pathlib import Path
from tkinter import Toplevel, Label, Text, Button, Frame, Entry, StringVar, filedialog, END, TOP, X
from tkinter.ttk import Notebook, Treeview
from tkinter.messagebox import showinfo, showerror, askyesno

from LabExT.View.Controls.CustomFrame import CustomFrame

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

        self.paths = list(self._exp_mgr.addon_settings['addon_search_directories'])

        #
        # top level window
        #
        self.wizard_window = Toplevel(self._root)
        self.wizard_window.title("Addon Settings")
        self.wizard_window.focus_force()

        self.wizard_window.columnconfigure(0, weight=1)
        self.wizard_window.rowconfigure(3, weight=1)

        #
        # top level hint
        #
        hint = "Addons in LabExT are additional Instrument, Measurement or Stage sub-classes loaded from anywhere on" \
               " your harddrive."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        #
        # addon path mutliline text field
        #
        addon_path_frame = CustomFrame(self.wizard_window)
        addon_path_frame.title = " addon paths "
        addon_path_frame.columnconfigure(1, weight=1)
        addon_path_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')

        # place hint
        hint = "Add all paths which you want LabExT to search for addon classes here. One path per line.\n" \
               "Your addon classes must be in a package below the given path, i.e. in a sub-folder" \
               " with an __init__.py file.\n" \
               "You must restart LabExT for any changes to take effect."
        top_hint = Label(addon_path_frame, text=hint)
        top_hint.grid(column=0, padx=5, pady=5, sticky='nswe', columnspan=4)

        #
        # list of addon paths
        #
        self.paths_frame = Frame(addon_path_frame)
        self.paths_frame.grid(column=0, columnspan=4, sticky='nswe')
        self.paths_frame.columnconfigure(0, weight=1)

        self._build_path_list()

        #
        # path entry
        #
        user_input_path = StringVar(self._root)
        Label(addon_path_frame, text="path:").grid(row=2, column=0, padx=5, sticky='w')
        Entry(addon_path_frame, textvariable=user_input_path).grid(row=2, column=1, padx=5, sticky='we')
        Button(addon_path_frame, text='Add Path', command=lambda: self.add_addon_path(user_input_path.get())).grid(row=2, column=2, padx=5, sticky='e')
        Button(addon_path_frame, text='Browse', command=lambda: self.add_addon_path(filedialog.askdirectory())).grid(row=2, column=3, padx=5, sticky='e')

        nb = Notebook(self.wizard_window)
        
        loaded_addons = {
            "Measurements": self._exp.measurements_classes,
            "Instruments": self._exp_mgr.instrument_api.instruments,
            "CardFrames": self._exp_mgr.live_viewer_cards,
            "Stages": self._exp_mgr.mover.stage_classes,
            "Chip Sources": self._exp_mgr.chip_source_api.chip_sources,
            "Export Formats": self._exp_mgr.export_format_api.export_formats,
        }

        for title, data in loaded_addons.items():
            frame = CustomFrame(nb)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            nb.add(frame, text=title)

            treeview = Treeview(frame)

            for title, paths in data.items():
                header = treeview.insert("", END, text=title)

                for path in paths.PluginLoader_module_path:
                    treeview.insert(header, END, text=path)

            treeview.grid(row=0, column=0, padx=10, pady=(10, 5), sticky='nswe')

        nb.grid(row=3, sticky='nswe')

        #
        # bottom row buttons
        #
        quit_button = Button(self.wizard_window,
                             text="Discard and Close",
                             command=self.close_dialog,
                             width=30,
                             height=1)
        quit_button.grid(row=8, column=0, padx=5, pady=5, sticky='sw')
        save_button = Button(self.wizard_window,
                             text="Save and Close",
                             command=self.save_and_close,
                             width=30,
                             height=1)
        save_button.grid(row=8, column=0, padx=5, pady=5, sticky='se')
    
    def _build_path_list(self):
        """ Rebuild the list of paths in the GUI. """
        for widget in self.paths_frame.winfo_children():
            widget.destroy()

        for i, addon_path in enumerate(self.paths):
            Label(self.paths_frame, text=addon_path).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            Button(self.paths_frame, text="Remove", command=lambda: self.remove_addon_path(addon_path)).grid(row=i, column=1, padx=5, pady=5, sticky='e')

    def add_addon_path(self, path_str):
        if not path_str:
            return
        
        path = Path(path_str.strip())

        if not path:
            return
        
        if '.' in basename(path):
            showerror('period not allowed',
                    'The last directory name of your path can not contain a period due to'
                    ' the way the addon import system works! Please rename or remove the'
                    ' path: ' + path_str,
                    parent=self.wizard_window)
            return
        
        if str(path) not in self.paths:
            self.paths.append(str(path))

        self._build_path_list()

    def remove_addon_path(self, path_str):
        if not askyesno('remove path', 'Do you really want to remove the path: ' + path_str + '?', parent=self.wizard_window):
            return
        
        if path_str in self.paths:
            self.paths.remove(path_str)

        self._build_path_list()


    def save_and_close(self, *args):
        if self._exp_mgr.addon_settings['addon_search_directories'] == self.paths:
            self.close_dialog()
            return
        
        self._exp_mgr.addon_settings['addon_search_directories'] = self.paths
        self._exp_mgr.save_addon_settings()

        if askyesno('restart required',
                 'Addon paths saved. Please restart LabExT to apply changes. Would you like to restart now?',
                 parent=self.wizard_window):
            
            # import here to avoid circular import
            from LabExT.View.MenuListener import MListener
            MListener.client_restart()

        self.close_dialog()

    def close_dialog(self, *args):
        self.wizard_window.destroy()