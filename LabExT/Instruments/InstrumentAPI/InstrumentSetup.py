#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import messagebox


def create_instrument_obj_impl(api, instrument_type, selected_instruments, initialized_instruments):
    """Initialises instrument based on type and category.

    Parameters
    ----------
    api : InstrumentAPI
        The reference to the InstrumentAPI object with loaded instrument classes.
    instrument_type : str
        Type of instrument: Laser, PowerMeter etc. as specified in instruments.config file.
    selected_instruments : dict
        A dictionary containing the instrument type strings as key and the chosen description dict as value
    initialized_instruments : dict
        A dictionary to which the instantiated instrument objects should be stored. Uses a tuple
        (instr type, class name) as keys and the instantiated instrument object as value.

    Returns
    -------
    Instrument
        Initialised instrument.
    """
    logger = logging.getLogger()
    logger.debug('Possible instruments: %s', selected_instruments)
    # dict description of selected instrument
    selected_instr_desc = selected_instruments[instrument_type]

    # class_name gives name of class file in folder 'Instruments'
    class_name = selected_instr_desc.get('class')
    logger.debug('Instrument class to instantiate is ' + str(class_name))

    visa_address = selected_instr_desc.get('visa')
    channel = selected_instr_desc.get('channel', None)
    kwargs = selected_instr_desc.get('args', {})
    logger.debug('Channel is:' + str(channel))
    logger.debug('Arguments are:' + str(kwargs))

    # purge entry for this instrument_type in self.instruments
    # make sure to first create a list of all keys, since we want to change self.instruments itself
    for tn, cn in [k for k in initialized_instruments.keys()]:
        if tn == instrument_type:
            del initialized_instruments[(tn, cn)]

    inst_class = api.instruments[class_name]

    try:
        # instantiate the instrument with the channel and the given kwargs
        try:
            instr_pointer = inst_class(visa_address=visa_address, channel=channel, **kwargs)
        except Exception as ex:
            logger.error(ex)
            instr_pointer = None

        if instr_pointer is not None:
            instr_pointer.instrument_config_descriptor = selected_instr_desc.copy()

        # instrument is successfully instantiated
        initialized_instruments[(instrument_type, class_name)] = instr_pointer

        return instr_pointer

    except TypeError as e:
        logger.debug(e)
        msg = 'Fatal TypeError: The config file specified a constructor argument that ' + \
              'is not available in the class of the instrument chosen, please choose another instrument.'
        logger.error(msg)
        messagebox.showinfo('Error', msg)
        initialized_instruments[(instrument_type, class_name)] = None
        return None
