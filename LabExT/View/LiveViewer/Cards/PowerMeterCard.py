#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import threading
from time import sleep
from tkinter import Button

from LabExT.Instruments.InstrumentAPI import InstrumentException
from LabExT.Measurements.MeasAPI import MeasParamInt
from LabExT.View.Controls.ParameterTable import ParameterTable, MeasParamFloat
from LabExT.View.Controls.PlotControl import PlotData
from LabExT.View.LiveViewer.Cards.CardFrame import CardFrame, show_errors_as_popup
from LabExT.ViewModel.Utilities.ObservableList import ObservableList


class PowerMeterCard(CardFrame):
    """
    Class to represent power meters. Contains functionality to connect, close and update the PM's parameters.
    """

    # these are the default powermeter parameters
    default_parameters = {
        # range of the power meter in dBm
        'powermeter range': MeasParamInt(value=0, unit='dBm'),
        # integration time of power meter
        'powermeter averagetime': MeasParamFloat(value=0.1, unit='s'),
        # integration time of power meter
        'powermeter wavelength': MeasParamFloat(value=1550.0, unit='nm'),
    }

    # static variable that defines the cards type
    instrument_type = "Power Meter"

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
        self.INSTRUMENT_TYPE = 'Power Meter'
        self.PLOTTING_ENABLED = True

        # create basics GUI elements from super class
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
        self.enable_button = Button(content_frame,
                                    text="Start PM",
                                    command=lambda: self.start_pm(self.available_instruments,
                                                                  self.ptable.to_meas_param(),
                                                                  self.color))
        self.enable_button.grid(row=1, column=0, padx=2, pady=2, sticky='NESW')
        self.disable_button = Button(content_frame,
                                     text="Stop PM",
                                     command=lambda: self.stop_pm(self.available_instruments,
                                                                  self.ptable.to_meas_param()))
        self.disable_button.grid(row=1, column=1, padx=2, pady=2, sticky='NESW')
        self.update_button = Button(content_frame,
                                    text="Update Settings",
                                    command=lambda: self.update_pm(self.available_instruments,
                                                                   self.ptable.to_meas_param()))
        self.update_button.grid(row=1, column=2, padx=2, pady=2, sticky='NESW')

        # register which buttons to enable / disable on state change
        self.buttons_active_when_settings_enabled.append(self.enable_button)
        self.buttons_inactive_when_settings_enabled.append(self.disable_button)
        self.buttons_inactive_when_settings_enabled.append(self.update_button)

    def tear_down(self):
        """
        Called on card destruction.
        """
        self.stop_pm(None, None)

    @show_errors_as_popup()
    def start_pm(self, instr, parameters, color):
        """
        Sets up the pm and starts it.
        """
        if self.initialized:
            self.model.plot_collection.remove(self.plot_data)
            self.initialized = False

        loaded_instr = self.load_instrument_instance()

        loaded_instr.open()

        plot = PlotData(ObservableList(), ObservableList(), color=color)
        self.model.plot_collection.append(plot)

        nopk = self.model.plot_size

        plot.x.extend([x for x in range(nopk)])
        plot.y.extend([float('nan') for _ in range(nopk)])

        pm_range = parameters['powermeter range'].value
        pm_atime = parameters['powermeter averagetime'].value
        pm_wavelength = parameters['powermeter wavelength'].value

        with loaded_instr.thread_lock:
            loaded_instr.wavelength = pm_wavelength
            loaded_instr.averagetime = pm_atime
            loaded_instr.unit = 'dBm'
            loaded_instr.range = pm_range
            loaded_instr.trigger(continuous=False)

        func = lambda: self.poll_pm()

        th = threading.Thread(target=func, name="live viewer measurement")

        self.instrument = loaded_instr
        self.polling_function = func
        self.active_thread = th
        self.enabled = True
        self.plot_data = plot
        self.initialized = True

        self.thread_finished = False
        th.start()
        self.disable_settings_interaction()

    @show_errors_as_popup()
    def stop_pm(self, instr, parameters):
        """
        Stops the pm.
        """
        self.enabled = False
        loaded_instr = self.instrument

        # the following block is needed for a few reasons. We want for the polling thread to be finished, to make sure
        # there are no requests or communications to the instruments left pending. If we however do not call the
        # update_idletasks() function, the plot window cannot update (as we, the main thread are waiting in a spinlock,
        # and in tk only the main thread is allowed to alter GUI elements), and therefore the thread will never exit,
        # leading to a deadlock. Hence we manually update the TK GUI, and allow the thread to finish.
        while not self.thread_finished:
            self.update_idletasks()
            self.update()
        if loaded_instr is None:
            return

        self.enable_settings_interaction()
        # since we know that the thread finished, we can now join the thread without risking a deadlock
        self.active_thread.join()

        self.instrument.close()
        self.instrument = None

    @show_errors_as_popup()
    def update_pm(self, instr, parameters):
        """
        Updates the power meters parameters.
        """
        self.paused = True
        sleep(0.2)

        loaded_instr = self.instrument
        if loaded_instr is None:
            self.paused = False
            return

        pm_range = parameters['powermeter range'].value
        pm_atime = parameters['powermeter averagetime'].value
        pm_wavelength = parameters['powermeter wavelength'].value

        if loaded_instr is not None:
            with loaded_instr.thread_lock:
                loaded_instr.wavelength = pm_wavelength
                loaded_instr.averagetime = pm_atime
                loaded_instr.unit = 'dBm'
                loaded_instr.range = pm_range
                loaded_instr.trigger(continuous=False)
        else:
            raise (InstrumentException("The Power Meter is currently not enabled"))

        self.paused = False

    @show_errors_as_popup()
    def poll_pm(self):
        """
        Function to be run in a thread, continuously polls the pm
        """
        loaded_instr = self.instrument
        plot = self.plot_data

        while self.enabled:
            if self.paused:
                sleep(0.2)
            else:
                with loaded_instr.thread_lock:
                    loaded_instr.trigger()
                    power_current = loaded_instr.fetch_power()
                # add the values to the plot
                del plot.y[0]
                plot.y.append(power_current)

        self.thread_finished = True

    def stop_instr(self):
        """
        This function is needed as a generic stopping function.
        """
        self.stop_pm(None, None)
