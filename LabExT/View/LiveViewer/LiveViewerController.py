#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import datetime
from collections import OrderedDict
import json
from json import JSONDecodeError
from os import makedirs
from os.path import dirname, join

from LabExT.Experiments.AutosaveDict import AutosaveDict
from LabExT.PluginLoader import PluginLoader
from LabExT.Utils import get_configuration_file_path, make_filename_compliant, get_labext_version
from LabExT.View.LiveViewer.Cards import CardFrame
from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel, PlotDataPoint
from LabExT.View.LiveViewer.LiveViewerView import LiveViewerView


class LiveViewerController:
    """
    Controller class for the live viewer. Contains all functions interacting the view and model classes.
    """

    def __init__(self, root, experiment_manager):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self.root = root
        self.experiment_manager = experiment_manager

        # set up the liveviewer model
        self.model = LiveViewerModel(root)
        self.model.lvcards_classes.update(self.experiment_manager.live_viewer_cards)
        self.experiment_manager.live_viewer_model = self.model

        # set up the liveviewer view
        self.view = LiveViewerView(self.root, self, self.model, experiment_manager)

        # sets the member variable current_window, needed by the LabExT backend
        self.current_window = self.view.main_window

        # restore previously saved state
        self.restore_lv_from_saved_parameters()

    def close_all_instruments(self):
        """Wrapper function that closes all instruments.

        Parameters
        ----------
        """
        for _, card in self.model.cards:
            card.stop_instr()

    def update_settings(self, parameters):
        """Updates the main parameters of the plot. These are the ones represented without a card, present
        on any liveviewer.

        Parameters
        ----------
        parameters :
            List of new parameters
        """

        # only keep this many seconds in the live plot
        self.model.plot_cutoff_seconds = abs(parameters["time range to display"].value)

        # the minimum y span
        self.model.min_y_span = abs(parameters["minimum y-axis span"].value)

        # enable or disable the bar plots on the right
        self.model.show_bar_plots = parameters["show bar plots"].value

        # averaging for bar plot
        self.model.averaging_bar_plot = max(1, int(abs(parameters["averaging in bar plot"].value)))

    def remove_card(self, card):
        """Removes a card from the liveviewer. This should be called when the user presses the 'x' symbol in the
        top right of a card.
        """

        # stop any interaction w/ instrument
        card.stop_instr()

        # tell plot to delete the corresponding traces
        for trace_key in self.model.traces_to_plot.keys():
            if trace_key[0] is card:
                card.data_to_plot_queue.put(PlotDataPoint(trace_name=trace_key[1], delete_trace=True))

        # hide card by removing from geometry manager, the card will be only destroyed later
        card.pack_forget()

        # schedule card frame for deletion after plot update tick
        self.root.after(
            int(2.0 * self.view.main_window.main_frame.plot_wrapper._animate_interval_ms),
            lambda: self._destroy_card(card),
        )

    def _destroy_card(self, card):
        """deferred call to destroy card frame after corresponding traces were removed"""
        self.model.cards.remove((card.CARD_TITLE, card))
        card.destroy()

    def show_main_window(self):
        """Lifts the LiveViewer main window to the front.

        Parameters
        ----------
        """
        self.view.main_window.lift()

    def toggle_plotting_active(self):
        if self.model.plotting_active:
            self.view.main_window.main_frame.plot_wrapper.stop_animation()
            self.view.main_window.main_frame.control_wrapper.pause_button.config(text="Continue Plotting")
            self.model.plotting_active = False
        else:
            self.view.main_window.main_frame.plot_wrapper.start_animation()
            self.view.main_window.main_frame.control_wrapper.pause_button.config(text="Pause Plotting")
            self.model.plotting_active = True

    def create_snapshot(self):
        param_output_path = str(self.experiment_manager.exp.save_parameters["Raw output path"].value)
        makedirs(param_output_path, exist_ok=True)

        inst_data = {}

        for _, card in self.model.cards:
            try:
                inst_data[card.instance_title] = card.instrument.get_instrument_parameter()
            except AttributeError as e:
                pass

        now = datetime.datetime.now()
        ts = str("{date:%Y-%m-%d_%H%M%S}".format(date=now))
        ts_iso = str(datetime.datetime.isoformat(now))

        save_file_name = make_filename_compliant("LiveViewerSnapshot_" + ts_iso)

        save_file_path = join(param_output_path, save_file_name)

        data = AutosaveDict(freq=50, file_path=save_file_path + ".json")

        data["software"] = OrderedDict()
        data["software"]["name"] = "LabExT"
        version_string, gitref_string = get_labext_version()
        data["software"]["version"] = version_string
        data["software"]["git rev"] = gitref_string

        data["chip"] = OrderedDict()
        if self.experiment_manager.chip is None:
            data["chip"]["name"] = "Chip Not Available"
            data["chip"]["description file path"] = "N/A"
        else:
            data["chip"]["name"] = self.experiment_manager.chip._name
            data["chip"]["description file path"] = self.experiment_manager.chip._path

        data["timestamp start"] = ts
        data["timestamp iso start"] = ts_iso
        data["timestamp"] = ts

        data["device"] = OrderedDict()
        data["device"]["id"] = 0
        data["device"]["in_position"] = "Not Available"
        data["device"]["out_position"] = "Not Available"
        data["device"]["type"] = "Live Viewed Chip"

        data["measurement name"] = "Liveviewer Snapshot"
        data["measurement name and id"] = "Liveviewer Snapshot"
        data["instruments"] = inst_data
        data["measurement settings"] = {}
        data["values"] = OrderedDict()
        data["error"] = {}

        for trace_key, plot_trace in self.model.traces_to_plot.items():
            this_card = trace_key[0]
            trace_name = trace_key[1]
            fqtn = f"{this_card.instance_title:s}: {trace_name:s}"
            data["values"][f"{fqtn:s}: y-values"] = plot_trace.y_values
            data["values"][f"{fqtn:s}: timestamps"] = plot_trace.timestamps

        data["finished"] = True

        data.save()

    @staticmethod
    def load_all_cards(experiment_manager):
        """
        This function dynamically loads all card objects, from the static cards directory
        """
        return_dict = {}

        plugin_loader = PluginLoader()
        plugin_loader_stats = {}

        cards_search_path = [join(dirname(__file__), "Cards")]  # include cards from LabExT core first
        cards_search_path += experiment_manager.addon_settings["addon_search_directories"]

        for csp in cards_search_path:
            plugins = plugin_loader.load_plugins(csp, plugin_base_class=CardFrame, recursive=True)
            unique_plugins = {v.CARD_TITLE: v for v in plugins.values() if v.CARD_TITLE not in return_dict}
            plugin_loader_stats[csp] = len(unique_plugins)
            return_dict.update(unique_plugins)

        return return_dict, plugin_loader_stats

    def save_parameters(self):
        """saves current parameters of live viewer to file, this includes global parameters and configured cards"""

        lv_state_to_save = []

        global_settings = {}
        self.view.main_window.main_frame.control_wrapper.cardM.ptable.serialize_to_dict(global_settings)
        lv_state_to_save.append(global_settings)

        for ctype, card in self.model.cards:
            instr_data = {}
            for irolename, irole in card.available_instruments.items():
                instr_data[irolename] = irole.choice

            param_data = {}
            card.ptable.serialize_to_dict(param_data)

            lv_state_to_save.append((ctype, instr_data, param_data))

        # write all elements to the json file
        fname = get_configuration_file_path(self.model.settings_file_name)
        with open(fname, "w") as json_file:
            json_file.write(json.dumps(lv_state_to_save))

    def restore_lv_from_saved_parameters(self):
        """restores a liveviewer state given previously saved parameters"""
        try:
            # load state from file
            fname = get_configuration_file_path(self.model.settings_file_name)
            with open(fname, "r") as json_file:
                loaded_lv_state = json.loads(json_file.read())

            # apply global settings
            self.view.main_window.main_frame.control_wrapper.cardM.ptable.deserialize_from_dict(loaded_lv_state[0])
            self.update_settings(self.view.main_window.main_frame.control_wrapper.cardM.ptable.to_meas_param())

            # create cards
            for ctype, _, _ in loaded_lv_state[1:]:
                self.model.cards.append((ctype, None))
            self.view.main_window.main_frame.control_wrapper.set_cards()

            # restore card settings
            for cidx, (_, instr_data, param_data) in enumerate(loaded_lv_state[1:]):
                _, card = self.model.cards[cidx]
                card.instr_selec.deserialize_from_dict(instr_data)
                card.ptable.deserialize_from_dict(param_data)
        except FileNotFoundError:
            # save file does not exist, don't care
            return
        except (KeyError, IndexError, ValueError, TypeError, JSONDecodeError) as _:
            # loading errors can be safely ignored as the state will be written anew upon liveviewer termination
            self.experiment_manager.logger.warning(
                "Could not load live viewer state from saved file. Live viewer reset to default settings."
            )
