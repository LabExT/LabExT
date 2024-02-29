#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

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


class PhoenixPhotonics(ChipSourceStep):

    CHIP_SOURCE_TITLE = "PhoeniX Photonics csv file"

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
        self.option_table.title = "PhoeniX manifest file"
        self.option_table.parameter_source = params

        self.load_button = Button(frame, text="Load File", command=self._load_csv_device_info)
        self.load_button.pack(side=TOP, padx=10, pady=5, anchor="e")

    def _load_csv_device_info(self):
        """
        Load device information from a csv file.

        This is the PhoeniX mask design standard description file format.

        Comments start with a % sign, and the rows are formatted like:
        [id] type, left X, left Y, right X, right Y
        """
        user_given_params = self.option_table.to_meas_param()
        file_path = user_given_params["file path"].value
        chip_name = user_given_params["chip name"].value

        try:
            devices = self._decode_phoenics_photonics_csv_file(file_path=file_path)
        except Exception as e:
            title = "CSV Reading Error"
            msg = f"Error reading CSV file. Error message:\n{repr(e)}"
            messagebox.showwarning(title=title, message=msg)
            self.wizard.logger.error(title + " " + msg)
            return

        self.submit_chip_info(name=chip_name, path=file_path, devices=devices)

    @staticmethod
    def _decode_phoenics_photonics_csv_file(file_path: str):

        txt_encodings = ["utf-8", "cp1252"]
        txt_encodings_errors = {k: None for k in txt_encodings}

        for txt_encoding in txt_encodings:
            try:
                dev_raw_data = np.genfromtxt(
                    file_path,
                    comments="%",
                    delimiter=",",
                    # necessary to get strings into ndarray
                    converters={0: lambda s: s.decode(txt_encoding)},
                )
                break
            except Exception as exc:
                txt_encodings_errors[txt_encoding] = repr(exc)
        else:
            raise ValueError(
                f"File {file_path:s} was unable to be decoded with any of these encodings {txt_encodings}. Errors: {txt_encodings_errors}."
            )

        devices = []
        for row_tuple in dev_raw_data:

            # extract id number and type string from first element in tuple
            id_type_strs = row_tuple[0].split("]")
            dev_id = str(id_type_strs[0].replace("[", "").replace("]", "").strip())
            dev_type = str(id_type_strs[1].strip())

            # input and output GC coordinates
            dev_inputs = [row_tuple[1], row_tuple[2]]
            dev_outputs = [row_tuple[3], row_tuple[4]]

            # create device object and store into dict
            dev = Device(id=dev_id, in_position=dev_inputs, out_position=dev_outputs, type=dev_type)
            devices.append(dev)

        return devices
