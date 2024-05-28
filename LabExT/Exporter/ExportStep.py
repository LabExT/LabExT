#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING
from tkinter import TOP, X, END, StringVar, Entry, Button, filedialog
from tkinter.ttk import Treeview, Label
import json
from copy import deepcopy

from LabExT.Utils import run_with_wait_window
from LabExT.View.Controls.Wizard import Step
from LabExT.Measurements.MeasAPI.Measparam import MeasParamString
from LabExT.View.Controls.ParameterTable import ParameterTable

if TYPE_CHECKING:
    from LabExT.Exporter.ExportWizard import ExportWizard
    from LabExT.View.Controls.CustomFrame import CustomFrame
else:
    ExportWizard = None
    Device = None
    CustomFrame = None


class ExportFormatStep(Step):
    """ 
    Base class for export format steps. 

    Normally, this class should be subclassed to implement the _export method.
    The _export method should call export_success when it is done.
    You can also override the build and build_overview methods to customize the step.

    The build method is used to create the GUI elements to configure the export.
    The build_overview method is used to show a confirmation of a successful export.

    By default, the build method promps the user for a directory and makes the result available in self.export_path.get().
    """
    
    FORMAT_TITLE = "Example Export Format Step (change me)"

    def __init__(self, wizard: ExportWizard) -> None:
        super().__init__(wizard=wizard, builder=self.build, title=self.FORMAT_TITLE)

        self._root = wizard.master
        self.on_next = self._on_next

    def build(self, frame: CustomFrame):
        """ Default implementation of the build method -- a single file path selection. """
        frame.title = self.FORMAT_TITLE

        self.export_path = StringVar(self._root, value=self.wizard.experiment_manager.exp._default_save_path)

        Label(frame, text="export directory:").grid(row=2, column=0, padx=5, sticky='w')
        Entry(frame, width=50, textvariable=self.export_path).grid(row=2, column=1, padx=5, sticky='we')
        Button(frame, text='Browse', command=lambda: self.export_path.set(filedialog.askdirectory())).grid(row=2, column=3, padx=5, sticky='e')

    def build_overview(self, frame: CustomFrame):
        """ Default implementation of the build_overview method -- shows exported data. """

        treeview = Treeview(frame)
        data = {}

        for measurement in self.wizard.selected_data:
            chip_title = f"ID {measurement['device']['id']} - chip {measurement['chip']['name']}"
            measurement_title = measurement["measurement name"]

            if not data.get(chip_title):
                data[chip_title] = []
            
            data[chip_title].append(measurement_title)
        
        for chip_title, measurements in data.items():
            chip_node = treeview.insert("", END, text=chip_title)
            for measurement_title in measurements:
                treeview.insert(chip_node, END, text=measurement_title)
            treeview.item(chip_node, open=True)
        treeview.pack(side=TOP, fill=X, padx=10, pady=(10, 5))


    def _on_next(self):        
        run_with_wait_window(
            self.wizard.master,
            "Exporting ...",
            lambda: self._export(deepcopy(self.wizard.selected_data))
        )
        
        return True
  
    def _export(self, data):
        raise NotImplementedError("Must be overridden by subclass.")

    def export_success(self):
        self.next_step_enabled = True
        self.wizard.__reload__()
        self.wizard.set_error("Data exported successfully!")
