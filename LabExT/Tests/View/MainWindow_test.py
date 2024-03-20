#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import json
import random
from os import remove
import pytest
from unittest.mock import Mock, patch

from typing import TYPE_CHECKING

import LabExT.Wafer.Device
import LabExT.Measurements.MeasAPI
from LabExT.ExperimentManager import ExperimentManager
from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Tests.Measurements.InsertionLossSweep_test import check_InsertionLossSweep_data_output
from LabExT.Tests.Utils import TKinterTestCase, randomword, mark_as_gui_integration_test

if TYPE_CHECKING:
    from LabExT.View.Controls.InstrumentSelector import InstrumentSelector
    from LabExT.View.Controls.SweepParameterFrame import SweepParameterFrame
else:
    InstrumentSelector = None
    SweepParameterFrame = None


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
        testinst.assertEqual(executed_meas['file path to reference meas.']['value'],
                             meas_props['file path to reference meas.'])
        testinst.assertEqual(executed_meas['discard raw transmission data']['value'],
                             meas_props['discard raw transmission data'])
        testinst.assertEqual(executed_meas['users comment']['value'], meas_props['users comment'])
        testinst.assertEqual(set(executed_meas.keys()),
                             {'wavelength start', 'wavelength stop', 'wavelength step', 'sweep speed', 'laser power',
                              'powermeter range', 'users comment', 'file path to reference meas.',
                              'discard raw transmission data'})


