#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Scrollbar, Canvas


class ScrollableFrame(Frame):

    def __init__(self, top, *args, **kwargs):
        Frame.__init__(self, top, *args, **kwargs)

        vscrollbar = Scrollbar(self, orient='vertical')
        vscrollbar.grid(row=0, column=1, sticky='ns')

        self.canvas = Canvas(self, yscrollcommand=vscrollbar.set)
        self.canvas.grid(row=0, column=0, sticky='nswe')

        vscrollbar.config(command=self.canvas.yview)

        # Make the canvas expandable
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create the canvas contents
        self.frame = Frame(self.canvas)

        # add the content frame to the canvas
        self.canvas_frame = self.canvas.create_window(4, 4, window=self.frame, anchor='nw')

        # bind callbacks, needed to propagate size changes from canvas to frame
        self.frame.bind('<Configure>', self._frame_changed)
        self.canvas.bind('<Configure>', self._canvas_changed)
        
    def get_content_frame(self):
        return self.frame

    def _canvas_changed(self, *args):
        self.canvas.itemconfigure(self.canvas_frame, width=self.canvas.winfo_width())

    def _frame_changed(self, *args):
        # marcoep: unclear if this is needed
        self.frame.update_idletasks()
        x1, y1, x2, y2 = self.canvas.bbox("all")
        height = self.canvas.winfo_height()
        self.canvas.config(scrollregion=(0, 0, x2, max(y2, height)))
