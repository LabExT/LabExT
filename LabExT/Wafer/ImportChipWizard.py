#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING
from tkinter import LEFT, RIGHT, Button, Label, TOP, X, OptionMenu, StringVar

from LabExT.View.Controls.Wizard import Wizard, Step

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.View.Controls.CustomFrame import CustomFrame
else:
    Tk = None
    ExperimentManager = None
    CustomFrame = None


class ImportChipWizard(Wizard):
    def __init__(self, master: Tk, experiment_manager: ExperimentManager) -> None:
        super().__init__(
            parent=master,
            width=800,
            height=600,
            on_cancel=None,
            on_finish=None,
            with_sidebar=True,
            with_error=True,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish",
        )
        self.experiment_manager = experiment_manager

        self.title("Import Chip")

        self.step_chip_source_selection = ChipSourceSelection(self)

        # load all available source steps
        self.source_config_steps_insts = {
            name: _class(wizard=self) for name, _class in self.experiment_manager.chip_source_api.chip_sources.items()
        }
        for step in self.source_config_steps_insts.values():
            step.previous_step = self.step_chip_source_selection

        self.current_step = self.step_chip_source_selection


class ChipSourceSelection(Step):
    def __init__(self, wizard) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Select Data Source")

        self.source_options_sel_var = None

        self.next_step = "I'm an ugly hack."
        self.next_step_enabled = True
        self.on_next = self._on_next

    def build(self, frame: CustomFrame):
        frame.title = "Select Data Source"

        source_options = list(self.wizard.experiment_manager.chip_source_api.chip_sources.keys())
        if not source_options:
            Label(frame, text="No chip sources available. Cannot continue.").pack(side=TOP, fill=X)
            self.wizard.set_error("No chip sources available.")
            return
        
        self.source_options_sel_var = StringVar(self.wizard, source_options[0])
        Label(frame, text="Choose which manifest importer / chip source to use:").pack(side=TOP)
        OptionMenu(frame, self.source_options_sel_var, *source_options).pack(side=TOP, fill=X)

    def _on_next(self):
        next_step_name = self.source_options_sel_var.get()
        self.next_step = self.wizard.source_config_steps_insts[next_step_name]
        return True
