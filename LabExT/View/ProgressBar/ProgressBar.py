#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Toplevel, ttk, Label, StringVar


class ProgressBar (Toplevel):
    def __init__(self, root, text):
        self.root = root
        Toplevel.__init__(self, self.root)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        size = tuple(int(_) for _ in self.geometry().split('+')[0].split('x'))
        x = screen_width / 2 - size[0] / 2
        y = screen_height / 2 - size[1] / 2
        self.geometry("+%d+%d" % (x, y))
        self.overrideredirect(1)

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
