#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Toplevel, Button, messagebox

from LabExT.Utils import get_visa_address
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentRole, InstrumentSelector
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.PlotControl import PlotControl


class SearchForPeakPlotsWindowModel:
    """
    Model class for SearchForPeakPlotsWindowModel. Contains all data needed.
    All attributes are defined as properties.
    """
    def __init__(self, experiment_manager):
        self.experiment_manager = experiment_manager

        self.instr_settings_path = None
        self.settings_path = None
        self.peak_searcher = None

        self.plots_left = None
        self.plots_right = None

    @property
    def settings_path(self):
        return self._settings_path

    @settings_path.setter
    def settings_path(self, new_path):
        self._settings_path = new_path

    @property
    def instr_settings_path(self):
        return self._instr_settings_path

    @instr_settings_path.setter
    def instr_settings_path(self, new_path):
        self._instr_settings_path = new_path

    @property
    def peak_searcher(self):
        return self._peak_searcher

    @peak_searcher.setter
    def peak_searcher(self, new_peak_searcher):
        self._peak_searcher = new_peak_searcher

    @property
    def plots_left(self):
        return self._plots_left

    @plots_left.setter
    def plots_left(self, new_plots_left):
        self._plots_left = new_plots_left

    @property
    def plots_right(self):
        return self._plots_right

    @plots_right.setter
    def plots_right(self, new_plots_right):
        self._plots_right = new_plots_right

    def load_peak_searcher(self):
        self.peak_searcher = self.experiment_manager.peak_searcher

    def load_settings_paths(self):
        self.instr_settings_path = "SearchForPeakPlotsWindows_instr_settings.json"
        self.settings_path = self.peak_searcher.settings_path_full

    def load_observed_list(self):
        # create observed list for plots
        self.plots_left = self.peak_searcher.plots_left
        self.plots_right = self.peak_searcher.plots_right

        self.plots_left.item_added.clear()
        self.plots_left.item_removed.clear()
        self.plots_left.on_clear.clear()

        self.plots_right.item_added.clear()
        self.plots_right.item_removed.clear()
        self.plots_right.on_clear.clear()

        self.plots_left.clear()
        self.plots_right.clear()


class PlottingSettingWidget(Toplevel):
    """
    The top level window containing a frame.
    """
    def __init__(self, root, model, view, controller):
        Toplevel.__init__(self, root)
        view.current_window = self

        self.model = model
        self.root = root
        self.controller = controller

        self.protocol("WM_DELETE_WINDOW", controller.on_close)
        self.geometry('+%d+%d' % (self.root.winfo_screenwidth() / 6,
                                  self.root.winfo_screenheight() / 6))
        self.lift()
        self.title('Search for Peak')

        self.plotting_frame = PlottingFrame(self, self.model, self.controller)


class PlottingFrame(CustomFrame):
    """
    The custom frame for structuring the contents.
    Contains two plots, as well as parameter and instrument selection tools
    """
    def __init__(self, parent, model, controller):
        CustomFrame.__init__(self, parent)
        self.model = model
        self.parent = parent

        self.grid(row=0, column=0)
        self.plot_left = PlotsWidget(self, 'Left Stage', self.model.plots_left)
        self.plot_left.grid(row=0, column=0, rowspan=2, columnspan=2, padx=5, pady=5)

        self.plot_right = PlotsWidget(self, 'Right Stage', self.model.plots_right)
        self.plot_right.grid(row=0, column=2, rowspan=2, columnspan=2, padx=5, pady=5)

        self.instruments_chooser_widget = InstrumentsChooserWidget(self, self.model)
        self.instruments_chooser_widget.grid(row=4, column=0, rowspan=1, columnspan=3)

        self.set_instruments_button = AcceptButton(self,
                                                   controller.set_instruments,
                                                   "1. Define Instruments for Search for Peak")
        self.set_instruments_button.grid(row=4, column=3)

        self.parameter_chooser_widget = ParameterChooserWidget(self, self.model)
        self.parameter_chooser_widget.grid(row=5, column=0, rowspan=1, columnspan=3)

        self.set_parameters_button = AcceptButton(self,
                                                  controller.execute_sfp_manually,
                                                  "2. Save Parameters and Execute Search for Peak")
        self.set_parameters_button.grid(row=5, column=3)


