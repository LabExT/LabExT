#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame, Label, Button, messagebox

from LabExT.View.Controls.DeviceTable import DeviceTable


class MoveDeviceWindow(Frame):
    """Frame used to choose a device to move the stages to.

    Attributes
    ----------
    selection : Device
        List of the selected devices.
    """

    def __init__(self, parent: Tk, experiment_manager, label):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Window in which frame will be placed.
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager.
        label : string
            Information for the user, will be displayed on bottom of
            frame.
        """
        super(MoveDeviceWindow, self).__init__(parent)

        self.logger = logging.getLogger()
        self.logger.debug('Initialise MoveDeviceWindow with parent: %s experiment_manager: %s info_text: %s',
                          parent, experiment_manager, label)

        self._root = parent
        self._experiment_manager = experiment_manager
        self._root.title = 'Device Overview'
        self._root.geometry('{}x{}'.format(1500, 750))

        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)
        self._text_label = label

        # selected device as "return value" of this window
        self.selection = None

        self.grid(row=0, column=0)  # place window in root element
        self._root.rowconfigure(0, weight=1)
        self._root.columnconfigure(0, weight=1)
        self.__setup__()  # setup the main window content

    def __on_close__(self):
        """Destroys the frame when user presses on 'x'. Called by
        Tkinter.
        """
        self.logger.debug('Closed MoveDeviceWindow')
        self._root.destroy()

    def __setup__(self):
        """Sets up all the elements in the frame.
        """
        self.logger.debug('Setup MoveDeviceWindow.')

        self._device_table = DeviceTable(self._root, self._experiment_manager)
        self._device_table.grid(column=0, row=0, sticky='nswe')

        self._info_label = Label(self._root, text=self._text_label)
        self._info_label.grid(column=0, row=1, sticky='')

        self._continue_button = Button(self._root, text="Continue", command=self._continue)
        self._continue_button.grid(column=0, row=1, sticky='e')

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    def _continue(self):
        """Called when user presses on continue button.
        Sets selection to selected device.
        """
        self.selection = self._device_table.get_selected_device()
        if self.selection is None:
            messagebox.showwarning('Selection Needed', 'Please select one device.', parent=self)
            return
        self._root.destroy()
