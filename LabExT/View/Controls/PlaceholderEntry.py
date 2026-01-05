#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from typing import Union
from tkinter import Entry, Tk, END, Frame


class PlaceholderEntry(Entry):
    def __init__(
            self,
            parent: Union[Tk, Frame, None] = None,
            placeholder: str = "Placeholder",
            placeholder_color: str = "grey",
            text_color=None,
            **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.text_color = text_color or self.cget("fg")
        self._has_placeholder = False

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

        self._show_placeholder()

    def _show_placeholder(self):
        if not self.get():
            self._set_text(self.placeholder, self.placeholder_color)
            self._has_placeholder = True

    def _hide_placeholder(self):
        if self._has_placeholder:
            self.delete(0, END)
            self.config(fg=self.text_color)
            self._has_placeholder = False

    def _on_focus_in(self, _):
        # Remove placeholder so user can type
        if self._has_placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, _):
        # Restore placeholder if left empty
        if not self.get():
            self._show_placeholder()

    def _set_text(self, text, color):
        self.delete(0, END)
        self.insert(0, text)
        self.config(fg=color)

    def get_value(self) -> str:
        """Return the logical value ('' if only placeholder is shown)."""
        if self._has_placeholder:
            return ""
        return self.get()