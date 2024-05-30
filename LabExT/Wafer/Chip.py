#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import json
from typing import List, Dict
from LabExT.Utils import get_configuration_file_path

from LabExT.Wafer.Device import Device


class Chip:
    """Chip is the implementation of a chip with devices."""

    CHIP_SAVE_FILE_NAME = "last_imported_chip.json"

    def __init__(self, name: str, devices: List[Device], path: str, _serialize_to_disk: bool = True):
        """Constructor.

        Parameters
        ----------
        name : string
            Name of the Chip.
        path : string
            Path to chip description. Can be file location, URL or something else.
        devices : List[Device]
            Holds all devices objects.
        """
        self._logger = logging.getLogger()
        self._logger.debug("Initialised Chip with name: %s", name)

        self._name = name
        assert isinstance(self._name, str), "Argument 'name' is not a string."
        assert len(self._name) > 0, "Argument 'name' cannot be empty."

        self._devices = devices
        assert isinstance(self._devices, list), "Argument 'devices' is not a list."
        for dev in self._devices:
            assert isinstance(dev, Device), "An element in devices is not of type Device."

        all_dev_ids = [dev.id for dev in self._devices]
        assert len(all_dev_ids) == len(set(all_dev_ids)), "Loaded device IDs must be unique!"

        self._path = path
        assert isinstance(self._path, str), "Argument 'path' is not a string."
        assert len(self._path) > 0, "Argument 'path' cannot be empty."

        # save loaded chip to disk for later easy reload
        if _serialize_to_disk:
            self._serialize()

    @property
    def path(self) -> str:
        """Return the filepath of the chip file."""
        return self._path

    @property
    def name(self) -> str:
        """Return the name of the chip."""
        return self._name

    @property
    def devices(self) -> Dict[str, Device]:
        """Return a dictionary of all devices with device ID as keys."""
        return {device.id: device for device in self._devices}

    def _serialize(self):
        """Saves chip information to disk for later re-use."""
        last_chip_fpath = get_configuration_file_path(self.CHIP_SAVE_FILE_NAME)
        with open(last_chip_fpath, "w") as fp:
            json.dump(
                {"name": self._name, "path": self._path, "devices": [dev.as_dict() for dev in self._devices]}, fp
            )

    @staticmethod
    def load_last_instantiated_chip():
        last_chip_fpath = get_configuration_file_path(Chip.CHIP_SAVE_FILE_NAME)
        with open(last_chip_fpath, "r") as fp:
            loaded_data = json.load(fp)
        return Chip(
            name=loaded_data["name"],
            devices=[Device(**dev_desc) for dev_desc in loaded_data["devices"]],
            path=loaded_data["path"],
            _serialize_to_disk=False,
        )
