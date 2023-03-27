#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from tkinter import StringVar, OptionMenu, Frame, Toplevel, Button, Label, messagebox, LEFT, RIGHT, TOP, X, BOTH, DISABLED, FLAT, NORMAL, Y, W
from typing import Callable, Type
from bidict import bidict

from LabExT.Measurements.MeasAPI.Measparam import MeasParamAuto
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.StageTable import StageTable

from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.PathPlanning import SingleModeFiber
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.config import DevicePort


class StageRegistrationWindow(Toplevel):
    """
    Window to register or edit a stage
    """

    NO_PORT_OPTION = "No, do not activate this stage for Move-to-Device."
    PORT_OPTION_TEMPLATE = "Yes, activate this stage for the {port} port of a device."

    DEFAULT_POLYGON = SingleModeFiber

    def __init__(
        self,
        master,
        mover: Type[MoverNew],
        on_finish: Type[Callable],
        calibration: Type[Calibration] = None,
        exclude_active_stages: bool = True
    ) -> None:
        """
        Constructor for new stage registration window.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        on_finish : Callable
            Callback when finish wizard
        calibration : Calibration = None
            Instance of a calibration. Optional, only when editing a calibration.
        exclude_active_stages : bool = True
            Active stages (already registered) are not displayed
        """
        super(StageRegistrationWindow, self).__init__(master)

        self.logger = logging.getLogger(self.__class__.__name__)

        self.mover: Type[MoverNew] = mover
        self.on_finish = on_finish
        self.exclude_active_stages = exclude_active_stages
        self.edit_calibration = calibration is not None

        if self.edit_calibration:
            self._calibration = calibration
        else:
            self._calibration = Calibration(self.mover)

        # calibration properties: store them during editing
        self._stage = self._calibration.stage
        self._port = self._calibration.device_port
        if self._calibration.stage_polygon:
            self._stage_polygon_cls = self._calibration.stage_polygon.__class__
            self._stage_polygon_parameters = self._calibration.stage_polygon.parameters
        else:
            self._stage_polygon_cls = self.DEFAULT_POLYGON
            self._stage_polygon_parameters = self.DEFAULT_POLYGON.default_parameters

        # port menu options
        self._port_menu_options = bidict({
            self.PORT_OPTION_TEMPLATE.format(port=port): port
            for port in DevicePort})
        self._port_menu_options[self.NO_PORT_OPTION] = None

        # TKinter vars
        self._stage_table = None
        self._polygon_cfg_table = None
        self._stage_port_var = StringVar(
            self, self._port_menu_options.inverse[self._port])
        self._stage_port_var.trace(W, self._on_stage_usage_selection)
        self._stage_polygon_var = StringVar(
            self, str(self._stage_polygon_cls.__name__))
        self._stage_polygon_var.trace(W, self._on_stage_polygon_selection)

        # Set up window
        self.title(
            f"Edit {self._calibration}" if self.edit_calibration else "New Stage Registration")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(900, 600, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        # Build window
        self._main_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        self._buttons_frame = Frame(
            self,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        self._buttons_frame.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)

        self._finish_button = Button(
            self._buttons_frame,
            text="Save and Close",
            width=15,
            state=DISABLED,
            command=self.finish)
        self._finish_button.pack(
            side=RIGHT, fill=Y, expand=0)

        self.__setup__()

    def __setup__(self) -> None:
        """
        Builds all widgets based on current state.
        """
        if self.edit_calibration:
            hint = f"Edit the stage registration for the stage '{self._calibration}'."
        else:
            hint = "Register a new stage to be able to use it in LabExT afterward. Press F1 for help."

        top_hint = Label(self._main_frame, text=hint)
        top_hint.pack(side=TOP, fill=X)

        # STEP 1: Select a stage
        self._stage_selection_step()

        # STEP 2: Use stage for move to device?
        self._stage_usage_step()

        # STEP 3: Set up polygon (optional)
        self._stage_polygon_step()

    def _stage_selection_step(self):
        """
        Builds a frame to select a stage.
        """
        stage_selection_frame = CustomFrame(self._main_frame)
        stage_selection_frame.title = "Stage Selection"
        stage_selection_frame.pack(side=TOP, fill=X, pady=5)

        if not self._stage:
            step_hint = Label(
                stage_selection_frame,
                text="Below you can see all the stages found by LabExT.\n "
                "If stages are missing, go back one step and check if all drivers are loaded.")
            step_hint.pack(side=TOP, fill=X, pady=5)

            self._stage_table = StageTable(
                stage_selection_frame,
                self.mover,
                self.exclude_active_stages)
            self._stage_table.pack(side=TOP, fill=X, expand=True)

            self._select_stage_button = Button(
                stage_selection_frame,
                text="Select marked stage",
                state=NORMAL if self._stage_table.has_stages_to_select else DISABLED,
                command=self._on_stage_selection)
            self._select_stage_button.pack(side=LEFT, pady=2)
        else:
            Label(
                stage_selection_frame,
                text=str(self._stage),
            ).pack(side=LEFT, fill=X)

            self._clear_stage_button = Button(
                stage_selection_frame,
                text="Clear selection",
                command=self._on_stage_selection_clear)
            self._clear_stage_button.pack(side=RIGHT, padx=5)

    def _stage_usage_step(self):
        """
        Builds a frame to choose the stage usage.
        """
        if not self._stage:
            return

        stage_usage_frame = CustomFrame(self._main_frame)
        stage_usage_frame.title = f"Enable Move-to-Device for '{self._stage}'"
        stage_usage_frame.pack(side=TOP, fill=X, pady=5)

        step_hint = Label(
            stage_usage_frame, text=f"You can use the stage '{self._stage}' to automatically move to device inputs or outputs. \n"
            "If this is desired, select below whether the stage should be used for a device's input or output port. \n"
            "This selection is optional; if you do not specify this, the stage can still be used for everything except the move-to-device feature.")
        step_hint.pack(side=TOP, fill=X, pady=5)

        Label(
            stage_usage_frame,
            text="Enable Move-to-Device for the Stage?:", anchor="w"
        ).pack(side=LEFT, fill=X, padx=(0, 5))

        self._port_menu = OptionMenu(
            stage_usage_frame,
            self._stage_port_var,
            *(list(self._port_menu_options.keys())))
        self._port_menu.pack(side=LEFT, padx=5, pady=5)

    def _stage_polygon_step(self):
        """
        Builds a frame to select a stage polygon and properties.
        """
        if self._port is None or self._stage is None:
            return

        stage_polygon_frame = CustomFrame(self._main_frame)
        stage_polygon_frame.title = f"Setup Stage Polygon for '{self._stage}'"
        stage_polygon_frame.pack(side=TOP, fill=X, pady=5)

        step_hint = Label(
            stage_polygon_frame,
            text=f"The selected stage '{self._stage}' will automatically move to the {self._port} port during Move-to-Device. \n"
            "To allow safe and collision-free movement of the stages, the dimensions of the stage are approximated by a polygon. \n"
            "Select a polygon below and change the properties if necessary.")
        step_hint.pack(side=TOP, fill=X, pady=5)

        polygon_selection_frame = Frame(stage_polygon_frame)
        polygon_selection_frame.pack(side=TOP, fill=X)

        Label(
            polygon_selection_frame,
            text="Stage polygon:", anchor="w"
        ).pack(side=LEFT, fill=X, padx=(0, 5))

        polygon_menu = OptionMenu(
            polygon_selection_frame,
            self._stage_polygon_var,
            *(list(self.mover.polygon_api.imported_classes.keys())))
        polygon_menu.pack(side=LEFT, padx=5, pady=5)

        if not self._stage_polygon_cls:
            return

        polygon_cfg_frame = Frame(stage_polygon_frame)
        polygon_cfg_frame.pack(side=TOP, fill=X)

        self._polygon_cfg_table = ParameterTable(polygon_cfg_frame)
        self._polygon_cfg_table.title = f"Configure Polygon: {self._stage_polygon_cls.__name__}"
        self._polygon_cfg_table.parameter_source = {l: MeasParamAuto(
            value=v) for l, v in self._stage_polygon_parameters.items()}
        self._polygon_cfg_table.pack(
            side=TOP, fill=X, expand=0, padx=2, pady=2)

    def __reload__(self) -> None:
        """
        Reloads window.
        """
        for child in self._main_frame.winfo_children():
            child.forget()

        if self._stage is None:
            self._finish_button.config(state=DISABLED)
        else:
            if self._port is None:
                self._finish_button.config(state=NORMAL)
            else:
                self._finish_button.config(
                    state=NORMAL if self._stage_polygon_cls else DISABLED)

        self.__setup__()
        self.update_idletasks()

    def finish(self) -> None:
        """
        Callback, when user wants to finish stage assignment.

        Builds the calibration and calls the on_finish callback.

        Destroys the window.
        """
        assert self._stage is not None, "No stage has been selected. Please select one of the available stages."

        if self._port is not None:
            assert self._stage_polygon_cls is not None, "You must select a stage polygon if the stage is to be activated for move-to-device."
            stage_polygon_cfg = self._polygon_cfg_table.make_json_able()
            stage_polygon = self._stage_polygon_cls.load(
                data=stage_polygon_cfg)
        else:
            stage_polygon = None

        self._calibration.stage = self._stage
        self._calibration.device_port = self._port
        self._calibration.stage_polygon = stage_polygon

        self.on_finish(self._calibration)
        self.destroy()

    #
    #   Callbacks
    #

    def _on_stage_selection(self) -> None:
        """
        Callback, when user hits "Select marked stage" button.
        """
        stage_cls = self._stage_table.get_selected_stage_cls()
        stage_address = self._stage_table.get_selected_stage_address()

        if not stage_cls or not stage_address:
            messagebox.showerror(
                "No stage selected",
                "No stage has been selected. Please select one of the available stages and try again.")
            return

        self.logger.info(
            f"Creating new stage object with class {stage_cls} and address {stage_address}")

        self._stage = stage_cls(address=stage_address)
        self.__reload__()

    def _on_stage_selection_clear(self) -> None:
        """
        Callback, when user wants to clear the current stage selection.
        """
        self._stage = None
        self.__reload__()

    def _on_stage_usage_selection(self, *args, **kwargs) -> None:
        """
        Callback, when user selects stage usage.
        """
        selected_port_option = str(self._stage_port_var.get())
        self._port = self._port_menu_options.get(selected_port_option, None)

        self.__reload__()

    def _on_stage_polygon_selection(self, *args, **kwargs) -> None:
        """
        Callback, when user selects a stage polygon.
        """
        selected_polygon_option = str(self._stage_polygon_var.get())
        self._stage_polygon_cls = self.mover.polygon_api.get_class(
            selected_polygon_option)
        self._stage_polygon_parameters = self._stage_polygon_cls.default_parameters

        self.__reload__()
