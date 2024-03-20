#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from typing import Dict, Callable


class CustomLogFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    COLORS: Dict[int, Callable[[str], str]] = {
        logging.DEBUG: (lambda s: CustomLogFormatter.grey + s + CustomLogFormatter.reset),
        logging.INFO: (lambda s: s),
        logging.WARNING: lambda s: CustomLogFormatter.yellow + s + CustomLogFormatter.reset,
        logging.ERROR: lambda s: CustomLogFormatter.red + s + CustomLogFormatter.reset,
        logging.CRITICAL: lambda s: CustomLogFormatter.bold_red + s + CustomLogFormatter.reset,
    }

    def __init__(self):
        super().__init__(
            "%(asctime)s : ||%(name)s:%(filename)s:%(funcName)s||40||:%(lineno)-3d : %(levelname)-7s : %(message)s"
        )

    def format(self, record):
        # run through original formatter
        outstr = super().format(record)

        # limit length of || surrounded part
        splt = outstr.split("||")

        # get cut length
        lim_length = int(splt[2])
        del splt[2]

        # cut string to desired length and set together again
        orig_loc = splt[1]
        if len(orig_loc) > lim_length - 3:
            splt[1] = "..." + orig_loc[-lim_length + 3 :]
        else:
            splt[1] = orig_loc.rjust(lim_length)

        # add color
        add_color = self.COLORS.get(record.levelno, lambda s: s)
        return add_color("".join(splt))
