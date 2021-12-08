#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from io import StringIO
import json
from unittest import TestCase
from unittest.mock import patch, mock_open

from LabExT.View.DriverPathDialog import DriverPathDialog


class DriverPathDialogUnitTest(TestCase):
    def setUp(self) -> None:
        self.dialog = DriverPathDialog(None)

    #
    #   Testing properties
    #

    @patch('LabExT.View.DriverPathDialog.get_configuration_file_path')
    def test_settings_path_file_setter(self, get_config_mock):
        get_config_mock.return_value = '/path/to/module.py'

        self.dialog.settings_path_file = 'my_path_file.txt'

        get_config_mock.assert_called_once_with('my_path_file.txt')
        self.assertEqual(self.dialog._settings_file_path, '/path/to/module.py')

    def test_settings_path_getter_successfully(self):
        expected_path = '/path/to/control/module.py'
        with patch('builtins.open', mock_open(read_data=json.dumps(expected_path))):
            actual_path = self.dialog.settings_path

        self.assertEqual(actual_path, expected_path)
        self.assertEqual(self.dialog._settings_path, expected_path)

    def test_settings_path_getter_invalid_json(self):
        expected_path = ''
        with patch('builtins.open', mock_open(read_data=expected_path)):
            with self.assertRaises(ValueError) as context:
                self.dialog.settings_path
            self.assertIn(
                'is not valid JSON.', str(context.exception))

    def test_settings_path_getter_file_does_not_exists(self):
        self.dialog._settings_file_path = 'null'
        with self.assertRaises(IOError) as context:
            self.dialog.settings_path
        self.assertIn(
            'does not exist.', str(context.exception))

    def test_settings_path_setter_successfully(self):
        new_path = '/my/new/path.py'
        with patch('builtins.open', mock_open(read_data=json.dumps('/old/path.py'))):
            self.dialog.settings_path = new_path

        self.assertEqual(self.dialog._settings_path, new_path)

    def test_settings_path_setter_notifies_updates(self):
        new_path = '/my/new/path.py'
        old_path = '/old/path.py'
        self.dialog._settings_path = old_path
        with patch('builtins.open', mock_open(read_data=json.dumps(old_path))):
            self.dialog.settings_path = new_path

        self.assertEqual(self.dialog._settings_path, new_path)
        self.assertTrue(self.dialog.path_has_changed)

        # Update again to the same path
        with patch('builtins.open', mock_open(read_data=json.dumps(new_path))):
            self.dialog.settings_path = new_path

        self.assertFalse(self.dialog.path_has_changed)
