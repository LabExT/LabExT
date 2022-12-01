#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import json
import logging

from tkinter import Frame, Label, OptionMenu, StringVar, Toplevel, Button, messagebox, RIGHT, TOP, X, BOTH, FLAT, Y, LEFT
from typing import Type
from datetime import datetime
from os.path import exists

from LabExT.Utils import run_with_wait_window
from LabExT.Movement.MoverNew import MoverNew
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.Wafer.Chip import Chip, Device


class LoadStoredCalibrationWindow(Toplevel):
    """
    Window to load stored calibrations
    """

    ASSIGNMENT_MENU_PLACEHOLDER = "-- unused --"

    def __init__(
        self,
        master,
        mover: Type[MoverNew],
        chip: Type[Chip]
    ) -> None:
        """
        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        chip : Chip
            Instance of the current chip.

        Raises
        ------
        RuntimeError
            If calibrations could not be restored.
        """
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip

        self.logger = logging.getLogger()

        self.calibration_settings = None
        if not exists(self.mover.calibration_settings_file):
            raise RuntimeError(
                "Calibration settings file does not exits.")

        with open(self.mover.calibration_settings_file, "r") as fp:
            self.calibration_settings = json.load(fp)

        if self.calibration_settings.get("chip_name") != self.chip.name:
            self.logger.warn(
                f"There is no stored calibrarion for the chip name '{self.chip.name}'."
                f"Instead found one for chip name '{self.calibration_settings.get('chip_name')}'")

        last_updated_at = "Unknown"
        if "last_updated_at" in self.calibration_settings:
            last_updated_at = datetime.fromisoformat(
                self.calibration_settings["last_updated_at"]).strftime("%d.%m.%Y %H:%M:%S")

        if not messagebox.askyesno(
            "Restore calibration",
                f"Found mover calibration for chip: {self.chip.name}. \n Last updated at: {last_updated_at}. \n"
                "Do you want to restore it?"):
            return

        self.stored_calibrations = self.calibration_settings.get(
            "calibrations", [])
        if len(self.stored_calibrations) == 0:
            raise RuntimeError(
                f"Calibration settings file {self.calibration_settings} does not contain any calibrations.")

        self.calibration_options = [
            f"Orientation: {c.get('orientation')} - Port: {c.get('device_port')}" for c in self.stored_calibrations]
        self.calibration_options.append(self.ASSIGNMENT_MENU_PLACEHOLDER)

        if self.calibration_settings.get("chip_name") != self.chip.name:
            if not messagebox.askokcancel(
                "Confirm restoring.",
                f"The calibration file {self.mover.calibration_settings_file} was calibrated "
                f"with chip {self.calibration_settings.get('chip_name')}. "
                    f"You imported chip {self.chip.name}. Are you sure to continue?"):
                return

        super(LoadStoredCalibrationWindow, self).__init__(master)

        # Set up window
        self.title("Restore calibrations from disk")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(800, 200, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        # Build window
        self._main_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        self.calibrations_vars = {
            s: StringVar(
                self._main_frame,
                self.ASSIGNMENT_MENU_PLACEHOLDER) for s in self.mover.available_stages}

        stage_assignment_frame = CustomFrame(self._main_frame)
        stage_assignment_frame.title = "Assign Stages"
        stage_assignment_frame.pack(side=TOP, fill=X)

        for avail_stage in self.mover.available_stages:
            available_stage_frame = Frame(stage_assignment_frame)
            available_stage_frame.pack(side=TOP, fill=X, pady=2)

            Label(
                available_stage_frame, text=str(avail_stage), anchor="w"
            ).pack(side=LEFT, fill=X, padx=(0, 10))

            calibration_menu = OptionMenu(
                available_stage_frame,
                self.calibrations_vars[avail_stage],
                *self.calibration_options)
            calibration_menu.pack(side=RIGHT, padx=5)

            Label(
                available_stage_frame, text="Calibrations:"
            ).pack(side=RIGHT, fill=X, padx=5)

        self._buttons_frame = Frame(
            self,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        self._buttons_frame.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)

        self._save_button = Button(
            self._buttons_frame,
            text="Apply calibrations",
            width=15,
            command=self.apply_calibrations)
        self._save_button.pack(
            side=RIGHT, fill=Y, expand=0)

    def apply_calibrations(self):
        """
        Callback, when user wants to apply the calibrations
        """
        # Resolve all calibrations.
        calibration_assignment = {}
        for stage, calibration_var in self.calibrations_vars.items():
            _calibration_var_value = str(calibration_var.get())
            if _calibration_var_value == self.ASSIGNMENT_MENU_PLACEHOLDER:
                continue

            try:
                _stored_calibration_index = self.calibration_options.index(
                    _calibration_var_value)
                _stored_calibration = self.stored_calibrations[_stored_calibration_index]
            except (ValueError, IndexError):
                messagebox.showerror(
                    "Error",
                    f"Could not find stored calibration for {_calibration_var_value}",
                    parent=self)
                return

            if _stored_calibration in calibration_assignment.values():
                messagebox.showerror(
                    "Error",
                    f"Calibration {_calibration_var_value} was selected twice.",
                    parent=self)
                return

            if _stored_calibration["stage_identifier"] != stage.identifier:
                if not messagebox.askyesno(
                    "Caution: Different stage identifiers",
                    f"Confirmation needed: The selected calibration was created with a stage with the identifier '{_stored_calibration['stage_identifier']}'. "
                    f"You are now trying to assign this calibration to the stage with the identifier '{stage.identifier}'. "
                    "Are you sure you want to apply this calibration to this stage?",
                        parent=self):
                    return

            calibration_assignment[stage] = _stored_calibration

        # Apply calibrations
        self.mover.reset_calibrations()
        for stage, stored_calibration in calibration_assignment.items():
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

        try:
            self.mover.dump_calibrations()
        except Exception as err:
            messagebox.showerror(
                "Error",
                f"Could not store calibration settings to disk: {err}",
                parent=self)
            return

        messagebox.showinfo(
            "Success",
            f"Successfully restored {len(calibration_assignment)} calibration(s)",
            parent=self)

        self.destroy()
