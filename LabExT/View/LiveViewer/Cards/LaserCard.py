#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Label, Button, StringVar

from LabExT.Instruments.InstrumentAPI import InstrumentException
from LabExT.Measurements.MeasAPI import MeasParamFloat
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.LiveViewer.Cards.CardFrame import CardFrame, show_errors_as_popup


class LaserCard(CardFrame):
    """
    Class to represent lasers. Contains functionality to connect, close and update the laser parameters.
    """

    default_parameters = {
        # laser wavelength
        'wavelength': MeasParamFloat(value=1550.0, unit='nm'),
        # laser power in dBm
        'laser power': MeasParamFloat(value=6.0, unit='dBm'),
    }

    # static variable that defines the cards type
    instrument_type = "Laser"

    def __init__(self, parent, controller, model, index):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        index :
            This cards index
        """
        self.INSTRUMENT_TYPE = 'Laser'
        self.PLOTTING_ENABLED = False
        self.laser_enabled_warning_text = StringVar()

        # create basic GUI elements from super class
        super().__init__(parent, controller, model, index)
        content_frame = self.content_frame  # created in constructor of super class
        content_frame.columnconfigure(0, minsize=120)
        content_frame.columnconfigure(1, minsize=120)
        content_frame.columnconfigure(2, minsize=120)
        content_frame.columnconfigure(3, weight=4)

        # row 0: parameter table
        self.ptable = ParameterTable(content_frame)
        self.ptable.title = 'Parameters'
        try:
            self.ptable.parameter_source = self.model.old_params[index]
        except IndexError:
            self.ptable.parameter_source = self.default_parameters.copy()
        self.ptable.grid(row=0, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # row 1: control buttons
        self.enable_button = Button(content_frame, text="Start Laser",
                                    command=lambda: self.start_laser(self.available_instruments,
                                                                     self.ptable.to_meas_param(),
                                                                     self.laser_enabled_warning_text))
        self.enable_button.grid(row=1, column=0, padx=2, pady=2, sticky='NESW')
        self.disable_button = Button(content_frame, text="Stop Laser",
                                     command=lambda: self.stop_laser(self.available_instruments,
                                                                     self.ptable.to_meas_param(),
                                                                     self.laser_enabled_warning_text))
        self.disable_button.grid(row=1, column=1, padx=2, pady=2, sticky='NESW')
        self.update_button = Button(content_frame, text="Update Settings",
                                    command=lambda: self.update_laser(self.available_instruments,
                                                                      self.ptable.to_meas_param(),
                                                                      self.laser_enabled_warning_text))
        self.update_button.grid(row=1, column=2, padx=2, pady=2, sticky='NESW')

        # row 1: laser enabled warning text
        self.label_en = Label(content_frame,
                              text="LASER ENABLED",
                              textvariable=self.laser_enabled_warning_text,
                              width=15)
        self.label_en.grid(row=1, column=3, padx=2, pady=2, sticky='NESW')
        self.label_en.config(fg='#f00')

        # register which buttons to enable / disable on state change
        self.buttons_active_when_settings_enabled.append(self.enable_button)
        self.buttons_inactive_when_settings_enabled.append(self.disable_button)
        self.buttons_inactive_when_settings_enabled.append(self.update_button)

    def tear_down(self):
        """
        Called on card destruction.
        """
        self.stop_laser(None, None, self.laser_enabled_warning_text)

    @show_errors_as_popup()
    def start_laser(self, instr, parameters, warning_variable):
        """
        Sets up the laser and starts it.
        """
        loaded_instr = self.load_instrument_instance()

        loaded_instr.open()

        wavelength = parameters['wavelength'].value
        laser_pwr = parameters['laser power'].value

        with loaded_instr.thread_lock:
            loaded_instr.wavelength = wavelength
            loaded_instr.power = laser_pwr
            loaded_instr.enable = True

        warning_variable.set("LASER ENABLED")

        self.instrument = loaded_instr
        self.enabled = True
        self.disable_settings_interaction()

    @show_errors_as_popup()
    def stop_laser(self, instr, parameters, warning_variable):
        """
        Stops the laser.
        """
        loaded_instr = self.instrument
        if loaded_instr is None:
            return
        with loaded_instr.thread_lock:
            loaded_instr.enable = False
        warning_variable.set("")
        self.enabled = False
        self.enable_settings_interaction()

        self.instrument.close()
        self.instrument = None

    @show_errors_as_popup()
    def update_laser(self, instr, parameters, warning_variable):
        """
        Updates the lasers parameters.
        """
        loaded_instr = self.instrument
        if loaded_instr is None:
            raise InstrumentException("The Laser is currently not enabled")

        wavelength = parameters['wavelength'].value
        laser_pwr = parameters['laser power'].value

        with loaded_instr.thread_lock:
            loaded_instr.wavelength = wavelength
            loaded_instr.power = laser_pwr

    def stop_instr(self):
        """
        This function is needed as a generic stopping function.
        """
        self.stop_laser(None, None, self.laser_enabled_warning_text)
