#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
from tkinter import Tk, Toplevel, Button, Label, Entry, Checkbutton, OptionMenu, messagebox

from LabExT.SearchForPeak.PeakSearcher import PeakSearcher
from LabExT.Utils import get_configuration_file_path, get_visa_address
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentRole, InstrumentSelector
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.PlotControl import PlotControl

BACKLASH_TEST_PARAM_PREFIX = 'Backlash Test: '


def serialize_combined(file_name, *widgets):
    """
    Merges the value dicts of multiple ParameterTable-derived widgets and writes
    them as a single settings file. Needed because ParameterTable.serialize()
    overwrites the whole file with only its own widget's data - calling it on two
    widgets pointed at the same file would let the second call erase the first's
    contribution.
    """
    combined_data = {}
    for widget in widgets:
        widget_settings = {}
        widget.serialize_to_dict(widget_settings)
        combined_data.update(widget_settings.get('data', {}))
    file_path = get_configuration_file_path(file_name)
    with open(file_path, 'w') as json_file:
        json_file.write(json.dumps({'data': combined_data}))
    return True


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
        self.plot_left.grid(row=0, column=0, rowspan=3, columnspan=3, padx=0, pady=0)

        self.plot_right = PlotsWidget(self, 'Right Stage', self.model.plots_right)
        self.plot_right.grid(row=0, column=3, rowspan=3, columnspan=3, padx=0, pady=0)

        self.instruments_chooser_widget = InstrumentsChooserWidget(self, self.model)
        self.instruments_chooser_widget.grid(row=3, column=0, rowspan=1, columnspan=3)

        # Both parameter tables live in their own sub-frame with an independent grid,
        # so they stack tightly against each other regardless of the outer grid's row
        # heights (which are dominated by the much taller plots in rows 0-2).
        self.parameters_frame = ParametersFrame(self, self.model)
        self.parameters_frame.grid(row=0, column=6, rowspan=5, columnspan=3, sticky='n')
        self.parameter_chooser_widget = self.parameters_frame.parameter_chooser_widget
        self.backlash_parameter_chooser_widget = self.parameters_frame.backlash_parameter_chooser_widget

        self.set_instruments_button = AcceptButton(self, controller.set_instruments, "1. Allocate Instruments")
        self.set_instruments_button.grid(row=3, column=3)

        self.save_parameters_button = AcceptButton(self, controller.save_parameters, "Save Parameters")
        self.save_parameters_button.grid(row=3, column=4)

        self.execute_sfp_button = AcceptButton(self, controller.execute_sfp_manually, "2. Execute Search for Peak")
        self.execute_sfp_button.grid(row=3, column=5)

        self.test_backlash_button = AcceptButton(self, controller.test_backlash, "Test Backlash (X/Y)")
        self.test_backlash_button.grid(row=4, column=5)


