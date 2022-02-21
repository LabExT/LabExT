#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from operator import add
from tkinter import BooleanVar, Checkbutton, Frame, Label, OptionMenu, StringVar, Button, messagebox, NORMAL, DISABLED, LEFT, RIGHT, TOP, X, E, W
from functools import partial, reduce
from itertools import product
from bidict import bidict
from typing import Type

from LabExT.Movement.Transformations import Dimension, KabschRotation, SinglePointFixation
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Movement.CoordinatePairingsWindow import CoordinatePairingsWindow
from LabExT.Movement.Calibration import AxesRotation, Calibration, Axis, CalibrationError, Direction
from LabExT.Utils import run_with_wait_window, try_to_lift_window
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.Wizard import Wizard


class StageCalibrationView(Wizard):
    """
    Implements a Wizard for calibrate the stages in 3 steps.

    1. Fix cooridnate system to allow relative movement in chip cooridnates
    2. Fix one single point to allow approx absolute movement in chip cooridnates
    3. Fully calibrate stages by defining a global rotation
    """

    STAGE_AXIS_OPTIONS = bidict({o: " ".join(map(str, o))
                                for o in product(Direction, Axis)})

    def __init__(self, parent, experiment_manager, controller, mover) -> None:
        super().__init__(
            parent,
            width=1000,
            height=700,
            on_cancel=self._on_cancel,
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
        self._make_3D_rotation_var = {
            c: BooleanVar(
                self.parent,
                self._current_full_calibrations[c].is_3D) for c in self.mover.calibrations.values()}
        self._make_3D_rotation_checkbuttons = {}
        self._full_calibration_new_pairing_button = None

        # -- 4. STEP: FINISH --
        self.finish_step = self.add_step(
            self._finish_step_builder,
            title="Finish",
            finish_step_enabled=True)

        # Global state
        self._coordinate_pairing_window = None

        # Connect steps
        self.fix_coordinate_system_step.next_step = self.fix_single_point_step
        self.fix_single_point_step.previous_step = self.fix_coordinate_system_step
        self.fix_single_point_step.next_step = self.full_calibration_step
        self.full_calibration_step.previous_step = self.fix_single_point_step
        self.full_calibration_step.next_step = self.finish_step

        # Start Wizard by setting the current step
        self.current_step = self.fix_coordinate_system_step

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
                command=lambda calibration=calibration: self._new_coordinate_pairing_window(
                    in_calibration=calibration if calibration.is_input_stage else None,
                    out_calibration=calibration if calibration.is_output_stage else None,
                    on_finish=partial(
                        self._apply_single_point_pairing,
                        calibration))).pack(
                side=RIGHT)

    def _full_calibration_step_builder(self, frame):
        """
        Step builder to make a full calibration.
        """
        frame.title = "Fully calibrate Stages"

        step_description = Label(
            frame,
            text="In this step all stages can be set by a global transformation to allow safe absolute moving in chip coordinates.\n"
            "Please define 2 or 3 coordinate pairs for each stage.")
        step_description.pack(side=TOP, fill=X)

        pairings_frame = CustomFrame(frame)
        pairings_frame.title = "Current Pairings"
        pairings_frame.pack(side=TOP, fill=X)

        pairings_table_frame = Frame(pairings_frame)
        pairings_table_frame.pack(side=TOP, fill=X, expand=False)

        CustomTable(
            parent=pairings_table_frame, selectmode='none', columns=(
                'Stage', 'Stage Cooridnate', 'Device', 'Chip Coordinate'), rows=reduce(
                add, [
                    r.pairings for r in self._current_full_calibrations.values()], []))

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

        self._full_calibration_new_pairing_button = Button(
            new_pairing_frame,
            text="New Pairing...",
            command=lambda: self._new_coordinate_pairing_window(
                in_calibration=self.mover.input_calibration if self._use_input_stage_var.get() else None,
                out_calibration=self.mover.output_calibration if self._use_output_stage_var.get() else None,
                on_finish=self._apply_pairings))
        self._full_calibration_new_pairing_button.pack(side=RIGHT)

        current_rotations_frame = CustomFrame(frame)
        current_rotations_frame.title = "Current Rotations"
        current_rotations_frame.pack(side=TOP, fill=X)

        for idx, (calibration, rotation) in enumerate(
                self._current_full_calibrations.items()):
            Label(
                current_rotations_frame,
                text=str(calibration),
            ).grid(column=0, row=idx, sticky=W)

            Label(
                current_rotations_frame,
                text=str(rotation),
                foreground='#4BB543' if rotation.is_valid else "#FF3333",
            ).grid(column=1, row=idx, padx=5, sticky=W)

            Label(
                current_rotations_frame,
                text="RMSD: {}".format(rotation.rmsd)
            ).grid(column=2, row=idx, padx=5, sticky=W)

            checkbutton_3D_rotation = Checkbutton(
                current_rotations_frame,
                text="3D Transformation",
                variable=self._make_3D_rotation_var[calibration],
                command=partial(
                    self._on_change_rotation_dimension,
                    calibration))
            checkbutton_3D_rotation.grid(column=3, row=idx, sticky=E)
            self._make_3D_rotation_checkbuttons[calibration] = checkbutton_3D_rotation

        rmsd_hint = Label(
            frame,
            text="RMSD: Root mean square distance between the set of chip coordinates and the set of stage coordinates after alignment."
        )
        rmsd_hint.pack(side=TOP, fill=X)

    def _finish_step_builder(self, frame):
        """
        Step builder for finish frame
        """
        frame.title = "Stage Calibration Finished"

        step_description = Label(
            frame,
            text="Congratulations! The Mover Stages are fully calibrated and can now be fully used. Click on 'Finish' to exit the wizard."
        )
        step_description.pack(side=TOP, fill=X)

    #
    #   Callback
    #

    def _on_cancel(self) -> bool:
        """
        Callback, when user wants to quit the wizard.
        Warns user, and resets calibration if agreed.
        """
        if messagebox.askokcancel(
            "Quit Wizard?",
            "Do you really want to cancel the calibration? All changes will be reset.",
                parent=self):
            self.mover.reset_calibrations()
            return True

        return False

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
            messagebox.showerror("Error", str(exec), parent=self)
            return False

        return True

    def _on_wiggle_axis(self, calibration: Type[Calibration], chip_axis: Axis):
        """
        Callback, when user what to wiggle a requested axis.
        """
        if self._performing_wiggle:
            messagebox.showerror(
                "Error",
                "Stage cannot wiggle because another stage is being wiggled. ",
                parent=self)
            return

        message = 'By proceeding this button will move the {} along the {} direction. \n\n'.format(calibration, chip_axis) \
                  + 'Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n' \
                  + 'For correct operation the stage should: \n' \
                  + 'First: Move in positive {}-Chip-Axis direction \n'.format(chip_axis) \
                  + 'Second: Move in negative {}-Chip-Axis direction \n\n'.format(chip_axis) \
                  + 'If not, please check your assignments.\n Do you want to proceed with wiggling?'

        if not messagebox.askokcancel("Warning", message, parent=self):
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
                    calibration, e), parent=self)
        finally:
            self._performing_wiggle = False

        self.lift()

    def _new_coordinate_pairing_window(
            self,
            in_calibration=None,
            out_calibration=None,
            on_finish=None):
        """
        Opens a new window to pair a chip cooridnate with a stage cooridnate.
        """

        if self._check_for_exisiting_coordinate_window():
            return

        try:
            self._coordinate_pairing_window = CoordinatePairingsWindow(
                self.experiment_manager,
                parent=self,
                in_calibration=in_calibration,
                out_calibration=out_calibration,
                on_finish=on_finish)
        except Exception as e:
            messagebox.showerror(
                "Error",
                "Could not initiate a new coordinate pairing: {}".format(e),
                parent=self)

    def _apply_single_point_pairing(self, calibration, pairings):
        """
        Callback, when user finishes single point pairing
        """
        if(len(pairings) > 0):
            self._current_single_point_fixations[calibration].update(
                pairings[0])

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
            messagebox.showerror("Error", str(exec), parent=self)
            return False

        return True

    def _apply_pairings(self, pairings):
        """
        Callback, when user finishes coordinate pairing for full calibration
        """
        for pairing in pairings:
            try:
                self._current_full_calibrations[pairing.calibration].update(
                    pairing)
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    "Could not update rotation: {}".format(e),
                    parent=self)
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
            messagebox.showerror("Error", str(exec), parent=self)
            return False

        return True

    def _on_change_rotation_dimension(self, calibration: Type[Calibration]):
        """
        Callback, when changing the rotation dimension.
        """
        self._current_full_calibrations[calibration].change_rotation_dimension(
            Dimension.THREE if self._make_3D_rotation_var[calibration].get() else Dimension.TWO)
        self.__reload__()

    #
    #   Helper
    #

    def _check_for_exisiting_coordinate_window(self) -> bool:
        """
        Ensures that only one window exists to create a new coordinate pair.

        Returns True if there is a exsiting window.
        """
        if self._coordinate_pairing_window is None or not try_to_lift_window(
                self._coordinate_pairing_window):
            return False

        if not messagebox.askyesno(
            "New Coordinate-Pairing",
            "You have an incomplete creation of a coordinate pair. Click Yes if you want to continue it or No if you want to create the new one.",
                parent=self._coordinate_pairing_window):
            self._coordinate_pairing_window._cancel()
            self._coordinate_pairing_window = None
            return False

        return True
