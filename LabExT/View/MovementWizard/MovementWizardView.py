#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Button, Toplevel, Label,  DISABLED, NORMAL
from functools import partial
from tkinter import Label, Button, Toplevel, Entry, Checkbutton, messagebox, DISABLED, NORMAL

from LabExT.Movement.Stage import Stage
from LabExT.Movement.MoverNew import MoverNew
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

    def driver_frame(self, row=0):
        driver_frame = CustomFrame(self.main_window)
        driver_frame.title = "Stage Driver Settings"
        driver_frame.grid(row=row, column=0, columnspan=3, padx=5, pady=5, sticky='nswe')
        driver_frame.columnconfigure(0, weight=1)

        Label(
            driver_frame,
            text="Are not all connected stages displayed? Check if all drivers are loaded and reload."
        ).grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky='nswe')

        for id, stage_class in enumerate(self.mover.stage_classes):
            Label(driver_frame, text=stage_class._META_DESCRIPTION, font='Helvetica 12 bold').grid(row=id+1, column=0, padx=5, pady=5, sticky='w')
            Label(
                driver_frame,
                text="Loaded" if stage_class.driver_loaded else "Not Loaded",
                foreground='#4BB543' if stage_class.driver_loaded else "#FF3333",
            ).grid(row=id+1, column=1, padx=5, pady=5)

            if stage_class.driver_specifiable:
                Button(
                    driver_frame,
                    text="Change driver path",
                    command=partial(self._on_driver_change, stage_class)
                ).grid(row=1, column=2, padx=5, pady=5, sticky='w')


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


    def configuration_frame(self, row=2):
        configuration_frame = CustomFrame(self.main_window)
        configuration_frame.title = "Stage Configuration"
        configuration_frame.grid(row=row, column=0,  padx=5, pady=5, sticky='nswe')
        configuration_frame.columnconfigure(0, weight=1)

        stage_reference_frame = CustomFrame(configuration_frame)
        stage_reference_frame.title = "Find Stage Reference"
        stage_reference_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nswe')

        Label(
            stage_reference_frame,
            text="Use this functionality to search for the reference mark and drive into neutral position"
        ).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='nswe')

        self._stage_reference_list(stage_reference_frame, self.mover.connected_stages)

        stage_properties_frame = CustomFrame(configuration_frame)
        stage_properties_frame.title = "Speed and Movement Settings"
        stage_properties_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky='nswe')     

        self._entry_z_movement = self._build_entry_with_label(
            stage_properties_frame,
            row=0,
            label="Z channel up-movement during xy movement:",
            unit="[um]",
            value=self.mover.z_lift
        )

        self._entry_xy_speed = self._build_entry_with_label(
            stage_properties_frame,
            row=1,
            label="Movement speed xy direction (valid range: 0...1e5um/s):",
            unit="[um/s]",
            value=self.mover.speed_xy
        )

        self._entry_z_speed = self._build_entry_with_label(
            stage_properties_frame,
            row=2,
            label="Movement speed z direction (valid range: 0...1e5um/s):",
            unit="[um/s]",
            value=self.mover.speed_z
        )

        Button(
            stage_properties_frame,
            text='Save settings',
            command=self._on_save_settings
        ).grid(row=3, column=0, padx=5, pady=5, sticky='w')

        z_axis_frame = CustomFrame(configuration_frame)
        z_axis_frame.title = "Z-Axis Settings"
        z_axis_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky='nswe')

        self._z_axis_invert_list(z_axis_frame, self.mover.connected_stages)


    #
    # Frame Parts
    #

    def _stage_reference_list(self, parent, stages):
        for idx, stage in enumerate(stages):
            Label(parent, text="Find Reference Mark for {}".format(str(stage))).grid(row=idx, column=0, sticky='W') 
            Button(
                parent,
                text="Find Reference Mark",
                command=partial(self._on_stage_reference, stage)
            ).grid(row=idx, column=1)

    def _z_axis_invert_list(self, parent, stages):
        for idx, stage in enumerate(stages):
            Label(parent, text="Invert Z-Axis for {}".format(str(stage))).grid(row=idx, column=0, sticky='W') 
            checkbox = Checkbutton(parent, command=stage.toggle_z_axis_direction)
            checkbox.grid(row=idx, column=1, sticky='W', padx=(30, 0))
            if stage.z_axis_inverted:
                checkbox.select()
            Button(
                parent,
                text="Wiggle Z-Axis",
                command=partial(self._on_stage_wiggle, stage)
            ).grid(row=idx, column=2)

    def _on_save_settings(self):
        self.controller.save_mover(
            speed_xy=float(self._entry_xy_speed.get()),
            speed_z=float(self._entry_z_speed.get()),
            z_lift=float(self._entry_z_movement.get())
        )

    #
    # Callbacks
    #        

    def _on_selected_connect(self):
        for iid in self._get_selected_stage():
            self.controller.connect_to_single_stage_by_poll_index(int(self._selection_table.get_tree().set(iid, 0)))

    def _on_selected_disconnect(self):
        for iid in self._get_selected_stage():
            self.controller.disconnect_to_single_stage_by_poll_index(int(self._selection_table.get_tree().set(iid, 0)))

    def _on_driver_change(self, stage_class):
         if not stage_class.driver_specifiable:
             return

         if stage_class.load_driver(parent=self.main_window):
             self.controller.load_driver_and_reload(stage_class)

    def _on_stage_wiggle(self, stage):
        message = """By proceeding this button will move {} along the z direction. \n\n
                     Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n
                     For correct operation the stage should: \n
                     First: Move upward \n
                     Second: Move downwards \n\n
                     If not, please invert the z-axis of the stage.\n Do you want to proceed with calibration?
                  """.format(str(stage))
        if messagebox.askokcancel("Warning", message):
            try:
                stage.wiggle_z_axis_positioner()
            except Exception as exc:
                self.error = "Could not wiggle stage: {}".format(exc)

    def _on_stage_reference(self, stage):
        message = "Make sure the stage has enough space to move, while searching for the reference mark." \
                  " The whole travel range needs to be clear of obstacles. Do you want to proceed?"
        if messagebox.askokcancel("Warning", message):
            try:
                stage.find_reference_mark()
            except Exception as exc:
                self.error = "Could not find reference mark: {}".format(exc)


    #
    # Helpers
    #

    def _get_selected_stage(self):
        iids = self._selection_table.get_tree().selection()
        if not iids:
            self.error = "Please select at least one stage."
            return []
        return iids

    def _build_entry_with_label(self, parent, row: int=0, label: str = None, unit: str =None, value: str = None) -> Entry:
        Label(parent, text=label).grid(row=row, column=0, sticky='W') 
        entry = Entry(parent)
        entry.grid(row=row, column=1, sticky='W', padx=(30, 0))
        Label(parent, text=unit).grid(row=row, column=2, sticky='W')
        
        if value:
            entry.delete(0, 'end')
            entry.insert(0, value)

        return entry