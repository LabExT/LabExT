#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import json
import random
from os import remove
from flaky import flaky
from unittest.mock import patch

import LabExT.Wafer.Device
import LabExT.Measurements.MeasAPI
from LabExT.ExperimentManager import ExperimentManager
from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Tests.Measurements.InsertionLossSweep_test import check_InsertionLossSweep_data_output
from LabExT.Tests.Utils import TKinterTestCase, randomword


def simulator_only_instruments_descriptions(name):
    if name[0:5] == 'Laser':
        return [{"visa": "None", "class": "LaserSimulator", "channels": [0, 1, 2, 3, 4]}]
    elif name[0:11] == 'Power Meter':
        return [{"visa": "None", "class": "PowerMeterSimulator", "channels": [1, 2, 3, 4]}]
    elif name[0:3] == 'OSA':
        return [{"visa": "None", "class": "OpticalSpectrumAnalyzerSimulator", "channels": []}]
    else:
        raise ValueError('Unknown name for simulator descriptions:' + str(name))


def check_InsertionLossSweep_meas_dict_meta_data(testinst, meas_record, dev_props=None, meas_props=None):
    if dev_props is not None:
        executed_dev = meas_record['device']
        testinst.assertEqual(executed_dev['id'], dev_props['id'])
        testinst.assertEqual(executed_dev['type'], dev_props['type'])

    if meas_props is not None:
        executed_meas = meas_record['measurement settings']
        testinst.assertEqual(executed_meas['wavelength start']['value'], meas_props['wavelength start'])
        testinst.assertEqual(executed_meas['wavelength stop']['value'], meas_props['wavelength stop'])
        testinst.assertEqual(executed_meas['wavelength step']['value'], meas_props['wavelength step'])
        testinst.assertEqual(executed_meas['sweep speed']['value'], meas_props['sweep speed'])
        testinst.assertEqual(executed_meas['laser power']['value'], meas_props['laser power'])
        testinst.assertEqual(executed_meas['powermeter range']['value'], meas_props['powermeter range'])
        testinst.assertEqual(executed_meas['users comment']['value'], meas_props['users comment'])
        testinst.assertEqual(set(executed_meas.keys()),
                             {'wavelength start', 'wavelength stop', 'wavelength step', 'sweep speed', 'laser power',
                              'powermeter range', 'users comment'})


