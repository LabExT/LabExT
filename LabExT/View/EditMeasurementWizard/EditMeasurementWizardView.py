#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Toplevel, Label

from LabExT.View.Controls.ScrollableFrame import ScrollableFrame


class WizardWindow(Toplevel):
    def __init__(self, parent):
        Toplevel.__init__(self, parent)
        self.title("New ToDo Wizard")
        screen_height = parent.winfo_screenheight()
        self.geometry("{:d}x{:d}+{:d}+{:d}".format(1000, screen_height - 200, 100, 50))
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.focus_force()


class WizardScrollableFrame(ScrollableFrame):
    def __init__(self, parent):
        ScrollableFrame.__init__(self, parent)
        self.grid(row=1, column=0, sticky="nswe")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bind("<Enter>", self._bound_to_mousewheel)
        self.bind("<Leave>", self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def unbound_mouse_wheel(self):
        self._unbound_to_mousewheel(None)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class EditMeasurementWizardView:
    """
    Creates a new or edits an existing measurement.
    """

    default_text = "..."

    def __init__(self, model, controller, parent, experiment_manager):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self.model = model
        self.controller = controller

        self.root = parent
        self._experiment_manager = experiment_manager

        self._experiment = self._experiment_manager.exp

        self.logger = logging.getLogger()
        self.logger.debug("Initializing EditMeasurementWizard.")

        # reference to toplevel GUI
        self.wizard_window = None
        self.scrollable_frame = None

        # internally used variables
        self._wizard_frame = None

    def setup_main_window(self):
        """
        Setup to toplevel GUI
        """
        # create wizard window, resizeable in columns, fixed with scrollbar in rows
        self.wizard_window = WizardWindow(self.root)

        self.wizard_window.bind("<F1>", self._experiment_manager.show_documentation)

        # place hint
        hint = (
            "Keyboard Shortcuts: Continue to next stage with Return. Revert to last stage with Escape."
            " Press F1 for help."
        )
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky="nswe")

        # place scrolling frame into top level window
        self.scrollable_frame = WizardScrollableFrame(self.wizard_window)

        # get the frame for the actual content
        self._wizard_frame = self.scrollable_frame.get_content_frame()
        self._wizard_frame.columnconfigure(0, weight=1)

    def register_keyboard_shortcut(self, keys: str, action) -> None:
        """Register keyboard shortcut on window level."""
        self.wizard_window.bind(keys, action)
