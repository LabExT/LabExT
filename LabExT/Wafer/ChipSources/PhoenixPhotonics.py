#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import TOP, X, Button, messagebox
from typing import TYPE_CHECKING, List

import pandas as pd

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
            devices = self._decode_csv_to_devices(filepath=file_path)
        except Exception as e:
            title = "CSV Reading Error"
            msg = f"Error reading CSV file. Error message:\n{repr(e)}"
            messagebox.showwarning(title=title, message=msg)
            self.wizard.logger.error(title + " " + msg)
            return

        self.submit_chip_info(name=chip_name, path=file_path, devices=devices)

    @staticmethod
    def _decode_csv_to_devices(filepath: str) -> List[Device]:

        df = pd.read_csv(filepath, comment="%", header=None)
        df.columns = [f"col{col}" for col in df.columns]
        id_label, input_x, input_y, output_x, output_y = df.columns[:5]

        numeric_cols = [input_x, input_y, output_x, output_y]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        # this separates a string of e.g. "[010101]your-label" to "010101", "your-label"
        df[["ID", "label"]] = df[id_label].str.extract(r"\[(.*?)\]\s*(.*)").apply(lambda s: s.str.strip())

        def _row_to_device(row: tuple) -> Device:
            return Device(
                id=getattr(row, "ID"),
                in_position=[getattr(row, input_x), getattr(row, input_y)],
                out_position=[getattr(row, output_x), getattr(row, output_y)],
                type=getattr(row, "label")
            )

        devices = [_row_to_device(row) for row in df.itertuples()]
        return devices
