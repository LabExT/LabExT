#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Tk
from typing import List, Literal, Any, Union

from LabExT.View.Controls.CustomTtkWidgets import CustomTreeview, CustomScrollbar


class CustomTable:
    """Creates a table with entries and scrollbars.
    """

    def __init__(self,
                 parent: Tk,
                 column_headers: List[str],
                 rows: List[tuple],
                 col_width: int = 20,
                 add_checkboxes: bool = False,
                 selectmode: Literal["extended", "browse", "none"] = "extended",
                 showmode: Literal["tree", "headings", "tree headings", ""] = "headings",
                 sortable: bool = True):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter window parent
        column_headers : List[str]
            Columns for the table
        rows : List[tuple]
            List of tuples for the rows of the table
        col_width : int, optional
            Column width
        selectmode : str, optional
            Whether the user can select items in the table
            'none' for no selection possible, 'browse' for single row selection, 'extended' for multiple rows selection
        sortable : bool, optional
            Sets ability to sort the table when clicking on the column headers
        """
        self.parent = parent
        self.col_width = col_width
        self.column_headers = column_headers
        self._rows = rows
        self._tree = None
        self._add_checkboxes = add_checkboxes
        self._select_mode = selectmode
        self._show_mode = showmode
        self._selection = dict()
        self._sortable = sortable

        self._build_ui()
        self._build_tree_columns()
        self._populate_initial_rows()

    def _build_ui(self):
        """Create a Treeview with two scrollbars."""
        self._tree = CustomTreeview(
            self.parent,
            columns=self.column_headers,
            show=self._show_mode,
            selectmode=self._select_mode)
        vsb = CustomScrollbar(self.parent, orient="vertical", command=self._tree.yview)
        hsb = CustomScrollbar(self.parent, orient="horizontal", command=self._tree.xview)
        self._tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='wns')
        hsb.grid(column=0, row=1, sticky='ew')
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

    def get_tree(self) -> CustomTreeview:
        """Getter for treeview object"""
        return self._tree

    def select_by_column_value(self, column: Union[str, int], value: Any) -> None:
        """ Select/focus an item based on the column and value. """
        column_names = self._tree["columns"]
        column_idx = column_names.index(column) if isinstance(column, str) else column

        children = self._tree.get_children()
        for idx, child in enumerate(children):
            if self._tree.item(child).get("values")[column_idx] == value:
                self._tree.selection_set(child)
                self._tree.focus(child)

    def select_by_id(self, device_id: str, id_column: int = 0) -> None:
        """ Select an item based on its id. Device id is assumed to be stored in the first column.
        This method will be DEPRECATED soon.
        """
        self.select_by_column_value(column=id_column, value=device_id)

    def _build_tree_columns(self):
        """Build up the tree based on values given in constructor.
        """
        for col in self.column_headers:
            self._tree.heading(
                col, text=col, command=lambda c=col: sort_tree_column(self._tree, c) if self._sortable else None)
            # adjust the column's width
            self._tree.column(col, width=self.col_width)

    def _populate_initial_rows(self) -> None:
        """Fill items into tree."""
        for i, item in enumerate(self._rows):
            self._tree.insert('', 'end', values=item)

    def add_row(self, row_values: tuple) -> None:
        """Add a single row to the tree."""
        self._tree.insert('', 'end', values=row_values)

    def remove_row(self, row_values: tuple) -> str:
        """Removes a row based on matching row values.

        Returns
        -------
        str
            The removed item's treeview iid.
        """
        for child in self._tree.get_children():
            current_values = self._tree.item(child).get('values')
            if tuple(current_values) == row_values:
                self._tree.delete(child)
                return child
        return ""

    def remove_all(self) -> None:
        """Removes all children/rows from the treeview."""
        for c in self._tree.get_children():
            self._tree.delete(c)


def sort_tree_column(tree: CustomTreeview, column_name: str, descending: bool = False) -> None:
    """ Sort the treeview by a given column. """
    row_ids = tree.get_children()
    column_values = [tree.set(row_id, column_name) for row_id in row_ids]

    def prepare(v: Any):
        if v == "":
            return float("inf")
        try:
            return float(v)
        except ValueError:
            return v

    prepared = list(map(prepare, column_values))
    sorted_pairs = sorted(zip(prepared, row_ids), key=lambda x: x[0], reverse=descending)

    # reorder rows
    for index, (_, row_id), in enumerate(sorted_pairs):
        tree.move(row_id, "", index)

    # toggle sorting direction on next click
    tree.heading(column_name, command=lambda col=column_name: sort_tree_column(tree, col, not descending))
