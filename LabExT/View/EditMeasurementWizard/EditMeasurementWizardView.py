#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Toplevel, Button, StringVar, OptionMenu, Label

from LabExT.View.Controls.AdhocDeviceFrame import AdhocDeviceFrame
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.View.Controls.InstrumentSelector import InstrumentSelector
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.ScrollableFrame import ScrollableFrame
from LabExT.View.TooltipMenu import CreateToolTip


class WizardWindow(Toplevel):
    def __init__(self, parent):
        Toplevel.__init__(self, parent)
        self.title("New ToDo Wizard")
        screen_height = parent.winfo_screenheight()
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(1000, screen_height - 200, 100, 50))
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.focus_force()


class WizardScrollableFrame(ScrollableFrame):
    def __init__(self, parent):
        ScrollableFrame.__init__(self, parent)
        self.grid(row=1, column=0, sticky='nswe')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bind('<Enter>', self._bound_to_mousewheel)
        self.bind('<Leave>', self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def unbound_mouse_wheel(self):
        self._unbound_to_mousewheel(None)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class EditMeasurementWizardView:
    """
    Creates a new or edits an existing measurement.
    """

    default_text = "..."

    def __init__(self, model, controller, parent, experiment_manager):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self.model = model
        self.controller = controller

        self.root = parent
        self._experiment_manager = experiment_manager

        self._experiment = self._experiment_manager.exp

        self.logger = logging.getLogger()
        self.logger.debug("Initializing EditMeasurementWizard.")

        # reference to toplevel GUI
        self.wizard_window = None
        self.scrollable_frame = None

        # internally used variables
        self._wizard_frame = None

        # user selected variables / GUI elements needed in ViewModel
        self.s0_device_table = None
        self.s0_selected_device_info = None
        self.s0_adhoc_frame = None
        self.s1_meas_name = None
        self.s1_meas_nr = None
        self.s1_meas_nr_label = None
        self.meas_nr_dropdown = None
        self.s2_instrument_selector = None
        self.s3_measurement_param_table = None

        # list to hold the contents of the wizard
        self.section_frames = [None, None, None, None, None]

    def setup_main_window(self):
        """
        Setup to toplevel GUI
        """
        # create wizard window, resizeable in columns, fixed with scrollbar in rows
        self.wizard_window = WizardWindow(self.root)

        self.wizard_window.bind('<F1>', self._experiment_manager.show_documentation)

        # place hint
        hint = "Keyboard Shortcuts: Continue to next stage with Return. Revert to last stage with Escape." \
               "Press F1 for help."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # place scrolling frame into top level window
        self.scrollable_frame = WizardScrollableFrame(self.wizard_window)

        # get the frame for the actual content
        self._wizard_frame = self.scrollable_frame.get_content_frame()
        self._wizard_frame.columnconfigure(0, weight=1)

    def s0_adhoc_device_selection_setup(self):
        """
        Setup stage 0: specify a custom device to measure.
        """
        stage = 0
        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Select Device"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        self.s0_adhoc_frame = stage_frame.add_widget(
            AdhocDeviceFrame(stage_frame),
            row=0, column=0, padx=5, pady=5, sticky='we')
        self.s0_adhoc_frame.title = "Define ad-hoc Device"

        stage_frame.continue_button = Button(stage_frame,
                                             text="Continue",
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=10)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.wizard_window.destroy())
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.controller.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=1, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)

    def s0_chip_device_selection_setup(self):
        """
        Setup stage 0: select the device with loaded chip file to measure.
        """
        stage = 0

        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Select Device"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        self.s0_device_table = DeviceTable(stage_frame, self._experiment_manager)
        stage_frame.add_widget(self.s0_device_table, row=0, column=0, padx=5, pady=5, sticky='we')

        self.s0_selected_device_info = Label(stage_frame, text="Selected device: ")
        stage_frame.add_widget(self.s0_selected_device_info, row=1, column=0, padx=5, pady=5, sticky='w')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Continue",
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=10)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.wizard_window.destroy())
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.model.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)

    def s1_measurement_selection_setup(self):
        """
        Setup stage 1: select which measurement
        """
        stage = 1

        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Select Measurement"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        measurement_list = list(self._experiment.measurement_list.copy())
        measurement_list.sort()

        self.s1_meas_name = StringVar(self.root, self.default_text)
        meas_dropdown = OptionMenu(stage_frame, self.s1_meas_name, *measurement_list)
        ttp = CreateToolTip(experiment_manager=self._experiment_manager,
                            widget=meas_dropdown,
                            stringvar=self.s1_meas_name)
        self.s1_meas_name.trace("w", lambda *args: ttp.change_content())
        stage_frame.add_widget(meas_dropdown, row=0, column=0, padx=5, pady=5, sticky='w')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Continue",
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=10)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.controller.stage_start(stage - 1))
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.controller.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=3, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)

    def s2_instrument_selection_setup(self):
        """
        Setup stage 2: select instruments according to selected measurement
        """
        stage = 2

        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Select Instruments"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        self.s2_instrument_selector = InstrumentSelector(stage_frame)
        self.s2_instrument_selector.title = 'Instruments of ' + str(self.model.s1_measurement.name)
        self.s2_instrument_selector.instrument_source = self.model.s1_available_instruments
        stage_frame.add_widget(self.s2_instrument_selector, row=0, column=0, padx=5, pady=5, sticky='we')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Continue",
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=10)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.controller.stage_start(stage - 1))
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.controller.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=1, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)

    def s3_measurement_parameter_setup(self):
        """
        Setup stage 3: specify measurement parameters
        """
        stage = 3

        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Select Measurement Parameters"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        self.s3_measurement_param_table = ParameterTable(stage_frame,
                                                         store_callback=self.model.s1_measurement.store_new_param)
        self.s3_measurement_param_table.title = 'Parameters of ' + str(self.model.s1_measurement.name)
        self.s3_measurement_param_table.parameter_source = self.model.s1_measurement.get_default_parameter()
        stage_frame.add_widget(self.s3_measurement_param_table, row=0, column=0, padx=5, pady=5, sticky='we')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Continue",
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=10)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.controller.stage_start(stage - 1))
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.controller.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=1, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)

    def s4_final_save_buttons(self):
        """
        Setup stage 4:
        """
        stage = 4

        stage_frame = CustomFrame(self._wizard_frame)
        stage_frame.title = "Save"
        self.section_frames[stage] = stage_frame
        stage_frame.grid(row=stage, column=0, padx=5, pady=5, sticky='we')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Discard and close window.",
                                             command=lambda: self.wizard_window.destroy(),
                                             width=30)
        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        stage_frame.continue_button = Button(stage_frame,
                                             text="Save Measurement to Queue!",
                                             font=("bold",),
                                             command=lambda: self.controller.stage_completed(stage),
                                             width=30)

        # register keyboard shortcuts
        self.wizard_window.bind("<Escape>", lambda event: self.controller.stage_start(stage - 1))
        self.wizard_window.bind("<Return>",
                                callback_if_btn_enabled(lambda event: self.controller.stage_completed(stage),
                                                        stage_frame.continue_button))

        # not using stage_frame.add_widget() to not automatically disable button!
        stage_frame.continue_button.grid(row=0, column=1, padx=5, pady=5, sticky='e')

        stage_frame.columnconfigure(0, weight=1)
        stage_frame.columnconfigure(1, weight=1)
