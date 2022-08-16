#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Label, Toplevel, Button, messagebox, RIGHT, TOP, X, BOTH, FLAT, Y
from typing import Type
from LabExT.Movement.Transformations import ChipCoordinate
from LabExT.Movement.config import Axis
from LabExT.Utils import run_with_wait_window

from LabExT.Movement.MoverNew import MoverNew
from LabExT.View.Controls.ParameterTable import ConfigParameter, ParameterTable


class MoveStagesRelativeWindow(Toplevel):
    """
    Window to move stages relative in chip coordinates
    """

    def __init__(
        self,
        master,
        mover: Type[MoverNew]
    ) -> None:
        """
        Constructor for new CoordinatePairing Window.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.

        Raises
        ------
        ValueError
            If input or output calibration are undefined but requested by user.
            If chip is None.
        """
        self.mover: Type[MoverNew] = mover

        if not self.mover.can_move_relatively:
            raise RuntimeError(
                f"Cannot perform relative movement, not all active stages are calibrated correctly. "
                "Note for each stage the coordinate system must be fixed.")

        super(MoveStagesRelativeWindow, self).__init__(master)

        self.parameters = {}

        # Set up window
        self.title("Move Stages Relative")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(600, 400, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        # Build window
        self._main_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        hint = "Move the stages relative in the chip coordinate system.\n"\
               "Note: the stages are NOT automatically z-lifted before lateral movement.\n"\
               "The stages will move one after each other in the order: top, right, bottom, left"
        Label(self._main_frame, text=hint).pack(side=TOP, fill=X)

        self._buttons_frame = Frame(
            self,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        self._buttons_frame.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)

        self._execute_button = Button(
            self._buttons_frame,
            text="Execute Movement",
            width=15,
            command=self.execute_movement)
        self._execute_button.pack(
            side=RIGHT, fill=Y, expand=0)

        self.parameter_tables = {}
        for calibration in self.mover.calibrations.values():
            movement_params = {}
            for axis in Axis:
                movement_params[axis] = ConfigParameter(
                    self, unit='um', parameter_type='number_float')

            parameter_table = ParameterTable(self._main_frame)
            parameter_table.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)
            parameter_table.title = f"Relative movement of {calibration}"
            parameter_table.parameter_source = movement_params

            self.parameter_tables[calibration] = parameter_table
            self.parameters[calibration] = movement_params

    def execute_movement(self):
        """
        Callback, when user wants to execute the movement.
        """
        movement_commands = {}
        for calibration, params in self.parameters.items():
            requested_offset = ChipCoordinate(
                x=float(params[Axis.X].value),
                y=float(params[Axis.Y].value),
                z=float(params[Axis.Z].value))

            if not requested_offset.is_zero:
                movement_commands[calibration.orientation] = requested_offset

        if self._confirm_movement(movement_commands):
            run_with_wait_window(
                self,
                "Moving stages relatively",
                lambda: self.mover.move_relative(movement_commands))

    def _confirm_movement(self, movement_commands) -> bool:
        """
        Asks the user to confirm the movement.
        """
        message = "By proceeding the following movement will be executed: \n\n"
        for orientation, coord in movement_commands.items():
            message += f"{orientation} stage is shifted by the offset {coord}.\n"

        message += "\nDo you want to proceed?"

        return messagebox.askokcancel("Confirm Movement", message, parent=self)
