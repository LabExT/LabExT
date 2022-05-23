#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import json
import random
from itertools import product
from os import remove
from os.path import join, dirname
from flaky import flaky
from unittest.mock import patch, mock_open

import LabExT.Wafer.Device
import LabExT.Measurements.MeasAPI
from LabExT.ExperimentManager import ExperimentManager
from LabExT.Instruments.LaserSimulator import LaserSimulator
from LabExT.Instruments.PowerMeterSimulator import PowerMeterSimulator
from LabExT.Measurements.DummyMeas import DummyMeas
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep
from LabExT.Tests.Measurements.InsertionLossSweep_test import check_ILsweep_data_output
from LabExT.Tests.Utils import TKinterTestCase, randomword
from LabExT.Tests.View.MainWindow_test import simulator_only_instruments_descriptions
from LabExT.View.ExperimentWizard.Components.DeviceWindow import DeviceWindow


@flaky(max_runs=3)
class ExperimentWizardTest(TKinterTestCase):

    def main_window_setup(self):
        with patch('LabExT.ExperimentManager.get_visa_lib_string', lambda: "@py"):
            with patch.object(ExperimentManager, 'setup_instruments_config', lambda _: False):
                self.expm = ExperimentManager(self.root, "", skip_setup=True)
                self.expm.exp.measurements_classes['InsertionLossSweep'] = InsertionLossSweep
                self.expm.exp.measurements_classes['DummyMeas'] = DummyMeas
                self.expm.instrument_api.instruments['LaserSimulator'] = LaserSimulator
                self.expm.instrument_api.instruments['PowerMeterSimulator'] = PowerMeterSimulator
                self.mwc = self.expm.main_window
                self.mwm = self.mwc.model
                self.mwv = self.mwc.view
                # this "patches" out some features of the classes due to patching not working across threads
                self.mwc.allow_GUI_changes = False
                self.mwm.allow_GUI_changes = False
                # live plotting does not work as we don't run a mainloop in tk
                self.expm.exp.live_plot_collection = []  # un-listenable list -> disables live plotting callbacks

    def test_experiment_wizard_repeated(self):
        self.test_experiment_wizard()
        self.test_experiment_wizard()
        self.test_experiment_wizard()

    def test_experiment_wizard(self):
        self.main_window_setup()

        # full transformation and sfp need initialization before usage
        self.assertFalse(self.mwm.status_transformation_enabled.get())
        self.assertFalse(self.mwm.status_sfp_initialized.get())

        # no ToDos and now loaded measurements at beginning
        self.assertEqual(len(self.expm.exp.to_do_list), 0)
        self.assertEqual(len(self.expm.exp.measurements), 0)

        # as we want to setup a multi-measurement multi-device run, we need a chip description file
        self.expm.import_chip(join(dirname(dirname(__file__)), 'example_chip_description_PhoeniX_style.csv'),
                              'chip_ExperimentWizardTest')
        self.assertIsNotNone(self.expm.chip)
        self.assertEqual(len(self.expm.chip._devices), 49)

        # open new measurement wizard
        with patch("builtins.open", mock_open(read_data="[]")):  # do not load saved settings
            self.mwv.frame.buttons_frame.new_exp_button.invoke()
            self.pump_events()
        exp_wizard_ctrl = self.mwv.frame.menu_listener._experiment_wizard

        #
        # select devices window
        #
        dev_subwindow = exp_wizard_ctrl.view.last_opened_subwindow
        self.assertTrue(isinstance(dev_subwindow, DeviceWindow))
        all_rows = dev_subwindow._device_table.get_tree().get_children()
        self.assertEqual(len(all_rows), 49)
        for cdev, tdev in zip(self.expm.chip._devices.values(),
                              (dev_subwindow._device_table.get_tree().item(_id) for _id in all_rows)):
            self.assertEqual(cdev._id, tdev['values'][1])
            self.assertEqual(cdev._in_position[0], float(tdev['values'][2].split(' ')[0]))
            self.assertEqual(cdev._in_position[1], float(tdev['values'][2].split(' ')[1]))
            self.assertEqual(cdev._out_position[0], float(tdev['values'][3].split(' ')[0]))
            self.assertEqual(cdev._out_position[1], float(tdev['values'][3].split(' ')[1]))
            self.assertEqual(cdev._type, tdev['values'][4])

        sel_these_device_ids = random.sample([k for k in self.expm.chip._devices.keys()], 3)
        for d in sel_these_device_ids:
            dev_subwindow._select_unselect_by_devid(d)
        self.pump_events()

        # double check that the table updated first column
        for cdev, tdev in zip(self.expm.chip._devices.values(),
                              (dev_subwindow._device_table.get_tree().item(_id) for _id in all_rows)):
            if cdev._id in sel_these_device_ids:
                self.assertEqual(tdev['values'][0], 'marked')
            else:
                self.assertEqual(tdev['values'][0], ' ')

        # continue to next step in wizard
        with patch("builtins.open", mock_open(read_data="[]")):  # do not load saved settings
            dev_subwindow._continue_button.invoke()
            self.pump_events()

        #
        # measurement selection step
        #
        meas_subwindow = exp_wizard_ctrl.view.last_opened_subwindow
        tree_children = meas_subwindow._meas_table.get_tree().get_children()
        self.assertEqual(len(self.expm.exp.measurements_classes), len(tree_children))
        for _id in tree_children:
            meas_info = meas_subwindow._meas_table.get_tree().item(_id)
            self.assertEqual(meas_info['values'][0], 0)
            self.assertIn(meas_info['values'][1], self.expm.exp.measurements_classes)

        with patch("builtins.open", mock_open(read_data="[]")):  # do not load saved settings
            meas_subwindow.select_all()
            self.pump_events()

        for cid, _id in enumerate(tree_children):
            meas_info = meas_subwindow._meas_table.get_tree().item(_id)
            self.assertEqual(meas_info['values'][0], cid + 1)

        with patch("builtins.open", mock_open(read_data="{}")):  # do not load saved settings
            with patch('LabExT.View.ExperimentWizard.Components.InstrumentWindow.get_visa_address',
                       simulator_only_instruments_descriptions):
                meas_subwindow._continue_button.invoke()
                self.pump_events()

        #
        # instrument selection step
        #
        instr_subwindow = exp_wizard_ctrl.view.last_opened_subwindow

        # the dummy measurement does not access any instruments
        dummy_selector = [k for k in instr_subwindow._all_selectors.keys()][0]
        self.assertEqual(len(dummy_selector.instrument_source), 0)

        # the insertion loss measurement should have two roles to select
        ilm_selector = [k for k in instr_subwindow._all_selectors.keys()][1]
        self.assertEqual(len(ilm_selector.instrument_source), 2)

        # set insertion loss measurement instrument roles to SW only simulators
        laser_role = ilm_selector.instrument_source['Laser']
        opm_role = ilm_selector.instrument_source['Power Meter']
        lsim = [l for l in laser_role.choices_human_readable_desc if "LaserSimulator" in l][0]
        pmsim = [l for l in opm_role.choices_human_readable_desc if "PowerMeterSimulator" in l][0]
        laser_role.selected_instr.set(lsim)
        laser_role.selected_channel.set("0")
        opm_role.selected_instr.set(pmsim)
        opm_role.selected_channel.set("1")

        with patch("builtins.open", mock_open(read_data="{}")):  # do not load saved settings
            with patch('LabExT.View.ExperimentWizard.Components.InstrumentWindow.get_visa_address',
                       simulator_only_instruments_descriptions):
                with patch('LabExT.Instruments.InstrumentAPI._Instrument.get_visa_lib_string', lambda: "@py"):
                    instr_subwindow.continue_button.invoke()
                    self.pump_events()

        #
        # measurement properties selection step
        #
        settings_subwindow = exp_wizard_ctrl.view.last_opened_subwindow

        # randomly set InsertionLossSweep properties
        random_dummy_props = {
            'number of points': random.randint(50, 500),
            'total measurement time': 0.01 + random.random() * 0.2,
            'mean': random.random() * 6.0 - 3.0,
            'std. deviation': random.random() * 2.0,
            'simulate measurement error': False
        }
        ps = settings_subwindow._meas_param_tables['DummyMeas']._parameter_source
        ps['number of points'].value = random_dummy_props['number of points']
        ps['total measurement time'].value = random_dummy_props['total measurement time']
        ps['mean'].value = random_dummy_props['mean']
        ps['std. deviation'].value = random_dummy_props['std. deviation']
        ps['simulate measurement error'].value = random_dummy_props['simulate measurement error']

        # randomly set InsertionLossSweep properties
        random_ilm_props = {
            'wavelength start': random.randint(1460, 1550),
            'wavelength stop': random.randint(1550, 1640),
            'wavelength step': random.choice([1.0, 2.0, 5.0, 10.0, 20.0, 25.0, 50.0]),
            'sweep speed': random.randint(40, 100),
            'laser power': random.randint(-20, 10),
            'powermeter range': random.randint(-80, -20),
            'users comment': 'automated testing ' + randomword(random.randint(2, 40))
        }
        ps = settings_subwindow._meas_param_tables['InsertionLossSweep']._parameter_source
        ps['wavelength start'].value = random_ilm_props['wavelength start']
        ps['wavelength stop'].value = random_ilm_props['wavelength stop']
        ps['wavelength step'].value = random_ilm_props['wavelength step']
        ps['sweep speed'].value = random_ilm_props['sweep speed']
        ps['laser power'].value = random_ilm_props['laser power']
        ps['powermeter range'].value = random_ilm_props['powermeter range']
        ps['users comment'].value = random_ilm_props['users comment']

        with patch.object(settings_subwindow._meas_param_tables['DummyMeas'], 'serialize'):
            with patch.object(settings_subwindow._meas_param_tables['InsertionLossSweep'], 'serialize'):
                settings_subwindow._ok_button.invoke()
                self.pump_events()

        #
        # finalize wizard
        #
        exp_wizard_ctrl.view.main_window.helper_window.continue_button.invoke()
        self.pump_events()

        self.assertEqual(len(self.expm.exp.to_do_list), 6)
        self.assertEqual(len(self.expm.exp.measurements), 0)

        # enable automatic mode
        self.mwm.var_mm_pause.set(False)
        self.pump_events()

        #
        # check saved properties of the ToDos
        #

        # check amount of instantiated correct
        dev_ids = [t.device._id for t in self.expm.exp.to_do_list]
        for dev_id in sel_these_device_ids:
            self.assertEqual(dev_ids.count(dev_id), 2)
        meas_names = [t.measurement.name for t in self.expm.exp.to_do_list]
        self.assertEqual(meas_names.count('DummyMeas'), 3)
        self.assertEqual(meas_names.count('InsertionLossSweep'), 3)

        # check that the correct combinations of dev id and measurement names were instantiated
        all_combs = [p for p in product(sel_these_device_ids, ['DummyMeas', 'InsertionLossSweep'])]
        to_dos_copied = self.expm.exp.to_do_list.copy()
        for cid, cmeas in all_combs:
            for t in self.expm.exp.to_do_list:
                if t.device._id == cid and t.measurement.name == cmeas:
                    to_dos_copied.remove(t)
                    break
            else:
                raise AssertionError('ToDo with dev id: ' + str(cid) + ' and meas name: ' + cmeas + ' not found.')
        self.assertEqual(len(to_dos_copied), 0)

        # check that pointers in the ToDos actually point to the devices loaded as part of chip
        for dev_id in sel_these_device_ids:
            todo_devs_with_this_id = [t.device for t in self.expm.exp.to_do_list if t.device._id == dev_id]
            for tdev in todo_devs_with_this_id:
                self.assertIs(tdev, self.expm.chip._devices[dev_id])

        # check that the measurements have the correct parameters set
        all_ilm_meas = [t.measurement for t in self.expm.exp.to_do_list if t.measurement.name == 'InsertionLossSweep']
        self.assertIs(all_ilm_meas[0], all_ilm_meas[1])
        self.assertIs(all_ilm_meas[0], all_ilm_meas[2])
        self.assertTrue(isinstance(all_ilm_meas[0], LabExT.Measurements.MeasAPI.Measurement))
        self.assertEqual(all_ilm_meas[0].parameters['wavelength start'].value, random_ilm_props['wavelength start'])
        self.assertEqual(all_ilm_meas[0].parameters['wavelength stop'].value, random_ilm_props['wavelength stop'])
        self.assertEqual(all_ilm_meas[0].parameters['wavelength step'].value, random_ilm_props['wavelength step'])
        self.assertEqual(all_ilm_meas[0].parameters['sweep speed'].value, random_ilm_props['sweep speed'])
        self.assertEqual(all_ilm_meas[0].parameters['laser power'].value, random_ilm_props['laser power'])
        self.assertEqual(all_ilm_meas[0].parameters['powermeter range'].value, random_ilm_props['powermeter range'])
        self.assertEqual(all_ilm_meas[0].parameters['users comment'].value, random_ilm_props['users comment'])
        self.assertEqual(set(all_ilm_meas[0].parameters.keys()),
                         {'wavelength start', 'wavelength stop', 'wavelength step', 'sweep speed', 'laser power',
                          'powermeter range', 'users comment'})

        # check that the measurements have the correct parameters set
        all_dm_meas = [t.measurement for t in self.expm.exp.to_do_list if t.measurement.name == 'DummyMeas']
        self.assertIs(all_dm_meas[0], all_dm_meas[1])
        self.assertIs(all_dm_meas[0], all_dm_meas[2])
        self.assertTrue(isinstance(all_dm_meas[0], LabExT.Measurements.MeasAPI.Measurement))
        self.assertEqual(all_dm_meas[0].parameters['number of points'].value, random_dummy_props['number of points'])
        self.assertEqual(all_dm_meas[0].parameters['total measurement time'].value,
                         random_dummy_props['total measurement time'])
        self.assertEqual(all_dm_meas[0].parameters['mean'].value, random_dummy_props['mean'])
        self.assertEqual(all_dm_meas[0].parameters['std. deviation'].value, random_dummy_props['std. deviation'])
        self.assertEqual(all_dm_meas[0].parameters['simulate measurement error'].value,
                         random_dummy_props['simulate measurement error'])
        self.assertEqual(set(all_dm_meas[0].parameters.keys()), {'number of points', 'total measurement time', 'mean',
                                                                 'std. deviation', 'simulate measurement error'})

        #
        # Back to Main Window: run simulation measurement
        #

        # various patches necessary s.t. tkinter runs although there is no main thread
        with patch('LabExT.View.MainWindow.MainWindowModel.MainWindowModel.exctrl_vars_changed'):
            with patch('LabExT.Experiments.StandardExperiment.StandardExperiment.read_parameters_to_variables'):
                self.mwm.commands[0].button_handle.invoke()
                self.pump_events()

        # wait for the simulated measurement to complete
        self.mwm.experiment_handler._experiment_thread.join()
        self.pump_events()

        #
        # post-run checks
        #

        self.assertEqual(len(self.expm.exp.to_do_list), 0)
        self.assertEqual(len(self.expm.exp.measurements), 6)

        for meas_record in self.expm.exp.measurements:

            if meas_record['measurement name'] == 'DummyMeas':
                pass
            elif meas_record['measurement name'] == 'InsertionLossSweep':
                pass
            else:
                raise AssertionError('Unknown measurement name: ' + str(meas_record['measurement name']))

        pass
