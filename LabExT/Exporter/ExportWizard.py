#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING
from tkinter import BOTH, Label, TOP, X, OptionMenu, StringVar, Frame
from LabExT.View.Controls.DeviceTable import DeviceTable

from LabExT.View.Controls.Wizard import Wizard, Step
from tkinter import Tk, Toplevel, Button
from LabExT.View.MeasurementTable import MeasurementTable

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.View.Controls.CustomFrame import CustomFrame
    from LabExT.Wafer.Chip import Chip
else:
    Tk = None
    ExperimentManager = None
    CustomFrame = None
    Chip = None


class ExportWizard(Wizard):
    def __init__(self, master: Tk, experiment_manager: ExperimentManager) -> None:
        super().__init__(
            parent=master,
            width=800,
            height=600,
            on_cancel=None,
            with_sidebar=True,
            with_error=True,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish",
        )
        self.experiment_manager = experiment_manager

        self.title("Export Data")

        self.step_export_format_selection = ExportFormatSelection(self)

        self.selected_data = None

        # load all available source steps
        self.source_config_steps_insts = {
            _class.FORMAT_TITLE: _class(wizard=self) for name, _class in self.experiment_manager.export_format_api.export_formats.items()
        }

        self.step_final_overview = ShowExportResult(self)

        # connect steps
        for step in self.source_config_steps_insts.values():
            step.previous_step = self.step_export_format_selection
            step.next_step = self.step_final_overview

        self.current_step = self.step_export_format_selection


class ExportFormatSelection(Step):
    def __init__(self, wizard) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Select Export Format")

        self.source_options_sel_var = None

        self.next_step = "I'm an ugly hack."
        self.next_step_enabled = False
        self.on_next = self._on_next

        self._meas_table = None

    def build(self, frame: CustomFrame):
        frame.title = "Select Export Format"
    
        source_options = [option.FORMAT_TITLE for option in self.wizard.experiment_manager.export_format_api.export_formats.values()]
        if not source_options:
            Label(frame, text="No export formats available. Cannot continue.").pack(side=TOP, fill=X)
            self.wizard.set_error("No export formats available.")
            return
        
        if not self.next_step_enabled:
            self.wizard.set_error("Select at least one measurement to export.")
        else:
            self.wizard.set_error("")

        # ###################
        # _MEASUREMENT TABLE_
        # ###################e

        old_selected = None

        if self._meas_table is not None:
            old_selected = self._meas_table.selected_measurements

        self._meas_table = MeasurementTable(parent=frame,
            experiment_manager=self.wizard.experiment_manager,
            total_col_width=750,
            do_changed_callbacks=False,
            allow_only_single_meas_name=False)

        self._meas_table.title = "Finished Measurements"
        self._meas_table._tree._checkbox_callback = self._on_table_click
        self._meas_table.grid(row=0, column=0, padx=5, pady=5, sticky="nswe")
        # this is an event so we can make sure all events are executed on the table before we potentially reload the window
        self.wizard.parent.bind("<<ExportMeasurementSelect>>", self._check_enable_next)

        self._meas_table.regenerate()
        
        if old_selected is not None:
            for id in old_selected.keys():
                self._meas_table.click_on_meas_by_hash(id)
        
        self._select_all_button = Button(
            frame,
            text='Toggle All Measurements',
            command=self._meas_table.click_on_all)
        self._select_all_button.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        # enable scaling
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        if self.source_options_sel_var is None:
            self.source_options_sel_var = StringVar(self.wizard, source_options[0])

        frame.add_widget(Label(frame, text="Choose which export format to use:"))
        frame.add_widget(OptionMenu(frame, self.source_options_sel_var, *source_options))

    def _on_table_click(self, item_iid, new_state):
        self._meas_table.select_item(item_iid, new_state)
        self.wizard.parent.event_generate("<<ExportMeasurementSelect>>", when="tail")

    def _check_enable_next(self, _):
        next_step_should_be_enabled = len(self._meas_table.selected_measurements.values()) > 0

        if next_step_should_be_enabled != self.next_step_enabled:
            self.next_step_enabled = next_step_should_be_enabled
            self.wizard.__reload__()

    def _on_next(self):
        self.wizard.selected_data = [v for v in self._meas_table.selected_measurements.values()]
        
        next_step_name = self.source_options_sel_var.get()
        self.next_step = self.wizard.source_config_steps_insts[next_step_name]
        self.wizard.step_final_overview.previous_step = self.next_step
        return True


class ShowExportResult(Step):
    def __init__(self, wizard) -> None:
        super().__init__(
            wizard, builder=self.build, title="Overview of Exported Data"
        )
        self.finish_step_enabled = True

    def build(self, frame: CustomFrame):
        frame.title = "Overview of Exported Data"
        self.previous_step.build_overview(frame)
     
