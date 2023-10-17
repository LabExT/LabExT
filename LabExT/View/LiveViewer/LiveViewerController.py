#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import datetime
from collections import OrderedDict
from os import makedirs
from os.path import dirname, join

from LabExT.Experiments.AutosaveDict import AutosaveDict
from LabExT.PluginLoader import PluginLoader
from LabExT.Utils import make_filename_compliant, get_labext_version
from LabExT.View.LiveViewer.Cards import CardFrame
from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel
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

        # set up the liveviewer view
        self.view = LiveViewerView(self.root, self, self.model, experiment_manager)

        # sets the member variable current_window, needed by the LabExT backend
        self.current_window = self.view.main_window

    def close_all_instruments(self):
        """Wrapper function that closes all instruments.

        Parameters
        ----------
        """
        for (_, card) in self.model.cards:
            card.stop_instr()

    def update_settings(self, parameters):
        """ Updates the main parameters of the plot. These are the ones represented without a card, present
        on any liveviewer.

        Parameters
        ----------
        parameters :
            List of new parameters
        """

        # only keep this many seconds in the live plot
        self.model.plot_cutoff_seconds = abs(parameters['time range to display'].value)

        # the minimum y span
        self.model.min_y_span = abs(parameters['minimum y-axis span'].value)

    def remove_card(self, card):
        """ Removes a card from the liveviewer. This should be called when the user presses the 'x' symbol in the
        top right of a card.
        """

        # stop any interaction w/ instrument
        card.stop_instr()

        # clean up the data from the plot
        to_remove = []
        for fqtn, plot_trace in self.model.traces_to_plot.items():
            if plot_trace.card_handle is card:
                to_remove.append(fqtn)
        for fqtn in to_remove:
            self.model.traces_to_plot[fqtn].line_handle.remove()
            self.model.traces_to_plot.pop(fqtn, None)

        # delete the cards record from the list of all cards
        self.model.cards.remove((card.CARD_TITLE, card))

        # issue the tk command to destroy the card
        card.destroy()

    def show_main_window(self):
        """ Lifts the LiveViewer main window to the front.

        Parameters
        ----------
        """
        self.view.main_window.lift()

    def create_snapshot(self):

        # ToDo: update with new method of storing plotting data

        param_output_path = str(self.experiment_manager.exp.save_parameters['Raw output path'].value)
        makedirs(param_output_path, exist_ok=True)

        inst_data = {}

        for i, (card_type, card) in enumerate(self.model.cards):
            try:
                inst_data[card_type + str(i)] = card.instrument.get_instrument_parameter()
            except AttributeError as e:
                pass

        now = datetime.datetime.now()
        ts = str('{date:%Y-%m-%d_%H%M%S}'.format(date=now))
        ts_iso = str(datetime.datetime.isoformat(now))

        save_file_name = make_filename_compliant("LiveViewerSnapshot_" + ts_iso)

        save_file_path = join(param_output_path, save_file_name)

        data = AutosaveDict(freq=50, file_path=save_file_path + ".json")

        data['software'] = OrderedDict()
        data['software']["name"] = "LabExT"
        version_string, gitref_string = get_labext_version()
        data['software']["version"] = version_string
        data['software']["git rev"] = gitref_string

        data['chip'] = OrderedDict()
        if self.experiment_manager.chip is None:
            data['chip']['name'] = "Chip Not Available"
            data['chip']['description file path'] = "N/A"
        else:
            data['chip']['name'] = self.experiment_manager.chip._name
            data['chip']['description file path'] = self.experiment_manager.chip._path

        data['timestamp start'] = ts
        data['timestamp iso start'] = ts_iso
        data['timestamp'] = ts

        data['device'] = OrderedDict()
        data['device']['id'] = 0
        data['device']['in_position'] = "Not Available"
        data['device']['out_position'] = "Not Available"
        data['device']['type'] = "Live Viewed Chip"

        data['measurement name'] = "Liveviewer Snapshot"
        data['measurement name and id'] = "Liveviewer Snapshot"
        data['instruments'] = inst_data
        data['measurement settings'] = {}
        data['values'] = OrderedDict()
        data['error'] = {}

        for i, (card_type, card) in enumerate(self.model.cards):
            for chlabel, pd in card.enabled_channels.items():
                data['values'][str(card_type) + " " + str(i) + ": " + str(chlabel)] = pd.y
                data['values']["x"] = pd.x

        data['finished'] = True

        data.save()

    @staticmethod
    def load_all_cards(experiment_manager):
        """
        This function dynamically loads all card objects, from the static cards directory
        """
        return_dict = {}

        plugin_loader = PluginLoader()
        plugin_loader_stats = {}

        cards_search_path = [join(dirname(__file__), 'Cards')]  # include cards from LabExT core first
        cards_search_path += experiment_manager.addon_settings['addon_search_directories']

        for csp in cards_search_path:
            plugins = plugin_loader.load_plugins(csp, plugin_base_class=CardFrame, recursive=True)
            unique_plugins = {v.CARD_TITLE: v for v in plugins.values() if v.CARD_TITLE not in return_dict}
            plugin_loader_stats[csp] = len(unique_plugins)
            return_dict.update(unique_plugins)

        return return_dict, plugin_loader_stats
