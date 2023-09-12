#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import queue
from tkinter import Frame, TOP, BOTH
import time
import numpy as np
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class LivePlotData:

    def __init__(self, max_elements=400):
        self.color = 'blue'
        self._queue = queue.Queue()
        self.max_elements = max_elements
        self._t = [float('nan')] * max_elements
        self._y = [float('nan')] * max_elements

    def push(self, value):
        new_data = (time.time(), value)
        self._queue.put_nowait(new_data)

    def get_ty(self):
        while not self._queue.empty():
            t, y = self._queue.get_nowait()
            self._t.append(t)
            self._y.append(y)
        if len(self._t) > self.max_elements:
            del self._t[0:len(self._t)-self.max_elements]
        if len(self._y) > self.max_elements:
            del self._y[0:len(self._y)-self.max_elements]
        return np.array(self._t), np.array(self._y)


class LivePlotControl(Frame):

    def __init__(self,
                 parent,
                 polling_time_s=0.02,
                 min_y_axis_span=None):
        super(LivePlotControl, self).__init__(parent)  # call the parent controls constructor

        self._root = parent  # keep a reference for the ui root
        self._min_y_axis_span = min_y_axis_span

        # set automatic updating time
        if polling_time_s < 1e-5:
            raise ValueError('Polling time must be larger than 10ums.')
        self._polling_time_ms = int(polling_time_s * 1000)
        self._polling_running = False  # flag to not start polling thread multiple times
        self._polling_kill_flag = False  # Gets set to true when the class is destroyed in order to stop polling

        self._x_label = "x"
        self._y_label = "y"

        self._figure = Figure(figsize=(12, 6), dpi=100)  # define plot size
        self.ax = self._figure.add_subplot(111)  # add subplot and save reference

        self._canvas = FigureCanvasTkAgg(self._figure, self)  # add figure to canvas

        self._canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)  # place canvas
        self._canvas.draw()  # show canvas

        self._toolbar = NavigationToolbar2Tk(self._canvas, self)  # enable plot toolbar
        self._toolbar.update()  # update toolbar
        self._canvas._tkcanvas.pack(side=TOP, fill=BOTH, expand=True)

        # start polling
        self._polling_kill_flag = False
        self._polling_running = True
        self._root.after(self._polling_time_ms, self.__polling__)

    def __polling__(self):
        """ Polls and updates data """
        if self._data_source is not None:
            for item in self._data_source:
                self.__plotdata_changed__(item)
        if not self._polling_kill_flag:
            # reschedule if not killed
            self._root.after(self._polling_time_ms, self.__polling__)
        else:
            # otherwise set running flag to false to signal completion
            self._polling_running = False

    def stop_polling(self):
        self._polling_kill_flag = True

    def destroy(self) -> None:
        self.stop_polling()
        Frame.destroy(self)
