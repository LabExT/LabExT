#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING, List

from LabExT.View.Controls.Wizard import Step
from LabExT.Wafer.Chip import Chip

if TYPE_CHECKING:
    from LabExT.Wafer.ImportChipWizard import ImportChipWizard
    from LabExT.Wafer.Device import Device
else:
    ImportChipWizard = None
    Device = None


class ChipSourceStep(Step):

    CHIP_SOURCE_TITLE = "Example Chip Source Step (change me)"

    def __init__(self, wizard: ImportChipWizard) -> None:
        super().__init__(wizard=wizard, builder=self.build, title=self.CHIP_SOURCE_TITLE, next_step_enabled=False)

    def build(self):
        raise NotImplementedError("Must be overridden by subclass.")

    def submit_chip_info(self, name: str, path: str, devices=List[Device]):
        self.wizard.submitted_chip = Chip(name=name, path=path, devices=devices)
        self.next_step_enabled = True
        self.wizard.__reload__()
        self.wizard.set_error("Chip manifest loaded successfully!")
