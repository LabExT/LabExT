#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import datetime
import json
from collections import OrderedDict
from os import makedirs
from os.path import dirname, join

from LabExT.Experiments.AutosaveDict import AutosaveDict
from LabExT.Measurements.MeasAPI import MeasParamAuto
from LabExT.PluginLoader import PluginLoader
from LabExT.Utils import get_configuration_file_path
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

        self.model.options = self.experiment_manager.live_viewer_cards
        # loads old, saved parameters
        self.load_parameters()

        # set up the liveviewer view
        self.view = LiveViewerView(self.root, self, self.model, experiment_manager)

        # sets the member variable current_window, needed by the LabExT backend
        self.current_window = self.view.main_window

        self.model.old_params = []

    def save_parameters(self):
        """Saves all parameters to a config file, so that when the next instance of the liveviewer is loaded,
        all the parameters remain the same.

        Parameters
        ----------
        """
        # initialize json element
        to_save = []
        # loop over all cards
        for (type, card) in self.model.cards:
            # for each card, make a json out of the parameter tables
            params = card.ptable.make_json_able()

            instr_data = {}
            for role_name in card.available_instruments:
                instr_data[role_name] = card.available_instruments[role_name].choice
            # build the config object
            config = [type, params, instr_data]
            # add the config to the list
            to_save.append(config)

        # write all elements to the json file
        fname = get_configuration_file_path('LiveViewerConfig.json')
        with open(fname, 'w') as json_file:
            json_file.write(json.dumps(to_save))

    def load_parameters(self):
        """Loads all parameters from a config file, so that when the next instance of the liveviewer is loaded,
        all the parameters remain the same.

        Parameters
        ----------
        """
        # try to open the json.
        try:
            fname = get_configuration_file_path('LiveViewerConfig.json')
            with open(fname, 'r') as json_file:
                data = json.loads(json_file.read())

            # read all configs from the json
            for old_card in data:
                # save the config to the model, by appending cards directly to the model
                self.model.cards.append((old_card[0], None))
                # load the config
                old_param = {}
                for op in old_card[1]:
                    old_param[op] = MeasParamAuto(old_card[1][op])

                # add the parameters to the old_params list
                self.model.old_params.append(old_param)
                self.model.old_instr.append(old_card[2])

        # if we do not succeed, the json does not exist and we do nothing
        except json.JSONDecodeError as e:
            pass

        except FileNotFoundError as e:
            pass

    def close_all_instruments(self):
        """Wrapper function that closes all instruments.

        Parameters
        ----------
        """
        for (card_type, card) in self.model.cards:
            card.stop_instr()

    def toggle_card_mode_enable(self, index):
        """ Switches one card at index to enable mode. This is, such that buttons can be greyed out while
        an instrument is active.

        Parameters
        ----------
        index :
            index of the card that needs to be toggled
        """
        self.model.cards[index][1].enable_settings_interaction()

    def toggle_card_mode_disable(self, index):
        """ Switches one card at index to disable mode. This is, such that buttons can be greyed out while
        an instrument is disabled.

        Parameters
        ----------
        index :
            index of the card that needs to be toggled
        """
        self.model.cards[index][1].disable_settings_interaction()

    def update_settings(self, parameters):
        """ Updates the main parameters of the plot. These are the ones represented without a card, present
        on any liveviewer.

        Parameters
        ----------
        parameters :
            List of new parameters
        """

        #
        # update x axis length
        #

        # load the number of points kept
        nopk = parameters['number of points kept'].value
        # find the difference in plot size
        diff = self.model.plot_size - nopk

        # set the axes to the new plot size
        self.model.live_plot.ax.set_xlim([0, nopk - 1])
        # manually update the canvas
        self.model.live_plot.__update_canvas__()

        # clean the plots, loop over all cards
        for c in self.model.cards:
            # find out whether the card has a plot attached
            if c[1].plot_data is not None:
                # clean
                if diff > 0:
                    # we need to remove points. The amount was calculated beforehand
                    pd = c[1].plot_data
                    for i in range(diff):
                        del(pd.y[0])
                        del(pd.x[nopk])
                elif diff < 0:
                    # we need to add points. The amount was calculated beforehand
                    c[1].plot_data.x.extend([x for x in range(self.model.plot_size, nopk)])
                    c[1].plot_data.y[0:0] = [float('nan') for _ in range(nopk - self.model.plot_size)]

        # set the number of point kepts in the model structure
        self.model.plot_size = nopk

        #
        # update min y span
        #

        min_y = parameters['minimum y-axis span'].value
        self.model.live_plot.min_y_axis_span = min_y
        self.model.min_y_span = min_y

    def remove_card(self, index):
        """ Removes a card from the liveviewer. This should be called when the user presses the 'x' symbol in the
        top right of a card.

        Parameters
        ----------
        index :
            Index of card that will be removed
        """
        # find the card that we need to remove
        (c_type, card) = self.model.cards[index]
        # call the cards tear down function
        card.tear_down()

        # issue the tk command to destroy the card
        card.destroy()

        # clean up the data
        # remove the plot collection
        if card.initialized:
            self.model.plot_collection.remove(card.plot_data)

        # delete the cards record from the list of all cards
        del(self.model.cards[index])

        # update the indices of all cards.
        # this is a slight work-around, but all cards need to know their index, to simplify and speedup various commands
        for i, (card_type, card) in enumerate(self.model.cards):
            card.index = i

    def update_color(self, index, color):
        """ Updates the color of a plot with a new one.

        Parameters
        ----------
        index :
            Index of card that will change color
        color :
            The new color for the plot
        """
        # update the plot_data element
        if self.model.cards[index][1].plot_data is not None:
            self.model.cards[index][1].plot_data.color = color

    def show_main_window(self):
        """ Lifts the LiveViewer main window to the front.

        Parameters
        ----------
        """
        self.view.main_window.lift()

    def create_snapshot(self):
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
            if card.plot_data is not None:
                data['values'][str(card_type) + " " + str(i) + ": " + card.last_instrument_type] = card.plot_data.y
                data['values']["x"] = card.plot_data.x

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
            unique_plugins = {v.instrument_type: v for v in plugins.values() if v.instrument_type not in return_dict}
            plugin_loader_stats[csp] = len(unique_plugins)
            return_dict.update(unique_plugins)

        return return_dict, plugin_loader_stats
