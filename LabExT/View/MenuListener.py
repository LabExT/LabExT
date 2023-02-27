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
from tkinter import filedialog, simpledialog, messagebox, Toplevel, Label, Frame, font

from LabExT.Utils import get_author_list, try_to_lift_window
from LabExT.View.AddonSettingsDialog import AddonSettingsDialog
from LabExT.View.Controls.DriverPathDialog import DriverPathDialog
from LabExT.View.ExperimentWizard.ExperimentWizardController import ExperimentWizardController
from LabExT.View.Exporter import Exporter
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

class MListener:
    """Listens to the events triggered by clicks on the menu bar.
    """

    def __init__(self, experiment_manager, root):
        """Constructor.

        Parameters
        ----------
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager.
        root : Tk
            Tkinter parent window.
        """
        self.logger = logging.getLogger()
        self.logger.debug('Initialised MenuListener with parent: %s experiment_manager: %s', root, experiment_manager)
        self._experiment_manager = experiment_manager
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
        self.instrument_conn_debuger_toplevel = None
        self.addon_settings_dialog_toplevel = None
        self.stage_driver_settings_dialog_toplevel = None
        self.about_toplevel = None
        self.pgb = None
        self.import_done = False
        self.stage_setup_toplevel = None
        self.mover_setup_toplevel = None
        self.calibration_setup_toplevel = None
        self.calibration_restore_toplevel = None

    def client_new_experiment(self):
        """Called when user wants to start new Experiment. Calls the
        ExperimentWizard.
        """
        if try_to_lift_window(self.swept_exp_wizard_toplevel):
            return

        # start the measurement wizard
        self.logger.debug('Opening new device sweep wizard window.')
        self._experiment_wizard = ExperimentWizardController(self._root, self._experiment_manager)
        self.swept_exp_wizard_toplevel = self._experiment_wizard.view.main_window
        self._experiment_wizard.start_wizard()

    def client_load_data(self):
        """Called when user wants to load data. Opens a file dialog
        and then imports selected files.
        """
        self.logger.debug('Client wants to load data.')

        # tk returns this in tuples of strings
        file_names_tuple = filedialog.askopenfilenames(
            title='Select files for import',
            filetypes=(('.json data', '*.json'), ('all files', '*.*')))
        self.file_names = [*file_names_tuple]

        self.logger.debug('Files to import: %s', self.file_names)

        if not self.file_names:
            self.logger.debug('Aborting file import. No files selected.')
            return

        self.import_done = False
        # here we set up the progress bar
        self.pgb = ProgressBar(self._root, 'Importing Files...')

        # now we can start the import thread
        Thread(target=self.import_runner).start()

        # this little loop here updates the progress bar
        while not self.import_done:
            self.pgb.update_idletasks()
            self.pgb.update()

        # finally, we can destroy the progress bar
        self.pgb.destroy()

    def import_runner(self):        # load measurements and append to current experiment's measurement list
        loaded_files = []
        for file_name in self.file_names:
            try:
                with open(file_name) as f:
                    raw_data = json.load(f)
                    self._experiment_manager.exp.load_measurement_dataset(raw_data, file_name)
                loaded_files.append(file_name)
            except Exception as exc:
                msg = "Could not import file {:s} due to: {:s}".format(file_name, repr(exc))
                self.logger.error(msg)
                messagebox.showerror("Load Data Error", msg)
                continue

        self.logger.info('Finished data import of files: {:s}'.format(str(loaded_files)))
        self.import_done = True

    def client_import_chip(self):
        """Called when user wants to import a new chip. Opens a file
        dialog, asks for a chip name and calls the experiment manager
        to change chip.
        """
        self.logger.debug('Client wants to import chip')

        # open a file dialog and ask for location of chip
        if self._experiment_manager.exp.to_do_list:
            messagebox.showinfo(
                'Error',
                'Please finish your experiment before you import a chip.')
            self.logger.warning('Cannot import new chip: there are still measurements to do.')
            return
        _chip_path = filedialog.askopenfilename(
            title="Select chip layout file",
            filetypes=(("chip layout", "*.txt"),
                       ("chip layout", "*.json"),
                       ("chip layout", "*.csv"),
                       ("all files", "*.*")))
        if _chip_path:
            _chip_name = simpledialog.askstring(
                title="Custom chip name",
                prompt="Set individual chip name",
                initialvalue="Chip_01")
            if _chip_name:
                try:
                    self._experiment_manager.import_chip(_chip_path, _chip_name)
                except Exception as exc:
                    msg = "Could not import chip due to: " + repr(exc)
                    self.logger.error(msg)
                    messagebox.showerror('Chip Import Error', msg)
                    return
                msg = "Chip with name {:s} and description " \
                      "file {:s} successfully imported.".format(_chip_name, _chip_path)
                self.logger.info(msg)
                messagebox.showinfo("Chip Import Success", msg)
            # if user presses cancel when asked for custom name we abort
            else:
                self.logger.info('Chip import aborted by user (cancelled name setting).')
        else:
            self.logger.info('Chip import aborted by user (no file selected).')

    def client_export_data(self):
        """Called when user wants to export data. Starts the Exporter.
        """
        if try_to_lift_window(self.exporter_toplevel):
            return

        self.logger.debug('Client wants to export data')
        exporter = Exporter(self._root, self._experiment_manager)
        self.exporter_toplevel = exporter._meas_window

    def client_quit(self):
        """
        Called when use clicks Quit menu entry. Quit the application.
        """
        sys.exit(0)

    def client_restart(self):
        """
        Called when user wants to restart the applications.
        """
        os.execl(sys.executable, sys.executable, *sys.argv)

    def client_setup_stages(self):
        """
        Open wizard to setup the stages.
        """
        if try_to_lift_window(self.stage_setup_toplevel):
            return
        
        self.stage_setup_toplevel = StageWizard(
            self._root,
            self._experiment_manager.mover,
            experiment_manager=self._experiment_manager)

    def client_setup_mover(self):
        """
        Open wizard to setup mover.
        """
        if try_to_lift_window(self.mover_setup_toplevel):
            return
        
        self.mover_setup_toplevel = MoverWizard(self._root, self._experiment_manager.mover)

    def client_calibrate_stage(self):
        """
        Open wizard to calibrate stages.
        """
        if try_to_lift_window(self.calibration_setup_toplevel):
            return
        
        self.calibration_setup_toplevel = CalibrationWizard(
            self._root,
            self._experiment_manager.mover,
            self._experiment_manager.chip,
            experiment_manager=self._experiment_manager)

    def client_move_stages(self):
        """
        Called when the user wants to move the stages manually.
        Opens a window with parameters for relative movement.
        """
        if try_to_lift_window(self.stage_movement_toplevel):
            return

        self.stage_movement_toplevel = MoveStagesRelativeWindow(
            self._root, self._experiment_manager.mover)

    def client_move_device(self):
        """
        Called when the user wants to move the stages to a specific device.
        Opens a MoveDeviceWindow and uses mover to perform the movement.
        """
        if try_to_lift_window(self.stage_device_toplevel):
            return

        self.stage_device_toplevel = MoveStagesDeviceWindow(
            self._root,
            self._experiment_manager.mover,
            self._experiment_manager.chip)

    def client_restore_calibration(self, chip):
        """
        Opens a window to restore calibrations.
        """
        if try_to_lift_window(self.calibration_restore_toplevel):
            return

        calibration_settings = self._experiment_manager.mover.load_stored_calibrations_for_chip(
            chip=chip)

        if not calibration_settings:
            self.logger.debug(
                f"No stored calibration found for {chip}")
            return

        last_updated_at = datetime.datetime.fromisoformat(
            calibration_settings["last_updated_at"]).strftime("%d.%m.%Y %H:%M:%S")

        if not messagebox.askyesno(
            "Restore calibration",
            f"Found mover calibration for chip: {chip.name}. \n Last updated at: {last_updated_at}. \n"
            "Do you want to restore it?"):
            return

        self.calibration_restore_toplevel = LoadStoredCalibrationWindow(
            self._root,
            self._experiment_manager.mover,
            calibration_settings=calibration_settings)

    def client_search_for_peak(self):
        """Called when user wants to open plotting window for search for peak observation."""
        if try_to_lift_window(self.sfpp_toplevel):
            return

        self.logger.debug('Opening new search for peak window.')
        sfpp = SearchForPeakPlotsWindow(parent=self._root,
                                        experiment_manager=self._experiment_manager)
        self.sfpp_toplevel = sfpp.plot_window

    def client_extra_plots(self):
        """ Called when user wants to open extra plots. """
        if try_to_lift_window(self.extra_plots_toplevel):
            return
        
        main_window = self._experiment_manager.main_window
        meas_table = main_window.view.frame.measurement_table
        self.logger.debug('Opening new extra plots window.')
        main_window.extra_plots = ExtraPlots(meas_table, main_window.view.frame)
        self.extra_plots_toplevel = main_window.extra_plots.cur_window

    def client_side_windows(self):
        raise DeprecationWarning("Open side windows is deprecated. Do not use.")

    def client_live_view(self):
        """Called when user wants to start live view.
        Creates a new instance of LiveViewer, which takes care of
        settings, instruments and plotting.
        """
        if try_to_lift_window(self.live_viewer_toplevel):
            return

        self.logger.debug('Opening new live viewer window.')
        lv = LiveViewerController(self._root, self._experiment_manager)  # blocking call until all settings have been made
        self.live_viewer_toplevel = lv.current_window  # reference to actual toplevel

    def client_instrument_connection_debugger(self):
        """ opens the instrument connection debugger """
        if try_to_lift_window(self.instrument_conn_debuger_toplevel):
            return

        icd = InstrumentConnectionDebugger(self._root, self._experiment_manager)
        self.instrument_conn_debuger_toplevel = icd.wizard_window

    def client_addon_settings(self):
        """ opens the addon settings dialog """
        if try_to_lift_window(self.addon_settings_dialog_toplevel):
            return

        asd = AddonSettingsDialog(self._root, self._experiment_manager)
        self.addon_settings_dialog_toplevel = asd.wizard_window

    def client_stage_driver_settings(self):
        """ opens the stage driver settings dialog """
        if try_to_lift_window(self.stage_driver_settings_dialog_toplevel):
            self._root.wait_window(
                self.stage_driver_settings_dialog_toplevel)
        else:
            self.stage_driver_settings_dialog_toplevel = DriverPathDialog(
                self._root,
                settings_file_path="mcsc_module_path.txt",
                title="Stage Driver Settings",
                label="SmarAct MCSControl driver module path",
                hint="Specify the directory where the module MCSControl_PythonWrapper is found.\nThis is external software,"
                "provided by SmarAct GmbH and is available from them. See https://smaract.com.")
            self._root.wait_window(
                self.stage_driver_settings_dialog_toplevel)

        if self.stage_driver_settings_dialog_toplevel.path_has_changed:
            if messagebox.askokcancel(
                "Stage Driver Path changed",
                "The path to the driver of the SmarAct MCSControl Interface was successfully changed."\
                "LabExT must be restarted for the changes to take effect. Do you want to restart LabExT now?",
                parent=self._root):
                self.client_restart()

       

    def client_documentation(self):
        """ Opens the documentation in a new browser session. """
        self._experiment_manager.show_documentation(None)

    def client_sourcecode(self):
        """Opens the sourcecode in a new browser session.
        """
        webbrowser.open('https://github.com/LabExT/LabExT')

    def client_load_about(self):
        """Opens an About window.
        """
        if try_to_lift_window(self.about_toplevel):
            return

        self.logger.debug('Client opens about window')
        self.about_toplevel = Toplevel(self._root)
        self.about_toplevel.attributes('-topmost', 'true')
        about_window = Frame(self.about_toplevel)
        about_window.grid(row=0, column=0)

        font_title = font.Font(size=12, weight='bold')
        font_normal = font.Font(size=10)

        label_title = Label(
            about_window, text='LabExT - Laboratory Experiment Tool')
        label_title.configure(font=font_title)
        label_title.grid(row=0, column=0)

        label_description = Label(
            about_window,
            text=
            'a laboratory experiment software environment for performing measurements and visualizing data\n' +
            f'Copyright (C) {datetime.date.today().strftime("%Y"):s} ETH Zurich and Polariton Technologies AG\n'
            'released under GPL v3, see LICENSE file'
        )
        label_description.configure(font=font_normal)
        label_description.grid(row=1, column=0)

        # authors are loaded form AUTHORS.md file
        authors = get_author_list()
        label_credits = Label(
            about_window,
            text='\n'.join(authors)
        )
        label_credits.configure(font=font_normal)
        label_credits.grid(row=9, column=0, rowspan=6)
