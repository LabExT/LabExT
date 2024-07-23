#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import time

import numpy as np

from LabExT.Instruments.InstrumentAPI import Instrument, InstrumentException


class OscilliscopeTektronixMSO64(Instrument):
    """
    ## OscilliscopeTektronixMSO64
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._net_timeout_ms = kwargs.get("net_timeout_ms", 5000)


    def open(self):
        super().open()
        self._inst.timeout = self._net_timeout_ms
        self._inst.read_termination = '\n'

    def get_waveform_settings(self):
        settings = self.request("WFMO?")

        setting_labels = ["BYT_NR", "BIT_NR", "ENCdg", "BN_Fmt", "ASC_Fmt", "BYT_OR", "WFId", "NR_Pt", "PT_Fmt", "Unknown_1", "XUNit", "XINcr", "XZEro", "PT_Off", "YUNit", "YINcr", "Y_Unknown_2", "YZEro", "DOMain", "WFMTYPe", "Unkwown_3", "Unkonwn_4"]

        settings_dict = {setting_labels[label]: value for label, value in enumerate(settings.split(';'))}
        return settings_dict
    
    def get_waveform(self):
        settings_dict = self.get_waveform_settings()

        print(settings_dict)

        data = self.query_binary_values('CURV?', datatype='h', is_big_endian=True)

        L = int(settings_dict['NR_Pt'])
        vscale = float(settings_dict['YINcr'])
        spacing = float(settings_dict['XINcr'])
        offset = -float(settings_dict["PT_Off"])*spacing
        y_offset = float(settings_dict["YZEro"])

        x_data = np.linspace(0+offset, spacing*L+offset, L).tolist()
        y_data = np.array(data) * vscale + y_offset

        return [x_data, y_data]