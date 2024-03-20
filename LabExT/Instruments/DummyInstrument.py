#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import threading

from LabExT.Instruments.InstrumentAPI import Instrument


class DummyInstrument(Instrument):
    """
    ## Dummy Instrument

    This class "plays" as if it's an instrument, similar to
    [mocking](https://docs.python.org/3.7/library/unittest.mock.html). If you want to make instruments optional in your
    measurement classes, you can use this instrument and setting / getting properties will not error. This helps
    avoiding enable checks everywhere in your measurement code.

    To be used e.g. to make the "SMU" instrument optional by a parameter setting:
    ```
        if self.use_smu:
            self.instr_smu = self.get_instrument('SMU')
        else:
            self.instr_smu = DummyInstrument()
    ```

    Later, this line returns either None or an actual measurement:
    ```
        t = self.instr_smu.spot_measurement()
    ```
    without having to do another check to self.use_smu.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(visa_address=kwargs.get('visa_address', ''), channel=None)
        self._dummy_open = False

    def __getattr__(self, item):
        """
        This function is called when we want to get an attribute which does not exist.
        So you can access any non-existing attribute of this class and will get a None-returning function back.
        """
        self.logger.debug(f"DummyInstrument reading attribute {item:s}, returning None-fct.")

        def dummy_fct(*args, **kwargs):
            return None

        return dummy_fct

    def __enter__(self):
        """
        Makes this class a context manager which does simply nothing.
        """
        self.logger.debug("DummyInstrument entering context.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Makes this class a context manager which does simply nothing.
        """
        self.logger.debug("DummyInstrument exiting context.")

    def get_instrument_parameter(self):
        return {'idn': self.idn()}

    @Instrument._open.getter  # weird way to override the parent's class property getter
    def _open(self):
        return self._dummy_open

    def open(self):
        self._dummy_open = True
        return None

    def close(self):
        self._dummy_open = False
        return None

    @Instrument.thread_lock.getter  # weird way to override the parent's class property getter
    def thread_lock(self):
        return threading.Lock()

    def clear(self):
        return None

    def idn(self):
        return "DummyInstrument class"

    def reset(self):
        return None

    def ready_check_sync(self):
        return True

    def ready_check_async_setup(self):
        return None

    def ready_check_async(self):
        return True

    def check_instrument_errors(self):
        return None

    def command(self, *args, **kwargs):
        return None

    def command_channel(self, *args, **kwargs):
        return None

    def request(self, *args, **kwargs):
        return ""

    def request_channel(self, *args, **kwargs):
        return ""

    def query(self, *args, **kwargs):
        return ""

    def query_channel(self, *args, **kwargs):
        return ""

    def write(self, *args):
        return None

    def write_channel(self, *args, **kwargs):
        return None

    def query_raw_bytes(self, *args, **kwargs):
        return None