class PlotsWidget(PlotControl):
    """
    The PlotsWidget subclass wraps the plots itself. It is uised two times, for both plots.
    """
    def __init__(self, parent, title, data):
        PlotControl.__init__(self, parent, add_toolbar=True, figsize=(5, 5), autoscale_axis=True)
        self.title = title
        self.show_grid = True
        self.data_source = data


class AcceptButton(Button):
    """
    A simple wrapper class for a button
    """
    def __init__(self, parent, callback, text):
        Button.__init__(self,
                        parent,
                        text=text,
                        command=callback)


class InstrumentsChooserWidget(InstrumentSelector):
    """
    This widget contains the instrument selection section.
    """
    def __init__(self, parent, model):
        InstrumentSelector.__init__(self, parent)
        self.parent = parent
        self.model = model

        self.logger = logging.getLogger()

        available_instruments = dict()
        # we specifically only want a laser and a powermeter
        io_set = get_visa_address('Laser')
        available_instruments.update({'Laser': InstrumentRole(self.parent.parent.root, io_set)})
        io_set = get_visa_address('Power Meter')
        available_instruments.update({'Power Meter': InstrumentRole(self.parent.parent.root, io_set)})

        self.title = 'Choose instruments'
        self.instrument_source = available_instruments

        if self.deserialize(self.model.instr_settings_path):
            self.logger.debug("Loading SearchForPeak instruments selection from file.")


class ParameterChooserWidget(ParameterTable):
    """
    This widget contains the parameter selection table.
    """
    def __init__(self, parent, model):
        ParameterTable.__init__(self, parent)
        self.model = model

        self.logger = logging.getLogger()

        self.title = 'Search for Peak Parameters'
        self.parameter_source = self.model.peak_searcher.parameters
        if self.deserialize(self.model.settings_path):
            self.logger.debug("Loading SearchForPeak parameters from file.")

        self.__setup__()


class SearchForPeakPlotsWindowView:
    """
    View Class for SearchForPeakPlotsWindow.
    Contains the current_window attribute, and once instanced sets up the window for interaction. Does not contain
    any logic.
    """
    def __init__(self, parent, model, controller):
        self.root = parent
        self.model = model
        self.controller = controller

        self.current_window = None

        self.main_window = PlottingSettingWidget(parent, model, self, self.controller)
        self.current_window = self.main_window

    @property
    def current_window(self):
        """
        Getter function for current_window
        """
        return self._current_window

    @current_window.setter
    def current_window(self, new_window):
        """
        Setter function for current_window
        """
        self._current_window = new_window


