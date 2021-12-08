#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Button, Toplevel, DISABLED, NORMAL

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.ApplicationView import ApplicationView

class MovementWizardView(ApplicationView):
    def __init__(self, parent, controller, mover) -> None:
        self.parent = parent
        self.controller = controller
        self.mover = mover

        self.main_window = Toplevel(self.parent)
        self.main_window.title("Movement Wizard")
        self.main_window.rowconfigure(2, weight=1)
        self.main_window.columnconfigure(0, weight=1)
        self.main_window.focus_force()

        self._selection_table = None

    def connection_frame(self, row=1) -> None:
        connection_frame = CustomFrame(self.main_window)
        connection_frame.title = "Stage Connection Manager"
        connection_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky='nswe')
        connection_frame.columnconfigure(1, weight=1)

        available_stages_frame = CustomFrame(connection_frame)
        available_stages_frame.title = "Available Stages"
        available_stages_frame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky='nswe')
        available_stages_frame.columnconfigure(0, weight=1)
        available_stages_frame.rowconfigure(0, weight=1)

        self._selection_table = CustomTable(
            parent=available_stages_frame,
            columns=('ID', 'Stage Description', 'Stage Class', 'Connection Type', 'Connection Address', 'Connected', 'Status'),
            rows=[(
                id,
                s.__class__._META_DESCRIPTION,
                s.__class__.__name__,
                s.__class__._META_CONNECTION_TYPE,
                s.address.encode('utf-8'),
                s.connected,
                s.get_status() if s.connected else '-- NO STATUS --'
            ) for id, s in enumerate(self.mover.stages)],
            selectmode='extended'
        )

        Button(
            connection_frame,
            text="Connect to all", 
            state=NORMAL if not self.mover.all_connected else DISABLED,
            command=self.controller.connect_to_all_stages,
            width=15
        ).grid(row=3, column=0, padx=5, pady=5, sticky='w')

        Button(
            connection_frame,
            text="Connect to selected",
            state=NORMAL if not self.mover.all_connected else DISABLED,
            command=self._on_selected_connect,
            width=15
        ).grid(row=3, column=1, padx=5, pady=5, sticky='w')

        Button(
            connection_frame,
            text="Disconnect to all",
            state=NORMAL if not self.mover.all_disconnected else DISABLED,
            command=self.controller.disconnect_to_all_stages,
            width=15
        ).grid(row=3, column=2, padx=5, pady=5, sticky='w')

        Button(
            connection_frame,
            text="Disconnect to selected",
            state=NORMAL if not self.mover.all_disconnected else DISABLED,
            command=self._on_selected_disconnect,
            width=15
        ).grid(row=3, column=3, padx=5, pady=5, sticky='w')

    #
    # Callbacks
    #        

    def _on_selected_connect(self):
        for iid in self._get_selected_stage():
            self.controller.connect_to_single_stage_by_poll_index(int(self._selection_table.get_tree().set(iid, 0)))

    def _on_selected_disconnect(self):
        for iid in self._get_selected_stage():
            self.controller.disconnect_to_single_stage_by_poll_index(int(self._selection_table.get_tree().set(iid, 0)))

    #
    # Helpers
    #

    def _get_selected_stage(self):
        iids = self._selection_table.get_tree().selection()
        if not iids:
            self.error = "Please select at least one stage."
            return []
        return iids
