#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from tkinter import TOP, X, Button, messagebox
from typing import TYPE_CHECKING

import numpy as np

from LabExT.Measurements.MeasAPI.Measparam import MeasParamString
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.Wafer.Device import Device
from LabExT.Wafer.ChipSourceAPI import ChipSourceStep

if TYPE_CHECKING:
    from LabExT.View.Controls.CustomFrame import CustomFrame
else:
    CustomFrame = None


class IBMMaskDescription(ChipSourceStep):

    CHIP_SOURCE_TITLE = "IBM mask description json file"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.option_table = None
        self.load_button = None

    def build(self, frame: CustomFrame):
        frame.title = self.CHIP_SOURCE_TITLE

        if self.option_table is not None:
            params = self.option_table.to_meas_param()
        else:
            params = {
                "file path": MeasParamString(value="", extra_type="openfile"),
                "chip name": MeasParamString(value="Chip1"),
            }

        self.option_table = ParameterTable(frame)
        self.option_table.pack(side=TOP, fill=X, padx=10, pady=(10, 5))
        self.option_table.title = "IBM manifest file"
        self.option_table.parameter_source = params

        self.load_button = Button(frame, text="Load File", command=self._load_json_device_info)
        self.load_button.pack(side=TOP, padx=10, pady=5, anchor="e")

    def _load_json_device_info(self):
        """
        Load device information from a json file.

        This is the IBM mask design standard description file format.

        If the information does not contain in- or outputs, both are
        set to [0, 0], if no type is specified it is set to 'No type',
        if no ID is provided, the device will be skipped and not
        initialised.
        """
        user_given_params = self.option_table.to_meas_param()
        file_path = user_given_params["file path"].value
        chip_name = user_given_params["chip name"].value

        # try decoding JSON
        try:
            with open(file_path, "r") as fp:
                raw_data = json.load(fp)
        except json.JSONDecodeError as e:
            title = "JSON Decode Error"
            msg = f"JSON format could not be decoded, error: {str(e):s}"
            self.wizard.logger.error(msg)
            messagebox.showerror(title=title, message=msg)
            return

        self.wizard.logger.info("Loading device information from JSON based description file.")
        devices = []
        for device in raw_data:
            # pop parameters from device's dictionary
            try:
                identifier = str(device.pop("ID"))
            except KeyError:
                self.wizard.logger.debug("Could not find ID in current device, skipping...")
                continue
            try:
                inputs = device.pop("Inputs")
                if len(inputs) > 1:
                    self.wizard.logger.warning(
                        "Found multiple input coordinates on device with ID: "
                        + "{:s}, ignoring all but the first one.".format(str(identifier))
                    )
                inputs = inputs[0]
            except KeyError:
                self.wizard.logger.debug("Could not find any inputs, set to [0,0]")
                inputs = [0.0, 0.0]
            try:
                outputs = device.pop("Outputs")
                if len(outputs) > 1:
                    self.wizard.logger.warning(
                        "Found multiple output coordinates on device with ID: "
                        + "{:s}, ignoring all but the first one.".format(str(identifier))
                    )
                outputs = outputs[0]
            except KeyError:
                self.wizard.logger.debug("Could not find any outputs, set to [0,0]")
                outputs = [0.0, 0.0]
            try:
                _type = str(device.pop("Type"))
            except KeyError:
                self.wizard.logger.debug("Could not find type, set to default")
                _type = "No type"

            dev = Device(id=identifier, in_position=inputs, out_position=outputs, type=_type, parameters=device)
            devices.append(dev)

        self.submit_chip_info(name=chip_name, path=file_path, devices=devices)
