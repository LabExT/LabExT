#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import logging

from tkinter import Frame, Label, OptionMenu, StringVar, Toplevel, Button, messagebox, RIGHT, TOP, X, BOTH, FLAT, Y, LEFT
from typing import Type

from LabExT.Utils import run_with_wait_window
from LabExT.Movement.MoverNew import MoverNew
from LabExT.View.Controls.CustomFrame import CustomFrame

class LoadStoredCalibrationWindow(Toplevel):
    """
    Window to load stored calibrations
    """

    ASSIGNMENT_MENU_PLACEHOLDER = "-- unused --"

    MENU_OPTION_TEMPLATE = "Stage-ID: {id} - Port: {port}"

    def __init__(
        self,
        master,
        mover: Type[MoverNew],
        calibration_settings: dict
    ) -> None:
        """
        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        calibration_settings : dict
            Data of stored calibration

        Raises
        ------
        RuntimeError
            If calibrations could not be restored.
        """
        super(LoadStoredCalibrationWindow, self).__init__(master)

        self.logger = logging.getLogger()

        self.mover: Type[MoverNew] = mover
        self.calibration_settings = calibration_settings
        self.stored_calibrations = self.calibration_settings.get(
            "calibrations", {})

        self.calibrations_vars = {}
        self.menu_options = [
            self.MENU_OPTION_TEMPLATE.format(id=c["stage_identifier"], port=c["device_port"])
            for c in self.stored_calibrations]
        self.menu_options.append(self.ASSIGNMENT_MENU_PLACEHOLDER)

        # Set up window
        self.title("Restore calibrations from disk")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(800, 200, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        self.__setup__()

    def __setup__(self):
        """
        Builds window to restore calibrations.
        """
        main_frame = Frame(self, borderwidth=0, relief=FLAT)
        main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        buttons_frame = Frame(
            self,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        buttons_frame.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)

        stage_assignment_frame = CustomFrame(main_frame)
        stage_assignment_frame.title = "Assign Stages"
        stage_assignment_frame.pack(side=TOP, fill=X)

        for avail_stage in self.mover.available_stages:
            available_stage_frame = Frame(stage_assignment_frame)
            available_stage_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                available_stage_frame, text=str(avail_stage), anchor="w"
            ).pack(side=LEFT, fill=X, padx=(0, 10))

            stored_stage = next(
                (c for c in self.stored_calibrations if c["stage_identifier"] == avail_stage.identifier),
                None)
            calibration_var = StringVar(
                main_frame,
                self.MENU_OPTION_TEMPLATE.format(
                    id=stored_stage["stage_identifier"], port=stored_stage["device_port"]
                ) if stored_stage else self.ASSIGNMENT_MENU_PLACEHOLDER)

            OptionMenu(
                available_stage_frame,
                calibration_var,
                *self.menu_options
            ).pack(side=RIGHT, padx=5)
            self.calibrations_vars[avail_stage] = calibration_var

            Label(
                available_stage_frame, text="Calibrations:"
            ).pack(side=RIGHT, fill=X, padx=5)

        Button(
            buttons_frame,
            text="Apply calibrations",
            width=15,
            command=self.apply_calibrations
        ).pack(side=RIGHT, fill=Y, expand=0)

    def apply_calibrations(self):
        """
        Callback, when user wants to apply the calibrations
        """
        assignment = self._resolve_calibrations()
        if any(
                c["stage_identifier"] != s.identifier for s,
                c in assignment.items()):
            if not messagebox.askyesno(
                "Caution: Different stage identifiers",
                "CONFIRMATION REQUIRED: Some calibrations were assigned to a stage with a different identifier than the one used to create the calibration. "
                "Incorrectly assigned calibrations cannot be guaranteed to work. Are you sure you want to apply these assignments?",
                    parent=self):
                return

        # Reset calibrations
        self.mover.reset_calibrations()

        # Apply calibrations
        for stage, stored_calibration in assignment.items():
            try:
                calibration = self.mover.restore_stage_calibration(
                    stage, stored_calibration)
            except Exception as err:
                messagebox.showerror(
                    "Error",
                    f"Failed to restored calibration: {err}",
                    parent=self)
                self.mover.reset_calibrations()
                return

            run_with_wait_window(
                self,
                f"Connecting to stage {stage}",
                lambda: calibration.connect_to_stage())

        # Store calibrations to disk
        self.mover.dump_calibrations()

        messagebox.showinfo(
            "Success",
            f"Successfully restored {len(assignment)} calibration(s)",
            parent=self)
        self.destroy()

    def _resolve_calibrations(self) -> dict:
        """
        Returns a dict that maps for each stage the corresponding calibration.
        """
        assignment = {}
        for stage, calibration_var in self.calibrations_vars.items():
            calibration_var_value = str(calibration_var.get())
            if calibration_var_value == self.ASSIGNMENT_MENU_PLACEHOLDER:
                continue

            menu_option_idx = self.menu_options.index(calibration_var_value)
            selected_calibration = self.stored_calibrations[menu_option_idx]

            if selected_calibration in assignment.values():
                raise ValueError(
                    f"Calibration {calibration_var_value} was selected twice. Please change your assignment.")

            assignment[stage] = selected_calibration

        return assignment
