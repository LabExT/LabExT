#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import messagebox


class ApplicationView:
    def __init__(self) -> None:
        pass

    @property
    def error(self):
        pass

    @error.setter
    def error(self, message):
        messagebox.showerror(title="An error has occurred", message=message)

    @property
    def info(self):
        pass

    @info.setter
    def info(self, message):
        messagebox.showinfo(title="Information", message=message)
