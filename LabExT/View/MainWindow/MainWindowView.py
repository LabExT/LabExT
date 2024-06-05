#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from platform import system
from tkinter import (
    Frame,
    Menu,
    Checkbutton,
    Label,
    StringVar,
    OptionMenu,
    LabelFrame,
    Button,
    scrolledtext,
    Entry,
    NORMAL,
    DISABLED,
)

from LabExT.Logs.LoggingWidgetHandler import LoggingWidgetHandler
from LabExT.Utils import get_labext_version
from LabExT.View.Controls.ControlPanel import ControlPanel
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.PlotControl import PlotControl
from LabExT.View.MeasurementTable import MeasurementTable
from LabExT.View.MenuListener import MListener
from LabExT.View.ToDoTable import ToDoTable


class MainWindowContextMenu(Menu):
    """
    The context menu up top. Upon instantiation creates labels and submenus.
    """

    def __init__(self, parent, menu_listener):
        self.parent = parent
        self._menu_listener = menu_listener
        self._mover = self._menu_listener._experiment_manager.mover
        Menu.__init__(self, self.parent)
        self._file = Menu(self, tearoff=0)
        self._movement = Menu(self, tearoff=0)
        self._view = Menu(self, tearoff=0)
        self._settings = Menu(self, tearoff=0)
        self._help = Menu(self, tearoff=0)

        self.add_cascade(label="File", menu=self._file)
        self.add_cascade(label="Movement", menu=self._movement)
        self.add_cascade(label="View", menu=self._view)
        self.add_cascade(label="Settings", menu=self._settings)
        self.add_cascade(label="Help", menu=self._help)

        self._file.add_command(label="Load Data", command=self._menu_listener.client_load_data)
        self._file.add_command(label="Import Chip", command=self._menu_listener.client_import_chip)
        self._file.add_command(label="Export Data", command=self._menu_listener.client_export_data)
        self._file.add_command(label="Restart", command=self._menu_listener.client_restart)
        self._file.add_command(label="Quit", command=self._menu_listener.client_quit)

        self._movement.add_command(label=f"State: {self._mover.state}", state=DISABLED)
        self._movement.add_separator()

        if self._mover.has_connected_stages:
            self._movement.add_command(
                label=f"{len(self._mover.calibrations)} connected stage(s):",
                state=DISABLED,
            )
            for c in self._mover.calibrations.values():
                self._movement.add_cascade(label=str(c), menu=self._make_calibration_menu(c))
            self._movement.add_separator()

        self._movement.add_command(label="Configure Stages...", command=self._menu_listener.client_setup_stages)
        self._movement.add_command(
            label="Configure Mover...",
            command=self._menu_listener.client_setup_mover,
            state=NORMAL if self._mover.has_connected_stages else DISABLED,
        )
        self._movement.add_command(
            label="Calibrate Stages...",
            command=self._menu_listener.client_calibrate_stage,
            state=NORMAL if self._mover.has_connected_stages else DISABLED,
        )
        self._movement.add_separator()
        self._movement.add_command(
            label="Move Stages Relative",
            command=self._menu_listener.client_move_stages,
            state=NORMAL if self._mover.can_move_relatively else DISABLED,
        )
        self._movement.add_command(
            label="Move Stages to Device",
            command=self._menu_listener.client_move_device,
            state=NORMAL if self._mover.can_move_absolutely else DISABLED,
        )
        self._movement.add_separator()
        self._movement.add_command(
            label="Search for Peak (Ctrl+S)",
            command=self._menu_listener.client_search_for_peak,
            state=NORMAL if self._mover.has_connected_stages else DISABLED,
        )

        self._view.add_command(label="Open Extra Plots", command=self._menu_listener.client_extra_plots)
        self._view.add_command(
            label="Start Live Instrument View (Ctrl+L)",
            command=self._menu_listener.client_live_view,
        )

        self._settings.add_command(
            label="Instrument Connection Debugger",
            command=self._menu_listener.client_instrument_connection_debugger,
        )
        self._settings.add_command(label="Addon Settings", command=self._menu_listener.client_addon_settings)
        self._settings.add_command(
            label="Stage Driver Settings",
            command=self._menu_listener.client_stage_driver_settings,
        )
        self._settings.add_command(
            label="Measurement Control Settings",
            command=self._menu_listener.client_measurement_control_settings
        )

        self._help.add_command(
            label="Documentation and Help (F1)",
            command=self._menu_listener.client_documentation,
        )
        self._help.add_command(label="Sourcecode", command=self._menu_listener.client_sourcecode)
        self._help.add_command(label="About", command=self._menu_listener.client_load_about)

    def _make_calibration_menu(self, calibration):
        calibration_menu = Menu(self)

        calibration_menu.add_command(label=f"State: {calibration.state}", state=DISABLED)
        calibration_menu.add_command(label=f"Orientation: {calibration._orientation}", state=DISABLED)
        calibration_menu.add_command(label=f"Device Port: {calibration._device_port}", state=DISABLED)

        return calibration_menu


