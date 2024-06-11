#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import datetime
import json
import logging
import sys
import os
import webbrowser
from threading import Thread
from tkinter import filedialog, messagebox, Toplevel, Label, Frame, font
from typing import TYPE_CHECKING

from LabExT.Utils import get_author_list, try_to_lift_window
from LabExT.View.AddonSettingsDialog import AddonSettingsDialog
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog
from LabExT.View.MeasurementControlSettings import MeasurementControlSettingsView
from LabExT.View.ExperimentWizard import ExperimentWizard
from LabExT.Exporter.ExportWizard import ExportWizard
from LabExT.View.ExtraPlots import ExtraPlots
from LabExT.View.InstrumentConnectionDebugger import InstrumentConnectionDebugger
from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
from LabExT.View.ProgressBar.ProgressBar import ProgressBar
from LabExT.View.SearchForPeakPlotsWindow import SearchForPeakPlotsWindow
from LabExT.View.Movement import (
    CalibrationWizard,
    MoverWizard,
    StageWizard,
    MoveStagesRelativeWindow,
    MoveStagesDeviceWindow,
    LoadStoredCalibrationWindow
)
from LabExT.Wafer.ImportChipWizard import ImportChipWizard

if TYPE_CHECKING:
    from LabExT.ExperimentManager import ExperimentManager
else:
    ExperimentManager = None


