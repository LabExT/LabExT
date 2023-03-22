#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from os import path
import json
import numpy as np
import _tkinter
import tkinter
from unittest.mock import patch
from LabExT.Movement.Stage import Stage
import pytest
from unittest import TestCase
import random
import string

RUNTESTS_DIR = path.abspath(path.dirname(__file__))
TRANSFORMATIONS_DIR = path.join(RUNTESTS_DIR, "transformations")


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


def get_calibrations_from_file(chip_file: str, stage_orientation: str) -> tuple:
    """
    Returns a tuple with a axes rotation, a list of stage coordinates and a list of chip coordinates.
    """
    trafo_file = path.join(TRANSFORMATIONS_DIR, chip_file)
    if not path.exists(trafo_file):
        raise RuntimeError("No transformation file exists for the requested Chip {}.".format(chip_file))

    with open(trafo_file) as f:
        data = json.load(f).get(stage_orientation)
        if not data:
            raise RuntimeError("No Transformations exist for the requested stage orientation {}.".format(stage_orientation))

        stage_coordinates = np.array(data.get("stageCoordinates"))
        chip_coordinates = np.array(data.get("chipCoordinates"))
        axes_rotation = np.array(data.get("axesRotation", np.identity(3)))

    return axes_rotation, stage_coordinates, chip_coordinates

def mark_as_laboratory_test(cls):
    """ Decorator to mark test as laboratory tests. These will be excluded, when run on CI. """
    condition = pytest.skip_laboratory_tests if hasattr(pytest, 'skip_laboratory_tests') else False
    return pytest.mark.skipif(condition, reason="skip tests that require laboratory equipment.")(cls)


def mark_as_gui_integration_test(cls):
    """ Decorator to mark a test class as GUI integration test. This will be skipped during normal CI runs. """
    condition = pytest.skip_gui_integration_tests if hasattr(pytest, 'skip_gui_integration_tests') else False
    return pytest.mark.skipif(condition, reason='Skip GUI integration tests during normal CI runs.')(cls)


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


def randomword(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))
