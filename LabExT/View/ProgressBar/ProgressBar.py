#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import _tkinter
from tkinter import Toplevel, ttk, Label, StringVar

import platform


class ProgressBar(Toplevel):
    def __init__(self, root, text):
        self.root = root
        Toplevel.__init__(self, self.root)

        self.attributes('-topmost', 'true')
        self.title("LabExT")
        self.prog = ttk.Progressbar(self, mode='indeterminate')
        self.prog.grid(row=1, column=0)
        self.prog.start()

        self.text = StringVar()
        self.text.set(text)

        lbl = Label(master=self,
                    textvariable=self.text)
        lbl.grid(row=0, column=0)

        # do not disable window border for MacOS w/ TKinter 8.6 as tkinter is buggy
        if 'darwin' not in platform.system().lower():
            # don't show classical window bar for progress bar
            self.overrideredirect(True)

        # this lets the window manager draw all windows, which is necessary as
        # the sizes of the window will be read below
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        size = tuple(int(_) for _ in self.geometry().split('+')[0].split('x'))
        x = screen_width / 2 - size[0] / 2
        y = screen_height / 2 - size[1] / 2
        self.geometry("+%d+%d" % (x, y))

