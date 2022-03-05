#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from time import sleep
from unittest.mock import patch

from LabExT.ExperimentManager import ExperimentManager
from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Tests.Utils import TKinterTestCase


def simulator_only_instruments_descriptions(name):
    if name[0:5] == 'Laser':
        return [{"visa": "None", "class": "LaserSimulator", "channels": [0, 1, 2, 3, 4] }]
    elif name[0:10] == 'PowerMeter':
        return [{"visa": "None", "class": "PowerMeterSimulator", "channels": [1, 2, 3, 4] }]
    elif name[0:3] == 'OSA':
        return [{"visa": "None", "class": "OpticalSpectrumAnalyzerSimulator", "channels": []}]
    else:
        raise ValueError('Unknown name for simulator descriptions:' + str(name))


class MainWindowTest(TKinterTestCase):

    def main_window_setup(self):

        # TODO: the patching does not work all cases!
        with patch('LabExT.Utils.get_visa_lib_string', lambda: "@py"):
            self.expm = ExperimentManager(self.root, "", skip_setup=True)
            self.expm.exp.measurements_classes['InsertionLossSweep'] = InsertionLossSweep
            self.expm.instrument_api.instruments['LaserSimulator'] = LaserSimulator
            self.expm.instrument_api.instruments['PowerMeterSimulator'] = PowerMeterSimulator
            self.mwc = self.expm.main_window
            self.mwm = self.mwc.model
            self.mwv = self.mwc.view

    def test_mainwindow_initial_state(self):

        self.main_window_setup()

        # full transformation and sfp need initialization before usage
        self.assertFalse(self.mwm.status_transformation_enabled.get())
        self.assertFalse(self.mwm.status_sfp_initialized.get())

        # no ToDos and now loaded measurements at beginning
        self.assertEqual(len(self.expm.exp.to_do_list), 0)
        self.assertEqual(len(self.expm.exp.measurements), 0)

        # assert no devices loaded
        self.assertIsNone(self.expm.chip)

    def test_mainwindow_single_IL_sweep(self):

        # TODO: the patching does not work all cases!
        with patch('LabExT.Utils.get_visa_address', simulator_only_instruments_descriptions):

            self.main_window_setup()

            # open new measurement wizard
            self.mwv.frame.buttons_frame.new_meas_button.invoke()
            self.pump_events()
            new_meas_wizard_c = self.mwm.last_opened_new_meas_wizard_controller

            # stage 0: ad-hoc device
            new_meas_wizard_c.view.s0_adhoc_frame._entry_id.delete(0, "end")
            new_meas_wizard_c.view.s0_adhoc_frame._entry_id.insert(0, '999')
            new_meas_wizard_c.view.s0_adhoc_frame._entry_type.delete(0, "end")
            new_meas_wizard_c.view.s0_adhoc_frame._entry_type.insert(0, 'MZM')
            new_meas_wizard_c.view.section_frames[0].continue_button.invoke()
            self.pump_events()

            # stage 1: meas selection
            new_meas_wizard_c.view.s1_meas_name.set('InsertionLossSweep')
            new_meas_wizard_c.view.section_frames[1].continue_button.invoke()
            self.pump_events()

            # stage 2: instrument selection - modify saved roles
            laser_role = new_meas_wizard_c.view.s2_instrument_selector.instrument_source['Laser']
            opm_role = new_meas_wizard_c.view.s2_instrument_selector.instrument_source['Power Meter']
            lsim = [l for l in laser_role.choices_human_readable_desc if "LaserSimulator" in l][0]
            pmsim = [l for l in opm_role.choices_human_readable_desc if "PowerMeterSimulator" in l][0]
            laser_role.selected_instr.set(lsim)
            laser_role.selected_channel.set("0")
            opm_role.selected_instr.set(pmsim)
            opm_role.selected_channel.set("1")

            new_meas_wizard_c.view.section_frames[2].continue_button.invoke()
            self.pump_events()

            # stage 3: parameter selection
            ps = new_meas_wizard_c.view.s3_measurement_param_table._parameter_source
            ps['wavelength start'].value = 1500
            ps['wavelength stop'].value = 1600
            ps['wavelength step'].value = 10.0
            ps['sweep speed'].value = 50.0
            ps['laser power'].value = -10.0
            ps['powermeter range'].value = -80.0
            ps['users comment'].value = 'automated testing'

            # TODO: use this patch to not save to file when testing
            #with patch('LabExT.View.Controls.ParameterTable.serialize'):
            new_meas_wizard_c.view.section_frames[3].continue_button.invoke()
            self.pump_events()

            # stage 4: save
            new_meas_wizard_c.view.section_frames[4].continue_button.invoke()
            self.pump_events()

            # Back to Main Window: run simulation measurement
            self.assertEqual(len(self.expm.exp.to_do_list), 1)
            self.assertEqual(len(self.expm.exp.measurements), 0)

            # this needs to be patched, otherwise measurement executor thread fails
            # ToDo: find out how to patch this properly
            with patch('LabExT.View.MainWindow.MainWindowModel'):
                self.mwm.commands[0].button_handle.invoke()
                self.pump_events()

            sleep(10)
            self.pump_events()

            self.assertEqual(len(self.expm.exp.to_do_list), 0)
            self.assertEqual(len(self.expm.exp.measurements), 1)