class MainWindowControlFrame(Frame):
    """
    The control frame used. Components are added from outside.
    """

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="nswe")
        title = Label(self, text="LabExT", font="Helvetica 18 bold")
        title.grid(row=0, column=0, pady=(20, 0), sticky="we")
        version, gitref = get_labext_version()
        if gitref != "-":
            version = Label(
                self,
                text="v" + str(version) + " @ Git ref " + str(gitref) + "\nPress F1 for help.",
            )
        else:
            version = Label(self, text="v" + str(version) + "\nPress F1 for help.")
        version.grid(row=1, column=0, pady=(0, 20), sticky="we")

        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=1)
        self.rowconfigure(6, weight=1)
        self.columnconfigure(0, weight=1)


class MainWindowControlPanel(ControlPanel):
    """
    The main control panel.
    Has some checkboxes and buttons, registers all callback functions for those.
    """

    def __init__(self, parent, model):
        self.parent = parent
        self.model = model
        ControlPanel.__init__(self, parent)
        self.logger = logging.getLogger()
        #
        # control buttons
        #
        self.logger.debug("Adding control buttons..")
        self.grid(row=5, column=0, sticky="we")
        self.title = "Execute ToDos"
        self.command_source = self.model.commands
        self.button_width = None

        # add checkboxes for execution controls
        self.exctrl_mm_pause = Checkbutton(
            self,
            text="Pause after every measurement (Manual Mode)",
            variable=self.model.var_mm_pause,
        )
        self.add_widget(self.exctrl_mm_pause, column=0, row=1, sticky="we")
        self.exctrl_mm_pause_reason = Label(self, textvariable=self.model.var_mm_pause_reason)
        self.exctrl_mm_pause_reason.config(state="disabled")
        self.add_widget(self.exctrl_mm_pause_reason, column=1, row=1, sticky="we")

        self.wait_time_lbl = Label(self, text="Seconds to wait between measurements")
        self.add_widget(self.wait_time_lbl, column=0, row=2, sticky="e")
        self.exctrl_wait_time = Entry(self, textvariable=self.model.var_imeas_wait_time_str)
        self.add_widget(self.exctrl_wait_time, column=1, row=2, sticky="w", padx=5, pady=5)

        self.exctrl_auto_move = Checkbutton(
            self,
            text="Automatically move Piezo Stages to device",
            variable=self.model.var_auto_move,
        )
        self.add_widget(self.exctrl_auto_move, column=0, row=3, sticky="we")
        self.exctrl_auto_move_reason = Label(self, textvariable=self.model.var_auto_move_reason)
        self.exctrl_auto_move_reason.config(state="disabled")
        self.add_widget(self.exctrl_auto_move_reason, column=1, row=3, sticky="we")

        self.exctrl_sfp_ena = Checkbutton(
            self,
            text="Execute Search-for-Peak before measurement",
            variable=self.model.var_sfp_ena,
        )
        self.add_widget(self.exctrl_sfp_ena, column=0, row=4, sticky="we")
        self.exctrl_sfp_ena_reason = Label(self, textvariable=self.model.var_sfp_ena_reason)
        self.exctrl_sfp_ena_reason.config(state="disabled")
        self.add_widget(self.exctrl_sfp_ena_reason, column=1, row=4, sticky="we")

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)


class MainWindowCouplingTools(LabelFrame):
    """
    Buttons for quick-accessing the auxiliary tools.
    """

    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        LabelFrame.__init__(self, self.parent, text="Couple Light to SiP Chip")
        self.grid(row=3, column=0, sticky="we")
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.live_viewer_btn = Button(
            self,
            text="Open Live Viewer (Ctrl+L)",
            command=self.controller.open_live_viewer,
        )
        self.live_viewer_btn.grid(row=0, column=0, sticky="we", padx=5, pady=5)
        self.peak_searcher_btn = Button(
            self,
            text="Peak Searcher (Ctrl+S)",
            command=self.controller.open_peak_searcher,
        )
        self.peak_searcher_btn.grid(row=1, column=0, sticky="we", padx=5, pady=5)


