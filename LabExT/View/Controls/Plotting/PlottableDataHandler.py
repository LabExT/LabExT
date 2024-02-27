#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from typing import Callable

from LabExT.View.MeasurementTable import SelectionChangedEvent
from LabExT.Experiments.TypeHints import MeasurementDict

PlottableDataChangedListener = Callable[["PlottableData"], None]
"""This type is used for the callbacks being notified when the plottable data changes.

The callback is called with the new plottable data as its first argument. This is done, 
when the user selects new entries in the measurement tree-view.
"""


class PlottableData:
    """This class represents a container mapping the selected measurements to the measured data.

    It also provides some helper-methods to query information about the represented data. This
    is e.g. the `measurementsMatch` property which conveys information about the types of parameters
    present in the different measurements.

    This class is a read-only class. It should only be modified by the `PlottableDataHandler`
    responsible for it.
    """

    def __init__(self) -> None:
        self.__measurement_map: dict[str, MeasurementDict] = {}
        """This dict is the internal representation of the mapping from hashes to data"""

        self.__common_params: list[str] = []
        """Contains the name of the params available in all of the stored measurements"""

        self.__common_values: list[str] = []
        """Contains the name of the values, i.e. the measured data categories, available in all measurements"""

    def _add_measurement(self, name: str, data: MeasurementDict) -> None:
        """Adds a measurement to the stored data. Raises `AssertionError` if `data` was previously added

        Args:
            name: The hash of the measurement to be added. Mustn't be already contained.
            data: `MeasurementDict` containing the data. Mustn't be already contained.
        """
        assert name not in self.__measurement_map.keys()

        self.__measurement_map[name] = data
        if len(self.__measurement_map) == 1:
            # this is the first data being added
            self.__common_params = data["measurement_params"].keys()
            if len(self.__common_params) == 0:
                self.__common_params = list()
            else:
                self.__common_params = list(self.__common_params)
            self.__common_values = list(data["values"].keys())
            return

        # there is already data -> check common params and values
        for param in self.__common_params.copy():
            if param not in data["measurement_params"]:
                self.__common_params.remove(param)
        for value in self.__common_values.copy():
            if value not in data["values"].keys():
                self.__common_values.remove(value)

    def _remove_measurement(self, name: str) -> None:
        """Removes a measurement from the stored data. Raises `AssertionError` if the measurement is not yet contained.

        Args:
            name: The hash of the measurement to be removed. Must be contained.
        """
        assert name in self.__measurement_map.keys()

        logger = logging.getLogger("LabExT.Core")
        logger.debug(f"Removing {name} from managed plot data...")

        # remove measurement
        del self.__measurement_map[name]

        # check if this was the last measurement
        if len(self.__measurement_map) == 0:
            logger.debug("No shared parameters of values")
            logger.debug("Done removing last measurement")
            self.__common_params.clear()
            self.__common_values.clear()
            return

        # we first have to set the parameters and values to something before we can start comparing to them
        # ugly hack to get the first value of a dict without having to create the full list (using iter and next)
        self.__common_params = next(iter(self.__measurement_map.values()))["measurement_params"]
        self.__common_params = list(self.__common_params.keys())
        self.__common_values = next(iter(self.__measurement_map.values()))["values"]
        self.__common_values = list(self.__common_values.keys())  # we don't want `DictKeys`

        # check for common parameters and values
        for param in self.__common_params.copy():
            for meas in self.__measurement_map.values():
                if param not in meas["measurement_params"]:
                    self.__common_params.remove(param)

        logger.debug(f"New shared parameters: {self.__common_params}")

        for value in self.__common_values.copy():
            for meas in self.__measurement_map.values():
                if value not in meas["values"].keys():
                    self.__common_values.remove(value)

        logger.debug(f"New shared values: {self.__common_values}")
        logger.debug("Done removing measurement")

    def keys(self) -> list[str]:
        """Returns the hashes of the measurements that are stored

        Returns:
            A list of hashes of the underlying measurements.
        """
        return list(self.__measurement_map.keys())

    def values(self) -> list[MeasurementDict]:
        """Returns the measurements that are stored."""
        return list(self.__measurement_map.values())

    def __getitem__(self, key) -> MeasurementDict:
        """Returns a view of the measurement belonging to the hash `key`.

        If `key` is not managed by this data, a `KeyError` is raised.
        """
        return self.__measurement_map[key].copy()

    def __len__(self) -> int:
        """Returns the number of measurements stored by this object."""
        return len(self.__measurement_map)

    @property
    def common_params(self) -> list[str]:
        """The names of the parameters shared by all selected measurements."""
        return self.__common_params.copy()

    @property
    def equal_params(self) -> list[str]:
        """A list of the names of parameters which are equal across all handled measurements."""
        equals = list()
        measurements = list(self.__measurement_map.values())
        for param_name in self.__common_params:
            current_param = measurements[0]["measurement_params"][param_name]
            if all(map(lambda meas: meas["measurement_params"][param_name] == current_param, measurements[1:])):
                equals.append(param_name)
        return equals

    @property
    def unequal_params(self) -> list[str]:
        """A list of the names of parameters which are not equal across all handled measurements."""
        unequals = list()
        measurements = list(self.__measurement_map.values())
        for param_name in self.__common_params:
            current_param = measurements[0]["measurement_params"][param_name]
            if any(map(lambda meas: meas["measurement_params"][param_name] != current_param, measurements[1:])):
                unequals.append(param_name)
        return unequals

    @property
    def common_values(self) -> list[str]:
        """The names of the values shared by all selected measurements."""
        return self.__common_values.copy()


