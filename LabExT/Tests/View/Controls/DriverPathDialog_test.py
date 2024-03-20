#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from unittest.mock import patch, mock_open
from pathlib import Path
import pytest

from LabExT.Tests.Utils import TKinterTestCase
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog


class DriverPathDialogTest(TKinterTestCase):

    @pytest.mark.flaky(reruns=3)
    def test_dialog_initial_state(self):
        settings_file_path = 'my_path_file.txt'
        current_driver_path = str(Path('/path/to/control/module.py'))

        with patch('LabExT.View.Controls.DriverPathDialog.get_configuration_file_path') as config_path:
            with patch('builtins.open', mock_open(read_data=json.dumps(current_driver_path))):

                dialog = DriverPathDialog(self.root, settings_file_path)

                config_path.assert_called_once_with(settings_file_path)

                self.assertEqual(
                    str(dialog._driver_path_entry.get()),
                    current_driver_path
                )

    @pytest.mark.flaky(reruns=3)
    def test_save_without_change(self):
        settings_file_path = 'my_path_file.txt'
        current_driver_path = str(Path('/path/to/control/module.py'))

        with patch('LabExT.View.Controls.DriverPathDialog.get_configuration_file_path'):
            with patch('builtins.open', mock_open(read_data=json.dumps(current_driver_path))):
                dialog = DriverPathDialog(self.root, settings_file_path)
                dialog._save_button.invoke()

                self.assertEqual(Path(dialog.driver_path), Path(current_driver_path))
                self.assertFalse(dialog.path_has_changed)

    @pytest.mark.flaky(reruns=3)
    def test_save_with_change(self):
        settings_file_path = 'my_path_file.txt'
        current_driver_path = str(Path('/path/to/control/module.py'))
        new_driver_path = str(Path('/my/new/path.py'))

        with patch('LabExT.View.Controls.DriverPathDialog.get_configuration_file_path'):
            with patch('builtins.open', mock_open(read_data=json.dumps(current_driver_path))):
                dialog = DriverPathDialog(self.root, settings_file_path)
                dialog._driver_path_entry.delete(0, "end")
                dialog._driver_path_entry.insert(0, new_driver_path)
                dialog._save_button.invoke()

                self.assertEqual(Path(dialog.driver_path), Path(new_driver_path))
                self.assertTrue(dialog.path_has_changed)