class MainWindowButtonsFrame(LabelFrame):
    """
    The buttons frame. Has buttons to add measurements.
    """

    def __init__(self, parent, main_frame, controller):
        self.main_frame = main_frame
        self.parent = parent
        self.controller = controller
        LabelFrame.__init__(self, self.parent, text="Create new ToDos")
        self.grid(row=4, column=0, sticky="we")
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.new_meas_button = Button(
            self,
            text="New Single Measurement (Ctrl+N)",
            command=self.controller.new_single_measurement,
        )
        self.new_meas_button.grid(row=0, column=0, sticky="we", padx=5, pady=5)
        self.new_meas_button.focus_set()
        self.new_exp_button = Button(
            self,
            text="New Multi-Device Multi-Measurement Experiment",
            command=self.controller.new_swept_devices_experiment,
        )
        self.new_exp_button.grid(row=1, column=0, sticky="we", padx=5)
        self.repeat_meas_button = Button(
            self,
            text="Repeat Last Executed Measurements (Ctrl+R)",
            command=self.controller.repeat_last_exec_measurement,
        )
        self.repeat_meas_button.grid(row=2, column=0, sticky="we", padx=5, pady=5)


class MainWindowParameterFrame(Frame):
    """
    The parameters frame, which contains text boxes for chip names and save directories.
    """

    def __init__(self, parent, model):
        self.parent = parent
        self.model = model
        Frame.__init__(self, parent)

        self.logger = logging.getLogger()
        #
        # parameter table
        #
        self.grid(row=2, column=0, sticky="we")
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.chip_parameter_table = ParameterTable(self)
        self.chip_parameter_table.grid(row=0, column=0, sticky="we")
        self.chip_parameter_table.title = "Chip Description Parameters"
        self.chip_parameter_table.enabled = self.model.allow_change_chip_params
        self.chip_parameter_table.parameter_source = self.model.chip_parameters
        if self.chip_parameter_table.deserialize(self.model.chiptable_settings_path):
            self.logger.info("Loaded experiment chip parameters from file.")
        self.chip_parameter_table.columnconfigure(0, weight=1)

        self.save_parameter_table = ParameterTable(self)
        self.save_parameter_table.grid(row=1, column=0, sticky="we")
        self.save_parameter_table.title = "Save Directory for JSON Files"
        self.save_parameter_table.enabled = self.model.allow_change_save_params
        self.save_parameter_table.parameter_source = self.model.save_parameters
        if self.save_parameter_table.deserialize(self.model.savetable_settings_path):
            self.logger.info("Loaded experiment save parameters from file.")
        self.save_parameter_table.columnconfigure(0, weight=1)


class MainWindowAxesFrame(LabelFrame):
    """
    The main axes frame. Contains two selectors for both y and x axis.
    """

    def __init__(self, parent, root, controller):
        self.parent = parent
        self.root = root
        self.controller = controller
        LabelFrame.__init__(self, self.parent, text="Choose Axes to Display")

        self.grid(row=6, column=0, sticky="we")
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self._x_axis_plot_label = Label(self, text="Set data for x-axis:")
        self._x_axis_plot_label.grid(row=1, column=0, sticky="we")
        self._y_axis_plot_label = Label(self, text="Set data for y-axis:")
        self._y_axis_plot_label.grid(row=0, column=0, sticky="we")

        self.x_axis_choice = StringVar(self.root)
        self.x_axis_choice.trace("w", self.controller.axis_changed)
        self.y_axis_choice = StringVar(self.root)
        self.y_axis_choice.trace("w", self.controller.axis_changed)
        self._axis_being_changed = False

        self._choices = [""]

        self.x_axis_plot_selector = OptionMenu(self, self.x_axis_choice, *self._choices)
        self.x_axis_plot_selector.grid(row=1, column=1, sticky="we")
        self.x_axis_plot_selector.rowconfigure(0, weight=1)
        self.x_axis_plot_selector.columnconfigure(1, weight=1)

        self.y_axis_plot_selector = OptionMenu(self, self.y_axis_choice, *self._choices)
        self.y_axis_plot_selector.grid(row=0, column=1, sticky="we")
        self.y_axis_plot_selector.rowconfigure(0, weight=1)
        self.y_axis_plot_selector.columnconfigure(1, weight=1)


