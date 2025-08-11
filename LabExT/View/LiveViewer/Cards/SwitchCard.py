#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Label, Button, StringVar
from typing import TYPE_CHECKING

from LabExT.Instruments.InstrumentAPI import InstrumentException
from LabExT.Measurements.MeasAPI import MeasParamInt
from LabExT.View.LiveViewer.Cards.CardFrame import CardFrame, show_errors_as_popup

if TYPE_CHECKING:
    from LabExT.Measurements.MeasAPI.Measurement import MEAS_PARAMS_TYPE
else:
    MEAS_PARAMS_TYPE = None


class SwitchCard(CardFrame):
    """
    Class to represent switches. Contains functionality to connect, close and update the switch parameters.
    """

    default_parameters = {
        'M = 1': MeasParamInt(value=1, unit='N Port'),
        'M = 2': MeasParamInt(value=2, unit='N Port'),
        'M = 3': MeasParamInt(value=3, unit='N Port'),
        'M = 4': MeasParamInt(value=4, unit='N Port'),
    }

    INSTRUMENT_TYPE = 'Switch'
    CARD_TITLE = 'Switch'

    def __init__(self, parent, controller, model):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        """
        self.switch_enabled_warning_text = StringVar()

        # create basic GUI elements from super class
        super().__init__(parent, controller, model)
        content_frame = self.content_frame  # created in constructor of super class
        content_frame.columnconfigure(0, minsize=120)
        content_frame.columnconfigure(1, minsize=120)
        content_frame.columnconfigure(2, minsize=120)
        content_frame.columnconfigure(3, weight=4)

        # row 0: control buttons
        self.enable_button = Button(content_frame, text="Start Switch",
                                    command=lambda: self.start_switch(self.ptable.to_meas_param()))
        self.enable_button.grid(row=0, column=0, padx=2, pady=2, sticky='NESW')
        self.disable_button = Button(content_frame, text="Stop Switch",
                                     command=lambda: self.stop_switch())
        self.disable_button.grid(row=0, column=1, padx=2, pady=2, sticky='NESW')
        self.update_button = Button(content_frame, text="Update Settings",
                                    command=lambda: self.update_switch(self.ptable.to_meas_param()))
        self.update_button.grid(row=0, column=2, padx=2, pady=2, sticky='NESW')

        # register which buttons to enable / disable on state change
        self.buttons_active_when_settings_enabled.append(self.enable_button)
        self.buttons_inactive_when_settings_enabled.append(self.disable_button)
        self.buttons_inactive_when_settings_enabled.append(self.update_button)

    @show_errors_as_popup()
    def start_switch(self, parameters: MEAS_PARAMS_TYPE):
        """
        Sets up the laser and starts it.
        """
        loaded_instr = self.load_instrument_instance()

        loaded_instr.open()

        # This is wrong
        n1 = parameters['M = 1'].value
        n2 = parameters['M = 2'].value
        n3 = parameters['M = 3'].value
        n4 = parameters['M = 4'].value

        with loaded_instr.thread_lock:
            loaded_instr.connect([(1, n1), (2, n2), (3, n3), (4, n4)])

        self.switch_enabled_warning_text.set("SWITCH ENABLED")

        self.instrument = loaded_instr
        self.card_active.set(True)

    @show_errors_as_popup()
    def stop_switch(self):
        """
        Stops the switch.
        """
        loaded_instr = self.instrument
        if loaded_instr is None:
            return
        with loaded_instr.thread_lock:
            loaded_instr.enable = False
        self.switch_enabled_warning_text.set("")
        self.card_active.set(False)

        self.instrument.close()
        self.instrument = None

    @show_errors_as_popup()
    def update_switch(self, parameters: MEAS_PARAMS_TYPE):
        """
        Updates the switch parameters.
        """
        loaded_instr = self.instrument
        if loaded_instr is None:
            raise InstrumentException("The Switch is currently not enabled")
        
        n1 = parameters['M = 1'].value
        n2 = parameters['M = 2'].value
        n3 = parameters['M = 3'].value
        n4 = parameters['M = 4'].value

        with loaded_instr.thread_lock:
            loaded_instr.connect([(1, n1), (2, n2), (3, n3), (4, n4)])

    def stop_instr(self):
        """
        This function is needed as a generic stopping function. Doesn't do anything for the switch.
        """
        self.stop_switch()
