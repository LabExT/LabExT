#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Toplevel, Button, Label, messagebox, LEFT, RIGHT, TOP, X, BOTH, DISABLED, FLAT, NORMAL, Y
from LabExT.View.Controls.CoordinateWidget import CoordinateWidget
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.DeviceTable import DeviceTable

from LabExT.Movement.Stage import StageError
import LabExT.Movement.Transformations as Transformations
from LabExT.View.Movement.StagePositionWidget import StagePositionWidget


class CoordinatePairingsWindow(Toplevel):
    """
    Window to pair a stage and chip coordinate.
    """

    def __init__(
            self,
            experiment_manager,
            parent,
            in_calibration=None,
            out_calibration=None):
        if in_calibration is None and out_calibration is None:
            raise ValueError(
                "At least one calibration is needed to create a coordinate pairing. ")

        if experiment_manager.chip is None:
            raise ValueError("Cannot create pairing without chip imported. ")

        self.experiment_manager = experiment_manager
        self._in_calibration = in_calibration
        self._out_calibration = out_calibration

        super(CoordinatePairingsWindow, self).__init__(parent)

        self._device = None
        self._in_stage_coordinate = None
        self._out_stage_coordinate = None

        # Set up window
        self.title("New Chip-Stage-Coordinates Pairings")
        self.geometry('{:d}x{:d}+{:d}+{:d}'.format(1000, 600, 200, 200))
        self.protocol('WM_DELETE_WINDOW', self._cancel)

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
            command=self._finish)
        self._finish_button.pack(
            side=RIGHT, fill=Y, expand=0)

        self.__setup__()

    def __setup__(self):
        """
        Builds all widgets based on current state.
        """
        hint = "In this window, a coordinate pairing between stages and chip devices can be created.\n" \
               "Please select a device first and then move the stages to the input or output port of the device."
        top_hint = Label(self._main_frame, text=hint)
        top_hint.pack(side=TOP, fill=X)

        self._select_device_frame()
        self._current_pairings_frame()

    def __reload__(self):
        """
        Reloads window.
        """
        for child in self._main_frame.winfo_children():
            child.forget()

        self._finish_button.config(state=NORMAL if self._device else DISABLED)

        self.__setup__()
        self.update_idletasks()

    @property
    def pairings(self):
        """
        Returns a list of coordinate pairings if device and stage coordinate is defined, otherwise empty list.
        """
        pairings = []
        if not self._device:
            return pairings

        if not self._out_stage_coordinate and not self._in_stage_coordinate:
            return pairings

        if self._in_calibration and self._in_stage_coordinate:
            pairings.append(Transformations.CoordinatePairing(
                self._in_calibration,
                self._in_stage_coordinate,
                self._device,
                self._device._in_position
            ))

        if self._out_calibration and self._out_stage_coordinate:
            pairings.append(Transformations.CoordinatePairing(
                self._out_calibration,
                self._out_stage_coordinate,
                self._device,
                self._device._out_position
            ))

        return pairings

    #
    #   Frames
    #

    def _current_pairings_frame(self):
        """
        Renders a frame to show the current pairings
        """
        frame = CustomFrame(self._main_frame)
        frame.pack(side=TOP, fill=X, pady=5)

        step_hint = Label(frame, text=self._get_coupling_hint())
        step_hint.pack(side=TOP, fill=X)

        if self._in_calibration:
            self._calibration_pairing_widget(
                frame, self._in_calibration).pack(
                side=TOP, fill=X)

        if self._out_calibration:
            self._calibration_pairing_widget(
                frame, self._out_calibration).pack(
                side=TOP, fill=X)

    def _select_device_frame(self):
        """
        Renders a frame to select a device.
        """
        frame = CustomFrame(self._main_frame)
        frame.title = "Device Selection"
        frame.pack(side=TOP, fill=X, pady=5)

        if not self._device:
            self._device_table = DeviceTable(frame, self.experiment_manager)
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
                text=self._device.short_str(),
                font='Helvetica 12 bold'
            ).pack(side=LEFT, fill=X)

            self._clear_device_button = Button(
                frame,
                text="Clear selection",
                command=self._on_device_selection_clear
            )
            self._clear_device_button.pack(side=LEFT, padx=5)

    #
    #   Callbacks
    #

    def _finish(self):
        try:
            if self._in_calibration:
                self._in_stage_coordinate = self._in_calibration.stage.get_current_position()
            if self._out_calibration:
                self._out_stage_coordinate = self._out_calibration.stage.get_current_position()

            self.destroy()
        except StageError as e:
            messagebox.showerror(
                "Error", "Could not get current position: {}".format(e))

    def _cancel(self):
        self._in_stage_coordinate = None
        self._out_stage_coordinate = None
        self._device = None
        self.destroy()

    def _on_device_selection(self):
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

        self.__reload__()

    def _on_device_selection_clear(self):
        """
        Callback, when user wants to clear the current device selection.
        """
        self._device = None
        self.__reload__()

    #
    #   Helpers
    #

    def _calibration_pairing_widget(self, parent, calibration):
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
                coordinate=self._device._in_position if calibration.is_input_stage else self._device._out_position
            ).pack(side=LEFT)

            Label(
                pairing_frame,
                text="will be paired with Stage coordinate:"
            ).pack(side=LEFT)

            StagePositionWidget(
                pairing_frame,
                stage=calibration.stage
            ).pack(side=LEFT)
        else:
            Label(
                pairing_frame,
                text="No device selected",
                foreground="#FF3333"
            ).pack(side=LEFT)

        return pairing_frame

    def _get_coupling_hint(self):
        if self._in_calibration and self._out_calibration:
            return "You have selected two stages to create a pairing:\n" \
                   "{} must be moved to the input port.\n" \
                   "{} must be moved to the output port.".format(self._in_calibration, self._out_calibration)

        if self._in_calibration:
            return "You have selected one stages to create a pairing:\n" \
                   "{} must be moved to the input port".format(self._in_calibration)

        if self._out_calibration:
            return "You have selected one stages to create a pairing:\n" \
                   "{} must be moved to the output port".format(self._out_calibration)
