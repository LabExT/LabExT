#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
from tkinter import Tk, Frame, Label, Button, messagebox

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable


class DeviceWindow(Frame):
    """Shows a table with all devices of the imported chip and lets
    the user select devices.
    """

    def __init__(self, parent: Tk, experiment_manager, callback=None):
        """Constructor

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        experiment_manager : ExperimentManager
            Current instance of the ExperimentManager
        """
        super(DeviceWindow, self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()
        self.logger.debug('Initialised DeviceWindow with parent:%s experiment_manager:%s', parent, experiment_manager)

        self.settings_path = get_configuration_file_path("DeviceWindow.json")

        self._root = parent
        self.callback = callback
        self._experiment_manager = experiment_manager
        self._root.title = 'Device Overview'
        self._root.geometry('{}x{}+{}+{}'.format(1500, 750, 300, 300))

        self._chip = experiment_manager.chip

        # list of all currently imported devices
        self._devices = list(self._chip._devices.values())

        # list of all selected devices
        self._selection = list()
        self._abort = False
        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)

        self.grid(row=0, column=0)  # place window in root element
        self.__setup__()  # setup the window content

    def __on_close__(self):
        """Called when user presses 'x'. Opens pop up to ask if user
        really wants to quit, since this class is part of the
        ExperimentWizard.
        """
        m = messagebox.askyesno('Quit',
                                'Do you want to quit the ExperimentWizard?')
        if m:
            self._store_to_file()
            self._root.destroy()
            self._abort = True

    def __setup__(self):
        """Sets up the window and the device table.
        """
        # columns with needed parameters
        def_columns = ["Selection", "ID", "In", "Out", "Type"]
        # get columns with all possible parameters
        columns = set()
        for device in self._devices:
            for param in device._parameters:
                columns.add(str(param))

        self.logger.debug('Columns for device window:%s', (def_columns + list(columns)))

        # fill rows with all devices and their parameters
        devs = list()
        for d in self._devices:
            tup = (' ', d._id, d._in_position, d._out_position, d._type)  # needed values
            for param in columns:
                # the value of parameter, empty if parameter does not exist
                # for that specific device
                val = d._parameters.get(param, '')
                # unpack the tuple, append the value of the new parameter
                # make a tuple again
                tup = (*tup, val)
            devs.append(tup)

        # create header
        self._info_label = Label(
            self._root,
            text=
            'Highlight one or more rows, then push the lower left buttons to mark the devices to be measured. ' + \
            'This screen remembers the selection you made previously.'
        )
        self._info_label.grid(column=0, row=0, padx=5, pady=5, sticky='nswe')

        # create table
        self._table_frame = CustomFrame(self._root)
        self._table_frame.title = "Devices on Chip"
        self._table_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        self._table_frame.rowconfigure(0, weight=1)
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(1, weight=1)

        self._device_table = CustomTable(self._table_frame, (def_columns + list(columns)), devs)

        # setup buttons and information labels for user
        self._selection_buttons_frame = Frame(self._root)
        self._selection_buttons_frame.grid(column=0, row=2, sticky='w')
        self._select_all_button = Button(
            self._selection_buttons_frame, text="(un)mark highlighted", command=self.mark_items)
        self._select_all_button.grid(column=0, row=0, padx=5, pady=5, sticky='w')
        self._select_all_button = Button(
            self._selection_buttons_frame, text="(un)mark all", command=self.mark_all)
        self._select_all_button.grid(column=1, row=0, padx=5, pady=5, sticky='w')

        self._info_label_bot = Label(
            self._root,
            text=
            'The devices selected will be sorted by increasing ID for creating ToDos.'
        )
        self._info_label_bot.grid(column=0, row=2, padx=5, pady=5, sticky='')

        self._continue_button = Button(
            self._root, text="continue", command=self._continue)
        self._continue_button.grid(column=0, row=2, padx=5, pady=5, sticky='e')

        self._load_from_file()

    def mark_items(self):
        """Called when user selects device. Adds selected device to
        selection list.
        """
        focused_item_iids = self._device_table._tree.selection()
        for fiid in focused_item_iids:
            dev_id = int(self._device_table._tree.set(fiid, 1))  # get id of device stored in 2nd column in table
            self._select_unselect_by_devid(dev_id=dev_id, fiid=fiid)

    def mark_all(self):
        """Called when user presses button. Selects/Deselects all
        devices shown in the table, depending on current selection.
        """
        # determine whether or not all devices are already selected
        perform_all_select = True
        if len(self._selection) == len(self._devices):
            perform_all_select = False
        # if all devices are not selected, select all
        if perform_all_select:
            self._selection.clear()
            for dev in self._devices:
                self._selection.append(dev)
            for item in self._device_table._tree.get_children(''):
                self._device_table._tree.set(item=item, column=0, value="marked")
        # if all are already selected, deselect all
        else:
            self._selection.clear()
            for item in self._device_table._tree.get_children(''):
                self._device_table._tree.set(item=item, column=0, value=" ")

    def _continue(self):
        """Called when user clicks on continue button. Sorts the
        selected devices by increasing ID and sets device_list in
        experiment to user selection, then closes window.
        """
        self._store_to_file()

        # we don't do anything if the user doesn't select any devices
        if not self._selection:
            messagebox.showinfo('Warning',
                                'Please select at least one device.')
            return

        self._experiment_manager.exp.device_list.extend(
            sorted(self._selection, key=lambda x: x._id)
        )

        self.logger.debug('Device list (sorted) in experiment:%s', self._experiment_manager.exp.device_list)
        self._root.destroy()
        if self.callback is not None:
            self.callback()

    def _select_unselect_by_devid(self, dev_id, fiid=None):
        curdev = self._chip._devices[dev_id]  # get device object

        # find tree item iid corresponding to device
        if fiid is None:
            all_childs = self._device_table.get_tree().get_children()
            for c in all_childs:
                # the following convoluted line gets the device id out of the values stored in the tree row
                c_dev_id = self._device_table.get_tree().item(c)['values'][1]
                if dev_id == c_dev_id:
                    fiid = c
                    break
            else:
                self.logger.debug("Cannot find device with id " + str(dev_id) + " in tree. Ignoring.")
                return

        # when the device is already selected, remove selection
        if curdev in self._selection:
            self._selection.remove(curdev)
            self._device_table._tree.set(fiid, 0, " ")  # needs to be a space, because else sortby doesn't work
        # if it's not, select it
        else:
            self._selection.append(curdev)
            self._device_table._tree.set(fiid, 0, "marked")

    def _load_from_file(self):
        # load and select previous selection, if file is given
        if os.path.exists(self.settings_path):
            with open(self.settings_path, "r") as f:
                stored_iids = json.load(f)
            for dev_id in stored_iids:
                if dev_id in self._chip._devices:
                    self._select_unselect_by_devid(dev_id=dev_id)

    def _store_to_file(self):
        with open(self.settings_path, "w") as f:
            sel_ids = [d._id for d in self._selection]
            json.dump(sel_ids, f)
