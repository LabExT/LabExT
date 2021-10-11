#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import tkinter as tk


class LoggingWidgetHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget
    Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    """

    def __init__(self, text_frame):
        logging.Handler.__init__(self)
        self.text_frame = text_frame
        self.setLevel("INFO")
        # ToDo: Maybe change the formatter. I used this because we have a very limited width
        formatter = logging.Formatter(
            "%(asctime)s:%(filename)s:%(funcName)s:\n%(message)s")
        self.setFormatter(formatter)
        self.counter = 0

    def emit(self, record):
        msg = self.format(record)
        msg = msg.replace('\n', '\n  ')

        try:
            self.text_frame.configure(state='normal')
            # if there are too many lines, delete at the beginning
            if self.counter > 500:
                self.text_frame.delete('1.0', '3.0')
                self.counter -= 1
            # add new line
            self.text_frame.insert(tk.END, msg + '\n')
            self.counter += 1
            self.text_frame.configure(state='disabled')
            # Autoscroll to the bottom
            self.text_frame.yview(tk.END)
        except tk.TclError:
            # the text_frame does not exist anymore, do not emit log
            pass
