#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Label, Toplevel, Frame, Button, FLAT, TOP, RIGHT, LEFT, X, Y, BOTH, NORMAL, DISABLED
from typing import Type


from LabExT.View.Controls.CustomFrame import CustomFrame


class Step:
    """
    Implementation of one Wizard Step.
    """

    ACTIVE_LABEL_COLOR = "#000000"
    INACTIVE_LABEL_COLOR = "#808080"

    def __init__(
            self,
            wizard,
            builder,
            title=None,
            on_next=None,
            on_previous=None,
            on_reload=None,
            previous_step_enabled=True,
            next_step_enabled=True,
            finish_step_enabled=False) -> None:
        """
        Constructor for a Wizard Step.
        """
        self.wizard: Type[Wizard] = wizard

        self.builder = builder

        self.on_next = on_next
        self.on_previous = on_previous
        self.on_reload = on_reload

        self.previous_step: Type[Step] = None
        self.next_step: Type[Step] = None

        self.previous_step_enabled = previous_step_enabled
        self.next_step_enabled = next_step_enabled
        self.finish_step_enabled = finish_step_enabled

        if self.wizard._sidebar_frame and title:
            self._sidebar_label = Label(
                self.wizard._sidebar_frame,
                anchor="w",
                text=title,
                foreground=self.INACTIVE_LABEL_COLOR)
            self._sidebar_label.pack(side=TOP, fill=X, padx=10, pady=5)
        else:
            self._sidebar_label = None

    def activate_sidebar_label(self):
        """
        Changes sidebar label to active color
        """
        if not self._sidebar_label:
            return

        self._sidebar_label.config(foreground=self.ACTIVE_LABEL_COLOR)

    def deactivate_sidebar_label(self):
        """
        Changes sidebar label to inactive color
        """
        if not self._sidebar_label:
            return

        self._sidebar_label.config(foreground=self.INACTIVE_LABEL_COLOR)

    @property
    def previous_step_available(self):
        """
        Returns a decision, if a previous step is available.

        A previous step is available if the current step is defined and enabled.
        """
        return self.previous_step is not None and self.previous_step_enabled

    @property
    def next_step_available(self):
        """
        Returns a decision, if a next step is available.

        A next step is available if the current step is defined and enabled.
        """
        return self.next_step is not None and self.next_step_enabled

    def on_next_callback(self):
        """
        Performs on_next callback.

        Returns True if callback not defined or callback succeeds, False otherwise.
        """
        if not self.on_next:
            return True

        return self.on_next()

    def on_previous_callback(self):
        """
        Performs on_update callback.

        Returns True if callback not defined or callback succeeds, False otherwise.
        """
        if not self.on_previous:
            return True

        return self.on_previous()

    def on_reload_callback(self):
        """
        Performs on_reload callback.

        Returns True if callback not defined or callback succeeds, False otherwise.
        """
        if not self.on_reload:
            return

        self.on_reload()