class MainWindowLoggingWidget(LabelFrame):
    """
    The logging widget. Displays all logged information.
    Registers itself with the logger.
    """

    def __init__(self, parent):
        self.parent = parent
        self.logger = logging.getLogger()
        LabelFrame.__init__(self, self.parent, text="Log")
        self.grid(row=2, rowspan=2, column=0, padx=5, pady=5, sticky="nswe")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        st = scrolledtext.ScrolledText(self, state="disabled")
        st.configure(font="TkFixedFont")
        st.grid(row=0, column=0, sticky="nswe")
        # register widget handler to root logger
        self.logger.addHandler(LoggingWidgetHandler(st))


class MainWindowMeasurementTable(MeasurementTable):
    """
    The main measurement table
    """

    def __init__(self, parent, experiment_manager):
        self.parent = parent
        self.experiment_manager = experiment_manager
        MeasurementTable.__init__(
            self,
            parent=self.parent,
            experiment_manager=self.experiment_manager,
            total_col_width=540,
            do_changed_callbacks=True,
            allow_only_single_meas_name=True,
        )

        self.title = "Finished Measurements"
        self.grid(row=2, column=1, padx=5, pady=5, sticky="nswe")


class MainWindowToDoTable(ToDoTable):
    """
    The main To do table.
    """

    def __init__(self, parent, controller, experiment_manager):
        self.parent = parent
        self.controller = controller
        self.experiment_manager = experiment_manager
        ToDoTable.__init__(
            self,
            parent=self.parent,
            experiment_manager=self.experiment_manager,
            total_col_width=480,
            selec_mode="browse",
            double_click_callback=self.controller.todo_edit,
        )
        self.title = "ToDo Queue"
        self.grid(row=2, column=2, padx=5, pady=5, sticky="nswe")


class MainWindowFinishedMeasFrame(CustomFrame):
    """
    Finished Measurements frame. Sets up the grid and places buttons at the bottom.
    """

    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        CustomFrame.__init__(self, self.parent)
        self.title = "Edit Finished Measurements"
        self.grid(row=3, column=1, padx=5, pady=5, sticky="nswe")

        _check_all_meas = Button(
            self,
            text="Check All",
            command=self.controller.check_all_measurements,
            width=10,
        )
        _check_all_meas.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        _uncheck_all_meas = Button(
            self,
            text="Uncheck All",
            command=self.controller.uncheck_all_plotted_measurements,
            width=10,
        )
        _uncheck_all_meas.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        _remove_checked_meas = Button(
            self,
            text="Remove Checked",
            command=self.controller.remove_checked_measurements,
            width=15,
        )
        _remove_checked_meas.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        _remove_all_meas = Button(
            self,
            text="Remove All",
            command=self.controller.remove_all_measurements,
            width=15,
        )
        _remove_all_meas.grid(row=0, column=3, padx=5, pady=5, sticky="w")


class MainWindowToDoFrame(CustomFrame):
    """
    Custom Frame implementation used for the To Do window.
    Sets up the grid and adds the control buttons at the bottom.
    """

    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        CustomFrame.__init__(self, parent)
        self.title = "Edit ToDo Queue"
        self.grid(row=3, column=2, padx=5, pady=5, sticky="nswe")

        _edit_todo_meas = Button(self, text="Edit ToDo", command=self.controller.todo_edit, width=10)
        _edit_todo_meas.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        _dupl_todo_meas = Button(self, text="Clone ToDo", command=self.controller.todo_clone, width=10)
        _dupl_todo_meas.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.delete_todo_meas = Button(self, text="Delete ToDo", command=self.controller.todo_delete, width=10)
        self.delete_todo_meas.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        _open_todo_side_window = Button(self, text="Side Window", command=self.controller.todo_side_window, width=10)
        _open_todo_side_window.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        _move_todo_up = Button(self, text="Move Up", command=self.controller.move_todo_up, width=10)
        _move_todo_up.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        _move_todo_down = Button(self, text="Move Down", command=self.controller.move_todo_down, width=10)
        _move_todo_down.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        _delete_all_todo_meas = Button(self, text="Delete All", command=self.controller.todo_delete_all, width=10)
        _delete_all_todo_meas.grid(row=0, column=6, padx=5, pady=5, sticky="w")


