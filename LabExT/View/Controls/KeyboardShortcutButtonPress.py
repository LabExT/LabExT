#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Button, TclError


def callback_if_btn_enabled(callback_fn, tk_button: Button):
    """
    Creates and returns a callback function which ONLY fires if the corresponding button element is in enabled state.

    Parameters
    ----------
    callback_fn
        function pointer to function to be called back, need to have exactly one argument: tk event
    tk_button
        reference to the Tk Button object for enabled state checking

    Returns
    -------
        a function reference which has builtin state checking for the associated button
    """
    logger = logging.getLogger()

    tk_button_local = tk_button
    callback_fn_local = callback_fn

    f_str = str(callback_fn_local)
    btn_str = str(tk_button_local)

    def cb(event):
        try:
            cur_state = tk_button_local["state"]
        except TclError:
            logger.warning(f"Button reference {btn_str:s} not found for state checking."
                           f" NOT executing keyboard shortcut callback.")
            return

        if cur_state != "disabled":
            callback_fn_local(event)
        else:
            logger.debug(
                f'Prevented keyboard shortcut to execute callback ({f_str:s}) due to not enabled button ({btn_str:s}).')

    return cb
