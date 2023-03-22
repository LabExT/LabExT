#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Toplevel, Button, Label, messagebox, LEFT, RIGHT, TOP, X, BOTH, DISABLED, FLAT, NORMAL, Y
from typing import Callable, Type
from LabExT.Utils import run_with_wait_window
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.View.Controls.CoordinateWidget import CoordinateWidget, StagePositionWidget

from LabExT.Movement.Transformations import CoordinatePairing
from LabExT.Movement.MoverNew import MoverNew
from LabExT.Movement.Calibration import Calibration
from LabExT.Movement.config import CoordinateSystem
from LabExT.Wafer.Chip import Chip


class CoordinatePairingsWindow(Toplevel):
    """
    Window to pair a stage and chip coordinate.
    """

    def __init__(
            self,
            master,
            mover: Type[MoverNew],
            chip: Type[Chip],
            on_finish: Type[Callable],
            experiment_manager=None,
            with_input_stage: bool = True,
            with_output_stage: bool = True) -> None:
        """
        Constructor for new CoordinatePairing Window.

        Parameters
        ----------
        master : Tk
            Tk instance of the master toplevel
        mover : Mover
            Instance of the current mover.
        chip : Chip
            Instance of the current imported Chip.
        on_finish : Callable
            Callback function, when user completed the pairing.
        experiment_manager : ExperimentManager = None
            Optional reference to experiment manager to perform SfP and Live Viewer
        with_input_stage : bool = True
            Specifies whether the input stage is to be used.
        with_output_stage : bool = True
            Specifies whether the output stage is to be used.

        Raises
        ------
        ValueError
            If input or output calibration are undefined but requested by user.
            If chip is None.
        """
        super(CoordinatePairingsWindow, self).__init__(master)

        self.chip: Type[Chip] = chip
        self.mover: Type[MoverNew] = mover
        self.experiment_manager = experiment_manager

        self.on_finish = on_finish
        self.with_input_stage = with_input_stage
        self.with_output_stage = with_output_stage

        if self.chip is None:
            raise ValueError("Cannot create pairing without chip imported. ")

        if self.with_input_stage and self.mover.input_calibration is None:
            raise ValueError(
                "No input stage defined, but requested by user to create a pairing.")

        if self.with_output_stage and self.mover.output_calibration is None:
            raise ValueError(
                "No input stage defined, but requested by user to create a pairing.")

        self._device = None

        # Set up window
        self.title("New Chip-Stage-Coordinates Pairings")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(1000, 600, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self.cancel)

        # Build window
        self._main_frame = Frame(self, borderwidth=0, relief=FLAT)
        self._main_frame.pack(side=TOP, fill=BOTH, expand=True, padx=10)

        self._buttons_frame = Frame(
            self,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0)
        self._buttons_frame.pack(side=TOP, fill=X, expand=0, padx=10, pady=10)

        hint = "Press Finish when you have reached an optimal coupling and want to save the pairings."
        finish_hint = Label(self._buttons_frame, text=hint)
        finish_hint.pack(side=LEFT)

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
        hint = "In this window, a coordinate pairing between stages and chip devices can be created.\n" \
               "Please select a device first and then move the stages to the input or output port of the device."
        top_hint = Label(self._main_frame, text=hint)
        top_hint.pack(side=TOP, fill=X)

        frame = CustomFrame(self._main_frame)
        frame.title = "Device Selection"
        frame.pack(side=TOP, fill=X, pady=5)

        if not self._device:
            self._device_table = DeviceTable(frame, self.chip)
            self._device_table.pack(side=TOP, fill=X, expand=True)

            self._select_device_button = Button(
                frame,
                text="Select marked device",
                command=self._on_device_selection
            )
            self._select_device_button.pack(side=LEFT, pady=2)
        else:
            Label(
                frame,
                text=self._device.id,
                font='Helvetica 12 bold'
            ).pack(side=LEFT, fill=X)

            self._clear_device_button = Button(
                frame,
                text="Clear selection",
                command=self._on_device_selection_clear
            )
            self._clear_device_button.pack(side=LEFT, padx=5)

        frame = CustomFrame(self._main_frame)
        frame.pack(side=TOP, fill=X, pady=5)

        step_hint = Label(frame, text=self._get_coupling_hint())
        step_hint.pack(side=TOP, fill=X)

        if self.with_input_stage:
            self._calibration_pairing_widget(
                frame, self.mover.input_calibration).pack(
                side=TOP, fill=X)

        if self.with_output_stage:
            self._calibration_pairing_widget(
                frame, self.mover.output_calibration).pack(
                side=TOP, fill=X)

        if self.experiment_manager:
            shortcuts_frame = CustomFrame(self._main_frame)
            shortcuts_frame.pack(side=TOP, fill=X, pady=5)

            search_for_peak_button = Button(
                shortcuts_frame,
                text="Perform Search for Peak...",
                command=self.experiment_manager.main_window.open_peak_searcher)
            search_for_peak_button.pack(
                side=RIGHT, fill=Y, pady=5, expand=0)

            live_viewer_button = Button(
                shortcuts_frame,
                text="Open Live Viewer...",
                command=self.experiment_manager.main_window.open_live_viewer)
            live_viewer_button.pack(
                side=RIGHT, fill=Y, pady=5, expand=0)

    def __reload__(self) -> None:
        """
        Reloads window.
        """
        for child in self._main_frame.winfo_children():
            child.forget()

        self._finish_button.config(state=NORMAL if self._device else DISABLED)

        self.__setup__()
        self.update_idletasks()

    def finish(self) -> None:
        """
        Callback, when user wants to finish the pairing.

        Builds the pairings and calls the on_finish callback.

        Destroys the window.
        """
        if self._device is None:
            messagebox.showwarning(
                'Device Needed',
                'Please select a device to create a pairing.',
                parent=self)
            return

        pairings = []

        if self.with_input_stage:
            pairings.append(self._get_pairing(self.mover.input_calibration))

        if self.with_output_stage:
            pairings.append(self._get_pairing(self.mover.output_calibration))

        self.on_finish(pairings)
        self.destroy()

    def cancel(self) -> None:
        """
        Callback, when user wants to cancel the pairing.

        Resets the device.

        Destroys the window.
        """
        self._device = None
        self.destroy()

    #
    #   Callbacks
    #

    def _on_device_selection(self) -> None:
        """
        Callback, when user hits "Select marked device" button.
        """
        self._device = self._device_table.get_selected_device()
        if self._device is None:
            messagebox.showwarning(
                'Selection Needed',
                'Please select one device.',
                parent=self)
            return

        self._ask_user_move_to_device()

        self.__reload__()

    def _on_device_selection_clear(self) -> None:
        """
        Callback, when user wants to clear the current device selection.
        """
        self._device = None
        self.__reload__()

    def _ask_user_move_to_device(self):
        """
        Asks the user whether to move to the device after selecting the device. This is possible after a single pairing.
        """
        if self._device is None or not self.mover.can_move_absolutely:
            return

        if not messagebox.askyesno(
                title="Move to device?",
                message="Do you want to move the stages close to the selected device using the available coarse calibration?",
                parent=self):
            return

        run_with_wait_window(
            self, description="Move to device {}".format(
                self._device.id), function=lambda: self.mover.move_to_device(
                self.chip, self._device))
    #
    #   Helpers
    #

    def _get_pairing(
            self,
            calibration: Type[Calibration]) -> Type[CoordinatePairing]:
        """
        Builds and returns a new coordinate pairing for the given calibration.

        Returns None if calibration is None.
        """
        if calibration is None:
            return

        if calibration.is_input_stage:
            chip_coord = self._device.input_coordinate
        elif calibration.is_output_stage:
            chip_coord = self._device.output_coordinate

        with calibration.perform_in_system(CoordinateSystem.STAGE):
            return CoordinatePairing(
                calibration,
                calibration.get_position(),
                self._device,
                chip_coord)

    def _calibration_pairing_widget(
            self, parent, calibration) -> Type[CustomFrame]:
        """
        Builds and returns a frame to display the current pairing state.
        """
        pairing_frame = CustomFrame(parent)
        pairing_frame.title = calibration.short_str
        pairing_frame.pack(side=TOP, fill=X, pady=5)

        if self._device:
            Label(
                pairing_frame,
                text="Chip coordinate:"
            ).pack(side=LEFT)

            CoordinateWidget(
                pairing_frame,
                coordinate=self._device.input_coordinate if calibration.is_input_stage else self._device.output_coordinate
            ).pack(side=LEFT)

            Label(
                pairing_frame,
                text="will be paired with Stage coordinate:"
            ).pack(side=LEFT)

            StagePositionWidget(pairing_frame, calibration).pack(side=LEFT)
        else:
            Label(
                pairing_frame,
                text="No device selected",
                foreground="#FF3333"
            ).pack(side=LEFT)

        return pairing_frame

    def _get_coupling_hint(self):
        """
        Displays a coupling hint depending on the given calibrations.
        """
        if self.with_input_stage and self.with_output_stage:
            return "You have selected two stages to create a pairing:\n" \
                   f"{self.mover.input_calibration} must be moved to the input port.\n" \
                   f"{self.mover.output_calibration} must be moved to the output port."

        if self.with_input_stage:
            return "You have selected one stages to create a pairing:\n" \
                   f"{self.mover.input_calibration} must be moved to the input port"

        if self.with_output_stage:
            return "You have selected one stages to create a pairing:\n" \
                   f"{self.mover.output_calibration} must be moved to the output port"