class MainWindowFrame(Frame):
    """
    The main Frame class. Provides setup routines for the main window.
    """

    def __init__(self, parent, model, controller, experiment_manager):
        """
        Constructor of the main frame. Sets up the TK grid and sets some variables.
        Most functionality is handled in the class specific functions below.
        """
        self.root = parent
        self.model = model
        self.controller = controller
        self.experiment_manager = experiment_manager

        Frame.__init__(self, self.root)

        # place main window in root element
        self.grid(row=0, column=0, sticky="nswe")

        # these settings are needed to make everything scale to the window size
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=2)
        self.rowconfigure(0, weight=100)
        self.rowconfigure(1, weight=100)
        self.rowconfigure(2, weight=100)
        self.rowconfigure(3, weight=1)

        self.menu = None
        self.menu_listener = None

        self.control_frame = None
        self.parameter_frame = None
        self.buttons_frame = None
        self.coupling_tools_panel = None
        self.control_panel = None

        self.selec_plot = None
        self.axes_frame = None

        self.logging_frame = None

        self.measurement_table = None
        self.to_do_table = None
        self.to_do_frame = None
        self.finished_meas_frame = None

    def set_up_menu(self):
        """
        Sets up the menu bar up top.
        """
        self.menu_listener = MListener(self.experiment_manager, self.root)
        self.menu = MainWindowContextMenu(self, self.menu_listener)

    def set_up_control_frame(self):
        """
        Sets up the control frame, as well as the two plot frames.
        """
        self.control_frame = MainWindowControlFrame(self)
        self.parameter_frame = MainWindowParameterFrame(self.control_frame, self.model)
        self.buttons_frame = MainWindowButtonsFrame(self.control_frame, self, self.controller)
        self.control_panel = MainWindowControlPanel(self.control_frame, self.model)
        self.coupling_tools_panel = MainWindowCouplingTools(self.control_frame, self.controller)
        self.axes_frame = MainWindowAxesFrame(self.control_frame, self.root, self.controller)

        self.selec_plot = PlotControl(
            self,
            add_toolbar=True,
            figsize=(5, 5),
            add_legend=True,
            onclick=self.menu_listener.client_extra_plots,
        )
        self.selec_plot.title = "Measurement Selection Plot"
        self.selec_plot.show_grid = True
        self.selec_plot.data_source = self.model.selec_plot_data
        self.selec_plot.grid(row=0, column=1, rowspan=2, columnspan=2, padx=10, pady=10, sticky='nswe')
        self.selec_plot.rowconfigure(0, weight=1)
        self.selec_plot.columnconfigure(0, weight=1)

    def set_up_logging_frame(self):
        """
        This function sets up the logging frame
        """
        self.logging_frame = MainWindowLoggingWidget(self)

    def set_up_auxiliary_tables(self):
        """
        Sets up the auxiliary tables for the main window. Contains set up routines for the measurement tables,
        and th to do tables.
        """
        self.measurement_table = MainWindowMeasurementTable(self, self.experiment_manager)
        self.to_do_table = MainWindowToDoTable(self, self.controller, self.experiment_manager)
        self.to_do_frame = MainWindowToDoFrame(self, self.controller)
        self.finished_meas_frame = MainWindowFinishedMeasFrame(self, self.controller)


class MainWindowView:
    """
    View Class for the main window. Sets up and controls everything about the main window, including
    the TKinter main window setup routines.
    """

    def __init__(self, model, controller, root, experiment_manager):
        self.model = model
        self.controller = controller
        self.root = root
        self.experiment_manager = experiment_manager

        self.logger = logging.getLogger()

        self.frame = None

    def set_up_root_window(self):
        """
        This sets up the TKinter Main window. Should be moved to a separate file at some point.
        """
        self.root.title(self.model.application_title)  # window title

        # connect to event in case the application closes and an experiment is
        # still running.
        self.root.protocol("WM_DELETE_WINDOW", self.controller.on_window_close)

        # add the frame
        self.frame = MainWindowFrame(self.root, self.model, self.controller, self.experiment_manager)

    def set_up_platform(self):
        """
        Handles platform specific code
        """
        if system() == "Windows":
            self.root.wm_state("zoomed")  # as large as possible without hiding task bar
        else:
            self.root.geometry("{}x{}".format(self.model.app_width, self.model.app_height))  # window size

    def set_up_main_window(self):
        """
        Setup main window
        """
        #
        # add menu bar
        #
        self.set_up_context_menu()

        self.frame.set_up_control_frame()

        self.frame.set_up_logging_frame()

        #
        # active and finished measurement tables
        #
        self.frame.set_up_auxiliary_tables()

    def set_up_context_menu(self):
        """
        Setup main window context menu and menu listener
        """
        self.frame.set_up_menu()
        self.root.config(menu=self.frame.menu)
