#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame, Button, messagebox

from LabExT.Utils import get_visa_address
from LabExT.View.Controls.InstrumentSelector import InstrumentRole
from LabExT.View.Controls.InstrumentSelector import InstrumentSelector


class InstrumentWindow(Frame):
    """Shows all necessary instruments for the selected measurements
    and lets the user choose the VISA addresses for each one of
    them using dropdown menus. This class is part of the
    ExperimentWizard.
    """

    def __init__(self, parent: Tk, experiment_manager, callback=None):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent class
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        super(InstrumentWindow,
              self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()
        self._root = parent
        self.callback = callback
        self._experiment_manager = experiment_manager
        self._root.title = 'Set Instruments'

        self.settings_file_prefix = "InstrumentWindow_instr_"

        self.logger.debug(
            'InstrumentWindow initialised with parent:%s experiment_manager:%s',
            parent, experiment_manager)
        self._all_selectors = {}

        # if the user aborts, this is set to true, used by the ExperimentWizard
        self._abort = False
        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)

        self.grid(row=0, column=0)  # place window in root element

        self.__setup__()  # setup the main window content

    def __on_close__(self):
        """Asks the user if (s)he wants to quit, since this class is
        part of the ExperimentWizard.
        """
        self._save_instr_selections()
        m = messagebox.askyesno('Quit',
                                'Do you want to quit the ExperimentWizard?')
        if m:
            self._root.destroy()
            self._abort = True

    def __setup__(self):
        """Sets up the frame.
        """
        self.logger.debug('Setup InstrumentWindow called.')
        counter = 0

        self.bind('<F1>', lambda e: self._experiment_manager.show_documentation())

        for i, measurement in enumerate(self._experiment_manager.exp.selected_measurements):
            # frame for every measurement
            self._instrument_measurement_table = InstrumentSelector(self)
            self._all_selectors.update({self._instrument_measurement_table: measurement})

            self._instrument_measurement_table.title = measurement.name
            self._instrument_measurement_table.grid(
                row=i,
                column=0,
                columnspan=2,
                padx=5,
                pady=5,
                sticky='w')
            # add instrument to gui
            available_instruments = dict()
            for role_name in measurement.get_wanted_instrument():
                io_set = get_visa_address(role_name)
                available_instruments.update({role_name: InstrumentRole(self._root, io_set)})

            self._instrument_measurement_table.instrument_source = available_instruments

            # load instrument selection from settings file
            self._instrument_measurement_table.deserialize(self.settings_file_prefix + measurement.settings_path)

            counter += 1

        self.continue_button = Button(self._root, text="Continue", command=self._continue)
        self.continue_button.grid(row=counter, column=0, sticky='se')
        self.logger.debug('Finished setup InstrumentWindow')

    def _continue(self):
        """Called by button press. Get the instruments selected and
        set these as the possible instruments in each measurement.
        """
        self.continue_button.config(state="disabled")

        # save instrument selection to settings file
        self._save_instr_selections()

        for m in self._all_selectors.values():
            m.selected_instruments.clear()
        for selector, measure in self._all_selectors.items():
            self.logger.debug('Selector: %s Measure:%s', selector, measure)
            for el, val in selector.instrument_source.items():
                if el in measure.selected_instruments and measure.selected_instruments[el] == val.choice:
                    messagebox.showinfo('Error', 'You cannot choose the same instrument twice')
                    return
                measure.selected_instruments.update({el: val.choice})
                self.logger.debug('Added %s:%s to selected_instruments', el, val.choice)

        try:
            # initialise all the instruments of all selected measurements
            for measure in self._experiment_manager.exp.selected_measurements:
                # show the progress bar

                measure.init_instruments()

            # only if this was successful, we will close this window
            self._root.destroy()

        except Exception as exc:
            self.continue_button.config(state="normal")
            messagebox.showerror("Instruments error!",
                                 "The instrument definition was not successful. Reason: " + repr(exc),
                                 parent=self)
            self.logger.exception("The instrument definition was not successful.")

        else:
            if self.callback is not None:
                self.callback()

    def _save_instr_selections(self):
        """ small helper, call this to save all instrument selections to a settings file """
        for selector, measure in self._all_selectors.items():
            selector.serialize(self.settings_file_prefix + measure.settings_path)
