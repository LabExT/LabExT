#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import argparse
import sys
import pytest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the LabExT test suite.",
        usage='python -m LabExT.Tests.runtests ...')
    parser.add_argument(
        '--laboratory_tests',
        action='store_true',
        default=False,
        help='Tests functionality that requires laboratory equipment.')
    parser.add_argument(
        '--skip_gui_integration_tests',
        action='store_true',
        default=False,
        help='Skip the GUI integration tests.')

    options = parser.parse_args()

    pytest.skip_laboratory_tests = not options.laboratory_tests
    if options.laboratory_tests:
        sys.argv.remove('--laboratory_tests')

    pytest.skip_gui_integration_tests = options.skip_gui_integration_tests
    if options.skip_gui_integration_tests:
        sys.argv.remove('--skip_gui_integration_tests')

    sys.exit(pytest.main())
