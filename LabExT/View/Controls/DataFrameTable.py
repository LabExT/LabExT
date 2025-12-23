from tkinter import Tk
from typing import Any, Literal, Union

import pandas as pd

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTtkWidgets import CustomTreeview, CustomScrollbar


class DataTable:

    def __init__(self, columns: list[str], rows: list[tuple[Any]]):
        self._df = pd.DataFrame(rows, columns=columns)
        self._current_df = self._df.copy()

    @property
    def df(self) -> pd.DataFrame:
        return self._current_df

    @property
    def full_df(self) -> pd.DataFrame:
        return self._df

    def sync(self) -> None:
        self._df.update(self._current_df)
        # handle newly added rows
        new_rows = self._current_df.index.difference(self._df.index)
        if not new_rows.empty:
            self._df = pd.concat([self._df, self._current_df.loc[new_rows]])

    def update_df(self, df: pd.DataFrame) -> None:
        self._current_df = df
        self.sync()

    def sort(self, column: str, ascending: bool) -> None:
        if column in self.df.columns:
            self._current_df = self._current_df.sort_values(column, ascending=ascending)


# ============================================================
# VIEW: TableView (Tkinter Treeview renderer)
# ============================================================


class TableView:
    """Tkinter UI element that ONLY handles displaying data."""

    def __init__(self,
                 parent: Tk,
                 column_headers: list[str],
                 col_width: int,
                 show_mode: Literal["tree", "headings", "tree headings", ""],
                 select_mode: Literal["extended", "browse", "none"]):

        self.parent = parent
        self.columns = column_headers
        self.tree: Union[CustomTreeview, None] = None
        self._col_width = col_width
        self._show_mode = show_mode
        self._select_mode = select_mode

        self._build_ui()

    # --------------------------------------------------------

    def _build_ui(self):
        """Initialize Treeview with scrollbars."""
        self.tree = CustomTreeview(
            self.parent,
            columns=self.columns,
            show=self._show_mode,
            selectmode=self._select_mode
        )

        vsb = CustomScrollbar(self.parent, orient="vertical", command=self.tree.yview)
        hsb = CustomScrollbar(self.parent, orient="horizontal", command=self.tree.xview)

        self.tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)

        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")

        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=self._col_width)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def populate_row(self, values: tuple[Any, ...], iid: Union[int, str, None] = None):
        self.tree.insert("", "end", iid=iid, values=values)

    def get_selected_row_indices(self) -> list[int]:
        selected_row_indices = [int(iid) for iid in self.tree.selection()]
        return selected_row_indices


# ============================================================
# CONTROLLER: TableController
# ============================================================


class TableController:
    def __init__(self, model: DataTable, view: TableView):
        self.model = model
        self.view = view

        self._sort_states = {col: False for col in self.model.df.columns}
        self._prepare_sorting()
        self.refresh()

    def _prepare_sorting(self) -> None:
        for column in self.model.df.columns:
            self.view.tree.heading(column, command=lambda c=column: self.sort_by_column(c))

    def sort_by_column(self, column: str) -> None:
        current = self._sort_states[column]
        self.model.sort(column, ascending=not current)
        self._sort_states[column] = not current
        self.refresh()

    def refresh(self) -> None:
        selected = set(self.view.get_selected_row_indices())
        self.view.clear()
        for idx, row_values in self.model.df.iterrows():
            self.view.populate_row(tuple(row_values), iid=str(idx))
            if idx in selected:
                self.view.tree.selection_add(str(idx))

    def get_df(self) -> pd.DataFrame:
        return self.model.df.copy()

    def update_df(self, df: pd.DataFrame) -> None:
        self.model.update_df(df)
        self.refresh()


# ============================================================
# FACADE: CustomTable (drop-in replacement)
# ============================================================


class DataFrameTable:

    def __init__(
            self,
            parent: Union[Tk, CustomFrame],
            column_headers: list[str],
            rows: list[tuple],
            col_width: int = 20,
            select_mode: Literal["extended", "browse", "none"] = "extended",
            show_mode: Literal["tree", "headings", "tree headings", ""] = "headings",
    ):
        self.model = DataTable(column_headers, rows)
        self.view = TableView(parent, column_headers, col_width, show_mode, select_mode)
        self.controller = TableController(self.model, self.view)

    def get_df(self) -> pd.DataFrame:
        return self.controller.get_df()

    def update_df(self, df: pd.DataFrame) -> None:
        self.controller.update_df(df)

    def get_selected_row_indices(self) -> list[int]:
        return self.view.get_selected_row_indices()
