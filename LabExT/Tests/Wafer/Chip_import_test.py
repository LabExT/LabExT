#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2024  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from os.path import dirname, join
from unittest.mock import Mock
import pytest

from LabExT.Tests.Utils import TKinterTestCase
from LabExT.Utils import setup_user_settings_directory
from LabExT.Wafer.Chip import Chip
from LabExT.Wafer.ChipSources.IBMMaskDescription import IBMMaskDescription
from LabExT.Wafer.ChipSources.PhoenixPhotonics import PhoenixPhotonics
from LabExT.Wafer.ImportChipWizard import ImportChipWizard


class ChipImportTest(TKinterTestCase):

    def setUp(self) -> None:
        super().setUp()

        setup_user_settings_directory(makedir_if_needed=True)

        self.expm = Mock()
        self.expm.chip_source_api.chip_sources = {
            "IBMMaskDescription": IBMMaskDescription,
            "PhoenixPhotonics": PhoenixPhotonics,
        }

    def setup_window(self):
        return ImportChipWizard(master=self.root, experiment_manager=self.expm)

    @pytest.mark.flaky(reruns=3)
    def test_create_window_instantiate_steps(self):
        window = self.setup_window()
        self.assertIsInstance(window.source_config_steps_insts["IBMMaskDescription"], IBMMaskDescription)
        self.assertIsInstance(window.source_config_steps_insts["PhoenixPhotonics"], PhoenixPhotonics)

    @pytest.mark.flaky(reruns=3)
    def test_IBM_format(self):

        window = self.setup_window()

        window.step_chip_source_selection.source_options_sel_var.set("IBMMaskDescription")
        window._next_button.invoke()
        self.pump_events()

        ps = window.current_step.option_table._parameter_source
        chip_desc_file_path = join(dirname(dirname(__file__)), "example_chip_description_IBM_style.json")
        ps["file path"].value = chip_desc_file_path
        ps["chip name"].value = "chip_test_IBM_format"
        window.current_step.load_button.invoke()
        self.pump_events()

        window._next_button.invoke()
        self.pump_events()

        self.assertIsInstance(window.submitted_chip, Chip)
        self.assertEqual(window.submitted_chip.name, "chip_test_IBM_format")
        self.assertEqual(window.submitted_chip.path, chip_desc_file_path)

        for _id in range(27):
            self.assertIn(str(_id), window.submitted_chip.devices)
        self.assertEqual(len(window.submitted_chip.devices), 30)
        self.assertIn("27a", window.submitted_chip.devices)
        self.assertIn("28b1", window.submitted_chip.devices)
        self.assertIn("29", window.submitted_chip.devices)

        self.assertEqual(window.submitted_chip.devices["3"].type, "cutback")
        self.assertAlmostEqual(window.submitted_chip.devices["3"].parameters["length"], 10857.3)
        self.assertAlmostEqual(window.submitted_chip.devices["3"].parameters["dlength"], 2500)

        self.assertEqual(window.submitted_chip.devices["29"].type, "cutback")
        self.assertAlmostEqual(window.submitted_chip.devices["29"].parameters["length"], 30000)


        window._finish_button.invoke()
        self.pump_events()

        self.expm.register_chip.assert_called_once_with(window.submitted_chip)

    @pytest.mark.flaky(reruns=3)
    def test_Phoenix_format(self):

        window = self.setup_window()

        window.step_chip_source_selection.source_options_sel_var.set("PhoenixPhotonics")
        window._next_button.invoke()
        self.pump_events()

        ps = window.current_step.option_table._parameter_source
        chip_desc_file_path = join(dirname(dirname(__file__)), "example_chip_description_PhoeniX_style.csv")
        ps["file path"].value = chip_desc_file_path
        ps["chip name"].value = "chip_test_Phoenix_format"
        window.current_step.load_button.invoke()
        self.pump_events()

        window._next_button.invoke()
        self.pump_events()

        self.assertIsInstance(window.submitted_chip, Chip)
        self.assertEqual(window.submitted_chip.name, "chip_test_Phoenix_format")
        self.assertEqual(window.submitted_chip.path, chip_desc_file_path)

        for _id in range(100, 146):
            self.assertIn(str(_id), window.submitted_chip.devices)
        self.assertIn("146a", window.submitted_chip.devices)
        self.assertIn("147b1", window.submitted_chip.devices)
        self.assertIn("148", window.submitted_chip.devices)

        self.assertEqual(len(window.submitted_chip.devices), 49)

        self.assertEqual(window.submitted_chip.devices["100"].type, "cutback#0.5")
        self.assertEqual(window.submitted_chip.devices["100"].parameters, {})

        self.assertEqual(window.submitted_chip.devices["137"].type, "passive#2##3")
        self.assertEqual(window.submitted_chip.devices["137"].parameters, {})

        self.assertAlmostEqual(window.submitted_chip.devices["125"].in_position[0], -1451.25)
        self.assertAlmostEqual(window.submitted_chip.devices["143"].out_position[1], -1287.5)


        window._finish_button.invoke()
        self.pump_events()

        self.expm.register_chip.assert_called_once_with(window.submitted_chip)
