#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from matplotlib.figure import Figure
from matplotlib.axes import Axes

class PlotModel:
    """The model part of the model-view-controller architecture for plotting"""

    def __init__(self) -> None:
        self._figure: Figure = Figure(figsize=(6, 5), dpi=100)
        self._axes: Axes = self._figure.add_subplot()

