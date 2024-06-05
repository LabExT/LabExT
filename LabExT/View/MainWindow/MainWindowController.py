#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os
import sys
from tkinter import Tk, Toplevel, messagebox
from tkinter.simpledialog import askinteger

from LabExT.Experiments.ToDo import ToDo
from LabExT.Utils import get_configuration_file_path
from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
from LabExT.View.MainWindow.MainWindowModel import MainWindowModel
from LabExT.View.MainWindow.MainWindowView import MainWindowView
from LabExT.View.SettingsWindow import SettingsWindow
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled
from LabExT.Wafer.Chip import Chip


class MainWindowController:
    """
    Controller class of MainWindow. Has functions to control various aspect of the window, and upon instantiation
    sets up the view and model classes.
    """

    def __init__(self, parent: Tk, experiment_manager):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager
        """

        self.logger = logging.getLogger()
        self.root = parent

        self.model = MainWindowModel(self, parent, experiment_manager)
        self.view = MainWindowView(self.model, self, self.root, experiment_manager)
        self.model.view = self.view

        self.root = parent  # save reference to ui hierarchy root
        self.experiment_manager = experiment_manager

        self.root.title(self.model.application_title)  # window title

        self.view.set_up_platform()

        self.logger.debug("MainWindow frame initialised.")

        self.view.set_up_root_window()

        self.extra_plots = None

        self.view.set_up_main_window()  # set up the main window content

        self._axis_being_changed = False

        self._register_keyboard_shortcuts()

        self.allow_GUI_changes = True

    def serialize_parameter_frame(self):
        # remove any chip path from parameters if chip is not loaded -> prevent offering reloading-of not loaded chip
        # on next startup
        if self.experiment_manager.chip is None:
            self.model.chip_parameters["Chip path"].value = ""
        if self.view.frame.parameter_frame.chip_parameter_table.serialize(self.model.chiptable_settings_path):
            self.logger.debug("Saved chip settings to file.")
        if self.view.frame.parameter_frame.save_parameter_table.serialize(self.model.savetable_settings_path):
            self.logger.debug("Saved json save path settings to file.")

    def on_window_close(self):
        """Called when user closes the application. Save experiment
        settings in .json and call context-callback.
        """
        self.serialize_parameter_frame()
        self.on_shutdown()

    def update_tables(self, plot_new_meas=False):
        """Updates the two tables in the main window."""
        if not self.allow_GUI_changes:
            return

        self.logger.debug("Updating tables...")
        # set the cursor to loading
        self.root.config(cursor="circle")
        self.view.frame.to_do_table.regenerate()
        self.view.frame.measurement_table.regenerate(plot_new_meas=plot_new_meas)
        # set the cursor back to normal
        self.root.config(cursor="")
        self.logger.debug("Done updating tables")

    def refresh_context_menu(self):
        """
        Refreshes context menu.
        """
        self.view.set_up_context_menu()

    def set_selec_plot_title(self, title):
        """set the title of the selected measurements plot"""
        self.view.frame.selec_plot.title = title

    def axis_changed(self, *args):
        """Called by tkinter if the user selects new axis. Repaints
        the selected measurement plot.

        Parameters
        ----------
        *args
            Tkinter arguments, not used
        """
        # internal flag to suppress multiple runs of this function when changing the variables below
        if self._axis_being_changed:
            return
        self._axis_being_changed = True

        # inform user
        self.logger.debug("Axis changed. Choices are: %s", self._choices)

        # load from settings file
        default_x, default_y = self._load_axis_settings()

        # sanity check the variables and set defaults
        if not self.view.frame.axes_frame.x_axis_choice.get() and self._choices:
            if default_x in self._choices:
                v = default_x
            else:
                v = list(self._choices)[0]
            self.view.frame.axes_frame.x_axis_choice.set(v)
        if not self.view.frame.axes_frame.y_axis_choice.get() and self._choices:
            if default_y in self._choices:
                v = default_y
            else:
                if len(self._choices) > 1:
                    v = list(self._choices)[1]
                else:
                    v = list(self._choices)[0]
            self.view.frame.axes_frame.y_axis_choice.set(v)
        if not self._choices:
            self.view.frame.axes_frame.x_axis_choice.set("")
            self.view.frame.axes_frame.y_axis_choice.set("")

        # store new axes settings to file
        self._store_axis_settings()

        # enable axis changing again
        self._axis_being_changed = False

        # update GUI
        self.view.frame.selec_plot.set_axes(
            self.view.frame.axes_frame.x_axis_choice.get(), self.view.frame.axes_frame.y_axis_choice.get()
        )
        self.view.frame.measurement_table.repaint(
            self.view.frame.axes_frame.x_axis_choice.get(), self.view.frame.axes_frame.y_axis_choice.get()
        )

    def _axis_options_changed(self, options, measurement_name):
        """Called by MeasurementTable when the possible axes changed,
        i.e. when the user selects a new plot. Refreshes the
        dropdowns.

        Parameters
        ----------
        options : list
            Possible axes.
        """
        self.logger.debug("Refreshing all dropdown options..")
        self.model.currently_plotted_meas_name = measurement_name

        # Sort dropdown options
        options = sorted(options)

        # remove all dropdown options
        menu_x = self.view.frame.axes_frame.x_axis_plot_selector["menu"]
        menu_x.delete(0, "end")
        # create new dropdown entry for every option
        for option in options:
            menu_x.add_command(
                label=option, command=lambda value=option: self.view.frame.axes_frame.x_axis_choice.set(value)
            )

        # remove all dropdown options
        menu_y = self.view.frame.axes_frame.y_axis_plot_selector["menu"]
        menu_y.delete(0, "end")
        # create new dropdown entry for every option
        for option in options:
            menu_y.add_command(
                label=option, command=lambda value=option: self.view.frame.axes_frame.y_axis_choice.set(value)
            )

        self._choices = options
        self.logger.debug("Choices are: %s ", self._choices)

        self.axis_changed()

    def _load_axis_settings(self):
        """
        load axis settings from savefile
        """
        settings_path = get_configuration_file_path(self.model.axis_settings_path)
        if os.path.exists(settings_path):
            with open(settings_path, "r") as fp:
                existing_settings = json.load(fp)
        else:
            existing_settings = {}

        # get settings for currently selected measurement name, using None in case not saved yet
        meas_axis_settings = existing_settings.get(self.model.currently_plotted_meas_name, {"x": None, "y": None})
        return meas_axis_settings["x"], meas_axis_settings["y"]

    def _store_axis_settings(self):
        """
        save axis settings to savefile
        """
        # don't save anything if no measurement to plot is selected
        if self.model.currently_plotted_meas_name is None:
            return

        # load whole settings file
        settings_path = get_configuration_file_path(self.model.axis_settings_path)
        if os.path.exists(settings_path):
            with open(settings_path, "r") as fp:
                existing_settings = json.load(fp)
        else:
            existing_settings = {}

        # overwrite currently plotted measurement axis setting
        existing_settings[self.model.currently_plotted_meas_name] = {
            "x": self.view.frame.axes_frame.x_axis_choice.get(),
            "y": self.view.frame.axes_frame.y_axis_choice.get(),
        }

        # save back to file
        with open(settings_path, "w") as fp:
            json.dump(existing_settings, fp)

    def open_edit_measurement_wizard(self):
        """
        Open
        """
        self.model.last_opened_new_meas_wizard_controller = EditMeasurementWizardController(
            self.root, self.experiment_manager
        )

    def repeat_last_exec_measurement(self):
        """
        Called on user click on "Repeat last executed Measurement"
        """
        self.serialize_parameter_frame()
        self.logger.debug("Requested repeating of last executed measurement.")
        last_executed_todos = self.experiment_manager.exp.last_executed_todos

        if not last_executed_todos:
            msg = "No measurement has yet been executed. There is nothing to repeat."
            messagebox.showwarning("No Previous Measurement", msg)
            self.logger.warning(msg)
            return

        recall_amount = askinteger(
            title="Repeat Last Measurements",
            prompt="How many of the previously executed measurements should be repeated?",
            initialvalue=1,
            minvalue=1,
        )
        if recall_amount is None:
            return

        if recall_amount > len(last_executed_todos):
            recall_amount = len(last_executed_todos)

        for last_todo in self.experiment_manager.exp.last_executed_todos[: (-1 * recall_amount - 1) : -1]:
            last_device, last_meas = last_todo
            new_meas = self.experiment_manager.exp.duplicate_measurement(last_meas)
            self.experiment_manager.exp.to_do_list.insert(0, ToDo(last_device, new_meas))

        # tell GUI to update the tables
        self.update_tables()

        # log action
        msg = f"Cloned the last {recall_amount:d} executed measurements into new ToDos."
        self.logger.info(msg)

    def check_all_measurements(self):
        """
        Called on user click on "Toggle All"
        """
        self.view.frame.measurement_table.show_all_plots()

    def uncheck_all_plotted_measurements(self):
        """
        Called on user click on "Uncheck All"
        """
        self.view.frame.measurement_table.hide_all_plots()

    def remove_checked_measurements(self):
        """
        Called on user click on "Remove checked"
        """
        current_selection = self.view.frame.measurement_table.selected_measurements
        if len(current_selection) == 0:
            return
        flag = messagebox.askyesno(
            "Remove Checked Measurements",
            "Do you really want to remove all checked measurements? \n"
            + "Notice: the save files of the measurements will NOT be deleted.",
        )
        if flag:
            cur_sel = [v for v in current_selection.values()]
            cur_sel_hashes = [k for k in current_selection.keys()]
            # uncheck hence unplot the current selection:
            self.view.frame.measurement_table.hide_all_plots(only_these_hashes=cur_sel_hashes)
            # remove the datasets
            for meas_dict in cur_sel:
                self.experiment_manager.exp.remove_measurement_dataset(meas_dict)
            # inform user
            msg = f"Removed {len(cur_sel):d} measurement datasets."
            self.logger.info(msg)
            # force reloading of all tables
            self.update_tables()

    def remove_all_measurements(self):
        """
        Called on user click on "Remove All"
        """
        flag = messagebox.askyesno(
            "Remove All Measurements",
            "Do you really want to remove all measurements? \n"
            + "Notice: the save files of the measurements will NOT be deleted.",
        )
        if flag:
            # get copy of list of all measurements
            cur_sel = list(self.experiment_manager.exp.measurements)
            # uncheck hence unplot the current selection:
            self.view.frame.measurement_table.hide_all_plots()
            # remove the datasets
            for meas_dict in cur_sel:
                self.experiment_manager.exp.remove_measurement_dataset(meas_dict)
            # inform user
            msg = f"Removed {len(cur_sel):d} measurement datasets."
            self.logger.info(msg)
            # force reloading of all tables
            self.update_tables()

    def todo_edit(self, tidx=None):
        """
        Called on user click on "Edit To Do" or from double click on To Do table
        """
        # if its called from a button click, the argument tidx is not set, and we need to get the to do index from the
        # to do table directly
        if tidx is None:
            selected_todo_idx = self.view.frame.to_do_table.get_selected_todo_index()
        else:
            selected_todo_idx = tidx

        if selected_todo_idx is not None and selected_todo_idx < len(self.experiment_manager.exp.to_do_list):
            # get measurement to edit
            selected_todo = self.experiment_manager.exp.to_do_list[selected_todo_idx]
            dev_list = [selected_todo.device]
            edit_meas_list = [selected_todo.measurement]
            # run SettingsWindow
            set_window = Toplevel(self.root)
            set_window.geometry("%dx%d" % (800, 800))
            set_window.lift()
            set_window.focus_force()
            SettingsWindow(
                set_window,
                self.experiment_manager,
                edit_meas_list=edit_meas_list,
                device_list=dev_list,
                force_noload=True,
            )
            self.root.wait_window(set_window)

            # tell GUI to update the tables
            self.update_tables()

            # log action
            msg = "Edited ToDo with measurement id {:s} and device id {:s} at list position {:d}.".format(
                selected_todo.measurement.get_name_with_id(), str(selected_todo.device.id), selected_todo_idx
            )
            self.logger.info(msg)
        else:
            msg = "No ToDo selected for editing. Click on the row in the ToDo Queue you want to edit."
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def todo_clone(self):
        """
        Called on user click on "Clone To Do"
        """
        selected_todo_idx = self.view.frame.to_do_table.get_selected_todo_index()
        if selected_todo_idx is not None and selected_todo_idx < len(self.experiment_manager.exp.to_do_list):
            # get measurement to duplicate
            selected_todo = self.experiment_manager.exp.to_do_list[selected_todo_idx]
            sel_device, sel_meas = selected_todo.device, selected_todo.measurement

            new_meas = self.experiment_manager.exp.duplicate_measurement(sel_meas)
            self.experiment_manager.exp.to_do_list.insert(selected_todo_idx + 1, ToDo(sel_device, new_meas))

            # tell GUI to update the tables
            self.update_tables()

            # log action
            msg = "Cloned ToDo with measurement id {:s} to id {:s} and device id {:s} to list position {:d}.".format(
                sel_meas.get_name_with_id(), new_meas.get_name_with_id(), str(sel_device.id), selected_todo_idx + 1
            )
            self.logger.info(msg)
        else:
            msg = "No ToDo selected for cloning. Click on the row in the ToDo Queue you want to clone."
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def todo_delete(self):
        """
        Called on user click on "Delete To Do"
        """
        selected_todo_idx = self.view.frame.to_do_table.get_selected_todo_index()
        if selected_todo_idx is not None and selected_todo_idx < len(self.experiment_manager.exp.to_do_list):
            # delete the to do from the to do list
            selected_todo = self.experiment_manager.exp.to_do_list.pop(selected_todo_idx)
            dev_to_del, meas_to_del = selected_todo.device, selected_todo.measurement

            # tell GUI to update the table contents
            self.update_tables()
            self.logger.info(
                "Deleted ToDo with measurement id {:s} and device id {:s} at list index {:d}.".format(
                    meas_to_del.get_name_with_id(), str(dev_to_del.id), selected_todo_idx
                )
            )
        else:
            msg = "No ToDo selected for deleting. Click on the row in the ToDo Queue which you want to delete."
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def todo_side_window(self):
        """
        Called on user click on "Side Window"
        """
        msg = "The side window functionality will be deprecated in a future minor release of LabExT."
        self.logger.warning(msg)
        messagebox.showwarning("Side Windows will be deprecated!", msg)
        selected_todo_idx = self.view.frame.to_do_table.get_selected_todo_index()
        if selected_todo_idx is not None and selected_todo_idx < len(self.experiment_manager.exp.to_do_list):
            sel_todo = self.experiment_manager.exp.to_do_list[selected_todo_idx]
            sel_device = sel_todo.device
            sel_meas = sel_todo.measurement
            sel_meas.open_side_windows()
            self.logger.info(
                "Opened Side Window for ToDo with measurement id {:s} and device id {:s} at list index {:d}.".format(
                    sel_meas.get_name_with_id(), str(sel_device.id), selected_todo_idx
                )
            )
        else:
            msg = (
                "No ToDo selected for opening the side window."
                + "Click on the row in the ToDo Queue for which you want to open a side window."
            )
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def move_todo_up(self):
        """
        Called on user click on "Move Up"
        """
        sel_idx = self.view.frame.to_do_table.get_selected_todo_index()
        todo_list = self.experiment_manager.exp.to_do_list
        if sel_idx == 0:
            msg = "ToDo already in first place."
            self.logger.info(msg)
        elif sel_idx is not None and sel_idx < len(todo_list):
            todo_list[sel_idx - 1], todo_list[sel_idx] = todo_list[sel_idx], todo_list[sel_idx - 1]
            # tell GUI to update the tables
            self.update_tables()
        else:
            msg = "No ToDo selected for moving up." + "Click on the row in the ToDo Queue which you want to move up."
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def move_todo_down(self):
        """
        Called on user click on "Move Down"
        """
        sel_idx = self.view.frame.to_do_table.get_selected_todo_index()
        todo_list = self.experiment_manager.exp.to_do_list
        if sel_idx == len(todo_list) - 1:
            msg = "ToDo already in last place."
            self.logger.info(msg)
        elif sel_idx is not None and sel_idx < len(todo_list):
            todo_list[sel_idx + 1], todo_list[sel_idx] = todo_list[sel_idx], todo_list[sel_idx + 1]
            # tell GUI to update the tables
            self.update_tables()
        else:
            msg = (
                "No ToDo selected for moving down." + "Click on the row in the ToDo Queue which you want to move down."
            )
            self.logger.warning(msg)
            messagebox.showwarning("No ToDo Selected", msg)

    def todo_delete_all(self):
        """
        Called on user click on "Delete All"
        """
        flag = messagebox.askyesno("Remove All To Dos", "Do you really want to remove all ToDos?")
        if flag:
            for i in range(len(self.experiment_manager.exp.to_do_list)):
                self.experiment_manager.exp.to_do_list.pop()
            self.update_tables()  # tell GUI to update the table contents
            self.logger.info("Deleted All ToDos.")

    def offer_chip_reload_possibility(self):
        chip_path = self.model.chip_parameters["Chip path"].value
        # chip_path is only set if the user did the "load chip" functionality
        # so to offer to re-load the same chip, its sufficient to check if chip_path was set to anything
        if not chip_path:
            # there was no chip loaded on last use of LabExT, do not offer reloading
            return
        try:
            reloaded_chip = Chip.load_last_instantiated_chip()
        except FileNotFoundError:
            return
        if chip_path != reloaded_chip.path:
            # paths don't match, don't offer reload possibility
            return
        user_wants_chip_reload = messagebox.askyesno(
            title="Previously used chip found!",
            message=f"A previously used chip named\n {reloaded_chip.name} \nwith description file\n {reloaded_chip.path}\nwas found."
            f" Do you want to continue using this chip?",
        )
        if not user_wants_chip_reload:
            return
        self.experiment_manager.register_chip(reloaded_chip)

    def offer_calibration_reload_possibility(self, chip):
        """
        Offers the possibility to restore a stored calibration.
        """
        self.view.frame.menu_listener.client_restore_calibration(chip)

    def open_import_chip(self):
        """opens window to import new chip"""
        self.serialize_parameter_frame()
        self.view.frame.menu_listener.client_import_chip()

    def open_live_viewer(self):
        """opens live-viewer window by calling appropriate menu listener function"""
        self.serialize_parameter_frame()
        self.view.frame.menu_listener.client_live_view()

    def open_peak_searcher(self):
        """opens search for peak window by calling appropriate menu listener function"""
        self.serialize_parameter_frame()
        self.view.frame.menu_listener.client_search_for_peak()

    def open_stage_calibration(self):
        """opens window to calibrate stages"""
        self.serialize_parameter_frame()
        self.view.frame.menu_listener.client_calibrate_stage()

    def start(self):
        """Calls the experiment handler to start the experiment."""
        self.serialize_parameter_frame()
        self.logger.debug("Start experiment")

        # internal callback
        self.model.on_experiment_start()

        # run experiment in another thread
        self.model.experiment_handler.run_experiment()

    def stop(self):
        """Stops the experiment manually. Called when user presses stop
        button.
        """
        self.logger.debug("Stop experiment")
        # interrupt the experiment
        self.model.experiment_handler.stop_experiment()
        # cleanup
        self.model.on_experiment_finished()

    def new_single_measurement(self):
        """
        Called when the user presses "new single measurement" button.
        Opens the new measurement window.
        """
        self.serialize_parameter_frame()
        self.experiment_manager.main_window.open_edit_measurement_wizard()

    def new_swept_devices_experiment(self):
        """
        Called when the user presses "New device sweep experiment" button.
        """
        self.serialize_parameter_frame()
        self.view.frame.menu_listener.client_new_experiment()

    def on_shutdown(self):
        """Gets called once the application is trying to close.
        Terminates the currently running experiment.
        """
        # stop experiment
        self.model.experiment_handler.stop_experiment()

        # call the cleanup function of the documentation engine
        self.experiment_manager.docu.cleanup()

        # close mainwindow and quit Python interpreter
        self.root.destroy()
        sys.exit(0)

    def _register_keyboard_shortcuts(self):
        self.root.bind("<F1>", self.experiment_manager.show_documentation)
        self.root.bind(
            "<F5>", callback_if_btn_enabled(lambda event: self.start(), self.model.commands[0].button_handle)
        )
        self.root.bind(
            "<Escape>", callback_if_btn_enabled(lambda event: self.stop(), self.model.commands[1].button_handle)
        )
        self.root.bind(
            "<Control-r>",
            callback_if_btn_enabled(
                lambda event: self.repeat_last_exec_measurement(), self.view.frame.buttons_frame.repeat_meas_button
            ),
        )
        self.root.bind(
            "<Control-n>",
            callback_if_btn_enabled(
                lambda event: self.new_single_measurement(), self.view.frame.buttons_frame.new_meas_button
            ),
        )
        self.root.bind(
            "<Delete>",
            callback_if_btn_enabled(lambda event: self.todo_delete(), self.view.frame.to_do_frame.delete_todo_meas),
        )
        self.root.bind(
            "<Control-l>",
            callback_if_btn_enabled(
                lambda event: self.open_live_viewer(), self.view.frame.coupling_tools_panel.live_viewer_btn
            ),
        )
        self.root.bind(
            "<Control-s>",
            callback_if_btn_enabled(
                lambda event: self.open_peak_searcher(), self.view.frame.coupling_tools_panel.peak_searcher_btn
            ),
        )
