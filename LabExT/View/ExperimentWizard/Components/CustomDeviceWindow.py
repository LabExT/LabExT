#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame, Label, Button, messagebox, Entry

from LabExT.Wafer.Device import Device


class CustomDeviceWindow(Frame):
    """Creates a Frame that shows a variable number of input fields
    and creates a new device from the provided inputs.
    """

    def __init__(self, parent: Tk, experiment_manager, callback=None):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        super(CustomDeviceWindow, self).__init__(parent)

        self.logger = logging.getLogger()
        self.logger.debug('Initialised CustomDeviceWindow with parent:%s experiment_manager:%s', parent, experiment_manager)

        self.callback = callback

        self._root = parent
        self._experiment_manager = experiment_manager
        self._root.title = 'Custom Device'
        self._extra_parameters = []
        # if the user aborts, this is set to True
        self._abort = False
        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)

        self.grid(row=0, column=0)  # place window in root element
        self.__setup__()  # setup the main window content

    def __on_close__(self):
        """Called if the user presses on 'x'. Asks if user really
        wants to close the ExperimentWizard.
        """
        m = messagebox.askyesno('Quit',
                                'Do you want to quit the ExperimentWizard?')
        if m:
            self._root.destroy()
            self._abort = True

    def __setup__(self):
        """Sets up the frame.
        """
        self._device_name_label = Label(self, text='Device ID (*):')
        self._device_name_label.grid(row=0, column=0)

        self._device_name_input = Entry(self)
        self._device_name_input.grid(row=0, column=1)

        self._device_in_label = Label(self, text='Input position:')
        self._device_in_label.grid(row=1, column=0)

        self._device_in_input = Entry(self)
        self._device_in_input.grid(row=1, column=1)

        self._device_out_label = Label(self, text='Output position:')
        self._device_out_label.grid(row=2, column=0)

        self._device_out_input = Entry(self)
        self._device_out_input.grid(row=2, column=1)

        self._device_type_label = Label(self, text='Type (*):')
        self._device_type_label.grid(row=3, column=0)

        self._device_type_input = Entry(self)
        self._device_type_input.grid(row=3, column=1)

        self._counter = 4

        # the window can max. support 100 input fields
        self._more_parameters_button = Button(
            self, text='Add more parameters', command=self._more_parameter)
        self._more_parameters_button.grid(row=100, column=0, sticky='w')

        self._continue_button = Button(
            self, text="Continue", command=self._continue)
        self._continue_button.grid(column=1, row=100, sticky='e')

    def _continue(self):
        """Called when user presses on 'Continue' button. Gets entries
        from user and creates a new device that is added to the
        experiment's device_list.
        """
        # we don't do anything if the user doesn't fill in all values
        _id = self._device_name_input.get()
        _in = self._device_in_input.get()
        _out = self._device_out_input.get()
        _type = self._device_type_input.get()

        # if the user does not fill in all compulsory fields
        # show a warning and do not continue
        if not _id or not _type:
            messagebox.showinfo('Warning',
                                'Please fill in all compulsory fields (*).')
            return
        # if the user did not provide device coordinates
        # set them to [0.0, 0.0] and continue
        if not _in:
            _in = [0.0, 0.0]
        if not _out:
            _out = [0.0, 0.0]

        # get all custom parameters added by user
        custom_params = dict()
        for tup in self._extra_parameters:
            custom_params.update({tup[0].get(): tup[1].get()})

        # create new device
        custom_device = Device(int(_id), _in, _out, _type, custom_params)

        self.logger.debug('Created device:%s', custom_device)
        self._experiment_manager.exp.device_list.append(custom_device)

        self._root.destroy()
        if self.callback is not None:
            self.callback()

    def _more_parameter(self):
        """Adds new parameter fields to the window for custom
        parameters.
        """
        param_key = Entry(self)
        param_value = Entry(self)
        self._extra_parameters.append((param_key, param_value))

        param_key.grid(row=self._counter, column=0)
        param_value.grid(row=self._counter, column=1)
        self._counter += 1
