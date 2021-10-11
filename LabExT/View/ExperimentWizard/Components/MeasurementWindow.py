#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame, Label, Button, messagebox

from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.TooltipMenu import CreateToolTip


class MeasurementWindow(Frame):
    """Shows all possible measurements in a table and lets the user
    decide on the order in which the measurements will be performed.
    Called by the ExperimentWizard.
    """

    def __init__(self, parent: Tk, experiment_manager, callback=None):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter window parent.
        experiment_manager : ExperimentManager
            Instance of the current ExperimentManager.
        """
        super(MeasurementWindow,
              self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()
        self.logger.debug('Initialised MeasurementWindow with parent: %s, experiment_manager: %s', parent, experiment_manager )
        self._root = parent
        self.callback = callback
        self._experiment_manager = experiment_manager
        self._root.title = 'Measurement Overview'
        self._root.geometry('{}x{}'.format(500, 250))

        # all possible measurements
        self._meas = self._experiment_manager.exp.measurement_list
        self.logger.debug('All possible measurements: %s', self._meas)

        # selected measurements
        self._selection = list()
        # if the user aborts, this is set to true, used by the ExperimentWizard
        self._abort = False

        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)

        self.grid(row=0, column=0)  # place window in root element
        self.__setup__()  # setup the window content

    def __on_close__(self):
        """Asks the user if (s)he wants to quit, since this class is
        part of the ExperimentWizard.
        """
        m = messagebox.askyesno('Quit',
                                'Do you want to quit the ExperimentWizard?')
        if m:
            self._root.destroy()
            self._abort = True
            self.logger.debug('User aborted MeasurementWindow')

    def __setup__(self):
        """Sets up the measurement table and the buttons.
        """

        # create the rows and columns for the table
        columns = ["Order", "Name"]
        rows = list()
        self._meas = list(self._meas)
        self._meas.sort()

        for meas in self._meas:
            tup = (0, meas)
            rows.append(tup)

        # create table
        self._meas_table = CustomTable(self._root, columns, rows)

        # insert the measurements to the table and add event when user selects a measurement
        for i, item in enumerate(self._meas_table._tree.get_children('')):
            self._meas_table._tree.item(item=item, tags=(str(i)))
            self._meas_table._tree.tag_bind(str(i), '<ButtonRelease-1>', self.select_item)
            CreateToolTip(experiment_manager=self._experiment_manager,
                          widget=self._meas_table._tree,
                          stringvar=i,
                          is_treeview=True,
                          item=item)

        # set up buttons and label with information for the user
        self._select_all_button = Button(
            self._root, text="Select all", command=self.select_all)
        self._select_all_button.grid(column=0, row=3, sticky='w')

        self._info_label = Label(
            self._root,
            text='Order 0 means that the measurement is not selected.\nRight click on measurement for info.')
        self._info_label.grid(column=0, row=3, sticky='')

        self._continue_button = Button(
            self._root, text="Continue", command=self._continue)
        self._continue_button.grid(column=0, row=3, sticky='e')

    def select_item(self, a):
        """Called when the user selects a measurement in the table.
        Sets the order of the measurements.

        Parameters
        ----------
        a : Tkinter Event Object
            Python object instance with attributes about the event.
        """
        # do nothing to the selection, if the header is clicked
        region = self._meas_table._tree.identify("region", a.x, a.y)
        if region == "heading":
            return

        # get the item, that was clicked on
        curMeas = self._meas_table._tree.focus()
        self.logger.debug('Client clicked on: %s', curMeas)
        meas = self._meas_table._tree.set(curMeas, 1)
        self.logger.debug('Measurement: %s', meas)
        order = int(self._meas_table._tree.set(curMeas, 0))
        self.logger.debug('Order: %s', order)

        # determine if item should be selected or deselected
        if meas in self._selection:
            self.logger.debug('Measurement was removed from selection.')

            self._selection.remove(meas)
            # update order of all selected measurements
            # get all measurements
            for item in self._meas_table._tree.get_children(''):
                othermeas = self._meas_table._tree.set(item, 1)
                # only regard the selected measurement
                if othermeas in self._selection:
                    # the order is the index in the selection list,
                    # because the deselected measurement is removed from self.selection
                    self._meas_table._tree.set(
                        item=item,
                        column=0,
                        value=self._selection.index(othermeas) + 1)
            # set order of selected measurement to 0 = deselected
            self._meas_table._tree.set(curMeas, 0, 0)
        else:
            self.logger.debug('Measurement was added to selection.')
            self._selection.append(meas)
            self._meas_table._tree.set(curMeas, 0, len(self._selection))

    def select_all(self):
        """Selects all measurements or deselects all, if all are
        selected.
        Called when user presses 'Select All' button.
        """
        # determine whether or not all measurements are already selected
        all_selected = False
        if len(self._selection) == len(self._meas):
            all_selected = True

        self.logger.debug('Currently all measurements are selected: %s', all_selected)

        # if all measurements are selected, deselect all, by giving them order 0
        if all_selected:
            self._selection.clear()
            for item in self._meas_table._tree.get_children(''):
                self._meas_table._tree.set(item=item, column=0, value=0)
        # else select all in ascending order
        else:
            self._selection.clear()
            for meas in self._meas:
                self._selection.append(meas)
            for i, item in enumerate(self._meas_table._tree.get_children('')):
                self._meas_table._tree.set(item=item, column=0, value=i + 1)

    def _continue(self):
        """Called when user presses on 'Continue' button.
        Calls Experiment to import measurements then closes to return
        to ExperimentWizard.
        """
        # if the user doesn't select any measurement, we don't do anything
        if not self._selection:
            messagebox.showinfo('Warning',
                                'Please select at least one measurement')
            return
        self.logger.debug('Will now import all measurements...')
        for meas in self._selection:
            self._experiment_manager.exp.create_measurement_object(meas)
        self._root.destroy()
        if self.callback is not None:
            self.callback()
