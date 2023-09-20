#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import threading
from time import sleep
from tkinter import Button

from LabExT.Measurements.MeasAPI import MeasParamInt, MeasParamFloat, MeasParamString
from LabExT.View.Controls.ParameterTable import ParameterTable
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
        # center wavelength of observed signal
        'powermeter wavelength': MeasParamFloat(value=1550.0, unit='nm'),
        # which channels to interrogate
        'channels to plot (comma separated)': MeasParamString(value='1')
    }

    INSTRUMENT_TYPE = 'Power Meter'
    CARD_TITLE = 'Poll Power Meter Channels'
    PLOTTING_ENABLED = True

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

        # create basics GUI elements from super class
        super().__init__(parent, controller, model)
        content_frame = self.content_frame  # created in constructor of super class
        content_frame.columnconfigure(0, minsize=120)
        content_frame.columnconfigure(1, minsize=120)
        content_frame.columnconfigure(2, minsize=120)
        content_frame.columnconfigure(3, weight=4)

        # thread-control related
        self.stop_thread = False
        self.thread_finished = True

        # row 0: parameter table
        self.ptable = ParameterTable(content_frame)
        self.ptable.title = 'Parameters'
        self.ptable.parameter_source = self.default_parameters.copy()
        self.ptable.grid(row=0, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # row 1: control buttons
        self.enable_button = Button(content_frame,
                                    text="Start PM",
                                    command=lambda: self.start_pm(self.ptable.to_meas_param()))
        self.enable_button.grid(row=1, column=0, padx=2, pady=2, sticky='NESW')
        self.disable_button = Button(content_frame,
                                     text="Stop PM",
                                     command=lambda: self.stop_pm())
        self.disable_button.grid(row=1, column=1, padx=2, pady=2, sticky='NESW')
        self.update_button = Button(content_frame,
                                    text="Update Settings",
                                    command=lambda: self.update_pm_errpopup(self.ptable.to_meas_param()))
        self.update_button.grid(row=1, column=2, padx=2, pady=2, sticky='NESW')

        # register which buttons to enable / disable on state change
        self.buttons_active_when_settings_enabled.append(self.enable_button)
        self.buttons_inactive_when_settings_enabled.append(self.disable_button)
        self.buttons_inactive_when_settings_enabled.append(self.update_button)

    @show_errors_as_popup()
    def start_pm(self, parameters):
        """
        Sets up the pm and starts it.
        """
        if self.card_active.get():
            raise RuntimeError('Cannot start pm when already started.')

        for pd in self.plotdata_to_show.values():
            self.model.plot_collection.remove(pd)
        self.plotdata_to_show.clear()

        loaded_instr = self.load_instrument_instance()
        loaded_instr.open()
        self.instrument = loaded_instr

        # ToDo - nice to have would be saving existing instrument parameters and restoring them afterwards

        # do the first setting of params
        self.update_pm(parameters)

        # Startet die Motoren!
        self._start_polling()

        self.card_active.set(True)

    def _start_polling(self):
        """ start polling thread """
        th = threading.Thread(target=lambda: self.poll_pm(), name="live viewer measurement")
        self.active_thread = th
        self.stop_thread = False
        self.thread_finished = False
        th.start()

    def _stop_polling(self):
        """ stop polling thread (busy wait until thread terminated) """
        self.stop_thread = True

        # the following block is needed for a few reasons. We want for the polling thread to be finished, to make sure
        # there are no requests or communications to the instruments left pending. If we however do not call the
        # update_idletasks() function, the plot window cannot update (as we, the main thread are waiting in a spinlock,
        # and in tk only the main thread is allowed to alter GUI elements), and therefore the thread will never exit,
        # leading to a deadlock. Hence we manually update the TK GUI, and allow the thread to finish.
        while not self.thread_finished:
            self.update_idletasks()
            self.update()
            sleep(1e-6)

        # # since we know that the thread finished, we can now join the thread without risking a deadlock
        # if self.active_thread is not None:
        #     self.active_thread.join()

    @show_errors_as_popup()
    def stop_pm(self):
        """
        Stops the pm.
        """
        self._stop_polling()

        if self.instrument is not None:
            # ToDo: would be nice to restore saved parameters here
            self.instrument.close()
            self.instrument = None

        self.card_active.set(False)

    @show_errors_as_popup()
    def update_pm_errpopup(self, *args, **kwargs):
        self.update_pm(*args, **kwargs)

    def update_pm(self, parameters):
        """
        Updates the power meters parameters.
        """
        loaded_instr = self.instrument
        if loaded_instr is None:
            raise RuntimeError('Instrument pointer is None, instrument is not loaded so cannot update.')

        pm_range = parameters['powermeter range'].value
        pm_atime = parameters['powermeter averagetime'].value
        pm_wavelength = parameters['powermeter wavelength'].value

        # validate chosen channels before changing anything
        channel_designators = [str(c).strip() for c in
                               str(parameters['channels to plot (comma separated)'].value).split(',')]
        valid_channels = [str(v) for v in loaded_instr.instrument_config_descriptor['channels']]
        for ac in channel_designators:
            if str(ac) not in valid_channels:
                raise ValueError(f'Channel {ac:s} is not a valid channel designator. Valid channels: {valid_channels}')

        self._stop_polling()

        # remove plots for previously enabled, now disabled channels
        to_remove = []
        for ac, plot in self.plotdata_to_show.items():
            if ac not in channel_designators:
                self.model.plot_collection.remove(plot)
                to_remove.append(ac)
        for ac in to_remove:
            self.plotdata_to_show.pop(ac)

        # add plots for previously disabled, now enabled channels
        for ac in channel_designators:
            if ac in self.plotdata_to_show:
                continue
            plot = PlotData(ObservableList(), ObservableList(), color=self.color, label=f'Ch{ac:s}')
            plot.x.extend([x for x in range(self.model.plot_size)])
            plot.y.extend([float('nan') for _ in range(self.model.plot_size)])
            self.plotdata_to_show[ac] = plot  # this keeps track of this card's plots
            self.model.plot_collection.append(plot)  # this puts the plot data onto the live viewer plot

        for ac in self.plotdata_to_show.keys():
            with loaded_instr.thread_lock:
                loaded_instr.channel = ac
                loaded_instr.wavelength = pm_wavelength
                loaded_instr.averagetime = pm_atime
                loaded_instr.unit = 'dBm'
                loaded_instr.range = pm_range
                loaded_instr.trigger(continuous=False)

        self._start_polling()

    @show_errors_as_popup()
    def poll_pm(self):
        """
        Function to be run in a thread, continuously polls the pm
        """
        while not self.stop_thread:
            with self.instrument.thread_lock:
                for ac, plot in self.plotdata_to_show.items():
                    self.instrument.channel = ac
                    self.instrument.trigger()
                    power_data = self.instrument.fetch_power()
                    del plot.y[0]
                    plot.y.append(power_data)
            sleep(1e-6)

        self.thread_finished = True

    def stop_instr(self):
        """
        This function is needed as a generic stopping function.
        """
        self.stop_pm()
