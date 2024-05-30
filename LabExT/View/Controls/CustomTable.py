#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from operator import itemgetter

from LabExT.View.Controls.CustomTtkWidgets import CustomTreeview, CustomScrollbar


class CustomTable(object):
    """Creates a table with entries and scrollbars.
    """

    def __init__(self,
                 parent,
                 columns,
                 rows,
                 col_width=20,
                 add_checkboxes=False,
                 selectmode='extended',
                 showmode='headings',
                 sortable=True):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter window parent
        columns : list
            Columns for the table
        rows : list
            List of tuples for the rows of the table
        col_width : int, optional
            Column width
        selectmode : str, optional
            Whether the user can select items in the table
            'none' for no selection possible, 'browse' for single row selection, 'extended' for multiple rows selection
        sortable : bool, optional
            Sets ability to sort the table when clicking on the column headers
        """
        self._col_width = col_width
        self._root = parent
        self._columns = columns
        self._rows = rows
        self._tree = None
        self._add_checkboxes = add_checkboxes
        self._select_mode = selectmode
        self._show_mode = showmode
        self._selection = dict()
        self._sortable = sortable

        self.logger = logging.getLogger()
        self.logger.debug('Initialised CustomTable with parent: %s columns: %s' +
                          ' number of rows: %d col_width: %s selectmode: %s showmode: %s' +
                          ' add checkboxes: %s',
                          parent, columns, len(rows), col_width, selectmode, showmode, add_checkboxes)
        self.__setup__()
        self._build_tree_columns()
        self.add_all()

    def __setup__(self):
        """Create a Treeview with two scrollbars.
        """
        self._tree = CustomTreeview(
            self._root,
            columns=self._columns,
            show=self._show_mode,
            selectmode=self._select_mode)
        vsb = CustomScrollbar(
            self._root, orient="vertical", command=self._tree.yview)
        hsb = CustomScrollbar(
            self._root, orient="horizontal", command=self._tree.xview)

        self._tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._tree.grid(column=0, row=0, sticky='nsew', in_=self._root)
        vsb.grid(column=1, row=0, sticky='wns', in_=self._root)
        hsb.grid(column=0, row=1, sticky='ew', in_=self._root)
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=1)

    def get_tree(self) -> CustomTreeview:
        """Getter for treeview object
        """
        return self._tree

    def select_by_id(self, device_id, id_column=0):
        """
        Select an item based on its id. Device id is assumed to be
        stored in the first column!

        Parameters
        ----------
        device_id : str
            Device ID.
        id_column : int
            The column of the table which contains the device IDs
        """
        children = self._tree.get_children()

        for ix, child in enumerate(children):
            if self._tree.item(child).get('values')[id_column] == device_id:
                self._tree.selection_set(child)
                self._tree.focus(child)

    def _build_tree_columns(self):
        """Build up the tree based on values given in constructor.
        """
        for col in self._columns:
            self._tree.heading(
                col, text=col, command=lambda c=col: sortby(self._tree, c, 0) if self._sortable else None)
            # adjust the column's width
            self._tree.column(col, width=self._col_width)

    def add_all(self):
        """Fill items into tree
        """
        for i, item in enumerate(self._rows):
            self._tree.insert('', 'end', values=item)

    def add_item(self, item):
        """Add an item to the tree.

        Parameters
        ----------
        item : tuple
            Row to be inserted
        """
        self._tree.insert('', 'end', values=item)

    def remove_item(self, item):
        """Removes an item from the tree.

        Parameters
        ----------
        item : tuple
            Row to be removed

        Returns
        -------
        str
            The removed item's treeview iid.
        """
        self.logger.debug('Remove item from CustomTable called with:%s', item)

        children = self._tree.get_children()
        for child in children:
            val = self._tree.item(child).get('values')
            # all values have to be the same to remove the item
            if all(v in val for v in item):
                self._tree.delete(child)
                return child

    def remove_all(self):
        """
        Removes all children from the treeview.
        """
        self.logger.debug('Remove all items from CustomTable called.')
        children = self._tree.get_children()
        for c in children:
            self._tree.delete(c)


def sortby(tree, col, descending):
    """Sorts tree contents when a column header is clicked on.

    Parameters
    ----------
    tree : tkinter.Treeview
        Tree to be sorted.
    col : string
        Column by which to sort.
    descending : bool
        Sort the tree in descending or ascending order.
    """
    # separate out the column data so we can verify it is all the same type
    column_keys = tree.get_children('')
    column_values = [tree.set(child, col) for child in column_keys]

    # if the all the data to be sorted is numeric change to float
    if all(map(is_float, column_values)):
        column_values = map(lambda item: float('+inf') if item == '' else float(item), column_values)

    data = zip(column_values, column_keys)
    
    # sort the data in place
    data = sorted(data, key=lambda x: (x, itemgetter(0)), reverse=descending)

    # move the items' position in the table
    for ix, item in enumerate(data):
        tree.move(item[1], '', ix)
    # switch so tree will sort in opposite direction next time it is clicked
    tree.heading(
        col, command=lambda col=col: sortby(tree, col, int(not descending)))
    
def is_float(s):
    """Helper function to check if a string is a float
    Unfortunately this is the most foolproof method in python

    Parameters
    ----------
    s : any
    """
    # We convert empty strings to +inf
    if s == '': return True

    try:
        float(s)
        return True
    except ValueError:
        return False
