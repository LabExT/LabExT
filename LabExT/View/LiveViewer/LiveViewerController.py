#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING

import datetime
from collections import OrderedDict
import json
from json import JSONDecodeError
from os import makedirs
from os.path import dirname, join
from typing import TYPE_CHECKING, Dict, Tuple
from copy import deepcopy

from LabExT.Experiments.AutosaveDict import AutosaveDict
from LabExT.PluginLoader import PluginLoader
from LabExT.Utils import get_configuration_file_path, make_filename_compliant, get_labext_version
from LabExT.View.LiveViewer.Cards import CardFrame
from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel, PlotDataPoint
from LabExT.View.LiveViewer.LiveViewerView import LiveViewerView

if TYPE_CHECKING:
    from tkinter import Tk, Toplevel
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.Measurements.MeasAPI.Measurement import MEAS_PARAMS_TYPE
else:
    Tk = None
    Toplevel = None
    ExperimentManager = None
    MEAS_PARAMS_TYPE = None


class LiveViewerController:
    """
    Controller class for the live viewer. Contains all functions interacting the view and model classes.
    """

    def __init__(self, root: Tk, experiment_manager: ExperimentManager):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self.root: Tk = root
        self.experiment_manager: ExperimentManager = experiment_manager

        # set up the liveviewer model
        self.model: LiveViewerModel = LiveViewerModel(root)
        self.model.lvcards_classes.update(self.experiment_manager.live_viewer_cards)
        self.experiment_manager.live_viewer_model = self.model

        # set up the liveviewer view
        self.view: LiveViewerView = LiveViewerView(self.root, self, self.model, experiment_manager)

        # sets the member variable current_window, needed by the LabExT backend
        self.current_window: Toplevel = self.view.main_window

        # restore previously saved state
        self.restore_lv_from_saved_parameters()

    def close_all_instruments(self):
        """Wrapper function that closes all instruments.

        Parameters
        ----------
        """
        for _, card in self.model.cards:
            card.stop_instr()

    def update_settings(self, parameters: MEAS_PARAMS_TYPE):
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

        # averaging for bar plot
        self.model.averaging_arrow_height = max(1, int(abs(parameters["averaging arrow height"].value)))

        # show FPS counter
        self.model.show_fps_counter = parameters["show FPS counter"].value

    def remove_card(self, card: CardFrame):
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

    def _destroy_card(self, card: CardFrame):
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

    def reference_set(self):
        # this sets the references of the plot traces to the last measured value
        for plot_trace in self.model.traces_to_plot.values():
            plot_trace.reference_set(n_avg=self.model.averaging_arrow_height)
        # store reference data to file for later recall
        reference_data = {plot_trace.line_label: plot_trace.reference_value for plot_trace in self.model.traces_to_plot.values()}
        fname = get_configuration_file_path(self.model.references_file_name)
        # make sure to keep existing data in the file
        try:
            with open(fname, "r") as json_file:
                existing_reference_data = json.loads(json_file.read())
            existing_reference_data.update(reference_data)
        except (FileNotFoundError, JSONDecodeError, AttributeError):
            self.experiment_manager.logger.warning(
                "Could not load live viewer reference values from file. Overwriting existing data."
            )
            existing_reference_data = reference_data.copy()
        with open(fname, "w") as json_file:
            json_file.write(json.dumps(existing_reference_data))
    
    def reference_clear(self):
        for plot_trace in self.model.traces_to_plot.values():
            plot_trace.reference_clear()

    def reference_recall(self):
        try:
            fname = get_configuration_file_path(self.model.references_file_name)
            with open(fname, "r") as json_file:
                reference_data = json.loads(json_file.read())
            for trace_label, reference_value in reference_data.items():
                for plot_trace in self.model.traces_to_plot.values():
                    if trace_label == plot_trace.line_label:
                        plot_trace.reference_set(reference_value)
                        break
        except FileNotFoundError:
            # save file does not exist, don't care
            return
        except (KeyError, AttributeError, JSONDecodeError) as _:
            # loading errors can be safely ignored as the reference values will be saved upon next set
            self.experiment_manager.logger.warning(
                "Could not load live viewer reference values from file. References cannot be recalled."
            )

    def create_snapshot(self):

        if not self.model.traces_to_plot:
            return

        param_output_path = str(self.experiment_manager.exp.save_parameters["Raw output path"].value)
        makedirs(param_output_path, exist_ok=True)

        cards_props = {}
        inst_props = {}
        for _, card in self.model.cards:
            param_data = {'data': {}}
            card.ptable.serialize_to_dict(param_data)
            cards_props[card.instance_title] = param_data['data']

            instr_data = {}
            for irolename, irole in card.available_instruments.items():
                instr_data[irolename] = irole.choice
            inst_props[card.instance_title] = instr_data

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
        data["device"]["type"] = "Live Viewer Snapshot"
        data["device"]["in_position"] = [0, 0]
        data["device"]["out_position"] = [0, 0]

        data["measurement name"] = "Live Viewer Snapshot"
        data["measurement name and id"] = "Live Viewer Snapshot"
        data["instruments"] = inst_props
        data["measurement settings"] = cards_props
        data["values"] = OrderedDict()
        data["error"] = {}

        for trace_key, plot_trace in self.model.traces_to_plot.items():
            this_card = trace_key[0]
            trace_name = trace_key[1]
            fqtn = f"{this_card.instance_title:s}: {trace_name:s}"
            data["values"][f"{fqtn:s}: y-values"] = deepcopy(plot_trace.y_values)
            data["values"][f"{fqtn:s}: timestamps"] = deepcopy(plot_trace.timestamps)

        data["finished"] = True

        data.save()

        self.experiment_manager.exp.load_measurement_dataset(meas_dict=data, file_path=save_file_path, force_gui_update=True)
        self.experiment_manager.logger.info(f"Saved visible live viewer traces to file at {save_file_path:s}.")

    @staticmethod
    def load_all_cards(experiment_manager: ExperimentManager) -> Tuple[Dict[str, type], Dict[str, int]]:
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
