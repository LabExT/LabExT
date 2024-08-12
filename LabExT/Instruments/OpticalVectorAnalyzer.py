#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Instruments.InstrumentAPI import Instrument, InstrumentException
import numpy as  np
import win32com.client
import os
import numpy as np
import pythoncom

class OpticalVectorAnalyzer(Instrument):
    """
    ### Optical Vector Analyzer (OVA) ###
    This class is used to control the Optical Vector Analyzer (OVA) from Luna Innovations. There are two available OVAs: 5100 (C-band) and 5113 (O-band).

    The OVA is a high-performance optical spectrum analyzer that provides accurate and reliable test and measurement data for a wide range of optical components and systems. It is based on the proven Michelson interferometer design and is capable of measuring the spectral characteristics of optical signals with high resolution and accuracy.

    The current implementation of the OVA class is based on the LabVIEW SDK provided by Luna Innovations. The SDK provides a set of LabVIEW VIs that can be used to control the OVA and acquire measurement data. The OVA class uses the win32com.client module to interact with the LabVIEW VIs and control the OVA.

    

    #### Methods

    * **grab_data()**: Acquire measurement data from the OVA.

    
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def open(self):
        """
        Open the connection to the OVA. Ensure that the OVA is connected to the computer and the LabVIEW SDK is installed.
        """
        pythoncom.CoInitialize()

        self.labview_app = win32com.client.Dispatch("LabVIEW.Application")

        # Construct the path to the file relative to the module directory
        vi_path = os.path.join(os.path.dirname(__file__), 'LabViewVIs', 'ConfigureOVA.vi')
        vi = self.labview_app.GetVIReference(vi_path)

        vi.Run

        # Grab data in graph object
        instrFound = np.array(vi.GetControlValue("instrFound"))

        CfgOK = np.array(vi.GetControlValue("Cfg OK?"))

        if not instrFound or not CfgOK:
            raise InstrumentException("Instrument Not Found or Config is Wrong")
        else:
            self.logger.debug("Successfully connected to OVA")
            return 

    def grab_data(self, dut_L: float = None, plot_data_type: str = "INSERTION_LOSS", center_wavelength: float = 1550.00, wl_range: float = 2.54, save_all_data: bool = False, filepath: str = 'C:\\Users\\Luna\\Documents\\test.txt', meas_type: str = "Transmission"):
        """
        Acquire measurement data from the OVA.

        :param find_dut_L: bool Find DUT Length
        :param plot_data_type: str Plot Measurement Type
        :param center_wavelength: float Center Wavelength
        :param wl_range: float Wavelength Range
        :param save_all_data: bool flag to save all data
        :param filepath: str filepath to temporarily save all data
        """

        print("opening labview")
        
        vi_path = os.path.join(os.path.dirname(__file__), 'LabViewVIs', 'AcquireSingleScan.vi')
        vi = self.labview_app.GetVIReference(vi_path)

        if center_wavelength > 1400: # Cband
            wl_range_dict = {
                '0.63': 0,
                '1.27': 1,
                '2.54': 2,
                '5.09': 3,
                '10.22': 4,
                '20.58': 5,
                '41.72': 6,
                '85.78': 7
            }
        else: #Oband
            wl_range_dict = {
                '0.88': 0,
                '1.76': 1,
                '3.53': 2,
                '7.08': 3,
                '14.25': 4,
                '28.82': 5,
                '58.97': 6
            }


        plot_data_dict = {
            'INSERTION_LOSS' : 0,
            'GROUP_DELAY' : 1,
            'CHROMATIC_DISPERSION' : 2,
            'POLARIZATION_DEPENDENT_LOSS' : 3,
            'POLARIZATION_MODE_DISPERSION' : 4,
            'LINEAR_PHASE_DEVIATION' : 5,
            'QUADRATIC_PHASE_DEVIATION' : 6,
            'JONES_MATRIX_ELEMENT_AMPLITUDES' : 7,
            'JONES_MATRIX_ELEMENT_PHASES' : 8,
            'TIME_DOMAIN_AMPLITUDE' : 9,
            'TIME_DOMAIN_WAVELENGTH' : 10,
            'MIN_MAX_LOSS' : 11,
            'SECOND_ORDER_PMD' : 12,
            'PHASE_RIPPLE_LINEAR' : 13,
            'PHASE_RIPPLE_QUADRATIC' : 14
        }

        # Set control values if any
        if dut_L > 0.0:
            vi.SetControlValue("Find DUT Length?", False)
            vi.SetControlValue("Length of DUT (m)", dut_L)
        else:
            vi.SetControlValue("Find DUT Length?", True)
        vi.SetControlValue("New Scan", True)
        vi.SetControlValue("Plot Data", True)
        vi.SetControlValue("Graph Sel", plot_data_dict[plot_data_type])
        vi.SetControlValue("Center WL", center_wavelength)
        vi.SetControlValue("WL Range", wl_range_dict[wl_range])
        vi.SetControlValue("Save Data", save_all_data)
        vi.SetControlValue("Output Spreadsheet File Path", filepath)
        vi.SetControlValue("Graph Data to Output", [True] * 20)
        vi.SetControlValue("Filter?", False)
        if meas_type == "Transmission":
            vi.SetControlValue("Meas Type", 1) # 0 for reflection, 1 for transmission
        else:
            vi.SetControlValue("Meas Type", 0) 

        self.logger.debug("Running Luna sweep measurement")

        vi.Run

        # Grab data in graph object
        result = np.array(vi.GetControlValue("Graph"))
        new_dut_L = vi.GetControlValue("Length of DUT (m)")

        # self.save_data()

        return result, new_dut_L

    def close(self):
        pythoncom.CoUninitialize()
        return

    def idn(self):
        return f"OVA"

    def get_instrument_parameter(self):
        return {'idn': self.idn()}