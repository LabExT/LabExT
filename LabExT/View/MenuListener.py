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
import webbrowser
from threading import Thread
from tkinter import filedialog, simpledialog, messagebox, Toplevel, Label, Frame, Button, TclError, font

from LabExT.Utils import run_with_wait_window, get_author_list
from LabExT.View.AddonSettingsDialog import AddonSettingsDialog
from LabExT.View.ConfigureStageWindow import ConfigureStageWindow
from LabExT.View.Controls.ParameterTable import ParameterTable, ConfigParameter
from LabExT.View.ExperimentWizard.ExperimentWizardController import ExperimentWizardController
from LabExT.View.Exporter import Exporter
from LabExT.View.ExtraPlots import ExtraPlots
from LabExT.View.InstrumentConnectionDebugger import InstrumentConnectionDebugger
from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
from LabExT.View.MoveDeviceWindow import MoveDeviceWindow
from LabExT.View.MovementWizard.MovementWizardController import MovementWizardController
from LabExT.View.ProgressBar.ProgressBar import ProgressBar
from LabExT.View.SearchForPeakPlotsWindow import SearchForPeakPlotsWindow
from LabExT.View.StageDriverSettingsDialog import StageDriverSettingsDialog


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
        self.sfpp_toplevel = None
        self.extra_plots_toplevel = None
        self.live_viewer_toplevel = None
        self.instrument_conn_debuger_toplevel = None
        self.addon_settings_dialog_toplevel = None
        self.stage_driver_settings_dialog_toplevel = None
        self.pgb = None
        self.import_done = False

    def client_new_experiment(self):
        """Called when user wants to start new Experiment. Calls the
        ExperimentWizard.
        """
        if self.swept_exp_wizard_toplevel is not None:
            try:
                self.swept_exp_wizard_toplevel.deiconify()
                self.swept_exp_wizard_toplevel.lift()
                self.swept_exp_wizard_toplevel.focus_set()
                self.logger.debug('Raising existing device sweep wizard window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

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
        self.logger.debug('Client wants to export data')
        Exporter(self._root, self._experiment_manager)

    def client_quit(self):
        """
        Called when use clicks Quit menu entry. Quit the application.
        """
        sys.exit(0)

    def client_configure_stages(self):
        """
        Open stage info and configuration window.
        """
        new_window = Toplevel(self._root)
        new_window.lift()
        ConfigureStageWindow(new_window, self._experiment_manager)

    def client_movement_wizard(self):
        self._movement_wizard = MovementWizardController(self._root, self._experiment_manager)
        self._movement_wizard.new()

    def client_move_stages(self):
        """Called when the user wants to move the stages manually.
        Opens a window with parameters for relative movement.
        """
        self.logger.debug('Client wants to move stages manually')

        # create new window
        new_window = Toplevel(self._root)
        new_window.attributes('-topmost', 'true')

        self._params = {}
        for dim_name in self._experiment_manager.mover.dimension_names:
            self._params[dim_name] = ConfigParameter(new_window, unit='um', parameter_type='number_float')

        param_table = ParameterTable(new_window)
        param_table.grid(row=0, column=0, padx=5, pady=50)
        param_table.title = 'Relative movement of stages'
        param_table.parameter_source = self._params

        if len(self._params) == 0:
            lbl = Label(new_window, text='Mover not initialized yet.')
            lbl.grid(row=0, column=0)
        else:
            ok_button = Button(new_window, text='Move stages', command=self._move_relative)
            ok_button.grid(row=1, column=0, sticky='e')

    def _move_relative(self):
        """Called when the user presses on button 'Move stages' in
        client_move_stages. Calls mover to perform a relative movement.
        """
        # get values from input fields
        relative_moves = []
        for dim_name in self._experiment_manager.mover.dimension_names:
            relative_moves.append(self._params[dim_name].value)
        self.logger.info('Client wants to move stages manually - %s', relative_moves)

        try:
            self._experiment_manager.mover.move_relative(*relative_moves, lift_z_dir=True)
        except Exception as exc:
            msg = 'Could not move stages manually! Reason: ' + repr(exc)
            messagebox.showinfo('Error', msg)
            self.logger.exception(msg)

    def client_move_device(self):
        """Called when the user wants to move the stages to a specific device.
        Opens a MoveDeviceWindow and uses mover to perform the movement.
        """
        self.logger.debug('client wants to move to specific device')

        if not self._experiment_manager.chip:
            msg = 'No chip file imported before moving to device. Cannot move to device without chip file present.'
            messagebox.showerror('No chip layout', msg)
            self.logger.error(msg)
            return
        if not self._experiment_manager.mover.trafo_enabled:
            msg = 'Stage coordinates not calibrated to chip. ' + \
                  'Please calibrate the coordinate transformation first before moving the stages automatically.'
            messagebox.showerror('Error: No transformation', msg)
            self.logger.error(msg)
            return

        # open a new window
        new_window = Toplevel(self._root)
        # place the table inside
        dev_window = MoveDeviceWindow(new_window,
                                      self._experiment_manager,
                                      'Please select the device to which you would like to move')
        self._root.wait_window(new_window)

        # get the selected device
        device = dev_window.selection

        # catch case where no device is selected
        if device is None:
            msg = 'No device selected. Aborting move.'
            messagebox.showwarning("No Device Selected", msg)
            self.logger.warning(msg)
            return

        # perform movement
        run_with_wait_window(
            self._root,
            "Moving to device...",
            lambda: self._experiment_manager.mover.move_to_device(device))

        msg = 'Successfully moved to device with ID: ' + str(device._id)
        messagebox.showinfo('Success', msg)
        self.logger.info(msg)

    def client_transformation(self):
        """Called when user wants to perform a coordinate transformation.
        Calls check_for_saved_transformation in mover to check for saved transformation.
        The user can than decide if he wants to load the saved transformation or make a new one.
        """
        self.logger.debug('Client wants to perform transformation.')

        if self._experiment_manager.chip:
            try:
                self._experiment_manager.mover.check_for_saved_transformation()
            except Exception as exc:
                msg = 'Transformation raised Exception. Reason: ' + repr(exc)
                messagebox.showinfo('Transformation aborted', msg)
                self.logger.error(msg)

            if not self._experiment_manager.mover.trafo_enabled:
                msg = 'Error: Automatic movement not enabled.'
                messagebox.showerror('Error', msg)
                self.logger.error(msg)
        else:
            msg = 'No chip file imported. Cannot do coordinate transformation for stages with no chip file present.'
            messagebox.showwarning('Error: No chip layout', msg)
            self.logger.warning(msg)

    def client_search_for_peak(self):
        """Called when user wants to open plotting window for search for peak observation."""
        if self.sfpp_toplevel is not None:
            try:
                self.sfpp_toplevel.deiconify()
                self.sfpp_toplevel.lift()
                self.sfpp_toplevel.focus_set()
                self.logger.debug('Raising existing search for peak window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

        self.logger.debug('Opening new search for peak window.')
        sfpp = SearchForPeakPlotsWindow(parent=self._root,
                                        experiment_manager=self._experiment_manager)
        self.sfpp_toplevel = sfpp.plot_window

    def client_extra_plots(self):
        """ Called when user wants to open extra plots. """
        if self.extra_plots_toplevel is not None:
            try:
                self.extra_plots_toplevel.deiconify()
                self.extra_plots_toplevel.lift()
                self.extra_plots_toplevel.focus_set()
                self.logger.debug('Raising existing extra plots window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

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
        if self.live_viewer_toplevel is not None:
            try:
                self.live_viewer_toplevel.deiconify()
                self.live_viewer_toplevel.lift()
                self.live_viewer_toplevel.focus_set()
                self.logger.debug('Raising existing live viewer window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

        self.logger.debug('Opening new live viewer window.')
        lv = LiveViewerController(self._root, self._experiment_manager)  # blocking call until all settings have been made
        self.live_viewer_toplevel = lv.current_window  # reference to actual toplevel

    def client_instrument_connection_debugger(self):
        """ opens the instrument connection debugger """
        if self.instrument_conn_debuger_toplevel is not None:
            try:
                self.instrument_conn_debuger_toplevel.deiconify()
                self.instrument_conn_debuger_toplevel.lift()
                self.instrument_conn_debuger_toplevel.focus_set()
                self.logger.debug('Raising existing instrument connection debugger window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

        icd = InstrumentConnectionDebugger(self._root, self._experiment_manager)
        self.instrument_conn_debuger_toplevel = icd.wizard_window

    def client_addon_settings(self):
        """ opens the addon settings dialog """
        if self.addon_settings_dialog_toplevel is not None:
            try:
                self.addon_settings_dialog_toplevel.deiconify()
                self.addon_settings_dialog_toplevel.lift()
                self.addon_settings_dialog_toplevel.focus_set()
                self.logger.debug('Raising existing addon settings dialog window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

        asd = AddonSettingsDialog(self._root, self._experiment_manager)
        self.addon_settings_dialog_toplevel = asd.wizard_window

    def client_stage_driver_settings(self):
        """ opens the stage driver settings dialog """
        if self.stage_driver_settings_dialog_toplevel is not None:
            try:
                self.stage_driver_settings_dialog_toplevel.deiconify()
                self.stage_driver_settings_dialog_toplevel.lift()
                self.stage_driver_settings_dialog_toplevel.focus_set()
                self.logger.debug('Raising existing addon settings dialog window.')
                return
            except TclError:
                pass  # Tcl Error if window cannot be raised because it has been closed

        sdd = StageDriverSettingsDialog(self._root)
        self.stage_driver_settings_dialog_toplevel = sdd.wizard_window

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
        self.logger.debug('Client opens about window')
        new_window = Toplevel(self._root)
        new_window.attributes('-topmost', 'true')
        about_window = Frame(new_window)
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
