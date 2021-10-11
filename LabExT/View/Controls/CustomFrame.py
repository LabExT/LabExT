#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from tkinter import LabelFrame, NORMAL, DISABLED, BooleanVar, Frame


class CustomFrame(LabelFrame):
    """Extended version of the tkinter frame. Provides some useful,
    general functionality.

    Attributes
    ----------
    enabled : bool
        Whether or not the child is enabled.
    title : str
        Title of the frame.
    """

    _title = ''

    @property
    def title(self):
        """Gets the title of the frame"""
        return self._title

    @title.setter
    def title(self, txt):
        """Sets the title of the frame"""
        self.config(text=txt)
        self._title = txt

    _enabled = True
    _enabled_var = None

    @property
    def enabled(self):
        """Gets if this control is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, v):
        """Sets if this control is enabled."""

        if type(v) is BooleanVar:
            self._enabled_var = v
            self._enabled_var.trace('w', self.__enabled_var_changed__)
            v = v.get()

        self._enabled = v
        self._recursive_state_change(self._children, self._enabled)

    def _recursive_state_change(self, children, enable_flag):
        for child in children:
            if child is not None:
                if isinstance(child, Frame):
                    self._recursive_state_change(child.winfo_children(), enable_flag)
                elif isinstance(child, CustomFrame):
                    child.enabled = enable_flag
                else:
                    child.config(state=(NORMAL if enable_flag else DISABLED))

    def __enabled_var_changed__(self, *args):
        self.enabled = self._enabled_var.get()

    def __init__(self, parent, *args, **kwargs):
        """Constructor

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        *args
            Arguments forwarded to superclass.
        **kwargs
            Names forwarded to superclass
        """
        super().__init__(parent, *args, **kwargs)
        self._root = parent  # keep reference to ui parent

        self._logger = logging.getLogger()

        # collection of all child controls that were added to the frame
        self._children = []
        self.title = self._title  # set the title initially

    def clear(self):
        """Remove all child ui controls from the frame."""
        for child in self._children:
            child.grid_forget()
        self._children = []

    def add_widget(self, widget, **kwargs):
        """Add child ui control to the frame and place it in the grid
        structure of the frame."""
        widget.grid(**kwargs)
        self._children.append(widget)
        return widget