@mark_as_gui_integration_test
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

    @pytest.mark.flaky(reruns=3)
    def test_mainwindow_repeated_IL_sweep(self):
        self.test_mainwindow_single_IL_sweep()
        self.test_mainwindow_single_IL_sweep()
        self.test_mainwindow_single_IL_sweep()

    @pytest.mark.flaky(reruns=3)
    def test_mainwindow_single_IL_sweep(self):
        with patch('LabExT.View.EditMeasurementWizard.WizardEntry.MeasurementSelect.get_visa_address',
                   simulator_only_instruments_descriptions):
            self.main_window_setup()

            # full transformation and sfp need initialization before usage
            self.assertFalse(self.mwm.status_mover_can_move_to_device.get())
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
                'id': randomword(random.randint(5, 25)),
                'type': randomword(random.randint(5, 25))
            }
            new_meas_wizard_c.entry_controllers[0]._view.content._entry_id.delete(0, "end")
            new_meas_wizard_c.entry_controllers[0]._view.content._entry_id.insert(0, str(random_dev_props['id']))
            new_meas_wizard_c.entry_controllers[0]._view.content._entry_type.delete(0, "end")
            new_meas_wizard_c.entry_controllers[0]._view.content._entry_type.insert(0, str(random_dev_props['type']))
            with patch.object(new_meas_wizard_c.entry_controllers[0]._view.content, 'serialize'):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    new_meas_wizard_c.entry_controllers[0]._view.continue_button.invoke()
                    self.pump_events()

            # stage 1: meas selection
            new_meas_wizard_c.entry_controllers[1]._view.meas_name.set('InsertionLossSweep')
            with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                new_meas_wizard_c.entry_controllers[1]._view.continue_button.invoke()
                self.pump_events()

            # stage 2: instrument selection - modify saved roles
            content: InstrumentSelector = new_meas_wizard_c.entry_controllers[2]._view.content
            laser_role = content.instrument_source['Laser']
            opm_role = content.instrument_source['Power Meter']
            lsim = next(l for l in laser_role.choices_human_readable_desc if "LaserSimulator" in l)
            pmsim = next(l for l in opm_role.choices_human_readable_desc if "PowerMeterSimulator" in l)
            laser_role.selected_instr.set(lsim)
            laser_role.selected_channel.set("0")
            opm_role.selected_instr.set(pmsim)
            opm_role.selected_channel.set("1")

            with patch.object(new_meas_wizard_c.entry_controllers[2]._view.content, 'serialize_to_dict', lambda _: None):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    with patch.object(new_meas_wizard_c, 'stage_start_logic'):
                        new_meas_wizard_c.entry_controllers[2]._view.continue_button.invoke()
                        self.pump_events()

            # stage 3: parameter selection with randomly generated params
            random_meas_props = {
                'wavelength start': random.randint(1460, 1550),
                'wavelength stop': random.randint(1550, 1640),
                'wavelength step': random.choice([1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0]),
                'sweep speed': random.randint(40, 100),
                'laser power': random.randint(-20, 10),
                'powermeter range': random.randint(-80, -20),
                'file path to reference meas.': '',  # don't use any reference data
                'discard raw transmission data': False,  # don't use a reference file
                'users comment': 'automated testing ' + randomword(random.randint(2, 40))
            }
            ps = new_meas_wizard_c.entry_controllers[3]._view.content._parameter_source
            ps['wavelength start'].value = random_meas_props['wavelength start']
            ps['wavelength stop'].value = random_meas_props['wavelength stop']
            ps['wavelength step'].value = random_meas_props['wavelength step']
            ps['sweep speed'].value = random_meas_props['sweep speed']
            ps['laser power'].value = random_meas_props['laser power']
            ps['powermeter range'].value = random_meas_props['powermeter range']
            ps['file path to reference meas.'].value = random_meas_props['file path to reference meas.']
            ps['discard raw transmission data'].value = random_meas_props['discard raw transmission data']
            ps['users comment'].value = random_meas_props['users comment']

            # this would otherwise save the test params to the user's settings
            with patch.object(new_meas_wizard_c.entry_controllers[3]._view.content, 'serialize_to_dict'):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    with patch.object(new_meas_wizard_c, 'stage_start_logic'):
                        new_meas_wizard_c.entry_controllers[3]._view.continue_button.invoke()
                        self.pump_events()

            # stage 4: sweeps
            random_reps = random.randint(2, 6)
            sweep_param_frame: SweepParameterFrame = new_meas_wizard_c.entry_controllers[4]._view.content
            sweep_param_frame._plus_button.invoke()
            self.pump_events()
            sweep_param_frame._ranges[0][2].set("wavelength start")
            self.pump_events()
            sweep_param_frame._ranges[0][1]._step_category.set(sweep_param_frame._ranges[0][1]._selection["step_count_repetition"])
            sweep_param_frame._ranges[0][1]._step_entry.delete(0, "end")
            sweep_param_frame._ranges[0][1]._step_entry.insert(0, str(random_reps))

            self.assertEqual(len(sweep_param_frame._ranges), 1)

            sweep_param_frame._plus_button.invoke()
            self.pump_events()
            self.assertEqual(len(sweep_param_frame._ranges), 2)
            sweep_param_frame._plus_button.invoke()
            self.pump_events()
            self.assertEqual(len(sweep_param_frame._ranges), 3)
            sweep_param_frame._minus_button.invoke()
            self.pump_events()
            self.assertEqual(len(sweep_param_frame._ranges), 2)

            random_start = random.randint(1560, 1630)
            sweep_param_frame._ranges[1][2].set("wavelength stop")
            self.pump_events()
            sweep_param_frame._ranges[1][1]._step_category.set(sweep_param_frame._ranges[1][1]._selection["step_count_linear"])
            sweep_param_frame._ranges[1][1]._from_entry.delete(0, "end")
            sweep_param_frame._ranges[1][1]._from_entry.insert(0, str(random_start))
            sweep_param_frame._ranges[1][1]._to_entry.delete(0, "end")
            sweep_param_frame._ranges[1][1]._to_entry.insert(0, str(random_start + 2))
            sweep_param_frame._ranges[1][1]._step_entry.delete(0, "end")
            sweep_param_frame._ranges[1][1]._step_entry.insert(0, "3")

            with patch.object(new_meas_wizard_c.entry_controllers[4]._view.content, 'serialize'):
                with patch.object(new_meas_wizard_c, 'serialize_settings', lambda: None):
                    new_meas_wizard_c.entry_controllers[4]._view.continue_button.invoke()
                    self.pump_events()

            # stage 5: save
            new_meas_wizard_c.entry_controllers[5]._view.continue_button.invoke()
            self.pump_events()

            # check if GUI provided values made it into the generated measurement
            self.assertEqual(len(self.expm.exp.to_do_list), random_reps * 3)
            self.assertEqual(len(self.expm.exp.measurements), 0)

            for i, new_to_do in enumerate(self.expm.exp.to_do_list):
                new_dev = new_to_do.device
                self.assertTrue(isinstance(new_dev, LabExT.Wafer.Device.Device))
                self.assertEqual(new_dev.id, random_dev_props['id'])
                self.assertEqual(new_dev.type, random_dev_props['type'])

                new_meas = new_to_do.measurement
                self.assertTrue(isinstance(new_meas, LabExT.Measurements.MeasAPI.Measurement))
                self.assertEqual(new_meas.parameters['wavelength start'].value, random_meas_props['wavelength start'])
                self.assertEqual(new_meas.parameters['wavelength stop'].value, random_start + (i % 3))
                self.assertEqual(new_meas.parameters['wavelength step'].value, random_meas_props['wavelength step'])
                self.assertEqual(new_meas.parameters['sweep speed'].value, random_meas_props['sweep speed'])
                self.assertEqual(new_meas.parameters['laser power'].value, random_meas_props['laser power'])
                self.assertEqual(new_meas.parameters['powermeter range'].value, random_meas_props['powermeter range'])
                self.assertEqual(new_meas.parameters['file path to reference meas.'].value,
                                 random_meas_props['file path to reference meas.'])
                self.assertEqual(new_meas.parameters['discard raw transmission data'].value,
                                 random_meas_props['discard raw transmission data'])
                self.assertEqual(new_meas.parameters['users comment'].value, random_meas_props['users comment'])
                self.assertEqual(set(new_meas.parameters.keys()),
                                 {'wavelength start', 'wavelength stop', 'wavelength step', 'sweep speed', 'laser power',
                                  'powermeter range', 'users comment', 'file path to reference meas.',
                                  'discard raw transmission data'})

            # enable automatic mode (GUI updates disabled, so hard-code setting experiment property)
            self.expm.exp.exctrl_pause_after_device = False
            # override show-messagebox (GUI updates disabled, so hard-code setting experiment property)
            self.expm.exp.show_meas_finished_infobox = lambda: None

            params = self.expm.exp.to_do_list[0].sweep_parameters
            # Back to Main Window: run simulation measurement
            # various patches necessary s.t. tkinter runs although there is no main thread
            with patch('LabExT.View.MainWindow.MainWindowModel.MainWindowModel.exctrl_vars_changed'):
                self.expm.exp.read_parameters_to_variables = Mock()
                self.mwm.commands[0].button_handle.invoke()
                self.pump_events()

            # wait for the simulated measurement to complete
            self.mwm.experiment_handler._experiment_thread.join()
            self.pump_events()

            # check if provided values are actually saved to the objects in LabExT
            self.assertEqual(len(self.expm.exp.to_do_list), 0)
            self.assertEqual(len(self.expm.exp.measurements), random_reps * 3)

            for i, executed_measurement in enumerate(self.expm.exp.measurements):
                random_meas_props['wavelength stop'] = random_start + (i % 3)
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
            import shutil
            import os
            if os.path.isdir(os.path.dirname(fpath)):
                shutil.rmtree(os.path.dirname(fpath))

