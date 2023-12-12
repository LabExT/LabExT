#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from typing import Callable

from LabExT.View.MeasurementTable import SelectionChangedEvent


class PlottableDataHandler:
    """The `PlottableDataHandler` creates a `PlottableData` object when the measurement selection changes.

    This object can be seen by the `PlotView` which will update its settings and its plot accordingly.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        pass

    @property
    def measurement_selection_changed_callback(self) -> Callable[[SelectionChangedEvent], None]:
        """This is the callback that should be registered with the `MeasurementTable`."""
        return self._on_selection_change

    def _on_selection_change(self, selection_changed_event: SelectionChangedEvent) -> None:
        """This method is called, when the selection of measurements in the `MeasurementTable` changes"""
        self._logger.debug("Recalculating plottable data, because of changed selection...")
        item_hash, is_checked, selection, measurement = selection_changed_event
        self._logger.debug("Done recalculating plottable data")
