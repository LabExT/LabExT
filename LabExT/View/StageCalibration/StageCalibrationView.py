#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from operator import add
from tkinter import W, BooleanVar, Checkbutton, Frame, Label, OptionMenu, StringVar, Button, messagebox, NORMAL, DISABLED, LEFT, RIGHT, TOP, X
from functools import partial, reduce
from itertools import product
from LabExT.Movement.Transformations import KabschRotation, SinglePointFixation
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow
from bidict import bidict
from typing import Type

from LabExT.Movement.Calibration import AxesRotation, Calibration, Axis, CalibrationError, Direction
from LabExT.Utils import run_with_wait_window, try_to_lift_window
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.Wizard import Wizard


class StageCalibrationView(Wizard):

    STAGE_AXIS_OPTIONS = bidict({o: " ".join(map(str, o))
                                for o in product(Direction, Axis)})

    def __init__(self, parent, experiment_manager, controller, mover) -> None:
        super().__init__(
            parent,
            width=1000,
            height=700,
            cancel_button_label="Cancel and Close",
            finish_button_label="Finish and Save"
        )
        self.title("Stage Calibration Wizard")

        self.controller = controller
        self.experiment_manager = experiment_manager
        self.mover = mover

        # -- 1. STEP: FIX COORDINATE SYSTEM --
        self.fix_coordinate_system_step = self.add_step(
            self._fix_coordinate_system_step_builder,
            title="Fix Coordinate System",
            on_reload=self._check_axis_calibration,
            on_next=self._on_save_axes_rotations)
        # Step state and variables
        self._performing_wiggle = False
        self._current_axes_rotations = {}
        self._axis_calibration_vars = {}
        self._axis_wiggle_buttons = {}

        for calibration in self.mover.calibrations.values():
            self._current_axes_rotations[calibration] = AxesRotation()

            axes_vars = {}
            for chip_axis in Axis:
                axes_vars[chip_axis] = StringVar(
                    self.parent, self.STAGE_AXIS_OPTIONS[(Direction.POSITIVE, chip_axis)])
                axes_vars[chip_axis].trace(
                    W,
                    lambda *_,
                    calibration=calibration,
                    chip_axis=chip_axis: self._on_axis_calibrate(
                        calibration,
                        chip_axis))

            self._axis_calibration_vars[calibration] = axes_vars

        # -- 2. STEP: FIX SINGLE POINT --
        self.fix_single_point_step = self.add_step(
            self._fix_single_point_step_builder,
            title="Fix Single Point",
            on_reload=self._check_single_point_fixations,
            on_next=self._on_save_single_point_fixations)
        # Step state and variables
        self._current_single_point_fixations = {
            c: SinglePointFixation() for c in self.mover.calibrations.values()}

        # -- 3. STEP: FULL CALIBRATION --
        self.full_calibration_step = self.add_step(
            self._full_calibration_step_builder,
            title="Fully calibrate Stages",
            on_reload=self._check_full_calibrations,
            on_next=self._on_save_full_calibrations)
        # Step state and variables
        self._current_full_calibrations = {
            c: KabschRotation() for c in self.mover.calibrations.values()}
        self._use_input_stage_var = BooleanVar(self.parent, True)
        self._use_output_stage_var = BooleanVar(self.parent, True)

        # Global state
        self._coordinate_pairing_window = None

        # Connect steps
        self.fix_coordinate_system_step.next_step = self.fix_single_point_step
        self.fix_single_point_step.previous_step = self.fix_coordinate_system_step
        self.fix_single_point_step.next_step = self.full_calibration_step
        self.full_calibration_step.previous_step = self.fix_single_point_step

        # Start Wizard by setting the current step
        self.current_step = self.full_calibration_step

    def _fix_coordinate_system_step_builder(self, frame: Type[CustomFrame]):
        """
        Step builder to fix the coordinate system.
        """
        frame.title = "Fix Coordinate System"

        step_description = Label(
            frame,
            text="In order for each stage to move relative to the chip coordinates, the direction of each axis of each stage must be defined. \n Postive Y-Axis: North of chip, Positive X-Axis: East of chip, Positive Z-Axis: Lift stage")
        step_description.pack(side=TOP, fill=X)

        for calibration in self.mover.calibrations.values():
            stage_calibration_frame = CustomFrame(frame)
            stage_calibration_frame.title = str(calibration)
            stage_calibration_frame.pack(side=TOP, fill=X, pady=2)

            for chip_axis in Axis:
                chip_axis_frame = Frame(stage_calibration_frame)
                chip_axis_frame.pack(side=TOP, fill=X)

                Label(
                    chip_axis_frame,
                    text="Positive {}-Chip-axis points to ".format(chip_axis.name)
                ).pack(side=LEFT)

                OptionMenu(
                    chip_axis_frame,
                    self._axis_calibration_vars[calibration][chip_axis],
                    *self.STAGE_AXIS_OPTIONS.values(),
                ).pack(side=LEFT)

                Label(chip_axis_frame, text="of Stage").pack(side=LEFT)

                wiggle_button = Button(
                    chip_axis_frame,
                    text="Wiggle {}-Axis".format(
                        chip_axis.name),
                    command=partial(
                        self._on_wiggle_axis,
                        calibration,
                        chip_axis),
                    state=NORMAL if self._current_axes_rotations[calibration].is_valid else DISABLED)
                wiggle_button.pack(side=RIGHT)

                self._axis_wiggle_buttons.setdefault(
                    calibration, {})[chip_axis] = wiggle_button

    def _fix_single_point_step_builder(self, frame):
        """
        Step builder to fix a single point.
        """
        frame.title = "Fix Single Point"

        step_description = Label(
            frame,
            text="To move the stage absolute to chip coordinates, a stage coordinate is fixed with a chip coordinate and the translation of the two coordinate systems is calculated. \n" +
            "Note: It is assumed that the chip and stage coordinate axes are parallel, which is not necessarily the case. Therefore this is only an approximation.")
        step_description.pack(side=TOP, fill=X)

        for calibration in self.mover.calibrations.values():
            single_point_fixation_frame = CustomFrame(frame)
            single_point_fixation_frame.title = str(calibration)
            single_point_fixation_frame.pack(side=TOP, fill=X, pady=2)

            current_fixation = self._current_single_point_fixations[calibration]

            Label(
                single_point_fixation_frame,
                text=str(current_fixation),
                foreground='#4BB543' if current_fixation.is_valid else "#FF3333",
            ).pack(
                side=LEFT)

            Button(
                single_point_fixation_frame,
                text="Update Pairing ...",
                command=partial(self._on_single_point_fixation, calibration)
            ).pack(side=RIGHT)
    
    def _full_calibration_step_builder(self, frame):
        """
        Step builder to make a full calibration.
        """
        frame.title = "Fully calibrate Stages"

        step_description = Label(
            frame,
            text="In this step all stages can be set by a global transformation to allow safe absolute moving in chip coordinates.\n" \
                 "Please define 2 or 3 coordinate pairs for each stage."
        )
        step_description.pack(side=TOP, fill=X)

        pairings_frame = CustomFrame(frame)
        pairings_frame.title = "Current Pairings"
        pairings_frame.pack(side=TOP, fill=X)

        pairings_table_frame = Frame(pairings_frame)
        pairings_table_frame.pack(side=TOP, fill=X, expand=False)

        CustomTable(
            parent=pairings_table_frame,
            selectmode='none',
            columns=(
                'Stage', 'Stage Cooridnate', 'Device', 'Chip Coordinate'
            ),
            rows=reduce(add, [r.pairings for r in self._current_full_calibrations.values()], []))

        new_pairing_frame = CustomFrame(pairings_frame)
        new_pairing_frame.title = "New Pairing"
        new_pairing_frame.pack(side=TOP, fill=X, pady=5)

        Checkbutton(
            new_pairing_frame,
            text="Use Input-Stage for Transformation".format(self.mover.input_calibration),
            variable=self._use_input_stage_var
        ).pack(side=LEFT)

        Checkbutton(
            new_pairing_frame,
            text="Use Output-Stage for Transformation".format(self.mover.output_calibration),
            variable=self._use_output_stage_var
        ).pack(side=LEFT)

        Button(
            new_pairing_frame,
            text="New Pairing...",
            command=self._on_new_rotation_pairing
        ).pack(side=RIGHT)

        current_rotation_frame = CustomFrame(frame)
        current_rotation_frame.title = "Current Rotations"
        current_rotation_frame.pack(side=TOP, fill=X, pady=2)

        for calibration, rotation in self._current_full_calibrations.items():
            Label(
                current_rotation_frame,
                text="{}: {}".format(calibration, rotation),
                foreground='#4BB543' if rotation.is_valid else "#FF3333",
            ).pack(side=TOP)

            
    
    #
    #   Callback
    #

    def _on_axis_calibrate(
            self,
            calibration: Type[Calibration],
            chip_axis: Axis):
        """
        Callback, when user changes stage to chip axis mapping.

        Updates current axis calibration.
        """
        selection = self._axis_calibration_vars[calibration][chip_axis].get()
        direction, stage_axis = self.STAGE_AXIS_OPTIONS.inverse[selection]
        self._current_axes_rotations[calibration].update(
            chip_axis=chip_axis, stage_axis=stage_axis, direction=direction
        )
        self.__reload__()

    def _check_axis_calibration(self):
        """
        Callback, when coordinate system fixation step gets reloaded.

        Checks, if the current assignment is valid.
        """
        if all(r.is_valid for r in self._current_axes_rotations.values()):
            self.current_step.next_step_enabled = True
            self.set_error("")
        else:
            self.current_step.next_step_enabled = False
            self.set_error("Please do not assign a stage axis twice.")

    def _on_save_axes_rotations(self):
        """
        Callback, when user finishes axes calibration.
        """
        try:
            self.controller.save_coordinate_system(
                self._current_axes_rotations)
        except CalibrationError as exec:
            messagebox.showerror("Error", str(exec))
            return False

        return True

    def _on_wiggle_axis(self, calibration: Type[Calibration], chip_axis: Axis):
        """
        Callback, when user what to wiggle a requested axis.
        """
        if self._performing_wiggle:
            messagebox.showerror(
                "Error", "Stage cannot wiggle because another stage is being wiggled. ")
            return

        message = 'By proceeding this button will move the {} along the {} direction. \n\n'.format(calibration, chip_axis) \
                  + 'Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n' \
                  + 'For correct operation the stage should: \n' \
                  + 'First: Move in positive {}-Chip-Axis direction \n'.format(chip_axis) \
                  + 'Second: Move in negative {}-Chip-Axis direction \n\n'.format(chip_axis) \
                  + 'If not, please check your assignments.\n Do you want to proceed with wiggling?'

        if not messagebox.askokcancel("Warning", message):
            return

        try:
            self._performing_wiggle = True
            run_with_wait_window(
                self, description="Wiggling {} of {}".format(
                    chip_axis, calibration), function=lambda: calibration.wiggle_axis(
                    chip_axis, self._current_axes_rotations[calibration]))
        except Exception as e:
            messagebox.showerror(
                "Error", "Could not wiggle {}! Reason: {}".format(
                    calibration, e))
        finally:
            self._performing_wiggle = False

        self.lift()

    def _on_single_point_fixation(self, calibration):
        """
        Callback, when user wants to update the single point fixation
        """
        if self._force_only_one_coordinate_window():
            self._coordinate_pairing_window = CoordinatePairingsWindow(
                self.experiment_manager,
                parent=self,
                in_calibration=calibration if calibration.is_input_stage else None,
                out_calibration=calibration if calibration.is_output_stage else None)
            self.wait_window(self._coordinate_pairing_window)
            pairings = self._coordinate_pairing_window.pairings
            if(len(pairings) > 0):
                self._current_single_point_fixations[calibration].update(
                    pairings[0])

            self._coordinate_pairing_window = None
            self.__reload__()

    def _check_single_point_fixations(self):
        """
        Callback, when single point fixation step gets reloaded.

        Checks, if the current fixations are valid.
        """
        if all(f.is_valid for f in self._current_single_point_fixations.values()):
            self.current_step.next_step_enabled = True
            self.set_error("")
        else:
            self.current_step.next_step_enabled = False
            self.set_error("Please define a point to fix for all stages.")

    def _on_save_single_point_fixations(self):
        """
        Callback, when user finishes single point fixation.
        """
        try:
            self.controller.save_single_point_fixation(
                self._current_single_point_fixations)
        except CalibrationError as exec:
            messagebox.showerror("Error", str(exec))
            return False

        return True

    def _on_new_rotation_pairing(self):
        """
        Callback, when user wants to create a new pairing for full calibration.
        """
        if self._force_only_one_coordinate_window():
            use_input = self._use_input_stage_var.get()
            use_output = self._use_output_stage_var.get()
            self._coordinate_pairing_window = CoordinatePairingsWindow(
                self.experiment_manager,
                parent=self,
                in_calibration=self.mover.input_calibration if use_input else None,
                out_calibration=self.mover.output_calibration if use_output else None)
            self.wait_window(self._coordinate_pairing_window)

            for pairing in self._coordinate_pairing_window.pairings:
                try:
                    self._current_full_calibrations[pairing.calibration].update(pairing)
                except Exception as e:
                    messagebox.showerror("Error", "Could not update rotation: {}".format(e))

            self._coordinate_pairing_window = None
            self.__reload__()

    def _check_full_calibrations(self):
        """
        Callback, when user reloads full calibration step.
        """
        if all(r.is_valid for r in self._current_full_calibrations.values()):
            self.current_step.next_step_enabled = True
            self.set_error("")
        else:
            self.current_step.next_step_enabled = False
            self.set_error("Please define a rotation for all stages.")

    
    def _on_save_full_calibrations(self):
        """
        Callback, when user saves full calibration.
        """
        try:
            self.controller.save_full_calibration(
                self._current_full_calibrations)
        except CalibrationError as exec:
            messagebox.showerror("Error", str(exec))
            return False

        return True


    #
    #   Helper
    #

    def _force_only_one_coordinate_window(self) -> bool:
        """
        Ensures that only one window exists to create a new coordinate pair.

        Returns True if it is ok, to create a new window.
        """
        if self._coordinate_pairing_window is None:
            return True

        if messagebox.askyesno(
            "New Coordinate-Pairing",
                "You have an unfinished coordinate pairing creation. Do you want to cancel it and create a new one?"):
            self._coordinate_pairing_window._cancel()
            return True
        else:
            return not try_to_lift_window(self._coordinate_pairing_window)
