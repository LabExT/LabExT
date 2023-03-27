#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import Type, Any
from tkinter import Frame, Label, TOP

from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.Movement.Stage import Stage
from LabExT.Movement.MoverNew import MoverNew


class StageTable(Frame):
    """
    Frame which contains a table to select a stage.
    """

    def __init__(
        self,
        parent,
        mover: Type[MoverNew],
        exclude_active_stages: bool = True
    ) -> None:
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            Window in which frame will be placed.
        mover : MoverNew
            Instance of current Mover.
        exclude_active_stages : bool = True
            Active stages (already registered) are not displayed
        """
        super(StageTable, self).__init__(parent)

        self.mover = mover
        self.logger = logging.getLogger()

        # Run discovering for available stages.
        self._all_available_stages = self.mover.get_available_stages()
        self._used_stages = [(s.__class__, s.address)
                             for s in self.mover.active_stages]
        self._available_stages = [
            s for s in self._all_available_stages if s not in self._used_stages]

        self._stage_table = None

        self.__setup__()

    def __setup__(self) -> None:
        """
        Setup stage table.
        """
        # Setup table containing all stages
        if self.has_stages_to_select:
            self._stage_table = CustomTable(
                self,
                columns=['ID', 'Description', 'Stage Class', 'Address'],
                rows=[(
                    idx,
                    str(cls.description),
                    str(cls.__name__),
                    str(address)
                ) for idx, (cls, address) in enumerate(self._available_stages)],
                col_width=20,
                selectmode='browse')
        else:
            Label(
                self,
                text="No stages available.",
                foreground="#FF3333"
            ).pack(side=TOP)

    @property
    def has_stages_to_select(self) -> bool:
        """
        Returns True if there are stages to select
        """
        return len(self._available_stages) > 0

    def get_selected_stage_cls(self) -> Stage:
        """
        Return the currently selected stage class.
        """
        selected_stage_tuple = self._get_selected_stage_tuple()
        if selected_stage_tuple:
            return selected_stage_tuple[0]

    def get_selected_stage_address(self) -> Any:
        """
        Return the currently selected stage address.
        """
        selected_stage_tuple = self._get_selected_stage_tuple()
        if selected_stage_tuple:
            return selected_stage_tuple[1]

    def set_selected_stage(
        self,
        stage_cls: Stage,
        stage_address: Any
    ) -> None:
        """
        Set the current selected entry by the stage idx
        """
        try:
            stage_idx = self._available_stages.index(
                (stage_cls, stage_address))
        except ValueError:
            pass
        self._stage_table.select_by_id(stage_idx)

    def _get_selected_stage_tuple(self) -> tuple:
        """
        Helper method to return the current selected stage tuple
        by table ID.
        """
        selected_id = self._stage_table._tree.focus()
        if not selected_id:
            return None

        stage_idx = int(self._stage_table._tree.set(selected_id, 0))
        self.logger.debug('Selected stage ID: %s', stage_idx)
        try:
            return self._available_stages[stage_idx]
        except IndexError as e:
            self.logger.error(
                f"Could not find stage idx {stage_idx} in stage table: {e}")
