#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import tkinter as tk

from typing import TYPE_CHECKING, Dict, Tuple

if TYPE_CHECKING:
    from tkinter.scrolledtext import ScrolledText
else:
    ScrolledText = None


class LoggingWidgetHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget
    Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    """

    LOGLEVEL_TO_TAG: Dict[int, Tuple[str, str]] = {
        logging.DEBUG: ("debug", "grey"),
        logging.INFO: ("info", "black"),
        logging.WARNING: ("warning", "orange"),
        logging.ERROR: ("error", "red"),
        logging.CRITICAL: ("critical", "firebrick"),
    }

    def __init__(self, text_frame: ScrolledText):
        logging.Handler.__init__(self)
        self.text_frame = text_frame
        self.setLevel("INFO")
        # ToDo: Maybe change the formatter. I used this because we have a very limited width
        formatter = logging.Formatter("%(asctime)s:%(filename)s:%(funcName)s:\n%(message)s")
        self.setFormatter(formatter)
        self.counter = 0

    def emit(self, record):
        if "nogui" in record.name.lower():
            # do not emit this record onto the GUI window if the nogui logger was used
            return

        msg = self.format(record)
        msg = msg.replace("\n", "\n  ")

        try:
            self.text_frame.configure(state="normal")
            # if there are too many lines, delete at the beginning
            if self.counter > 500:
                self.text_frame.delete("1.0", "3.0")
                self.counter -= 1
            # add new line
            self.text_frame.insert(tk.END, msg + "\n", self.LOGLEVEL_TO_TAG[record.levelno][0])
            for log_tag, color in self.LOGLEVEL_TO_TAG.values():
                self.text_frame.tag_config(log_tag, foreground=color)
            self.counter += 1
            self.text_frame.configure(state="disabled")
            # Autoscroll to the bottom
            self.text_frame.yview(tk.END)
        except tk.TclError:
            # the text_frame does not exist anymore, do not emit log
            pass
