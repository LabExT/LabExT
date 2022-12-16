#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import numpy as np

from tkinter import Frame, Toplevel, Button, Label, StringVar, messagebox, LEFT, RIGHT, TOP, X, BOTH, DISABLED, FLAT, NORMAL, Y, SUNKEN
from typing import Callable, Type
from LabExT.Utils import run_with_wait_window
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.View.Controls.CoordinateWidget import CoordinateWidget, StagePositionWidget

from LabExT.Movement.Transformations import CoordinatePairing, calculate_z_plane_angle, rigid_transform_with_orientation_preservation
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

        self._input_kabsch_rmsd = StringVar(self, value="0.0")
        self._input_tilt_angle = StringVar(self, value=("0", "0", "0"))

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

        frame = Frame(self._main_frame)
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
        self,
        parent,
        calibration
    ) -> Type[CustomFrame]:
        """
        Builds and returns a frame to display the current pairing state.
        """
        frame = CustomFrame(parent)
        frame.title = calibration.short_str
        frame.pack(side=TOP, fill=X, pady=5, padx=2)

        if not self._device:
            Label(
                frame,
                text="No device selected",
                foreground="#FF3333"
            ).pack(side=LEFT)
            return frame

        self._build_pairing_frame(frame, calibration)
        self._build_live_kabsch_frame(frame, calibration)

        return frame

    def _build_pairing_frame(
        self,
        parent,
        calibration
    ) -> None:
        """
        Builds a frame for coordinate pairing
        """
        if not self._device:
            return

        pairing_frame = Frame(parent)
        pairing_frame.pack(side=TOP, fill=X, pady=2)

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

    def _build_live_kabsch_frame(
        self,
        parent,
        calibration
    ) -> None:
        """
        Builds a frame for live kabsch properties
        """
        if not self._device:
            return

        curr_pairing = self._get_pairing(calibration)

        kabsch_rotation = calibration._kabsch_rotation
        old_stage_coords = kabsch_rotation.stage_coordinates.copy()
        old_chip_coords = kabsch_rotation.chip_coordinates.copy()
        new_stage_coords = np.append(old_stage_coords, np.array(
            [curr_pairing.stage_coordinate.to_numpy()]).T, axis=1)
        new_chip_coords = np.append(old_chip_coords, np.array(
            [curr_pairing.chip_coordinate.to_numpy()]).T, axis=1)

        if old_chip_coords.shape[1] >= 3 and old_stage_coords.shape[1] >= 3:
            old_rotation, _, _, _, old_rmsd = rigid_transform_with_orientation_preservation(
                old_chip_coords, old_stage_coords, axes_rotation=calibration._axes_rotation.matrix)
            _, old_angle_deg, _ = calculate_z_plane_angle(old_rotation)
        else:
            old_rmsd = 0
            old_angle_deg = 0

        if new_chip_coords.shape[1] >= 3 and new_stage_coords.shape[1] >= 3:
            new_rotation, _, _, _, new_rmsd = rigid_transform_with_orientation_preservation(
                new_chip_coords, new_stage_coords, axes_rotation=calibration._axes_rotation.matrix)
            _, new_angle_deg, _ = calculate_z_plane_angle(new_rotation)
        else:
            new_rmsd = 0
            new_angle_deg = 0

        live_kabsch_frame = CustomFrame(parent)
        live_kabsch_frame.title = "Kabsch Properties:"
        live_kabsch_frame.pack(side=TOP, fill=X, pady=2)

        def get_relative_change(new, old) -> float:
            try:
                return (new - old) / old * 100.0
            except ZeroDivisionError:
                return 0.0

        rmsd_change = get_relative_change(new_rmsd, old_rmsd)
        Label(
            live_kabsch_frame,
            text="Root-Mean-Square Deviation:"
        ).grid(row=0, column=0, padx=(0, 5))
        Label(
            live_kabsch_frame,
            text="{:.2f} um from {:.2f} um".format(
                old_rmsd, new_rmsd)
        ).grid(row=0, column=1, padx=(0, 5))
        Label(
            live_kabsch_frame,
            text="{:.2f}% {}".format(
                rmsd_change, "increase" if rmsd_change > 0 else "decrease"),
            foreground="#FF3333" if rmsd_change > 0 else "#4BB543"
        ).grid(row=0, column=2)

        angle_change = get_relative_change(new_angle_deg, old_angle_deg)
        Label(
            live_kabsch_frame,
            text="Angle between XY Plane:"
        ).grid(row=1, column=0, padx=(0, 5))
        Label(
            live_kabsch_frame,
            text="{:.2f}° from {:.2f}°".format(
                old_angle_deg, new_angle_deg)
        ).grid(row=1, column=1, padx=(0, 5))
        Label(
            live_kabsch_frame,
            text="{:.2f}% {}".format(
                angle_change, "increase" if angle_change > 0 else "decrease"),
            foreground="#FF3333" if angle_change > 0 else "#4BB543"
        ).grid(row=1, column=2)

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