@flaky(max_runs=3)
class MainWindowTest(TKinterTestCase):

    def main_window_setup(self):
        with patch('LabExT.ExperimentManager.get_visa_lib_string', lambda: "@py"):
            with patch.object(ExperimentManager, 'setup_instruments_config', lambda _: False):
                self.expm = ExperimentManager(self.root, "", skip_setup=True)
                self.expm.exp.measurements_classes['InsertionLossSweep'] = InsertionLossSweep
                self.expm.instrument_api.instruments['LaserSimulator'] = LaserSimulator
                self.expm.instrument_api.instruments['PowerMeterSimulator'] = PowerMeterSimulator
                self.mwc = self.expm.main_window
                self.mwm = self.mwc.model
                self.mwv = self.mwc.view
                # this "patches" out some features of the classes due to patching not working across threads
                self.mwc.allow_GUI_changes = False
                self.mwm.allow_GUI_changes = False

    def test_mainwindow_repeated_IL_sweep(self):
        self.test_mainwindow_single_IL_sweep()
        self.test_mainwindow_single_IL_sweep()
        self.test_mainwindow_single_IL_sweep()

    def test_mainwindow_single_IL_sweep(self):
        with patch('LabExT.View.EditMeasurementWizard.EditMeasurementWizardController.get_visa_address',
                   simulator_only_instruments_descriptions):
            self.main_window_setup()

            # full transformation and sfp need initialization before usage
            self.assertFalse(self.mwm.status_transformation_enabled.get())
            self.assertFalse(self.mwm.status_sfp_initialized.get())

            # no ToDos and now loaded measurements at beginning
            self.assertEqual(len(self.expm.exp.to_do_list), 0)
            self.assertEqual(len(self.expm.exp.measurements), 0)

            # assert no devices loaded
            self.assertIsNone(self.expm.chip)

            # open new measurement wizard
            self.mwv.frame.buttons_frame.new_meas_button.invoke()
            self.pump_events()
            new_meas_wizard_c = self.mwm.last_opened_new_meas_wizard_controller

            # stage 0: ad-hoc device with randomly generated params
            random_dev_props = {
                'id': int(random.randint(0, 99999)),
                'type': randomword(random.randint(5, 25))
            }
            new_meas_wizard_c.view.s0_adhoc_frame._entry_id.delete(0, "end")
            new_meas_wizard_c.view.s0_adhoc_frame._entry_id.insert(0, str(random_dev_props['id']))
            new_meas_wizard_c.view.s0_adhoc_frame._entry_type.delete(0, "end")
            new_meas_wizard_c.view.s0_adhoc_frame._entry_type.insert(0, str(random_dev_props['type']))
            with patch.object(new_meas_wizard_c.view.s0_adhoc_frame, 'serialize'):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    new_meas_wizard_c.view.section_frames[0].continue_button.invoke()
                    self.pump_events()

            # stage 1: meas selection
            new_meas_wizard_c.view.s1_meas_name.set('InsertionLossSweep')
            with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
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

            with patch.object(new_meas_wizard_c.view.s2_instrument_selector, 'serialize', lambda _: None):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    new_meas_wizard_c.view.section_frames[2].continue_button.invoke()
                    self.pump_events()

            # stage 3: parameter selection with randomly generated params
            random_meas_props = {
                'wavelength start': random.randint(1460, 1550),
                'wavelength stop': random.randint(1550, 1640),
                'wavelength step': random.choice([1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0]),
                'sweep speed': random.randint(40, 100),
                'laser power': random.randint(-20, 10),
                'powermeter range': random.randint(-80, -20),
                'users comment': 'automated testing ' + randomword(random.randint(2, 40))
            }
            ps = new_meas_wizard_c.view.s3_measurement_param_table._parameter_source
            ps['wavelength start'].value = random_meas_props['wavelength start']
            ps['wavelength stop'].value = random_meas_props['wavelength stop']
            ps['wavelength step'].value = random_meas_props['wavelength step']
            ps['sweep speed'].value = random_meas_props['sweep speed']
            ps['laser power'].value = random_meas_props['laser power']
            ps['powermeter range'].value = random_meas_props['powermeter range']
            ps['users comment'].value = random_meas_props['users comment']

            # this would otherwise save the test params to the user's settings
            with patch.object(new_meas_wizard_c.view.s3_measurement_param_table, 'serialize'):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    new_meas_wizard_c.view.section_frames[3].continue_button.invoke()
                    self.pump_events()

            # stage 4: save
            new_meas_wizard_c.view.section_frames[4].continue_button.invoke()
            self.pump_events()

            # check if GUI provided values made it into the generated measurement
            self.assertEqual(len(self.expm.exp.to_do_list), 1)
            self.assertEqual(len(self.expm.exp.measurements), 0)
            new_to_do = self.expm.exp.to_do_list[0]

            new_dev = new_to_do.device
            self.assertTrue(isinstance(new_dev, LabExT.Wafer.Device.Device))
            self.assertEqual(new_dev._id, random_dev_props['id'])
            self.assertEqual(new_dev._type, random_dev_props['type'])

            new_meas = new_to_do.measurement
            self.assertTrue(isinstance(new_meas, LabExT.Measurements.MeasAPI.Measurement))
            self.assertEqual(new_meas.parameters['wavelength start'].value, random_meas_props['wavelength start'])
            self.assertEqual(new_meas.parameters['wavelength stop'].value, random_meas_props['wavelength stop'])
            self.assertEqual(new_meas.parameters['wavelength step'].value, random_meas_props['wavelength step'])
            self.assertEqual(new_meas.parameters['sweep speed'].value, random_meas_props['sweep speed'])
            self.assertEqual(new_meas.parameters['laser power'].value, random_meas_props['laser power'])
            self.assertEqual(new_meas.parameters['powermeter range'].value, random_meas_props['powermeter range'])
            self.assertEqual(new_meas.parameters['users comment'].value, random_meas_props['users comment'])
            self.assertEqual(set(new_meas.parameters.keys()),
                             {'wavelength start', 'wavelength stop', 'wavelength step', 'sweep speed', 'laser power',
                              'powermeter range', 'users comment'})

            # Back to Main Window: run simulation measurement
            # various patches necessary s.t. tkinter runs although there is no main thread
            with patch('LabExT.View.MainWindow.MainWindowModel.MainWindowModel.exctrl_vars_changed'):
                with patch('LabExT.Experiments.StandardExperiment.StandardExperiment.read_parameters_to_variables'):
                    self.mwm.commands[0].button_handle.invoke()
                    self.pump_events()

            # wait for the simulated measurement to complete
            self.mwm.experiment_handler._experiment_thread.join()
            self.pump_events()

            # check if provided values are actually saved to the objects in LabExT
            self.assertEqual(len(self.expm.exp.to_do_list), 0)
            self.assertEqual(len(self.expm.exp.measurements), 1)
            executed_measurement = self.expm.exp.measurements[0]

            # check content in the dictionary saved in the executed measurements
            check_InsertionLossSweep_meas_dict_meta_data(self,
                                                         executed_measurement,
                                                         random_dev_props,
                                                         random_meas_props)
            # for checking the simulated data, we can re-use the checker function from the measurement's test
            check_InsertionLossSweep_data_output(test_inst=self, data_dict=executed_measurement, params_dict=random_meas_props)

            # do the same analysis on the saved file
            fpath = executed_measurement['file_path_known']
            with open(fpath, 'r') as fp:
                fsaved_meas = json.load(fp)  # tests if valid JSON

            # check content of saved file
            check_InsertionLossSweep_meas_dict_meta_data(self,
                                                         fsaved_meas,
                                                         random_dev_props,
                                                         random_meas_props)
            check_InsertionLossSweep_data_output(test_inst=self, data_dict=fsaved_meas, params_dict=random_meas_props)

            # delete the generated save file
            remove(fpath)
