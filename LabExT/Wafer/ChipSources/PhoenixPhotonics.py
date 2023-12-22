#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING

from LabExT.Wafer.ChipSourceAPI import ChipSourceStep

if TYPE_CHECKING:
    from LabExT.View.Controls.CustomFrame import CustomFrame
else:
    CustomFrame = None



class PhoenixPhotonics(ChipSourceStep):

    CHIP_SOURCE_TITLE = "PhoeniX Photonics csv format"

    def build(self, frame: CustomFrame):

        # todo: fill functionality to import csv file

        pass