class Wizard(Toplevel):
    """
    Implementation of a Wizard Widget.
    """
    SIDEBAR_WIDTH = 200

    ERROR_COLOR = "#FF3333"

    def __init__(
            self,
            parent,
            width=640,
            height=480,
            on_cancel=None,
            on_finish=None,
            with_sidebar=True,
            with_error=True,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish") -> None:
        Toplevel.__init__(
            self,
            parent,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
            relief=FLAT)

        self.parent = parent

        self.logger = logging.getLogger()

        self._current_step: Type[Step] = None

        self.on_cancel = on_cancel
        self.on_finish = on_finish

        # Build Wizard
        if with_sidebar:
            self._sidebar_frame = CustomFrame(self, width=self.SIDEBAR_WIDTH)
            self._sidebar_frame.pack(side=LEFT, fill=BOTH, anchor='nw')
        else:
            self._sidebar_frame = None

        self._content_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._content_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        self._main_frame = Frame(
            self._content_frame,
            borderwidth=0,
            relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True)

        if with_error:
            self._error_frame = Frame(
                self._content_frame, borderwidth=0, relief=FLAT)
            self._error_frame.pack(side=TOP, fill=X, padx=10, expand=0)
            self._error_label = Label(
                self._error_frame,
                text=None,
                foreground=self.ERROR_COLOR,
                anchor="w")
            self._error_label.pack(side=LEFT, fill=X)
        else:
            self._error_label = None

        self._control_frame = Frame(
            self._content_frame,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        self._control_frame.pack(side=TOP, fill=X, expand=0)

        self._cancel_button = Button(
            self._control_frame,
            text=cancel_button_label,
            width=10,
            command=self._cancel)
        self._cancel_button.pack(
            side=RIGHT, fill=Y, expand=0, padx=(
                5, 10), pady=10)

        self._finish_button = Button(
            self._control_frame,
            text=finish_button_label,
            width=10,
            command=self._finish)
        self._finish_button.pack(
            side=RIGHT, fill=Y, expand=0, padx=(
                20, 5), pady=10)

        self._next_button = Button(
            self._control_frame,
            text=next_button_label,
            width=10,
            command=self._next_step)
        self._next_button.pack(side=RIGHT, fill=Y, expand=0, padx=5, pady=10)

        self._previous_button = Button(
            self._control_frame,
            text=previous_button_label,
            width=10,
            command=self._previous_step)
        self._previous_button.pack(
            side=RIGHT, fill=Y, expand=0, padx=5, pady=10)

        self.wm_geometry("{width:d}x{height:d}".format(
            width=width + self.SIDEBAR_WIDTH if with_sidebar else width,
            height=height))
        self.protocol('WM_DELETE_WINDOW', self._cancel)

    @property
    def current_step(self) -> Type[Step]:
        """
        Returns the current step object.
        """
        return self._current_step

    @current_step.setter
    def current_step(self, step: Type[Step]) -> None:
        """
        Sets the current step, updates the sidebar and resets error.

        Reloads Wizard afterwards.
        """
        if self._current_step:
            self._current_step.deactivate_sidebar_label()

        if step:
            step.activate_sidebar_label()

        self.set_error("")

        self._current_step = step
        self.__reload__()

    def __reload__(self):
        """
        Updates the Wizard contents.
        """
        self.current_step.on_reload_callback()

        # Update Button States
        self._previous_button.config(
            state=NORMAL if self.current_step.previous_step_available else DISABLED)
        self._next_button.config(
            state=NORMAL if self.current_step.next_step_available else DISABLED)
        self._finish_button.config(
            state=NORMAL if self.current_step.finish_step_enabled else DISABLED)

        # Remove all widgets in main frame
        for child in self._main_frame.winfo_children():
            child.forget()

        # Create step frame and build it by calling step builder
        step_frame = CustomFrame(self._main_frame)
        self.current_step.builder(step_frame)
        step_frame.pack(side=LEFT, fill=BOTH, padx=10, pady=(10, 2), expand=1)

        self.update_idletasks()

    def add_step(self, *args, **kwargs) -> Type[Step]:
        """
        Creates and returns a new wizard step.
        """
        return Step(self, *args, **kwargs)

    def set_error(self, message):
        if not self._error_label:
            return

        self._error_label.config(text=message)

    def _finish(self):
        """
        Gets called, when user clicks finish button
        """
        if not self.current_step.finish_step_enabled:
            return

        if self._on_finish_callback():
            self.destroy()

    def _cancel(self):
        """
        Gets called, when user clicks cancel button
        """
        if self._on_cancel_callback():
            self.destroy()

    def _previous_step(self):
        """
        Gets called, when user clicks previous step button
        """
        if not self.current_step.previous_step_available:
            return

        if not self.current_step.on_previous_callback():
            return

        self.current_step = self.current_step.previous_step

    def _next_step(self):
        """
        Gets called, when user clicks next step button
        """
        if not self.current_step.next_step_available:
            return

        if not self._current_step.on_next_callback():
            return

        self.current_step = self._current_step.next_step

    def _on_cancel_callback(self) -> bool:
        """
        Performs on_cancel callback.

        Returns True if callback not defined or callback succeeds, False otherwise.
        """
        if not self.on_cancel:
            return True

        return self.on_cancel()

    def _on_finish_callback(self) -> bool:
        """
        Performs on_finish callback.

        Returns True if callback not defined or callback succeeds, False otherwise.
        """
        if not self.on_finish:
            return True

        return self.on_finish()
