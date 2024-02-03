#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import Literal
import logging
from operator import itemgetter

import pandas as pd
import numpy as np

from LabExT.View.Controls.CustomTtkWidgets import CustomTreeview, CustomScrollbar


class CustomTable:
    """ Creates a table with entries and scrollbars. """

    def __init__(self,
                 parent,
                 columns: list[str],
                 rows: list[tuple],
                 col_width=20,
                 selectmode: Literal["extended", "browse", "none"] = "extended",
                 showmode='headings') -> None:

        self.logger = logging.getLogger()
        self._col_width = col_width
        self._root = parent
        self._tree = None

        self._data = pd.DataFrame(data=rows, columns=columns)

        self._tree = CustomTreeview(self._root, columns=columns, show=[showmode], selectmode=selectmode)

        self.__setup__()

    def __setup__(self):
        """Create a Treeview with two scrollbars.
        """
        vsb = CustomScrollbar(self._root, orient="vertical", command=self._tree.yview)
        hsb = CustomScrollbar(self._root, orient="horizontal", command=self._tree.xview)

        self._tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._tree.grid(column=0, row=0, sticky='nsew', in_=self._root)
        vsb.grid(column=1, row=0, sticky='wns', in_=self._root)
        hsb.grid(column=0, row=1, sticky='ew', in_=self._root)
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=1)

        # build up the tree based on values given in constructor
        for col in self._data.columns:
            self._tree.heading(col, text=col, command=lambda c=col: sort_by(self._tree, c))
            self._tree.column(col, width=self._col_width)

        # add all
        for row in self._data.values:
            self._tree.insert('', 'end', values=tuple(row))

    def get_tree(self) -> CustomTreeview:
        """Getter for treeview object
        """
        return self._tree

    def focus(self):
        return self._tree.focus()

    def select_by(self, row_value, column_index: int) -> None:
        """ Select an item based on its value and column index. """
        for child in self._tree.get_children():
            if self._tree.item(child).get('values')[column_index] == row_value:
                self._tree.selection_set(child)
                self._tree.focus(child)

    def set_by(self, row_value, column_index: int):
        """ Select an item based on its value and column index. """
        return self._tree.set(row_value, column_index)

    def add_item(self, row_values: tuple) -> None:
        """Add an item to the tree."""
        self._tree.insert('', 'end', values=row_values)

    def remove_item(self, item_iid: str) -> str:
        """ Remove an item with the given treeview iid and return it as a string. """
        if item_iid in self._tree.get_children():
            self._tree.delete(item_iid)
            return item_iid

    def remove_all(self):
        """
        Removes all children from the treeview.
        """
        for child in self._tree.get_children():
            self._tree.delete(child)

    def filter_with(self, keyword: str) -> None:
        """ Filter the table with the given keyword. """

        row_selection = np.zeros(self._data.shape[0], dtype=bool)
        for col in self._data.columns:
            row_selection = np.logical_or(row_selection, self._data[col].astype(str).str.contains(keyword))

        filtered_dataframe = self._data[row_selection]

        self.remove_all()

        # add all
        for row in filtered_dataframe.values:
            self._tree.insert('', 'end', values=tuple(row))


def sort_by(tree: CustomTreeview, col: str, descending: bool = False) -> None:
    """Sorts tree contents when a column header is clicked on.

    Parameters
    ----------
    tree : tkinter.Treeview
        Tree to be sorted.
    col : string
        Column by which to sort.
    descending : bool
        Sort the tree in ascending or descending order.
    """
    # grab values to sort
    raw_data = [(tree.set(child, col), child) for child in tree.get_children('')]

    data = []
    # if the data to be sorted is numeric change to float
    for i, item in enumerate(raw_data):
        if item[0].isdigit():
            tup = (int(item[0]), item[1])
            data.append(tuple(tup))
        elif item[0] == '':
            tup = (float('+inf'), item[1])
            data.append(tuple(tup))
        else:
            data.append(item)

    # sort the data in place
    data = sorted(data, key=lambda x: (x, itemgetter(0)), reverse=descending)

    # move the items' position in the table
    for ix, item in enumerate(data):
        tree.move(item[1], '', ix)
    # switch so tree will sort in opposite direction next time it is clicked
    tree.heading(col, command=lambda _col=col: sort_by(tree, col, not descending))
