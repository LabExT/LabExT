#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING
from tkinter import Label, TOP, X

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

        self.current_step = self.step_chip_source_selection


class ChipSourceSelection(Step):
    def __init__(self, wizard) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Select Data Source")

    def build(self, frame: CustomFrame):
        frame.title = "Select Data Source"

        Label(frame, text="Hello World!").pack(side=TOP, fill=X)
