#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.

This file is an example for creating a unit-test class to test a single instrument. For a full understanding,
see https://docs.python.org/3/library/unittest.html.

Required lab setup:
 <describe your lab setup required for this test here>
"""

import unittest

from LabExT.Instruments.DummyInstrument import DummyInstrument
from LabExT.Tests.Utils import ask_user_yes_no, mark_as_laboratory_test


# import your instrument / measurement class here
# from LabExT.Instruments.something import something

@mark_as_laboratory_test
class ExampleInstrumentTest(unittest.TestCase):

    #
    # test case constants
    #

    visa_address = "TCPIP0::example-instrument.somewhere.ethz.ch::INST0"
    instr = None
    example_constant = 42
    user_interaction_required = True

    #
    # setup and teardown methods
    # i.e. methods executed before/after test case(s)
    #

    def setUp(self) -> None:
        # This method gets executed BEFORE EVERY test case.
        pass

    @classmethod
    def setUpClass(cls) -> None:
        # This method gets executed ONCE before ALL test cases.
        cls.instr = DummyInstrument()  # Replace with your instrument instance
        cls.instr.open()

    def tearDown(self) -> None:
        # This method gets executed AFTER EVERY test cases execution.
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        # This method gets executed ONCE after ALL test cases.
        cls.instr.close()

    #
    # test cases
    #

    def test_example(self):
        # Every method whose name starts with "test_" is its own test case. It will get executed and its
        # result is displayed together with its name.
        # The TestCase class supplies many different assert* methods which allows you check and report failures.
        # see https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertEqual
        self.assertEqual(True, True)  # this will always pass!

    # this is how you skip a test, there is also skipIf and skipUnless for dynamic skipping
    @unittest.skip("don't execute as this is just an example test case and would always fail")
    def test_example2(self):
        self.assertEqual(True, False)  # this will never pass!$

    # This test case checks things with mandatory user interaction
    def test_example_user_interaction(self):
        self.assertTrue(True)
        self.assertTrue(ask_user_yes_no('Should the test pass?', default_answer=False))

    # This test case checks whether the user_interaction_flag works nicely
    def test_example_user_interaction_required(self):
        if self.user_interaction_required:
            self.assertTrue(ask_user_yes_no('Should the test pass, if_clause?', default_answer=False))
