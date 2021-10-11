#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from functools import wraps
from tkinter import Frame, Button, Label, colorchooser, messagebox

from LabExT.Utils import get_visa_address
from LabExT.View.Controls.InstrumentSelector import InstrumentRole, InstrumentSelector

colors = {
    0: 'red',
    1: 'purple',
    2: 'blue',
    3: 'green',
    4: 'skyblue',
    5: 'black',
    6: 'orange',
    7: 'yellow'
}


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

    INSTRUMENT_TYPE = 'FILL ME'
    PLOTTING_ENABLED = True

    default_parameters = {}

    def __init__(self, parent, controller, model, index):

        # refs to LiveViewer objects
        self.model = model
        self.controller = controller
        # my index
        self.index = index
        # root window where I will be placed
        self._root = parent
        # logger, is always handy
        self.logger = logging.getLogger()
        # plot color
        self.color = colors.get(index, 'gray')
        # keep my references which buttons to gray out when
        self.buttons_active_when_settings_enabled = []
        self.buttons_inactive_when_settings_enabled = []

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
        self.label = Label(self, text=self.INSTRUMENT_TYPE)
        self.label.grid(row=0, column=0, padx=2, pady=2, sticky='NSW')

        # row 0: color selection button
        if self.PLOTTING_ENABLED:
            self.color_button = Button(self, text="", command=self.choose_color, bg=self.color)
            self.color_button.grid(row=0, column=1, sticky='NESW')

        # row 0: remove card button
        self.remove_button = Button(self, text="X", command=lambda: controller.remove_card(self.index))
        self.remove_button.grid(row=0, column=3, sticky='NE')

        # row 1: instrument selector
        self.available_instruments = dict()
        io_set = get_visa_address(self.INSTRUMENT_TYPE)
        self.available_instruments.update({self.INSTRUMENT_TYPE: InstrumentRole(self._root, io_set)})

        try:
            for role_name in self.model.old_instr[index]:
                if role_name in self.available_instruments:
                    self.available_instruments[role_name].create_and_set(self.model.old_instr[index][role_name])
        except IndexError:
            pass

        self.instr_selec = InstrumentSelector(self)
        self.instr_selec.title = 'Instrument'
        self.instr_selec.instrument_source = self.available_instruments
        self.instr_selec.grid(row=1, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # row 2: user's content frame, filled by subclasses
        self.content_frame = Frame(self)
        self.content_frame.grid(row=2, column=0, columnspan=4, padx=2, pady=2, sticky='NESW')

        # define the card-related attributes
        self.instrument = None
        self.polling_function = None
        self.active_thread = None
        self.enabled = None
        self.paused = False
        self.thread_finished = True
        self.plot_data = None

        self.string_var = None
        self.initialized = False

        self.last_instrument_type = ""

    def load_instrument_instance(self):
        """
        Use this function to get an instance from the instrument selector dropdown.
        """
        selected_instruments = dict()
        for role_name, role_instrs in self.available_instruments.items():
            selected_instruments.update({role_name: role_instrs.choice})

            # do not let card load an instrument if any other card already has the same instrument active
            for i, (_, card) in enumerate(self.model.cards):
                if card is self:
                    continue
                if card.INSTRUMENT_TYPE is not self.INSTRUMENT_TYPE:
                    continue
                if not card.enabled:
                    continue
                if card.instrument is None:
                    continue
                self_desc = role_instrs.choice
                foreign_desc = card.instrument.instrument_config_descriptor
                if self_desc['visa'] == foreign_desc['visa'] \
                        and self_desc['class'] == foreign_desc['class'] \
                        and self_desc['channel'] == foreign_desc['channel']:
                    raise RuntimeError('This instrument is already active in another card.')

        loaded_instr = self.controller.experiment_manager.instrument_api.create_instrument_obj(self.INSTRUMENT_TYPE,
                                                                                               selected_instruments,
                                                                                               {})

        self.last_instrument_type = loaded_instr.instrument_parameters['class']
        return loaded_instr

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

    def choose_color(self):
        """
        Displays the color selection tool.
        """
        if not self.PLOTTING_ENABLED:
            raise NotImplementedError('Plotting is not implemented for this card. Cannot choose color.')
        # variable to store hexadecimal code of color
        color_code = colorchooser.askcolor(title="Choose color")
        self.color = color_code[1]
        self.controller.show_main_window()
        self.color_button.configure(bg=color_code[1])
        self.controller.update_color(self.index, self.color)

    def stop_instr(self):
        raise NotImplementedError

    def tear_down(self):
        raise NotImplementedError
