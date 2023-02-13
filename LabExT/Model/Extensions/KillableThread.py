#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import ctypes
from threading import Thread


class KillableThread(Thread):
    """
    This thread can be terminated manually.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True

    def terminate(self):
        """must raise the SystemExit type, instead of a SystemExit() instance
        due to a bug in PyThreadState_SetAsyncExc"""
        if not self.is_alive():
            return
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.ident), ctypes.py_object(SystemExit))
        if res == 0:
            raise ValueError('Invalid thread ID')
        elif res != 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(self.ident, 0)
            raise SystemError('PyThreadState_SetAsyncExc failed')
