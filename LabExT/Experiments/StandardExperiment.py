#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import datetime
import logging
import socket
import sys
import traceback
from collections import OrderedDict
from glob import glob
from os import rename, makedirs
from os.path import dirname, join
from pathlib import Path
from tkinter import Tk, messagebox

from LabExT.Experiments.AutosaveDict import AutosaveDict
from LabExT.Measurements.MeasAPI.Measurement import Measurement
from LabExT.PluginLoader import PluginLoader
from LabExT.Utils import make_filename_compliant, get_labext_version
from LabExT.View.Controls.ParameterTable import ConfigParameter
from LabExT.ViewModel.Utilities.ObservableList import ObservableList


def calc_measurement_key(measurement):
    """calculate the unique but hardly one-way functional 'hash' of a measurement"""
    hash_str = str(measurement["timestamp_iso_known"])
    hash_str += str(measurement["device"]["id"])
    hash_str += str(measurement["device"]["type"])
    hash_str += str(measurement["name_known"])
    return hash_str


class StandardExperiment:
    """ StandardExperiment implements the routine of performing single or multiple measurements and gathers their
    output data dictionary. """

    def __init__(self, experiment_manager, parent: Tk, chip, mover=None):

        self.logger = logging.getLogger()

        self._experiment_manager = experiment_manager  # LabExT main class
        self._parent = parent  # Tk parent object, needed for Tkinter variables in ConfigParameters and cursor change

        self._mover = mover  # stage mover class, used to move to device in automated sweeps
        self._peak_searcher = experiment_manager.peak_searcher  # peak server, used to SfP in automated sweeps

        # addon loading
        self.plugin_loader = PluginLoader()  # used to load measurements from addon folders
        self.plugin_loader_stats = {}  # contains infos on how many measurements from which paths were loaded.
        self.measurements_classes = {}  # contains names and classes of loaded measurements

        # user given parameters about chip
        self._chip = chip
        self.chip_parameters = {}
        self.save_parameters = {}
        self._default_save_path = join(str(Path.home()), "laboratory_measurements")

        # plot collections, main window plot observe these lists
        self.live_plot_collection = ObservableList()  # right plot, measurements can plot during run
        self.selec_plot_collection = ObservableList()  # left plot, plotting of finished measurement data

        # used in "new device sweep" wizard
        self.device_list = []  # selected devices to sweep over
        self.selected_measurements = []  # selected measurement names to execute on each device

        # datastructure to store all FUTURE measurements
        self.to_do_list = []  # list to contain all future ToDos, do not redefine!
        self.last_executed_todo = None  # store last executed to do (Tuple(Device, Measurement))
        self._fqdn_of_exp_runner = socket.getfqdn()  # get the FQDN of the running computer to save into datasets
        self._labext_vers = get_labext_version()  # get the LabExT version to save into datasets

        # execution control variables
        self.exctrl_pause_after_device = False
        self.exctrl_auto_move_stages = False
        self.exctrl_enable_sfp = False

        # data structures for FINISHED measurements
        self.measurements = ObservableList()
        self.measurements_hashes = []

        self.__setup__()

    @property
    def measurement_list(self):
        """ measurement_list is a read-only set of all registered measurement class names """
        return set(self.measurements_classes.keys())

    def __setup__(self):
        """Initialise all experiment specific parameters.
        """
        self.chip_parameters['Chip name'] = ConfigParameter(
            self._parent,
            value=self._chip._name if self._chip else 'UnknownChip',
            parameter_type='text')
        self.chip_parameters['Chip path'] = ConfigParameter(
            self._parent,
            value=self._chip._path if self._chip else '',
            parameter_type='text',
            allow_user_changes=False)
        self.save_parameters['Raw output path'] = ConfigParameter(
            self._parent,
            value=self._default_save_path,
            parameter_type='folder')

    def run(self):
        self.logger.info('Running experiment.')

        # update local exctrl variables from GUI, just for safety
        self._experiment_manager.main_window.model.exctrl_vars_changed()

        # update local parameters
        self.param_chip_name = str(self.chip_parameters['Chip name'].value)
        self.param_chip_file_path = str(self.chip_parameters['Chip path'].value)
        self.param_output_path = str(self.save_parameters['Raw output path'].value)
        makedirs(self.param_output_path, exist_ok=True)

        # we iterate over every measurement of every device in the To Do Queue
        while 0 < len(self.to_do_list):

            current_todo = self.to_do_list[0]
            device = current_todo.device
            measurement = current_todo.measurement

            self.logger.debug('Popped device:%s with measurement:%s',
                              device.short_str(),
                              measurement.get_name_with_id())

            now = datetime.datetime.now()
            ts = str('{date:%Y-%m-%d_%H%M%S}'.format(date=now))
            ts_iso = str(datetime.datetime.isoformat(now))

            # save result to file and to execute measurements list
            save_file_name = str(self.param_chip_name) + \
                             '_id' + str(device._id) + \
                             '_' + str(device._type) + \
                             '_' + measurement.name + \
                             '_' + ts
            save_file_name = make_filename_compliant(save_file_name)

            save_file_path = join(self.param_output_path, save_file_name)
            save_file_path = self.uniquify_safe_file_name(save_file_path)
            save_file_ending = ".json.part"

            # create and populate output data save dictionary
            data = AutosaveDict(freq=50, file_path=save_file_path + save_file_ending)

            data['software'] = OrderedDict()
            data['software']['name'] = "LabExT"
            data['software']['version'] = self._labext_vers[0]
            data['software']['git rev'] = self._labext_vers[1]
            data['software']['computer'] = self._fqdn_of_exp_runner

            data['experiment settings'] = OrderedDict()
            data['experiment settings']['pause after each device'] = self.exctrl_pause_after_device
            data['experiment settings']['auto move stages to device'] = self.exctrl_auto_move_stages
            data['experiment settings']['execute search for peak'] = self.exctrl_enable_sfp

            data['chip'] = OrderedDict()
            data['chip']['name'] = self.param_chip_name
            data['chip']['description file path'] = self.param_chip_file_path

            data['device'] = device.get_device_data()

            data['timestamp start'] = ts
            data['timestamp iso start'] = ts_iso
            data['timestamp'] = ts

            data['measurement name'] = measurement.name
            data['measurement name and id'] = measurement.get_name_with_id()
            data['instruments'] = measurement._get_data_from_all_instruments()
            data['measurement settings'] = {}
            data['values'] = OrderedDict()
            data['error'] = {}

            data['finished'] = False

            # only move if automatic movement is enabled
            if self.exctrl_auto_move_stages:
                self._mover.move_to_device(device)
                self.logger.info('Automatically moved to device:' + str(device.short_str()))

            # execute automatic search for peak
            if self.exctrl_enable_sfp:
                self._peak_searcher.update_params_from_savefile()
                data['search for peak'] = self._peak_searcher.search_for_peak()
                self.logger.info('Search for peak done.')
            else:
                data['search for peak'] = None
                self.logger.info('Search for peak not enabled. Not executing automatic search for peak.')

            self._parent.config(cursor='circle')
            self.logger.info('Executing measurement %s on device %s.',
                             measurement.get_name_with_id(),
                             device.short_str())

            measurement_executed = False
            try:
                measurement.measure(device, data)
                save_file_ending = ".json"
                measurement_executed = True
            except Exception as exc:
                # log error to file
                etype, evalue, _ = sys.exc_info()
                data['error'] = OrderedDict()
                data['error']['type'] = str(etype)
                data['error']['desc'] = repr(evalue)
                data['error']['traceback'] = traceback.format_exc()
                # error during measurement, go into pause mode
                self._experiment_manager.main_window.model.var_mm_pause.set(True)
                msg = 'Error occurred during measurement: ' + repr(exc)
                messagebox.showinfo('Measurement Error', msg)
                self.logger.exception(msg)
                save_file_ending = "_error.json"
            except SystemExit:
                # log error to file
                etype, evalue, _ = sys.exc_info()
                data['error'] = OrderedDict()
                data['error']['type'] = "Abort"
                data['error']['desc'] = "Measurement aborted by user."
                data['error']['traceback'] = traceback.format_exc()
                save_file_ending = "_abort.json"

            finally:
                self._parent.config(cursor='')

                # clear live plots after experiment finished
                while len(self.live_plot_collection) > 0:
                    self.live_plot_collection.remove(self.live_plot_collection[0])

                # save instrument parameters again
                data['instruments'] = measurement._get_data_from_all_instruments()

                # get measurement end timestamp
                ts = str('{date:%Y-%m-%d_%H%M%S}'.format(date=datetime.datetime.now()))
                data['timestamp end'] = ts
                data['timestamp'] = ts
                data['finished'] = True

                # save current measurement's data on disk
                data.save()
                data.auto_save = False
                final_path = save_file_path + save_file_ending
                rename(data.file_path, final_path)

                self.logger.info('Saved data of current measurement: %s to %s',
                                 measurement.get_name_with_id(),
                                 final_path)

                # save to do reference in case user hits "Redo last measurement" button
                self.last_executed_todo = (device, measurement)

            # shift to do to executed measurements when successful and update GUI
            if measurement_executed:
                self.load_measurement_dataset(data, final_path, force_gui_update=False)
                self.to_do_list.pop(0)
            self.update(plot_new_meas=True)

            # if manual mode activated, break here
            if self.exctrl_pause_after_device:
                break

            # if we finished all the devices in the to_do_list
            # then we finished measuring everything
            if not self.to_do_list:
                self.logger.debug('Measurements finished, queue empty. Clearing...')
                self.to_do_list.clear()
                self.update()

                messagebox.showinfo("Measurements finished!", "Measurements finished!")
                self.logger.info("Experiment and hereby all measurements finished.")

    def load_measurement_dataset(self, meas_dict, file_path, force_gui_update=True):
        """
        Use this to add a dictionary of a measurement recorded dataset to the measurements. This function
        takes over error checking of loaded datasets.
        """
        # trigger key error if chip is not present
        _ = meas_dict['chip']
        # trigger key error if device is not present
        _ = meas_dict['device']
        # check if id and type are there of device
        for dk in ['id', 'type']:
            if dk not in meas_dict['device']:
                raise KeyError("device->" + str(dk))
        # check multi option keys
        for k in ['timestamp start', 'timestamp', 'timestamp end']:
            if k in meas_dict:
                meas_dict['timestamp_known'] = meas_dict[k]
                break
        else:
            raise KeyError('"timestamp" or "timestamp end" or "timestamp start"')
        for k in ['measurement name', 'name']:
            if k in meas_dict:
                meas_dict['name_known'] = meas_dict[k]  # copy to known name
                break
        else:
            raise KeyError('"measurement name" or "name"')
        for k in ['timestamp iso start', 'timestamp_known']:
            if k in meas_dict:
                meas_dict['timestamp_iso_known'] = meas_dict[k]
                break

        # check if values is present and if any values vector is present
        if not len(meas_dict['values']) > 0:
            raise ValueError("Measurement record needs to contain at least one values dict.")

        # check for duplicates
        meas_hash = calc_measurement_key(meas_dict)
        if meas_hash in self.measurements_hashes:
            raise ValueError("Duplicate measurement found!")

        # add file path to dictionary
        meas_dict["file_path_known"] = file_path

        # all good, append to measurements
        self.measurements_hashes.extend([meas_hash])
        self.measurements.extend([meas_dict])  # dont trigger gui update if not explicitly requested by kwarg

        # tell GUI to update
        if force_gui_update:
            self.update()

    def import_measurement_classes(self):
        """
        Load all measurement files in Measurement folder and update
        measurement list.
        """
        # stats are only kept for last import call
        self.plugin_loader_stats.clear()

        meas_search_paths = [join(dirname(dirname(__file__)), 'Measurements')]  # include Meas. from LabExT core first
        meas_search_paths += self._experiment_manager.addon_settings['addon_search_directories']

        for msp in meas_search_paths:
            plugins = self.plugin_loader.load_plugins(msp, plugin_base_class=Measurement, recursive=True)
            unique_plugins = {k: v for k, v in plugins.items() if k not in self.measurements_classes}
            self.plugin_loader_stats[msp] = len(unique_plugins)
            self.measurements_classes.update(unique_plugins)

        self.logger.debug('Available measurements loaded. Found: %s', self.measurement_list)

    def remove_measurement_dataset(self, meas_dict):
        mh = calc_measurement_key(meas_dict)
        self.measurements_hashes.remove(mh)
        self.measurements.remove(meas_dict)

    def create_measurement_object(self, class_name):
        """Import, load and initialise measurement.

        Parameters
        ----------
        class_name : str
            Name of the measurement to be initialised.
        """
        self.logger.debug('Loading measurement: %s', class_name)
        meas_class = self.measurements_classes[class_name]
        measurement = meas_class(experiment=self, experiment_manager=self._experiment_manager)
        self.selected_measurements.append(measurement)
        return measurement

    def duplicate_measurement(self, orig_meas):
        """
        Returns a new measurement object with the same parameters as an original measurement.

        Parameters
        ----------
        orig_meas : Measurement
            Measurement object to be duplicated.
        """
        # create same class object
        new_meas = self.create_measurement_object(orig_meas.__class__.__name__)
        # update selected instruments
        new_meas.selected_instruments.update(orig_meas.selected_instruments)
        # initialize instruments
        new_meas.init_instruments()
        # copy values of all parameters
        for pname, pval in orig_meas.parameters.items():
            new_meas.parameters[pname].value = pval.value

        return new_meas

    def update_chip(self, chip):
        """Update reference to chip and respective parameters.

        Parameters
        ----------
        chip : Chip
            New chip object
        """
        self.logger.debug('Updating chip... New chip: %s', chip)
        self._chip = chip
        self.chip_parameters['Chip name'].value = chip._name
        self.chip_parameters['Chip path'].value = chip._path

        self.update()

    def update(self, plot_new_meas=False):
        """Updates main window tables.
        """
        self._experiment_manager.main_window.update_tables(plot_new_meas=plot_new_meas)

    def uniquify_safe_file_name(self, desired_filename):
        """ Makes filename unique for safe files. """
        existing = glob(desired_filename + "*")
        if len(existing) > 0:
            add_idx = 2
            while True:
                new_fn = desired_filename + "_" + str(add_idx)
                existing = glob(new_fn + "*")
                if not existing:
                    return new_fn
                else:
                    add_idx += 1
        else:
            return desired_filename
