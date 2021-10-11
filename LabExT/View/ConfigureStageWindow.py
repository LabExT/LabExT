#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import threading
import time
from tkinter import Tk, Frame, Label, Button, Entry, messagebox, Checkbutton, ttk, TclError

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled


class ConfigureStageWindow(Frame):
    """This window lets the user configure the stages and also displays the status codes of each positioner
        (left and right stage) in real time
    """

    def __init__(self, parent: Tk, experiment_manager):
        """
        """
        super(ConfigureStageWindow, self).__init__(parent)

        self.logger = logging.getLogger()
        self.logger.debug('Initialised ConfigureStageWindow with parent:%s experiment_manager:%s', parent,
                          experiment_manager)
        self._root = parent
        self._experiment_manager = experiment_manager
        self._mover = self._experiment_manager.mover
        self._root.title = 'Piezo Stage Configuration'
        self._root.geometry('{}x{}'.format(800, 500))

        # if the user aborts, this is set to true, used by the ExperimentWizard
        self._abort = False
        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)

        self.grid(row=0, column=0)  # place window in root element
        self.__setup__()  # setup the window content

    def __on_close__(self):
        """Called when user presses 'x' or quit button
        """
        self.save_values()
        self._stop_thread = True
        self._root.destroy()
        self.aborted = True

    def __setup__(self):
        """
        Function to setup all GUI elements of the ConfigureStageWindow
        """
        if not self._mover.mover_enabled:
            messagebox.showwarning("No driver loaded", "No Piezo-Stage driver loaded. Cannot configure stages.")
            self._root.destroy()
            return

        if self._mover.left_stage is None and self._mover.right_stage is None:
            try:
                self._mover.init_stages()
            except Exception as E:
                msg = "Error during stage configuration: " + repr(E)
                messagebox.showerror("Configure Stages Error", msg)
                self.logger.error(msg)

        try:
            curr_speed_xy = self._mover.get_speed_of_stages_xy()
            curr_speed_z = self._mover.get_speed_of_stages_z()
        except Exception as exc:
            messagebox.showinfo('Error', 'Could not read speed of stages setting! \n Reason: ' + repr(exc) \
                                + '\n\n Setting speeds to 0, check stage configuration window to change.')
            self.logger.exception('Could not read current speed of stages')
            curr_speed_xy = 0
            curr_speed_z = 0
        try:
            z_up_movement = self._mover.get_z_lift()
        except Exception as exc:
            messagebox.showinfo('Error', 'Could not read z lift of stages setting! \n Reason: ' + repr(exc) \
                                + '\n\n Setting speeds to 0, check stage configuration window to change.')
            self.logger.exception('Could not read current z lift of stages')
        try:
            z_direction_left = self._mover.get_z_axis_direction_left()
            if self._mover.num_stages == 2:
                z_direction_right = self._mover.get_z_axis_direction_right()
        except Exception as exc:
            messagebox.showinfo('Error', 'Could not read current z axis orientation of stages! \n Reason: ' + repr(exc) \
                                + '\n\n Consult stages configuration to set the z direction of the stages.')
            self.logger.exception('Could not read current setting of stages.')
            z_up_movement = -1

        self.logger.debug('Configure Stage window called.')

        self._piezo_settings_frame = CustomFrame(self._root)
        self._piezo_settings_frame.title = "Piezo Stage Settings"
        self._piezo_settings_frame.grid(row=0, column=0, sticky='WENS', padx=10)

        self._find_ref_mark_frame = CustomFrame(self._root)
        self._find_ref_mark_frame.title = "Find reference mark"
        self._find_ref_mark_frame.grid(row=1, column=0, sticky='WENS', padx=10, pady=10)

        self._status_frame = CustomFrame(self._root)
        self._status_frame.title = "Status of piezo stages"
        self._status_frame.grid(row=2, column=0, sticky='WENS', padx=10)

        self._label_z_movement = Label(self._piezo_settings_frame, text="Z channel up-movement during xy movement:")
        self._label_xy_speed = Label(self._piezo_settings_frame,
                                     text="Movement speed xy direction (valid range: 0...1e5um/s):")
        self._label_z_speed = Label(self._piezo_settings_frame,
                                    text="Movement speed z direction (valid range: 0...1e5um/s):")
        self._label_xy_speed_unit = Label(self._piezo_settings_frame, text="[um/s]")
        self._label_z_speed_unit = Label(self._piezo_settings_frame, text="[um/s]")
        self._label_z_movement_unit = Label(self._piezo_settings_frame, text="[um]")
        self._label_z_axis_movement = Label(self._piezo_settings_frame, text="Z-axis movement")
        self._label_left_stage = Label(self._piezo_settings_frame, text="Left stage")
        self._label_right_stage = Label(self._piezo_settings_frame, text="Right stage")
        self._label_wiggle_explanation = Label(self._piezo_settings_frame,
                                               text="Please make sure to test the movement direction of the z-axis after you have changed the \'invert\' setting.\n"
                                                    "The checked \'invert\' box can be totally normal. Use the wiggling and follow the instructions to check if the z-direction is set correctly",
                                               justify='left')
        self._entry_xy_speed = Entry(self._piezo_settings_frame)
        self._entry_z_movement = Entry(self._piezo_settings_frame)
        self._entry_z_speed = Entry(self._piezo_settings_frame)
        self._button_quit = Button(self._root, text='Quit', command=self.__on_close__)
        self._button_find_reference_mark = Button(self._find_ref_mark_frame, text='Find reference mark',
                                                  command=self.find_reference_mark_warning)
        self._label_find_ref_mark = Label(self._find_ref_mark_frame,
                                          text="By pressing this button, the stages search \n for "
                                               "the reference mark and drive into neutral position")

        self._button_toggle_left = Button(self._piezo_settings_frame, text="Wiggle left z-axis",
                                          command=self.toggle_z_axis_warning_left)
        self._button_toggle_right = Button(self._piezo_settings_frame, text="Wiggle right z-axis",
                                           command=self.toggle_z_axis_warning_right)
        self._check_left_invert = Checkbutton(self._piezo_settings_frame, text="invert",
                                              command=self.invert_left_stage)
        self._check_right_invert = Checkbutton(self._piezo_settings_frame, text="invert",
                                               command=self.invert_right_stage)
        self._sep1 = ttk.Separator(self._piezo_settings_frame).grid(row=3, sticky="EW", pady=10, columnspan=3)

        self._label_z_movement.grid(row=0, column=0, sticky='W')
        self._label_xy_speed.grid(row=1, column=0, sticky='W')
        self._label_z_speed.grid(row=2, column=0, sticky='W')
        self._label_xy_speed_unit.grid(row=1, column=2, sticky='W')
        self._label_z_speed_unit.grid(row=2, column=2, sticky='W')
        self._label_z_movement_unit.grid(row=0, column=2, sticky='W')
        self._label_z_axis_movement.grid(row=4, column=0, sticky='W')
        curr_row = 4
        self._label_left_stage.grid(row=curr_row, column=1, sticky='W', padx=(30, 0))
        self._label_right_stage.grid(row=curr_row, column=2, sticky='W')
        self._button_toggle_left.grid(row=curr_row + 1, column=1, sticky='W', padx=(30, 0))
        self._button_toggle_right.grid(row=curr_row + 1, column=2, sticky='W')
        self._check_left_invert.grid(row=curr_row + 2, column=1, sticky='W', padx=(30, 0))
        self._check_right_invert.grid(row=curr_row + 2, column=2, sticky='W')
        self._label_wiggle_explanation.grid(row=curr_row + 3, column=0, columnspan=3, sticky='W')

        self._label_find_ref_mark.grid(row=0, column=0, sticky='W')
        self._entry_xy_speed.grid(row=1, column=1, sticky='W', padx=(30, 0))
        self._entry_z_movement.grid(row=0, column=1, sticky='W', padx=(30, 0))
        self._entry_z_speed.grid(row=2, column=1, sticky='W', padx=(30, 0))
        self._button_quit.grid(row=3, column=0)
        self._button_find_reference_mark.grid(row=0, column=1, sticky='W', padx=(30, 0))

        self._entry_xy_speed.delete(0, 'end')
        self._entry_xy_speed.insert(0, '{:.2e}'.format(curr_speed_xy))
        self._entry_z_movement.delete(0, 'end')
        self._entry_z_movement.insert(0, str(z_up_movement))
        self._entry_z_speed.delete(0, 'end')
        self._entry_z_speed.insert(0, '{:.2e}'.format(curr_speed_z))
        if z_direction_left == 1:
            self._check_left_invert.deselect()
        else:
            self._check_left_invert.select()

        if self._mover.num_stages == 2:
            if z_direction_right == 1:
                self._check_right_invert.deselect()
            else:
                self._check_right_invert.select()

        self._label_status = Label(self._status_frame, text="Channel status code")
        self._label_left_stage = Label(self._status_frame, text="Left stage")
        self._label_right_stage = Label(self._status_frame, text="Right stage")
        self._label_status_x = Label(self._status_frame, text="x channel")
        self._label_status_y = Label(self._status_frame, text="y channel")
        self._label_status_z = Label(self._status_frame, text="z channel")
        self._label_status_x_left = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')
        self._label_status_y_left = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')
        self._label_status_z_left = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')
        self._label_status_x_right = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')
        self._label_status_y_right = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')
        self._label_status_z_right = Label(self._status_frame, text="----------", borderwidth=2, relief='sunken')

        self._label_status.grid(row=0, column=2, columnspan=3)
        self._label_left_stage.grid(row=1, column=2)
        self._label_right_stage.grid(row=1, column=4, padx=(10, 0))
        self._label_status_x.grid(row=2, column=0, padx=10)
        self._label_status_y.grid(row=3, column=0, padx=10)
        self._label_status_z.grid(row=4, column=0, padx=10)
        self._label_status_x_left.grid(row=2, column=2)
        self._label_status_y_left.grid(row=3, column=2)
        self._label_status_z_left.grid(row=4, column=2)
        self._label_status_x_right.grid(row=2, column=4, padx=(10, 0))
        self._label_status_y_right.grid(row=3, column=4, padx=(10, 0))
        self._label_status_z_right.grid(row=4, column=4, padx=(10, 0))

        # register key binding
        self._root.bind('<Return>', callback_if_btn_enabled(self.save, self._button_quit))

        self._stop_thread = False
        thread = threading.Thread(target=self.print_status)
        thread.start()

    def save(self, event):
        """
        if user presses enter the values are also saved
        """
        self.save_values()

    def save_values(self):
        """
        saves the current settings
        """
        try:
            new_xy_speed_ums = float(self._entry_xy_speed.get())
            if new_xy_speed_ums == 0:
                messagebox.showwarning("XY Speed Warning", "Setting a xy speed of 0 will turn the speed control OFF! \n"
                                       "The stage will now move as fast as possible. Set a different speed if "
                                       "this is not intended.")
            self._mover.set_speed_of_stages_xy(new_xy_speed_ums)
            self.logger.info('Stage xy speed is set to: ' + '{:.2e}'.format(new_xy_speed_ums) + 'um/s')
        except Exception as E:
            messagebox.showerror("Configure Stages Error", "xy Speed not set \n " + repr(E))
            self.logger.error("Error during stage configuration, XY speed not set: " + repr(E))

        try:
            new_z_speed_ums = float(self._entry_z_speed.get())
            if new_z_speed_ums == 0:
                messagebox.showwarning("Z Speed Warning", "Setting a z speed of 0 will turn the speed control OFF! \n"
                                       "The stage will now move as fast as possible. Set a different speed if "
                                       "this is not intended.")
            self._mover.set_speed_of_stages_z(new_z_speed_ums)
            self.logger.info('Stage z speed is set to: ' + '{:.2e}'.format(new_z_speed_ums) + 'um/s')
        except Exception as E:
            messagebox.showerror("Configure Stages Error", "z speed not set: " + repr(E))
            self.logger.error("Error during stage configuration, z speed not set: " + repr(E))

        try:
            z_lift = float(self._entry_z_movement.get())
            self._mover.set_z_lift(z_lift)
            self.logger.info('Z lift is set to: ' + '%10.3e' % z_lift + 'um')
        except Exception as E:
            messagebox.showerror("Configure Stages Error", "z lift not set: " + repr(E))
            self.logger.error("Error during stage configuration, z lift not set: " + repr(E))

        # save settings
        self._mover.save_settings()

    def print_status(self):
        """
        prints the status of each channel
        """
        status_code = [['----------'] * 3] * 2
        while True:
            try:
                status_code = self._mover.get_status_code()
            except Exception as exc:
                msg = 'Could not read channel status codes! Stopping status reading thread. \n Reason: ' + repr(exc)
                messagebox.showinfo('Error', msg)
                self.logger.exception(msg)
                break

            try:
                self._label_status_x_left.config(text=status_code[0][0])
                self._label_status_y_left.config(text=status_code[0][1])
                self._label_status_z_left.config(text=status_code[0][2])
                self._label_status_x_right.config(text=status_code[1][0])
                self._label_status_y_right.config(text=status_code[1][1])
                self._label_status_z_right.config(text=status_code[1][2])
            except TclError:
                pass  # ignore GUI related errors in case window was already closed but thread is still executing

            time.sleep(0.1)
            if self._stop_thread:
                break

    def find_reference_mark_warning(self):
        """
        Window to warn the user, before the find_refernce_mark command is executed
        """
        message = "Make sure the stages have enough space to move, while searching for the reference mark." \
                  " The whole travel range needs to be clear of obstacles. Do you want to proceed?"

        if messagebox.askokcancel("Warning", message):
            try:
                self._mover.find_reference_mark_all()
            except Exception as exc:
                messagebox.showinfo('Error', 'Could not find reference mark! Reason: ' + repr(exc))
                self.logger.exception('Could not find reference mark.')

    def toggle_z_axis_warning_left(self):
        """
        A warning/info window appears to inform the user what will happen next and asks to proceed.
        If the user clicks on ok, the left stage will be toggled around the z-axis.
        """
        message = 'By proceeding this button will move the left piezo stage along the z direction. \n\n' \
                  + 'Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n' \
                  + 'For correct operation the stage should: \n' \
                  + 'First: Move upward \n' \
                  + 'Second: Move downwards \n\n' \
                  + 'If not, please invert the z-axis of the stage.\n Do you want to proceed with calibration?'

        if messagebox.askokcancel("Warning", message):
            try:
                self._mover.left_stage.wiggle_z_axis_positioner()
            except Exception as exc:
                msg = 'Could not toggle left stage! Reason: ' + repr(exc)
                messagebox.showinfo('Error', msg)
                self.logger.exception(msg)

    def toggle_z_axis_warning_right(self):
        """
        A warning/info window appears to inform the user what will happen next and asks to proceed.
        If the user clicks on ok, the right stage will be toggled around the z-axis.
        """
        if self._mover.num_stages != 2:
            messagebox.showinfo("Info", "Right stage is not connected.")
        else:
            message = 'By proceeding, this button will move the right piezo stage along the z direction \n\n' \
                      + 'Please make sure it has enough travel range(+-5mm) to avoid collision. \n\n' \
                      + 'For correct operation the stage should: \n' \
                      + 'First: Move upward \n' \
                      + 'Second: Move downwards \n\n' \
                      + 'If not, please invert the z-axis of the stage.\n Do you want to proceed with calibration?'

            if messagebox.askokcancel("Warning", message):
                try:
                    self._mover.right_stage.wiggle_z_axis_positioner()
                except Exception as exc:
                    msg = 'Could not toggle right stage! Reason: ' + repr(exc)
                    messagebox.showinfo('Error', msg)
                    self.logger.exception(msg)

    def invert_left_stage(self):
        """
        Inverts the z-axis of the left stage
        """
        try:
            self._mover.left_stage.invert_z_axis()
            self._mover.save_settings()
        except Exception as exc:
            messagebox.showinfo('Error', 'Could not invert z-axis of left stage! Reason: ' + repr(exc))
            self.logger.exception('Could not invert left stage.')

    def invert_right_stage(self):
        """
        Inverts the z-axis of the right stage
        """
        if self._mover.num_stages == 2:
            try:
                self._mover.right_stage.invert_z_axis()
                self._mover.save_settings()
            except Exception as exc:
                messagebox.showinfo('Error', 'Could not invert z-axis of right stage! Reason: ' + repr(exc))
                self.logger.exception('Could not invert right stage.')
        else:
            messagebox.showinfo('Error', 'The right stage is not connected. Cannot invert.')
