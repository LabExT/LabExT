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

    options = parser.parse_args()

    pytest.run_laboratory_tests = options.laboratory_tests
    if options.laboratory_tests:
        sys.argv.remove('--laboratory_tests')

    pytest.main()