class MListener:
    """Listens to the events triggered by clicks on the menu bar."""

    def __init__(self, experiment_manager: ExperimentManager, root):
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager.
        root : Tk
            Tkinter parent window.
        """
        self.logger = logging.getLogger()
        self.logger.debug("Initialised MenuListener with parent: %s experiment_manager: %s", root, experiment_manager)
        self._experiment_manager = experiment_manager
        self._experiment_wizard = None
        self._root = root

        # toplevel tracking to simply raise window if already opened once instead of opening a new one
        self.swept_exp_wizard_toplevel = None
        self.exporter_toplevel = None
        self.stage_configure_toplevel = None
        self.stage_movement_toplevel = None
        self.stage_device_toplevel = None
        self.sfpp_toplevel = None
        self.extra_plots_toplevel = None
        self.live_viewer_toplevel = None
        self.instrument_conn_debugger_toplevel = None
        self.addon_settings_dialog_toplevel = None
        self.stage_driver_settings_dialog_toplevel = None
        self.measurement_control_settings_toplevel = None
        self.about_toplevel = None
        self.pgb = None
        self.import_done = False
        self.stage_setup_toplevel = None
        self.mover_setup_toplevel = None
        self.calibration_setup_toplevel = None
        self.calibration_restore_toplevel = None
        self.import_chip_wizard_toplevel = None

    def client_new_experiment(self):
        """Called when user wants to start new Experiment. Calls the ExperimentWizard."""
        if not self._experiment_manager.chip:
            messagebox.showinfo(
                title="No Chip Loaded",
                message="This feature currently only works when a chip is loaded. "
                "Please make sure you import a chip first.",
            )
            return

        if try_to_lift_window(self.swept_exp_wizard_toplevel):
            return
        # start the measurement wizard
        self.swept_exp_wizard_toplevel = ExperimentWizard(self._root, self._experiment_manager)

    def client_load_data(self) -> None:
        """Called when user wants to load data. Opens a file dialog and then imports selected files."""

        filepaths = [
            *filedialog.askopenfilenames(
                title="Select file for import", filetypes=((".json data", "*.json"), ("all files", "*.*"))
            )
        ]

        if not filepaths:
            self.logger.debug("Aborting file import. No files selected.")
            return
        self.logger.debug(f"Files to import: {filepaths}")

        self.import_done = False
        self.pgb = ProgressBar(self._root, text="Importing files ...")

        Thread(target=self.import_runner(filepaths=filepaths)).start()
        while not self.import_done:
            self.pgb.update_idletasks()
            self.pgb.update()

        self.pgb.destroy()

    def import_runner(self, filepaths: list[str]) -> None:
        """Load measurements and append to current experiment's measurement list"""
        loaded_files = []
        for file_name in filepaths:
            try:
                with open(file_name) as f:
                    raw_data = json.load(f)
                self._experiment_manager.exp.load_measurement_dataset(raw_data, file_name)
                loaded_files.append(file_name)
            except Exception as exc:
                msg = f"Could not import file {file_name} due to: {repr(exc)}"
                self.logger.error(msg)
                messagebox.showerror(title="Load Data Error", message=msg)
                continue

        self.logger.info(f"Finished data import of files: {loaded_files}")
        self.import_done = True

    def client_import_chip(self):

        if self._experiment_manager.exp.to_do_list:
            self.logger.error("Cannot import new chip: there are still ToDos enqueued.")
            messagebox.showinfo("Error", "ToDo queue is not empty. Cannot import new chip.")
            return

        if try_to_lift_window(self.import_chip_wizard_toplevel):
            return

        self.import_chip_wizard_toplevel = ImportChipWizard(
            master=self._root, experiment_manager=self._experiment_manager
        )

    def client_export_data(self):
        """Called when user wants to export data. Starts the Exporter.
        """
        
        if try_to_lift_window(self.exporter_toplevel):
            return
        
        self.exporter_toplevel = ExportWizard(
            master=self._root,
            experiment_manager=self._experiment_manager
        )

    @staticmethod
    def client_quit():
        """Called when use clicks Quit menu entry. Quit the application."""
        sys.exit(0)

    @staticmethod
    def client_restart():
        """Called when user wants to restart the applications."""
        os.execl(sys.executable, sys.executable, *sys.argv)

    def client_setup_stages(self):
        """Open wizard to set up the wizard stages."""
        if try_to_lift_window(self.stage_setup_toplevel):
            return

        self.stage_setup_toplevel = StageWizard(
            self._root, self._experiment_manager.mover, experiment_manager=self._experiment_manager
        )

    def client_setup_mover(self):
        """Open wizard to set up mover."""
        if try_to_lift_window(self.mover_setup_toplevel):
            return

        self.mover_setup_toplevel = MoverWizard(self._root, self._experiment_manager.mover)

    def client_calibrate_stage(self):
        """Open wizard to calibrate stages."""
        if try_to_lift_window(self.calibration_setup_toplevel):
            return

        self.calibration_setup_toplevel = CalibrationWizard(
            self._root,
            self._experiment_manager.mover,
            self._experiment_manager.chip,
            experiment_manager=self._experiment_manager,
        )

    def client_move_stages(self):
        """Called when the user wants to move the stages manually. Opens a window with parameters for relative movement.
        """
        if try_to_lift_window(self.stage_movement_toplevel):
            return

        self.stage_movement_toplevel = MoveStagesRelativeWindow(self._root, self._experiment_manager.mover)

    def client_move_device(self):
        """Called when the user wants to move the stages to a specific device. Opens a MoveDeviceWindow and uses mover
        to perform the movement.
        """
        if try_to_lift_window(self.stage_device_toplevel):
            return

        self.stage_device_toplevel = MoveStagesDeviceWindow(
            self._root, self._experiment_manager.mover, self._experiment_manager.chip
        )

    def client_restore_calibration(self, chip):
        """Opens a window to restore calibrations."""
        if try_to_lift_window(self.calibration_restore_toplevel):
            return

        calibration_settings = self._experiment_manager.mover.load_stored_calibrations_for_chip(chip=chip)

        if not calibration_settings:
            self.logger.debug(f"No stored calibration found for {chip}")
            return

        last_updated_at = datetime.datetime.fromisoformat(calibration_settings["last_updated_at"]).strftime(
            "%d.%m.%Y %H:%M:%S"
        )

        if not messagebox.askyesno(
            title="Restore calibration",
            message=f"Found mover calibration for chip: {chip.name}. \n Last update at: {last_updated_at}. \n"
                    f"Do you want to restore it?"
        ):
            return

        self.calibration_restore_toplevel = LoadStoredCalibrationWindow(
            self._root, self._experiment_manager.mover, calibration_settings=calibration_settings
        )

    def client_search_for_peak(self):
        """Called when user wants to open plotting window for search for peak observation."""
        if try_to_lift_window(self.sfpp_toplevel):
            return

        self.logger.debug("Opening new search for peak window.")
        sfpp = SearchForPeakPlotsWindow(parent=self._root, experiment_manager=self._experiment_manager)
        self.sfpp_toplevel = sfpp.plot_window

    def client_extra_plots(self):
        """Called when user wants to open extra plots."""
        if try_to_lift_window(self.extra_plots_toplevel):
            return

        main_window = self._experiment_manager.main_window
        meas_table = main_window.view.frame.measurement_table
        self.logger.debug("Opening new extra plots window.")
        main_window.extra_plots = ExtraPlots(meas_table, main_window.view.frame)
        self.extra_plots_toplevel = main_window.extra_plots.cur_window

    def client_live_view(self):
        """Called when user wants to start live view. Creates a new instance of LiveViewer, which takes care of
        settings, instruments and plotting.
        """
        if try_to_lift_window(self.live_viewer_toplevel):
            return

        self.logger.debug("Opening new live viewer window.")
        lv = LiveViewerController(self._root, self._experiment_manager)  # blocking call until all settings are made
        self.live_viewer_toplevel = lv.current_window  # reference to actual toplevel

    def client_instrument_connection_debugger(self):
        """opens the instrument connection debugger"""
        if try_to_lift_window(self.instrument_conn_debugger_toplevel):
            return

        icd = InstrumentConnectionDebugger(self._root, self._experiment_manager)
        self.instrument_conn_debugger_toplevel = icd.wizard_window

    def client_addon_settings(self):
        """opens the addon settings dialog"""
        if try_to_lift_window(self.addon_settings_dialog_toplevel):
            return

        asd = AddonSettingsDialog(self._root, self._experiment_manager)
        self.addon_settings_dialog_toplevel = asd.wizard_window

    def client_stage_driver_settings(self):
        """opens the stage driver settings dialog"""
        if try_to_lift_window(self.stage_driver_settings_dialog_toplevel):
            self._root.wait_window(self.stage_driver_settings_dialog_toplevel)
        else:
            self.stage_driver_settings_dialog_toplevel = DriverPathDialog(
                self._root,
                settings_file_path="mcsc_module_path.txt",
                title="Stage Driver Settings",
                label="SmarAct MCSControl driver module path",
                hint="Specify the directory where the module MCSControl_PythonWrapper is found.\n"
                     "This is an external software provided by SmarAct GmbH and is available from them.\n"
                     "See https://smaract.com."
            )
            self._root.wait_window(self.stage_driver_settings_dialog_toplevel)

        if self.stage_driver_settings_dialog_toplevel.path_has_changed:
            if messagebox.askokcancel(
                title="Stage Driver Path changed",
                message="The path to the driver ofo the SmarAct MCSControl Interface was successfully changed."
                        "LabExT must be restarted for the changes to take effect. Do you want to restart LabExT now?",
                parent=self._root
            ):
                self.client_restart()

    def client_measurement_control_settings(self):
        """Open measurement control settings dialog."""
        if try_to_lift_window(self.measurement_control_settings_toplevel):
            return

        meas_settings = MeasurementControlSettingsView(self._root, self._experiment_manager)
        self.measurement_control_settings_toplevel = meas_settings.window

    def client_documentation(self):
        """Opens the documentation in a new browser session."""
        self._experiment_manager.show_documentation(None)

    @staticmethod
    def client_sourcecode():
        """Opens the sourcecode in a new browser session."""
        webbrowser.open("https://github.com/LabExT/LabExT")

    def client_load_about(self):
        """Opens an About window."""
        if try_to_lift_window(self.about_toplevel):
            return

        self.logger.debug("Client opens about window")
        self.about_toplevel = Toplevel(self._root)
        self.about_toplevel.attributes("-topmost", "true")
        about_window = Frame(self.about_toplevel)
        about_window.grid(row=0, column=0)

        font_title = font.Font(size=12, weight="bold")
        font_normal = font.Font(size=10)

        label_title = Label(about_window, text="LabExT - Laboratory Experiment Tool")
        label_title.configure(font=font_title)
        label_title.grid(row=0, column=0)

        label_description = Label(
            about_window,
            text=f"a laboratory experiment software environment for performing measurements and visualizing data.\n"
                 f"Copyright (C) {datetime.date.today().strftime('%Y'):s} ETH Zurich and Polariton Technologies AG\n"
                 f"released under GPL v3, see LICENSE file"
        )
        label_description.configure(font=font_normal)
        label_description.grid(row=1, column=0)

        # authors are loaded form AUTHORS.md file
        authors = get_author_list()
        label_credits = Label(about_window, text="\n".join(authors))
        label_credits.configure(font=font_normal)
        label_credits.grid(row=9, column=0, rowspan=6)
