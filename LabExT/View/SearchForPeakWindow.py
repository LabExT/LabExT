#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Button, Frame, StringVar, Toplevel, OptionMenu, Label, BOTTOM, TOP, LEFT, RIGHT, X, W, messagebox
from typing import Type
from LabExT.Measurements.MeasAPI.Measparam import MeasParamAuto

from LabExT.Utils import get_visa_address
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentRole, InstrumentSelector
from LabExT.View.Controls.StageSelector import StageRole, StageSelector
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.PlotControl import PlotControl

from LabExT.SearchForPeak import SearchForPeak


class SearchForPeakWindow(Toplevel):

    def __init__(
        self,
        master,
        search_for_peak: Type[SearchForPeak]
    ) -> None:
        Toplevel.__init__(self, master)
        self.search_for_peak = search_for_peak

        # self.protocol("WM_DELETE_WINDOW", controller.on_close)
        self.geometry('+%d+%d' % (self.master.winfo_screenwidth() / 6,
                                  self.master.winfo_screenheight() / 6))
        self.lift()
        self.title('Search for Peak')

        # self.plotting_frame = PlottingFrame(self)

        self.setup_frame = SetupFrame(self, self.search_for_peak)
        self.setup_frame.pack(side=BOTTOM, fill=X, padx=5)

    def __reload__(self):

        for child in self.setup_frame.winfo_children():
            child.forget()

        self.setup_frame.__setup__()


