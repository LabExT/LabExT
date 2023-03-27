#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import logging

from tkinter import Frame, Checkbutton, BooleanVar, Toplevel, Button, messagebox, RIGHT, TOP, X, BOTH, FLAT, Y, LEFT
from typing import Type

from LabExT.Utils import run_with_wait_window
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Calibration import Calibration
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.Wafer.Chip import Chip


class LoadStoredCalibrationWindow(Toplevel):
    """
    Window to load stored calibrations
    """

    def __init__(
        self,
        master,
        mover: Type[MoverNew],
        chip: Type[Chip],
        calibration_settings: dict
    ) -> None:
        """
        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        chip: Chip
            Instance of current chip.
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
        self.chip: Type[Chip] = chip

        self.calibration_settings = calibration_settings
        self.stored_calibrations = self.calibration_settings.get(
            "calibrations", {})

        self.calibration_vars = [
            BooleanVar(self, True) for _ in self.stored_calibrations]

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
        stage_assignment_frame.title = "Assign Stored Calibrations"
        stage_assignment_frame.pack(side=TOP, fill=X)

        for idx, c in enumerate(self.stored_calibrations):
            stored_stage = c.get("stage", {})

            available_calibration_frame = Frame(stage_assignment_frame)
            available_calibration_frame.pack(side=TOP, fill=X, pady=2)

            Checkbutton(
                available_calibration_frame,
                text="Stage {} with address {}".format(
                    stored_stage.get(
                        "class",
                        "Unknown"),
                    stored_stage.get(
                        "parameters",
                        {}).get(
                        "address",
                        "Unknown")),
                variable=self.calibration_vars[idx]).pack(
                side=LEFT,
                fill=X,
                padx=(
                    0,
                    10))

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
        # Reset calibrations
        self.mover.reset_calibrations()

        restored_calibrations = 0
        for idx, calibration_var in enumerate(self.calibration_vars):
            enable_calibration = bool(calibration_var.get())
            if not enable_calibration:
                continue

            stored_calibration = self.stored_calibrations[idx]

            try:
                calibration = Calibration.load(
                    mover=self.mover,
                    data=stored_calibration,
                    chip=self.chip)
                run_with_wait_window(
                    self,
                    "Connecting to stage.",
                    lambda: self.mover.register_stage_calibration(calibration))
            except Exception as err:
                messagebox.showerror(
                    "Calibration Error",
                    f"Failed to load calibration from disk: {err}",
                    parent=self)
                continue

            restored_calibrations += 1

        # Store calibrations to disk
        self.mover.dump_calibrations()

        messagebox.showinfo(
            "Success",
            f"Successfully restored {restored_calibrations} calibration(s)",
            parent=self)
        self.destroy()
