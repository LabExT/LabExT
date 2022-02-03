#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


import _tkinter
import tkinter
import pytest
from unittest import TestCase


class TKinterTestCase(TestCase):
    def setUp(self):
        self.root = tkinter.Tk()
        self.pump_events()

    def tearDown(self):
        if self.root:
            self.root.destroy()
            self.pump_events()

    def pump_events(self):
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass


def mark_as_laboratory_test(klass):
    """
    Decorator to mark test as laboratory tests. These will be exclude, when run on CI.
    """
    return pytest.mark.skipif(not pytest.run_laboratory_tests, reason="skip tests that require laboratory equipment.")(klass)


def ask_user_yes_no(ask_string="Is one kg of feathers lighter than one kg of iron?", default_answer=True):
    """ Ask the user a yes/no question:
     * Returns True on yes
     * False on no.
     * Raises RuntimeError on abort.
     * Repeats question if unclear answer.

      You can set a default answer: set to True for default 'yes', set to False for default 'no', set to None
      for no default and the user has to provide an answer."""
    yes_answers = ['y', 'yes']
    no_answers = ['n', 'no']
    abort_answers = ['a', 'abort']

    if default_answer is None:
        expl_answer_string = " [y]es/[n]o/[a]bort: "
    elif default_answer:
        expl_answer_string = " [Y]es/[n]o/[a]bort: "
        yes_answers.append('')
    elif not default_answer:
        expl_answer_string = " [y]es/[N]o/[a]bort: "
        no_answers.append('')
    else:
        raise ValueError("Argument default_answer must be True, False or None.")

    while True:
        ans = input(ask_string + expl_answer_string)
        ans = ans.strip().lower()
        if ans in yes_answers:
            return True
        elif ans in no_answers:
            return False
        elif ans in abort_answers:
            raise RuntimeError("User aborted yes-no-question.")
        else:
            continue