class PlottableDataHandler:
    """The `PlottableDataHandler` creates a `PlottableData` object when the measurement selection changes.

    This object can be seen by the `PlotView` which will update its settings and its plot accordingly.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

        self._managed_data = PlottableData()
        """The `PlottableData` object being handled by `self`."""

        self._data_changed_callbacks: list[PlottableDataChangedListener] = []
        """This list holds the callbacks that are notified if the underlying data object changes.

        This could e.g. be used to update the plotting canvas or the settings frame.
        """

    def add_plottable_data_changed_listener(self, new_listener: PlottableDataChangedListener) -> None:
        """Adds a new listener to be notified when the underlying plottable data changes."""
        if not new_listener in self._data_changed_callbacks:
            new_listener(self._managed_data)
            self._data_changed_callbacks.append(new_listener)

    def remove_plottable_data_changed_listener(self, listener: PlottableDataChangedListener) -> None:
        """Removes the given listener from the list of notified listeners if it is contained in it.

        Args:
            listener: The listener to remove. If it is not yet contained in the list of listeners this is a no-op.
        """
        if listener in self._data_changed_callbacks:
            self._data_changed_callbacks.remove(listener)

    @property
    def measurement_selection_changed_callback(self) -> Callable[[SelectionChangedEvent], None]:
        """This is the callback that should be registered with the `MeasurementTable`."""
        return self._on_selection_change

    def _on_selection_change(self, selection_changed_event: SelectionChangedEvent) -> None:
        """This method is called, when the selection of measurements in the `MeasurementTable` changes"""
        self._logger.debug("Recalculating plottable data, because of changed selection...")

        item_hashes, is_checked, selection_overview, measurement = selection_changed_event

        selected_hashes = [meas for meas, state in selection_overview if state]
        if len(set(self._managed_data.keys()).symmetric_difference(selected_hashes)) == 0:
            self._logger.debug("Data didn't change")
            return

        if type(item_hashes) != list:
            # single item was selected
            item_hashes = [item_hashes]
        if type(measurement) != list:
            # single item was selected
            measurement = [measurement]

        for item_hash, meas in zip(item_hashes, measurement):
            if is_checked and item_hash not in self._managed_data.keys():
                self._managed_data._add_measurement(item_hash, meas)
            elif not is_checked and item_hash in self._managed_data.keys():
                self._managed_data._remove_measurement(item_hash)

        self._logger.debug("Notifying data_changed callbacks")
        for callback in self._data_changed_callbacks:
            callback(self._managed_data)

        self._logger.debug("Done recalculating plottable data")
