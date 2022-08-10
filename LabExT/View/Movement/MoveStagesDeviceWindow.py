#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Label, Toplevel, Button, messagebox, RIGHT, TOP, X, BOTH, FLAT, Y
from typing import Type
from LabExT.Utils import run_with_wait_window

from LabExT.Movement.MoverNew import MoverNew
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.Wafer.Chip import Chip, Device


class MoveStagesDeviceWindow(Toplevel):
    """
    Window to move stages to device
    """

    def __init__(
        self,
        master,
        mover: Type[MoverNew],
        chip: Type[Chip]
    ) -> None:
        """
        Constructor for new move to device Window.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        mover : Chip
            Instance of the current chip.

        Raises
        ------
        RuntimeError
            If mover cannot move absolutely
            If chip is None.
        """
        self.mover: Type[MoverNew] = mover
        self.chip: Type[Chip] = chip

        if not self.mover.can_move_absolutely:
            raise RuntimeError(
                f"Cannot perform absolute movement, not all active stages are calibrated correctly. "
                "Note for each stage a coordinate transformation must be defined.")

        if self.chip is None:
            raise RuntimeError(
                "'No chip file imported before moving to device. Cannot move to device without chip file present.")

        super(MoveStagesDeviceWindow, self).__init__(master)

        # Set up window
        self.title("Move Stages to Device")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(1000, 400, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.destroy)

        # Build window
        self._main_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        hint = "Automatically move the stages to a device selected below.\n"\
               f"The stages are z-lifted by {self.mover.z_lift:.0f}nm before the lateral movement and lowered again afterwards.\n"
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

        self._device_table = DeviceTable(self._main_frame, self.chip)
        self._device_table.pack(side=TOP, fill=X)

    def execute_movement(self):
        """
        Callback, when user wants to execute the movement.
        """
        selected_device = self._device_table.get_selected_device()
        if selected_device is None:
            messagebox.showwarning(
                'Selection Needed',
                'Please select one device.',
                parent=self)
            return

        if self._confirm_movement(selected_device):
            run_with_wait_window(
                self,
                f"Moving to Device {selected_device.id}",
                lambda: self.mover.move_to_device(self.chip, selected_device))

    def _confirm_movement(self, device: Type[Device]) -> bool:
        """
        Asks the user to confirm the movement.
        """
        message = f"By proceeding the stages will be moved to device {device.id}\n"\
            "Do you want to proceed?"

        return messagebox.askokcancel("Confirm Movement", message, parent=self)
