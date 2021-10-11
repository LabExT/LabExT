#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging


class CustomLogFormatter(logging.Formatter):

    def __init__(self):
        super().__init__(
            "%(asctime)s : ||%(name)s:%(filename)s:%(funcName)s||40||:%(lineno)-3d : %(levelname)-7s : %(message)s"
        )

    def format(self, record):
        # run through original formatter
        outstr = super().format(record)

        # limit length of || surrounded part
        splt = outstr.split('||')

        # get cut length
        lim_length = int(splt[2])
        del splt[2]

        # cut string to desired length and set together again
        orig_loc = splt[1]
        if len(orig_loc) > lim_length - 3:
            splt[1] = "..." + orig_loc[-lim_length+3:]
        else:
            splt[1] = orig_loc.rjust(lim_length)

        return "".join(splt)
