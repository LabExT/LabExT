#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import queue
import tkinter
from functools import wraps
from typing import TYPE_CHECKING, Dict, Optional, List
from tkinter import Frame, Button, Label, messagebox, BooleanVar

from LabExT.Utils import get_visa_address
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.InstrumentSelector import InstrumentRole, InstrumentSelector

if TYPE_CHECKING:
    from LabExT.Measurements.MeasAPI.Measurement import MEAS_PARAMS_TYPE
    from tkinter import Tk
    from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
    from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel
    from logging import Logger
    from LabExT.Instruments.InstrumentAPI import Instrument
    from threading import Thread
else:
    MEAS_PARAMS_TYPE = None
    Tk = None
    LiveViewerController = None
    LiveViewerModel = None
    Logger = None
    Instrument = None
    Thread = None


def show_errors_as_popup(caught_err_classes=(Exception,)):
    """ Catches the error classes specified in the argument and shows a TKinter messagebox. """

    def decorator(func):
        @wraps(func)
        def new_func(*args, **kwargs):
            try:
                retval = func(*args, **kwargs)
                return retval
            except caught_err_classes as E:
                # If an error which is a (sub-)class of any in caught_err_classes, we catch it and display it in an
                # message box and put an error message to the logger.
                try:
                    # This line works if this decorator is used for CardFrame sub-classes.
                    parent = args[0].controller.view.main_window
                except:
                    # If this decorator is used outside, we cannot find the parent window reference for now.
                    # Setting the parent to None displays the message box ontop the Tk root (= LabExT main window)
                    parent = None
                    logging.getLogger().debug('Decorator show_errors_as_popup is used outside CardFrame! '
                                              'Displaying messagebox with Tk-root as parent.')
                logging.getLogger().error(str(E))
                messagebox.showerror('Error', str(E), parent=parent)

        return new_func

    return decorator


class CardFrame(Frame):
    """
    Parent class for all cards. Contains functions that inherited card types must follow.
    """

    INSTRUMENT_TYPE: str = 'FILL ME'
    CARD_TITLE: str = 'FILL ME'

    default_parameters: MEAS_PARAMS_TYPE = {}

    def __init__(self, parent: Tk, controller: LiveViewerController, model: LiveViewerModel):

        # refs to LiveViewer objects
        self.model: LiveViewerModel = model
        self.controller: LiveViewerController = controller

        # root window where I will be placed
        self._root: Tk = parent
        # logger, is always handy
        self.logger: Logger = logging.getLogger()

        # card attributes
        self.instance_title: str = f'{self.CARD_TITLE:s} {self.model.next_card_index:d}'
        self.model.next_card_index += 1
        self.instrument: Optional[Instrument] = None  # reference to instantiated instrument driver
        self.active_thread: Optional[Thread] = None  # reference to sub-thread (used for polling etc.)
        self.data_to_plot_queue = queue.SimpleQueue()
        self.card_active = BooleanVar(master=parent, value=False)  # indicator if card is active or not
        self.card_active.trace('w', self._card_active_status_changed)

        self.last_instrument_type: str = ""  # keep instrument info for saving out traces to file

        # keep my references which buttons to gray out when
        self.buttons_active_when_settings_enabled: List[Button] = []
        self.buttons_inactive_when_settings_enabled: List[Button] = []

        # setup my main frame, its 3 rows by 3 columns
        Frame.__init__(self, parent, relief="groove", borderwidth=2)
        self.columnconfigure(0, weight=4)
        self.columnconfigure(1, minsize=100)
        self.columnconfigure(2, weight=4)
        self.columnconfigure(3, weight=4)

        #
        # defining common GUI elements + frame for GUI elements set in sub-class
        #

        # row 0: title
        self.label = Label(self, text=self.instance_title)
        self.label.grid(row=0, column=0, padx=2, pady=2, sticky='NSW')

        # row 0: remove card button
        self.remove_button = Button(self, text="X", command=lambda: controller.remove_card(self))
        self.remove_button.grid(row=0, column=3, sticky='NE')

        # row 1: instrument selector
        self.available_instruments: Dict[str, InstrumentRole] = dict()
        io_set = get_visa_address(self.INSTRUMENT_TYPE)
        self.available_instruments.update({self.INSTRUMENT_TYPE: InstrumentRole(self._root, io_set)})

        self.instr_selec = InstrumentSelector(self)
        self.instr_selec.title = 'Instrument'
        self.instr_selec.instrument_source = self.available_instruments
        self.instr_selec.grid(row=1, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # row 2: parameter table for this card
        self.ptable = ParameterTable(self)
        self.ptable.title = 'Parameters'
        self.ptable.parameter_source = self.default_parameters.copy()
        self.ptable.grid(row=2, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # row 3: user's content frame, filled by subclasses
        self.content_frame = Frame(self)
        self.content_frame.grid(row=3, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

    def load_instrument_instance(self):
        """
        Use this function to get an instance from the instrument selector dropdown.
        """
        selected_instruments = dict()
        for role_name, role_instrs in self.available_instruments.items():
            selected_instruments.update({role_name: role_instrs.choice})

        loaded_instr = self.controller.experiment_manager.instrument_api.create_instrument_obj(self.INSTRUMENT_TYPE,
                                                                                               selected_instruments,
                                                                                               {})

        self.last_instrument_type = loaded_instr.instrument_parameters['class']
        return loaded_instr

    def _card_active_status_changed(self, *args):
        # callback on the card_active variable
        # automatically set GUI elements depending on if card is active or not
        try:
            if self.card_active.get():
                self.disable_settings_interaction()
            else:
                self.enable_settings_interaction()
        except tkinter.TclError:
            # sometimes the card is already destroyed
            # so changes in GUI raise TclError but can safely be ignored
            pass

    def enable_settings_interaction(self):
        # call this function when you want to enable GUI elements for changing settings
        # e.g. on stopping live-polling or closing the instrument connection
        for b in self.buttons_active_when_settings_enabled:
            b["state"] = "active"
        for b in self.buttons_inactive_when_settings_enabled:
            b["state"] = "disable"
        self.instr_selec.enabled = True

    def disable_settings_interaction(self):
        # call this function when you want to disable GUI elements for changing settings
        # e.g. on starting live-polling or opening the instrument connection
        for b in self.buttons_active_when_settings_enabled:
            b["state"] = "disable"
        for b in self.buttons_inactive_when_settings_enabled:
            b["state"] = "active"
        self.instr_selec.enabled = False

    def stop_instr(self):
        raise NotImplementedError