class PlotsWidget(PlotControl):
    """
    The PlotsWidget subclass wraps the plots itself. It is used two times, for both plots.
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
        io_set = get_visa_address('Power Meter 1')
        available_instruments.update({'Power Meter 1': InstrumentRole(self.parent.parent.root, io_set)})
        io_set = get_visa_address('Power Meter 2')
        available_instruments.update({'Power Meter 2': InstrumentRole(self.parent.parent.root, io_set)})
        io_set = get_visa_address('Power Meter 3')
        available_instruments.update({'Power Meter 3': InstrumentRole(self.parent.parent.root, io_set)})
        io_set = get_visa_address('Power Meter 4')
        available_instruments.update({'Power Meter 4': InstrumentRole(self.parent.parent.root, io_set)})
        io_set = get_visa_address('Switch')
        available_instruments.update({'Switch': InstrumentRole(self.parent.parent.root, io_set)})

        self.title = 'Choose instruments'
        self.instrument_source = available_instruments

        if self.deserialize(self.model.instr_settings_path):
            self.logger.debug("Loading SearchForPeak instruments selection from file.")


class GroupedPassParameterTable(ParameterTable):
    """
    A ParameterTable variant that condenses PeakSearcher's repeated
    'First/Second/Third Peak Search: <X>' parameters into a single row per <X>,
    with three side-by-side value widgets (one per pass) instead of one full row
    per parameter per pass. All other (non-repeated) parameters still render as
    one row each, exactly like the base ParameterTable.

    Serialization/deserialization/to_meas_param are inherited unchanged from
    ParameterTable, since they operate on the underlying flat parameter dict, not
    on this class's visual layout - so nothing else in this window needs to change.
    """
    PASS_HEADERS = tuple(PeakSearcher.PASS_NAMES)
    PASS_PREFIXES = tuple(f'{name} Peak Search: ' for name in PeakSearcher.PASS_NAMES)
    GROUPED_ENTRY_WIDTH = 10

    def _make_value_widget(self, parameter, width=None):
        """Builds just the value-editing widget for one ConfigParameter."""
        if parameter.parameter_type == 'bool':
            return Checkbutton(self, variable=parameter.variable,
                              state='normal' if parameter.allow_user_changes else 'disabled')
        elif parameter.parameter_type == 'dropdown':
            if not isinstance(parameter.options, (list, tuple)):
                raise ValueError(
                    "Dropdown options has to be a list or tuple, got {} instead.".format(type(parameter.options)))
            return OptionMenu(self, parameter.variable, *parameter.options)
        else:
            return Entry(self, textvariable=parameter.variable,
                        width=width if width is not None else self._customwidth,
                        state='normal' if parameter.allow_user_changes else 'disabled')

    def __setup__(self):
        self.clear()
        if self.parameter_source is None:
            return

        # group parameter names that share a common 'Peak Search: <suffix>' suffix
        # across the First/Second/Third prefixes; everything else stays ungrouped
        grouped = {}
        ungrouped = []
        for parameter_name in self.parameter_source:
            for pass_idx, prefix in enumerate(self.PASS_PREFIXES):
                if parameter_name.startswith(prefix):
                    suffix = parameter_name[len(prefix):]
                    grouped.setdefault(suffix, [None] * len(self.PASS_PREFIXES))[pass_idx] = parameter_name
                    break
            else:
                ungrouped.append(parameter_name)

        r = 0

        # ungrouped parameters: same one-row-per-parameter layout as the base class
        for parameter_name in ungrouped:
            parameter = self.parameter_source[parameter_name]
            self.add_widget(Label(self, text='{}:'.format(parameter_name)),
                            row=r, column=0, padx=5, sticky='w')
            self.rowconfigure(r, weight=1)
            self.columnconfigure(0, weight=1)

            self.add_widget(self._make_value_widget(parameter), row=r, column=1, padx=5, sticky='we')
            if parameter.parameter_type not in ('bool', 'dropdown'):
                self.columnconfigure(1, weight=2)

            if parameter.unit is not None:
                self.add_widget(Label(self, text='[{}]'.format(parameter.unit)),
                                row=r, column=2, padx=5, sticky='we')

            if parameter.parameter_type == 'folder':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_folders),
                                row=r, column=2, padx=5, sticky='we')
            if parameter.parameter_type == 'file':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_files),
                                row=r, column=2, padx=5, sticky='we')
            if parameter.parameter_type == 'openfile':
                self.add_widget(Button(self, text='browse...', command=parameter.browse_files_open),
                                row=r, column=2, padx=5, sticky='we')
            r += 1

        # grouped parameters: one row per suffix, three value columns (one per pass)
        if grouped:
            for col, header in enumerate(self.PASS_HEADERS, start=1):
                self.add_widget(Label(self, text=header, font=('TkDefaultFont', 9, 'bold')),
                                row=r, column=col, padx=5, sticky='w')
            r += 1

            for suffix, keys in grouped.items():
                self.add_widget(Label(self, text='{}:'.format(suffix)),
                                row=r, column=0, padx=5, sticky='w')
                self.rowconfigure(r, weight=1)

                unit_shown = False
                unit = None
                for col, key in enumerate(keys, start=1):
                    if key is None:
                        continue
                    parameter = self.parameter_source[key]
                    self.add_widget(self._make_value_widget(parameter, width=self.GROUPED_ENTRY_WIDTH),
                                    row=r, column=col, padx=5, sticky='we')
                    unit = parameter.unit
                if unit is not None and not unit_shown:
                    self.add_widget(Label(self, text='[{}]'.format(unit)),
                                    row=r, column=len(self.PASS_HEADERS) + 1, padx=5, sticky='w')
                    unit_shown = True
                r += 1


class ParameterChooserWidget(GroupedPassParameterTable):
    """
    This widget contains the parameter selection table for everything except the
    backlash test parameters, which get their own separate widget/table below this
    one (see BacklashTestParameterWidget).
    """
    def __init__(self, parent, model):
        GroupedPassParameterTable.__init__(self, parent)
        self.model = model

        self.logger = logging.getLogger()

        self.title = 'Search for Peak Parameters'
        self.parameter_source = {
            name: param for name, param in self.model.peak_searcher.parameters.items()
            if not name.startswith(BACKLASH_TEST_PARAM_PREFIX)
        }

        if self.deserialize(self.model.settings_path):
            self.logger.debug("Loading SearchForPeak parameters from file.")

        self.__setup__()


class BacklashTestParameterWidget(ParameterTable):
    """
    Separate parameter table shown below the main Search for Peak parameters,
    containing only the 'Backlash Test: <X>' parameters used by
    PeakSearcher.test_backlash().
    """
    def __init__(self, parent, model):
        ParameterTable.__init__(self, parent)
        self.model = model

        self.logger = logging.getLogger()

        self.title = 'Backlash Test Parameters'
        self.parameter_source = {
            name: param for name, param in self.model.peak_searcher.parameters.items()
            if name.startswith(BACKLASH_TEST_PARAM_PREFIX)
        }

        if self.deserialize(self.model.settings_path):
            self.logger.debug("Loading Backlash Test parameters from file.")

        self.__setup__()


class ParametersFrame(CustomFrame):
    """
    Wraps the main Search for Peak parameter table and the Backlash Test parameter
    table in a single sub-frame with its own independent grid, so they stack tightly
    against each other regardless of the outer window's row heights (which are
    dominated by the much taller plots).
    """
    def __init__(self, parent, model):
        CustomFrame.__init__(self, parent)

        self.parameter_chooser_widget = ParameterChooserWidget(self, model)
        self.parameter_chooser_widget.grid(row=0, column=0, sticky='new')

        self.backlash_parameter_chooser_widget = BacklashTestParameterWidget(self, model)
        self.backlash_parameter_chooser_widget.grid(row=1, column=0, sticky='new', pady=(10, 0))


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

        # load the observed lists data structures from the peak searcher
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
        if serialize_combined(self.model.settings_path,
                              self.view.main_window.plotting_frame.parameter_chooser_widget,
                              self.view.main_window.plotting_frame.backlash_parameter_chooser_widget):
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
        self.view.main_window.plotting_frame.save_parameters_button.config(state="disabled")
        self.view.main_window.plotting_frame.execute_sfp_button.config(state="disabled")
        self.view.main_window.plotting_frame.test_backlash_button.config(state="disabled")

    def enable_buttons(self):
        """
        A function that enables all buttons.
        """
        self.view.main_window.plotting_frame.set_instruments_button.config(state="normal")
        self.view.main_window.plotting_frame.save_parameters_button.config(state="normal")
        self.view.main_window.plotting_frame.execute_sfp_button.config(state="normal")
        self.view.main_window.plotting_frame.test_backlash_button.config(state="normal")

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

    def save_parameters(self) -> None:
        """ Save current parameters to measurement and savefile. """
        self.model.peak_searcher.parameters = {
            **self.view.main_window.plotting_frame.parameter_chooser_widget.to_meas_param(),
            **self.view.main_window.plotting_frame.backlash_parameter_chooser_widget.to_meas_param(),
        }
        # save sfp parameters (both tables) to file
        if serialize_combined(self.model.settings_path,
                              self.view.main_window.plotting_frame.parameter_chooser_widget,
                              self.view.main_window.plotting_frame.backlash_parameter_chooser_widget):
            self.logger.debug("Saving SearchForPeak parameters to file.")

    def execute_sfp_manually(self):
        """Function to manually start the search for peak algorithm.
        """

        self.disable_buttons()
        self.save_parameters()
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

    def test_backlash(self):
        """Function to manually run the stage backlash/direction self-test (X/Y only,
        Z is never moved). Only requires stages to be configured, not the Laser/Power
        Meter/Switch instruments.
        """

        self.disable_buttons()
        self.save_parameters()

        try:
            results = self.model.peak_searcher.test_backlash()
        except Exception as err:
            messagebox.showerror("Backlash test error!", "The backlash test failed. Reason: " + repr(err),
                                 parent=self.view.main_window)
            self.logger.exception("The backlash test failed.")
        else:
            summary = "\n".join(
                f"{name}: {'PASS' if r['passed'] else 'FAIL'} (max error {r['max_error_um']:.3f}um)"
                for name, r in results.items()
            )
            if all(r['passed'] for r in results.values()):
                messagebox.showinfo("Backlash Test", f"Backlash test PASSED.\n\n{summary}",
                                    parent=self.view.main_window)
            else:
                messagebox.showwarning("Backlash Test", f"Backlash test FAILED for one or more axes.\n\n{summary}",
                                       parent=self.view.main_window)
            self.logger.debug(f"Backlash test done: {results}")

        self.enable_buttons()


class SearchForPeakPlotsWindow:
    def __init__(self, parent: Tk, experiment_manager):
        self.controller = SearchForPeakPlotsWindowController(parent, experiment_manager)
        self.plot_window = self.controller.view.main_window