class SearchForPeakPlotsWindowController:
    """
    Controller class for SearchForPeakPlotsWindow. Gets set up first, and then sets up both model and view subclasses.
    Contains all logic as function, and is stored as a reference in both the model and view classes.
    """
    def __init__(self, parent: Tk, experiment_manager):
        # set up model and view classes
        self.model = SearchForPeakPlotsWindowModel(experiment_manager)
        # load the peak searcher and save it to the model
        self.model.load_peak_searcher()
        # load the settings paths and save it to the model
        self.model.load_settings_paths()

        # set up the logger
        self.logger = logging.getLogger()
        self.logger.debug('Search for Peak Plots initialised with parent:%s experiment_manager:%s',
                          parent, experiment_manager)

        # load the observed lists datastrucutre from the peak searcher
        self.model.load_observed_list()

        self.view = SearchForPeakPlotsWindowView(parent, self.model, self)

    def on_close(self):
        """
        If user presses 'x', exit the plotting window.
        """
        # Clear all callbacks because the PeakSearcher object still exists after killing this window
        # but contains callbacks to this window which we are about to destroy now.
        self.view.main_window.plotting_frame.plot_left.data_source = None
        self.view.main_window.plotting_frame.plot_right.data_source = None

        # save configurations to file
        # save SFP parameters to file
        if self.view.main_window.plotting_frame.parameter_chooser_widget.serialize(self.model.settings_path):
            self.logger.debug("Saving SearchForPeak parameters to file.")
        if self.view.main_window.plotting_frame.instruments_chooser_widget.serialize(self.model.instr_settings_path):
            self.logger.debug("Saving SearchForPeak instruments definitions to file.")

        self.view.current_window.destroy()
        self.view.current_window = None

    def disable_buttons(self):
        """
        A function that disables all buttons.
        """
        self.view.main_window.plotting_frame.set_instruments_button.config(state="disabled")
        self.view.main_window.plotting_frame.set_parameters_button.config(state="disabled")

    def enable_buttons(self):
        """
        A function that enables all buttons.
        """
        self.view.main_window.plotting_frame.set_instruments_button.config(state="normal")
        self.view.main_window.plotting_frame.set_parameters_button.config(state="normal")

    def set_instruments(self):
        """If user selected instruments, initialise them and continue.
        """

        self.disable_buttons()

        self.logger.debug('SearchForPeakPlotsWindows::_set_instruments:')
        for el, val in self.view.main_window.plotting_frame.instruments_chooser_widget.instrument_source.items():
            self.model.peak_searcher.selected_instruments.update({el: val.choice})
            self.logger.debug('Element %s, Choice %s', el, val.choice)

        try:
            self.model.peak_searcher.init_instruments()
        except Exception as err:
            messagebox.showerror("Search for peak error!",
                                 "The instrument definition was not successful. Reason: " + repr(err),
                                 parent=self.view.main_window)
            self.logger.exception("The instrument definition was not successful.")
        else:
            messagebox.showinfo("Search for Peak",
                                "Search for peak instruments definition done.",
                                parent=self.view.main_window)
            self.logger.debug("Search for peak instruments definition done.")

        # all good
        self.model.peak_searcher.initialized = True
        self.model.experiment_manager.main_window.model.status_sfp_initialized.set(self.model.peak_searcher.initialized)

        self.enable_buttons()

    def execute_sfp_manually(self):
        """Function to manually start the search for peak algorithm.
        """

        self.disable_buttons()
        # save SFP parameters to measurement
        self.model.peak_searcher.parameters = \
            self.view.main_window.plotting_frame.parameter_chooser_widget.to_meas_param()

        # save SFP parameters to file
        if self.view.main_window.plotting_frame.parameter_chooser_widget.serialize(self.model.settings_path):
            self.logger.debug("Saving SearchForPeak parameters to file.")
        if self.view.main_window.plotting_frame.instruments_chooser_widget.serialize(self.model.instr_settings_path):
            self.logger.debug("Saving SearchForPeak instruments definitions to file.")

        try:
            self.model.peak_searcher.search_for_peak()
        except Exception as err:
            messagebox.showerror("Search for peak error!", "The search for peak algorithm failed. Reason: " + repr(err),
                                 parent=self.view.main_window)
            self.logger.exception("The search for peak algorithm failed.")
        else:
            messagebox.showinfo("Search for Peak", "Search for peak algorithm done.",
                                parent=self.view.main_window)
            self.logger.debug("Search for peak algorithm done.")

        # beautify plots with legends, axes labels, and titles
        self.view.main_window.plotting_frame.plot_left.ax.legend(loc='lower center')
        self.view.main_window.plotting_frame.plot_left.set_axes('deviation from start [um]', 'power [dBm]')
        self.view.main_window.plotting_frame.plot_left.title = 'Left Stage'
        self.view.main_window.plotting_frame.plot_left.__update_canvas__()
        self.view.main_window.plotting_frame.plot_right.ax.legend(loc='lower center')
        self.view.main_window.plotting_frame.plot_right.set_axes('deviation from start [um]', 'power [dBm]')
        self.view.main_window.plotting_frame.plot_right.title = 'Right Stage'
        self.view.main_window.plotting_frame.plot_right.__update_canvas__()

        self.enable_buttons()


class SearchForPeakPlotsWindow:
    def __init__(self, parent: Tk, experiment_manager):
        self.controller = SearchForPeakPlotsWindowController(parent, experiment_manager)
        self.plot_window = self.controller.view.main_window
