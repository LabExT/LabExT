#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
from typing import List

import numpy as np

from LabExT.Wafer.Device import Device


class Chip:
    """Chip is the implementation of a chip with devices."""

    def __init__(self, name: str = None, devices: List[Device] = None):
        """Constructor.

        Parameters
        ----------
        name : string, optional
            Name of the Chip.
        devices : List[Device], optional
            Holds all devices objects
        """
        self._logger = logging.getLogger()
        self._logger.debug('Initialised Chip with name: %s', name)
        self._path = None
        self._name = name
        self._devices = devices
        if not devices:
            self._devices = []

        self._logger.debug('Number of devices in chip: %s', len(self._devices))

    @property
    def path(self) -> str:
        """ Return the filepath of the chip file. """
        return self._path

    @property
    def name(self) -> str:
        """ Return the name of the chip. """
        return self._name

    @property
    def devices(self) -> dict:
        """ Return a dictionary of all devices with device ID as keys. """
        return {device.id: device for device in self._devices}

    @classmethod
    def from_file(cls, filepath: str, name: str = None):
        """ Create a Chip-instance from a chip file. """
        chip = cls(name=name)
        chip._path = filepath
        chip._load_information()
        return chip

    def _load_information(self):
        """Loads the information contained in chip file and creates
        devices accordingly, adds them to the internal dictionary.
        """
        if self._path is None:
            raise ValueError('There is no file path to load the chip data.')

        self._logger.debug('Starting to load information of chip from file.')
        try:
            with open(self._path) as fp:
                self._load_json_device_info(file_pointer=fp)
            return
        except json.decoder.JSONDecodeError:
            self._logger.info("File {:s} is not JSON format, trying CSV format.".format(self._path))

        self._load_csv_device_info(file_path=self._path)
        return

    def _load_csv_device_info(self, file_path):
        """
        Load device information from a csv file.

        This is the PhoeniX mask design standard description file format.

        Comments start with a % sign, and the rows are formatted like:
        [id] type, left X, left Y, right X, right Y
        """

        # reads each line into a tuple and throws error if there are inconsistencies between lines

        last_exc = None
        for txt_encoding in ['utf-8', 'cp1252']:
            try:
                dev_raw_data = np.genfromtxt(file_path,
                                             comments='%',
                                             delimiter=',',
                                             # necessary to get strings into ndarray
                                             converters={0: lambda s: s.decode(txt_encoding)})
                break
            except Exception as exc:
                last_exc = repr(exc)
                self._logger.warning("CSV reading error when using encoding {:s}. Error: {:s}".format(
                    txt_encoding, last_exc
                ))
        else:
            raise RuntimeError("CSV reading error, no encoding successfully tried. Last error: {:s}".format(
                last_exc
            ))

        for row_tuple in dev_raw_data:

            # extract id number and type string from first element in tuple
            id_type_strs = row_tuple[0].split(']')
            dev_id = str(id_type_strs[0].replace('[', '').replace(']', '').strip())
            dev_type = str(id_type_strs[1].strip())

            # input and output GC coordinates
            dev_inputs = [row_tuple[1], row_tuple[2]]
            dev_outputs = [row_tuple[3], row_tuple[4]]

            # create device object and store into dict
            dev = Device(dev_id, dev_inputs, dev_outputs, dev_type)
            self._devices.append(dev)

    def _load_json_device_info(self, file_pointer):
        """
        Load device information from a json file.

        This is the IBM mask design standard description file format.

        If the information does not contain in- or outputs, both are
        set to [0, 0], if no type is specified it is set to 'No type',
        if no ID is provided, the device will be skipped and not
        initialised.
        """

        # try decoding JSON
        raw_data = json.load(file_pointer)

        self._logger.info("Loading device information from JSON based description file.")
        for device in raw_data:
            # pop parameters from device's dictionary
            try:
                identifier = str(device.pop('ID'))
            except KeyError:
                self._logger.debug('Could not find ID in current device, skipping...')
                continue
            try:
                inputs = device.pop("Inputs")
                if len(inputs) > 1:
                    self._logger.warning("Found multiple input coordinates on device with ID: " +
                                         "{:s}, ignoring all but the first one.".format(str(identifier)))
                inputs = inputs[0]
            except KeyError:
                self._logger.debug('Could not find any inputs, set to [0,0]')
                inputs = [0.0, 0.0]
            try:
                outputs = device.pop("Outputs")
                if len(outputs) > 1:
                    self._logger.warning("Found multiple output coordinates on device with ID: " +
                                         "{:s}, ignoring all but the first one.".format(str(identifier)))
                outputs = outputs[0]
            except KeyError:
                self._logger.debug('Could not find any outputs, set to [0,0]')
                outputs = [0.0, 0.0]
            try:
                _type = device.pop("Type")
            except KeyError:
                self._logger.debug('Could not find type, set to default')
                _type = 'No type'

            dev = Device(identifier, inputs, outputs, _type, device)
            self._devices.append(dev)
