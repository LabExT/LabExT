#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk
from tkinter.ttk import Treeview, Scrollbar

from LabExT.View.Controls.CustomFrame import CustomFrame


class ToDoTable(CustomFrame):
    """Shows the devices and measurements to be performed (measurement
    queue) in the main window.
    """

    def __init__(self, parent, experiment_manager, total_col_width, selec_mode, double_click_callback=None):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        total_col_width : int
            Column width of the table
        selec_mode : string
            Choose whether the user can select items in the table
        double_click_callback : function pointer
            optional, give it a function which is to be executed on a double click on a row, the function gets
            the To Do index as its sole argument.
        """
        super(ToDoTable, self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()
        self.logger.debug('Initialised DeviceTable with parent:%s experiment_manager:%s col_width:%s selec_mode:%s',
                          parent, experiment_manager, total_col_width, selec_mode)

        self._total_col_width = total_col_width
        self._selection_mode = selec_mode
        self._root = parent
        self._experiment_manager = experiment_manager
        self._double_click_callback = double_click_callback

        # list of to do
        self._original_todo_list = experiment_manager.exp.to_do_list

        # table widget
        self._todo_table_widget = None

        self.__setup__()  # setup window content

    def __setup__(self):
        """Set up the table.
        """
        # we only show ID, in- and outputs and the measurement performed
        def_columns = ["Place in Queue", "Device ID", "Type", "Measurement"]
        pct_columns_width = [0.1, 0.1, 0.4, 0.4]

        # create widgets
        self._tree = Treeview(
            self,
            show="headings",
            columns=def_columns,
            selectmode='browse'
        )
        vsb = Scrollbar(self, orient="vertical", command=self._tree.yview)
        hsb = Scrollbar(self, orient="horizontal", command=self._tree.xview)

        # configure widgets and place in grid
        self._tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._tree.grid(column=0, row=0, sticky='nsew', in_=self)
        vsb.grid(column=1, row=0, sticky='wns', in_=self)
        hsb.grid(column=0, row=1, sticky='ew', in_=self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # adjust the column names
        for col_name, col_width_pct in zip(def_columns, pct_columns_width):
            self._tree.heading(col_name, text=col_name)
            self._tree.column(col_name, width=int(self._total_col_width * col_width_pct))

        # enable the double-click callback
        if self._double_click_callback is not None:
            self._tree.bind("<Double-Button-1>", self._double_click, True)

    def _double_click(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            tidx = self._tree.item(item)['values'][0]  # access value in first column, this is the to-do index
            self._double_click_callback(tidx)

    def get_selected_todo_index(self):
        """
        Returns the index of the selected row.
        """
        selected_iid = self._tree.focus()
        self.logger.debug('Selected iid: %s', selected_iid)
        if not selected_iid:
            return None
        todo_idx = int(self._tree.set(selected_iid, 0))
        self.logger.debug('Selected ToDo index: %s', todo_idx)
        return todo_idx

    def regenerate(self):
        """
        Repopulate the table based on the to do list.

        Delete all items which are still displayed but not anymore in to do list. Add all items which are
        not displayed but in to do list.

        Final step is to sort all displayed items in the treeview and adapt their displayed index.
        """

        # get list of hashes from currently displayed items
        leftover_hashes = list(self._tree.get_children(item=""))

        # compare SOLL vs IST list of what we need to display
        for tidx, todo in enumerate(self._original_todo_list):

            todo_hash = todo.get_hash()

            # case: item in original list and displayed list, all fine, skip to next
            if todo_hash in leftover_hashes:
                self._tree.set(item=todo_hash, column=0, value=str(tidx))
                self._tree.move(item=todo_hash, parent="", index=tidx)
                leftover_hashes.remove(todo_hash)
                continue

            # case: new item added to original list and not yet in displayed list
            dev, measurement = todo.device, todo.measurement
            todo_values = (tidx,
                           dev._id,
                           dev._type,
                           measurement.get_name_with_id())
            self._tree.insert(parent="", index=tidx, iid=todo_hash, values=todo_values)

        # case: item still in displayed list but not anymore in original list
        self._tree.delete(*leftover_hashes)
