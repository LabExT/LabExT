#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import webbrowser
from os.path import isfile, dirname, join
from threading import Thread

import matplotlib

from LabExT.DocumentationEngine.Engine import DocumentationEngine
from LabExT.Experiments.StandardExperiment import StandardExperiment
from LabExT.Instruments.InstrumentAPI import InstrumentAPI
from LabExT.Instruments.ReusingResourceManager import ReusingResourceManager
from LabExT.Movement.Mover import Mover
from LabExT.SearchForPeak.PeakSearcher import PeakSearcher
from LabExT.Utils import DeprecatedException, get_configuration_file_path, get_visa_lib_string
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled
from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
from LabExT.View.MainWindow.MainWindowController import MainWindowController
from LabExT.View.ProgressBar.ProgressBar import ProgressBar
from LabExT.Wafer.Chip import Chip

matplotlib.use('TkAgg')
RESOURCE_MANAGER = None


class ExperimentManager:
    """ExperimentManager is called upon start of the application by
    Main.py and will remain alive until the program quits

    Attributes
    ----------
    chip : Chip
        Currently loaded chip.
    exp : Experiment
        Experiment currently running.
    main_window : Frame
        Tkinter main Frame.
    mover : Mover
        Takes care of all movement related actions.
    """

    def __init__(self, root, log_file_path, chip=None):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root object.
        chip : Chip, optional
            Chip object, may be created upon startup.
        """
        self.logger = logging.getLogger()
        self.logger.info('Initialise ExperimentManager with chip: %s', chip)

        self._root = root
        self.root = root
        self._log_file_name = log_file_path
        self.addon_settings = None
        self.chip = chip
        self.mover = Mover(self)
        self.peak_searcher = PeakSearcher(None, self, mover=self.mover, parent=self.root)
        self.instrument_api = InstrumentAPI(self)
        self.docu = None
        self.live_viewer_cards = {}
        self.lvcards_import_stats = {}

        # make sure instruments.config file is present, as its used in the resource manager
        instruments_are_default = self.setup_instruments_config()

        # create global unique resource manager
        global RESOURCE_MANAGER
        if RESOURCE_MANAGER is not None:
            raise RuntimeError("ExperimentManager must only be instantiated once!")
        RESOURCE_MANAGER = ReusingResourceManager(get_visa_lib_string())
        self.resource_manager = RESOURCE_MANAGER

        # create a new StandardExperiment
        self.exp = StandardExperiment(self, root, chip, self.mover)
        self.peak_searcher.set_experiment(self.exp)

        # load addon settings from settings file
        self.load_addon_settings()

        # here we start fully loading LabExT. Its also where we start the Progressbar.
        # Although Tkinter is technically thread - safe(assuming Tk is built with --enable - threads), practically
        # speaking there are still problems when used in multithreaded Python applications. The problems stem from
        # the fact that the _tkinter module attempts to gain control of the main thread via a polling technique
        # when processing calls from other threads.
        # This is why we need to put all the setting up into a different thread (yayy)
        # since we are working in a diffrent thread, we need a variable to signal the end of the process
        self.setup_done = False
        # here we set up the progress bar
        self.pgb = ProgressBar(root, 'Welcome to LabExt\nWe are setting everything up for you!')
        # this is needed, since tk automatically opens a root window, which we do not want. The withdraw
        # command hides that window
        root.withdraw()

        # now we can start the setup thread, we pass the text variable as an argument, so we can send updates
        # to the window
        Thread(target=self.setup_runner).start()

        # this little loop here updates the progress bar
        while not self.setup_done:
            self.pgb.update_idletasks()
            self.pgb.update()

        # finally, we can destroy the progress bar window and continue with setting up the main window
        self.pgb.destroy()

        # recall the root window since we hid it during progress bar loading
        root.deiconify()

        # create and open main window GUI
        self.main_window = MainWindowController(self._root, self)
        self.main_window.offer_chip_reload_possibility()

        # update status the first time
        self.main_window.model.status_mover_driver_enabled.set(self.mover.mover_enabled)
        self.main_window.model.status_transformation_enabled.set(self.mover.trafo_enabled)
        self.main_window.model.status_sfp_initialized.set(self.peak_searcher.initialized)

        # Keyboard Shortcuts
        self.root.bind("<F1>", self.show_documentation)
        self.root.bind("<F5>",
                       callback_if_btn_enabled(lambda event: self.main_window.start(),
                                               self.main_window.model.commands[0].button_handle))
        self.root.bind("<Escape>",
                       callback_if_btn_enabled(lambda event: self.main_window.stop(),
                                               self.main_window.model.commands[1].button_handle))
        self.root.bind("<Control-r>",
                       callback_if_btn_enabled(lambda event: self.main_window.repeat_last_exec_measurement(),
                                               self.main_window.view.frame.buttons_frame.repeat_meas_button))
        self.root.bind("<Control-n>",
                       callback_if_btn_enabled(lambda event: self.main_window.new_single_measurement(),
                                               self.main_window.view.frame.buttons_frame.new_meas_button))
        self.root.bind("<Delete>",
                       callback_if_btn_enabled(lambda event: self.main_window.todo_delete(),
                                               self.main_window.view.frame.to_do_frame.delete_todo_meas))

        # inform user about mover status
        if not self.mover.mover_enabled:
            self.logger.warning('Could not load piezo-stage driver. All movement through LabExT will be deactivated.')

        # inform user where to find the log file
        self.logger.info("Log file path: " + str(self._log_file_name))

        # inform user about loaded addons:
        meas_addon_stats = '\n'.join(['    imported {:d} measurements from {:s}'.format(n, path) for path, n in
                                      self.exp.plugin_loader_stats.items()])
        instr_addon_stats = '\n'.join(['    imported {:d} instruments from {:s}'.format(n, path) for path, n in
                                       self.instrument_api.plugin_loader_stats.items()])
        lvcards_addon_stats = '\n'.join(['    imported {:d} lvcards from {:s}'.format(n, path) for path, n in
                                         self.lvcards_import_stats.items()])
        self.logger.info('Plugins loaded:\n' +
                         '  Measurements\n' + meas_addon_stats + '\n' +
                         '  Instruments\n' + instr_addon_stats + '\n' +
                         '  LVCards\n' + lvcards_addon_stats)

        if instruments_are_default:
            self.logger.warning(
                "--\n\nWARNING: LabExT loaded the default instruments.config file! Please use the Instrument Connection"
                " settings to load your own settings and to connect to real instruments!\n\n--")

        # we're good to go!
        self.logger.info("LabExT started.")

    def set_experiment(self, experiment):
        raise DeprecatedException("Experiment object must not be recreated!")

    def import_chip(self, path, name=None):
        """Import a new chip from file.

        Parameters
        ----------
        path : string
            Location of the chip file.
        name : string, optional
            Name of the string, displayed in MainWindow.

        Raises
        ------
        ValueError
            If path is empty.
        """
        self.logger.debug('Import chip requested.')

        if not path:
            self.logger.error('Wants to import chip without path. Throwing..')
            raise ValueError("Empty path, could not import chip!")
        else:
            # create chip based on description file on path
            self.chip = Chip(path, name)
            # ban user to make any more changes to exp parameters
            self.main_window.model.allow_change_chip_params.set(False)
            # update chip reference in subclasses
            if self.exp is not None:
                self.exp.update_chip(self.chip)
            if self.mover is not None:
                self.mover._chip = self.chip
                self.mover.trafo_enabled = False
                self.main_window.model.status_transformation_enabled.set(False)

    def show_documentation(self, event):
        if self.docu.docu_available:
            webbrowser.open(self.docu.temp_file)

    def setup_runner(self):
        # first we load all Measurements
        self.exp.import_measurement_classes()
        # then we load all Instruments
        self.instrument_api.load_all_instruments()
        # finally, we load all cards for the liveviewer
        self.live_viewer_cards, self.lvcards_import_stats = LiveViewerController.load_all_cards(experiment_manager=self)
        # then we generate the documentation
        # generate the documentation
        self.docu = DocumentationEngine(experiment_manager=self)
        self.docu.generate_index_html()
        self.setup_done = True

    def load_addon_settings(self):
        """ Loads the LabExT addon settings into self.addon_settings from persisting file """
        addon_settings_file = get_configuration_file_path('addon_paths.json')
        try:
            with open(addon_settings_file, 'r') as fp:
                self.addon_settings = json.load(fp)
        except FileNotFoundError:
            self.addon_settings = {'addon_search_directories': []}
            self.save_addon_settings()

    def save_addon_settings(self):
        """ Saves the LabExT addon settings in self.addon_settings to persisting file """
        addon_settings_file = get_configuration_file_path('addon_paths.json')
        with open(addon_settings_file, 'w') as fp:
            json.dump(self.addon_settings, fp)

    def setup_instruments_config(self):
        """ Makes sure that a default set of instrument configuration is present in the LabExT config dir """
        instr_config_path = get_configuration_file_path('instruments.config')
        if not isfile(instr_config_path):
            with open(join(dirname(__file__), 'Instruments', 'instruments.config.default'), 'r') as fp:
                cfg_data = json.load(fp)
            with open(instr_config_path, 'w') as fp:
                json.dump(cfg_data, fp)
            return True
        else:
            return False