class SetupFrame(CustomFrame):
    """
    Custom Frame for setting up search for peak.
    """

    def __init__(
        self,
        master,
        search_for_peak: Type[SearchForPeak]
    ) -> None:
        CustomFrame.__init__(self, master)
        self.search_for_peak = search_for_peak

        self.logger = logging.getLogger()

        self._available_peak_searchers = self.search_for_peak.peak_searcher_api.imported_classes

        # Define TKinter vars
        self._peak_searcher_var = StringVar(
            self.master,
            self.search_for_peak.peak_searcher.__class__.__name__)
        self._peak_searcher_var.trace(W, self._on_peak_searcher_selection)

        self._instrument_selector = None
        self._stage_selector = None
        self._parameter_table = None

        self.__setup__()

    def __setup__(self) -> None:
        """

        """
        # Step 1: Select a peak searcher rountine.
        self._select_peak_searcher()

        if not self.search_for_peak.peak_searcher:
            return

        # Step 2: Define Instruments, Stages and Parameters
        self._setup_peak_searcher()

    def _select_peak_searcher(self):
        """

        """
        peak_searcher_frame = CustomFrame(self)
        peak_searcher_frame.title = "Select a Peak Searcher"
        peak_searcher_frame.pack(side=TOP, fill=X, pady=5)

        if len(self._available_peak_searchers) > 0:
            Label(
                peak_searcher_frame,
                text="Peak Searcher Routine:", anchor="w"
            ).pack(side=LEFT, fill=X, padx=(0, 5))
            peak_searcher_menu = OptionMenu(
                peak_searcher_frame,
                self._peak_searcher_var,
                *list(self._available_peak_searchers.keys()))
            peak_searcher_menu.pack(side=LEFT, padx=5, pady=5)
        else:
            Label(
                peak_searcher_frame,
                text="No peak searcher available. Please check the addons and imports.",
                foreground="#FF3333").pack(
                side=TOP)

    def _setup_peak_searcher(self):
        """

        """
        setup_peak_searcher_frame = Frame(self)
        setup_peak_searcher_frame.pack(side=TOP, fill=X, pady=5)

        self._instrument_selector = self._create_instrument_selector(
            setup_peak_searcher_frame)
        self._instrument_selector.pack(side=TOP, fill=X)

        self._stage_selector = self._create_stage_selector(
            setup_peak_searcher_frame)
        self._stage_selector.pack(side=TOP, fill=X)

        self._parameter_table = self._create_parameter_table(
            setup_peak_searcher_frame)
        self._parameter_table.pack(side=TOP, fill=X)

        self._setup_button = Button(
            self,
            text=f"Setup {self.search_for_peak.peak_searcher}",
            command=self._on_peak_searcher_setup)
        self._setup_button.pack(side=LEFT)

        self._setup_button = Button(
            self,
            text=f"Setup and Execute {self.search_for_peak.peak_searcher}",
            command=self._on_peak_searcher_execute)
        self._setup_button.pack(side=RIGHT)

    # Reloading

    # def __reload__(self) -> None:
    #     """
    #     Clears frame and reloads contents.
    #     Use this method if a selection changed.
    #     """
    #     for child in self.master.winfo_children():
    #         child.forget()

    #     self.master__setup__()

    # Callbacks

    def _on_peak_searcher_selection(self, *args, **kwargs) -> None:
        """
        Callback, when user changes peak searcher selection.
        """
        peak_searcher_name = str(self._peak_searcher_var.get())
        try:
            self.search_for_peak.set_peak_searcher_by_name(peak_searcher_name)
        except Exception as err:
            messagebox.showerror(
                "Search for Peak Error",
                f"Failed to set new peak searcher: {err}",
                parent=self.master)
            return

    def _on_peak_searcher_execute(self) -> None:

        # DISABLE BUTTONS

        self._on_peak_searcher_setup()

        try:
            self.search_for_peak.run()
        except Exception as err:
            messagebox.showerror(
                "Search for peak error!",
                "The search for peak algorithm failed. Reason: " +
                repr(err),
                parent=self.master)
            self.logger.exception("The search for peak algorithm failed.")
        else:
            messagebox.showinfo(
                "Search for Peak",
                "Search for peak algorithm done.",
                parent=self.master)
            self.logger.debug("Search for peak algorithm done.")

        # ENABLE BUTTONS

    def _on_peak_searcher_setup(self) -> None:

        # DISABLE BUTTONS

        # Setup instruments
        selected_instruments = {}
        for el, val in self._instrument_selector.instrument_source.items():
            selected_instruments.update({el: val.choice})
            self.logger.debug(
                'Instruments: Element %s, Choice %s', el, val.choice)

        try:
            self.search_for_peak.initialize_selected_instruments(
                selected_instruments)
        except Exception as err:
            messagebox.showerror(
                "Search for peak error!",
                "The instrument definition was not successful. Reason: " +
                repr(err),
                parent=self.master)
            self.logger.exception(
                "The instrument definition was not successful.")
        else:
            self.logger.info("Search for peak instruments definition done.")

        # Setup Stages
        selected_stages = {}
        for el, val in self._stage_selector.stages_source.items():
            selected_stages.update({el: val.choice})
            self.logger.debug('Stages: Element %s, Choice %s', el, val.choice)

        try:
            self.search_for_peak.set_selected_stages(selected_stages)
        except Exception as err:
            messagebox.showerror(
                "Search for peak error!",
                "The stages definition was not successful. Reason: " +
                repr(err),
                parent=self.master)
            self.logger.exception("The stages definition was not successful.")
        else:
            self.logger.info("Search for peak stages definition done.")

        # Parameters
        selected_parameters = self._parameter_table.to_meas_param()
        try:
            self.search_for_peak.set_selected_parameters(selected_parameters)
        except Exception as err:
            messagebox.showerror(
                "Search for peak error!",
                "The parameter definition was not successful. Reason: " +
                repr(err),
                parent=self.master)
            self.logger.exception(
                "The parameter definition was not successful.")
        else:
            self.logger.info("Search for peak parameter definition done.")

        # ENABLE BUTTON

    # Helper

    def _create_instrument_selector(self, parent) -> Type[InstrumentSelector]:
        """
        Returns a new InstrumentSelector for given search for peak instruments.
        """
        if self.search_for_peak.peak_searcher is None:
            return

        stored_instr_settings = self.search_for_peak.get_peak_searcher_settings(
            self.search_for_peak.peak_searcher, self.search_for_peak.INSTRUMENTS_KEY)

        instrument_selector = InstrumentSelector(parent)
        instrument_selector.title = "Define Instruments for {}".format(
            self.search_for_peak.peak_searcher)

        available_instruments = {}
        for role_name in self.search_for_peak.peak_searcher.get_wanted_instruments():
            io_set = get_visa_address(role_name)
            instr_role = InstrumentRole(self.master, io_set)

            if role_name in stored_instr_settings:
                instr_role.create_and_set(stored_instr_settings[role_name])

            available_instruments.update({role_name: instr_role})
        instrument_selector.instrument_source = available_instruments

        return instrument_selector

    def _create_stage_selector(self, parent) -> Type[StageSelector]:
        """
        Returns a new StageSelector for given search for peak stages.
        """
        if self.search_for_peak.peak_searcher is None:
            return

        stored_stage_settings = self.search_for_peak.get_peak_searcher_settings(
            self.search_for_peak.peak_searcher, self.search_for_peak.STAGES_KEY)

        stage_selector = StageSelector(parent)
        stage_selector.title = "Define Stages for {}".format(
            self.search_for_peak.peak_searcher)

        available_stages = {}
        for role_name in self.search_for_peak.peak_searcher.get_wanted_stages():
            stage_role = StageRole(
                self.master,
                self.search_for_peak.mover.calibrations)
            if role_name in stored_stage_settings:
                stage_role.create_and_set(
                    stored_stage_settings[role_name])

            available_stages.update({role_name: stage_role})

        stage_selector.stages_source = available_stages

        return stage_selector

    def _create_parameter_table(self, parent) -> Type[ParameterTable]:
        """
        Returns a new ParameterTable for given search for peak parameters.
        """
        if self.search_for_peak.peak_searcher is None:
            return

        parameter_table = ParameterTable(parent)
        parameter_table.title = f"{self.search_for_peak.peak_searcher} Parameters"
        parameter_table.parameter_source = self.search_for_peak.peak_searcher.parameters

        stored_parameter_settings = self.search_for_peak.get_peak_searcher_settings(
            self.search_for_peak.peak_searcher, self.search_for_peak.PARAMETERS_KEY)

        for k, v in stored_parameter_settings.items():
            if k in parameter_table.parameter_source:
                parameter_table.parameter_source[k].value = v

        return parameter_table


class PlottingFrame(CustomFrame):
    """
    The custom frame for structuring the contents.
    Contains two plots, as well as parameter and instrument selection tools
    """

    def __init__(self, parent):
        CustomFrame.__init__(self, parent)
        self.parent = parent

        self.grid(row=0, column=0)
        # self.plot_left = PlotsWidget(self, 'Left Stage', self.model.plots_left)
        # self.plot_left.grid(row=0, column=0, rowspan=2, columnspan=2, padx=5, pady=5)

        # self.plot_right = PlotsWidget(self, 'Right Stage', self.model.plots_right)
        # self.plot_right.grid(row=0, column=2, rowspan=2, columnspan=2, padx=5, pady=5)


class PlotsWidget(PlotControl):
    """
    The PlotsWidget subclass wraps the plots itself. It is uised two times, for both plots.
    """

    def __init__(self, parent, title, data):
        PlotControl.__init__(
            self, parent, add_toolbar=True, figsize=(
                5, 5), autoscale_axis=True)
        self.title = title
        self.show_grid = True
        self.data_source = data
