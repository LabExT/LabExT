#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

from pandas import DataFrame

from LabExT.Measurements.MeasAPI.Measurement import Measurement
from LabExT.Wafer.Device import Device
from LabExT.Utils import make_filename_compliant

class ToDo:
    def __init__(self,
                 device: Device,
                 measurement: Measurement,
                 part_of_sweep: bool = False,
                 sweep_parameters: DataFrame = None,
                 dictionary_wrapper: "DictionaryWrapper" = None):
        """Create a new ToDo
        
        Args:
            device: A reference to the device this measurement should be run on
            measurement: The measurement that should be run
            part_of_sweep: This should only be `True` if this ToDo is part of a sweep
            sweep_parameters: If the `ToDo` is part of a sweep this argument mustn't be `None`
            dictionary_wrapper: If the `ToDo` is part of a sweep this argument mustn't be `None`
        """
        assert (part_of_sweep and sweep_parameters is not None) or not part_of_sweep
        assert (part_of_sweep and dictionary_wrapper is not None) or not part_of_sweep

        self.device = device
        self.measurement = measurement
        self._timestamp = int(time.time() * 1e6)
        self.part_of_sweep = part_of_sweep
        self.sweep_parameters = sweep_parameters

        self.dictionary_wrapper = dictionary_wrapper
        """This reference is shared between all `ToDo`s which are part of the same sweep."""

    def __getitem__(self, item):
        """ make To-Do class compatible with old code which used (device,measurement) tuples as ToDos """
        if item == 0:
            return self.device
        elif item == 1:
            return self.measurement
        else:
            raise KeyError(item)

    def __str__(self):
        return "<ToDo: " + str(self.measurement.get_name_with_id()) + " on " + str(self.device) + ">"

    def __repr__(self):
        return self.__str__()

    def get_hash(self):
        """calculate the unique but hardly one-way functional 'hash' of a to-do"""
        hash = str(self.device)
        hash += str(self.measurement.get_name_with_id())
        hash += str(self._timestamp)
        return hash

class DictionaryWrapper:
    """This class wraps a dictionary and a subfolder name (str).
    
    It acts like a pointer, such that many objects can have a view onto the 
    same data, but the data can be changed as a whole after initialization.

    This is needed for measurements belonging to a sweep. They all need to 
    share the dictionary with the summary information of the sweep, however,
    this is only created once the first measurement is run. To be able to 
    update the references the other measurements use, they are given a reference
    to this wrapper class instead, which holds a reference to the final dictionary
    once it's created.
    """

    def __init__(self, dictionary: dict = None) -> None:
        """Initializes a new `DictionaryWrapper`
        
        Args:
            dictionary: The `dict` that should be wrapped or `None`
        """
        
        self._dictionary = dictionary
        self._subfolder_name = ""

    @property
    def available(self) -> bool:
        """Returns `True` if this wrapper contains a dictionary.
        
        A dictionary can be set with `self.wrap(...)`.
        """
        return self._dictionary is not None

    @property
    def get(self) -> dict:
        """Returns a reference to the wrapped dictionary or `None` if `self.available == False`."""
        return self._dictionary

    def wrap(self, dictionary: dict) -> None:
        self._dictionary = dictionary

    @property
    def subfolder_name(self) -> str:
        """Returns the wrapped subfolder name."""
        return self._subfolder_name

    @subfolder_name.setter
    def subfolder_name(self, new_name) -> None:
        """Sets the wrapped subfolder name."""
        self._subfolder_name = make_filename_compliant(new_name)