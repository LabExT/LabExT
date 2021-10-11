#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import shutil
from tkinter import Toplevel, Label, Button, Frame, messagebox, filedialog

from LabExT.Instruments.ReusingResourceManager import OpenedResource
from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTable import CustomTable


class InstrumentConnectionDebugger:
    """
    See all open instrument connections and interact with them.
    """

    def __init__(self, parent, experiment_manager):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.

        """
        self._root = parent
        self._exp_mgr = experiment_manager
        self._res_mgr = self._exp_mgr.resource_manager
        self.logger = logging.getLogger()

        self.instr_cfg_path = get_configuration_file_path('instruments.config')

        self.instr_cfg_table = None
        self.manually_opened_instrs = {}
        self.resource_frames = []

        # draw GUI
        self.__setup__()

        # populate GUI with data
        self.reload_instruments()

    def __setup__(self):
        """
        Setup to toplevel GUI
        """
        # create window
        self.wizard_window = Toplevel(self._root)
        self.wizard_window.title("Instrument Connections")
        self.wizard_window.geometry('%dx%d+%d+%d' % (900, 1000, 300, 300))
        self.wizard_window.rowconfigure(2, weight=1)
        self.wizard_window.columnconfigure(0, weight=1)
        self.wizard_window.focus_force()

        # place hint
        hint = "This window shows all available instruments for each type and all currently open connections.\n" \
               "To configure the following settings, you must load an instruments.config file using the button below."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        #
        # place VISA library information
        #
        visa_frame = CustomFrame(self.wizard_window)
        visa_frame.title = " Instrument Connection settings "
        visa_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        visa_frame.columnconfigure(0, weight=1)
        visa_frame.columnconfigure(1, weight=1)

        Label(visa_frame, text="used instruments.config file:").grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        Label(visa_frame, text=self.instr_cfg_path).grid(row=1, column=1, padx=5, pady=5,
                                                         sticky='nswe')

        Label(visa_frame, text="pyvisa visa-config-string:").grid(row=2, column=0, padx=5, pady=5, sticky='nswe')
        Label(visa_frame, text=str(self._res_mgr._lrm_visa_lib_str)).grid(row=2, column=1, padx=5, pady=5,
                                                                          sticky='nswe')

        Label(visa_frame, text='currently used visa library path:').grid(row=3, column=0, padx=5, pady=5, sticky='nswe')
        Label(visa_frame, text=str(self._res_mgr.visalib.library_path)).grid(row=3, column=1, padx=5, pady=5,
                                                                             sticky='nswe')

        avail_instr_frame = CustomFrame(visa_frame)
        avail_instr_frame.title = "  available instrument types and addresses  "
        avail_instr_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky='nswe')
        avail_instr_frame.columnconfigure(0, weight=1)
        avail_instr_frame.rowconfigure(0, weight=1)

        self.instr_cfg_table = CustomTable(parent=avail_instr_frame,
                                           columns=('Instrument type', 'at VISA address', 'used class'),
                                           rows=self._get_available_instr_cfg(),
                                           selectmode='browse')  # custom table inserts itself into the parent frame

        open_conn_btn = Button(visa_frame,
                               text="open connection to selection",
                               command=self._open_conn_to_selection,
                               width=30)
        open_conn_btn.grid(row=5, column=1, padx=5, pady=5, sticky='nse')

        load_new_cfg_btn = Button(visa_frame,
                                  text="load new instrument.config file",
                                  command=self._load_new_instr_cfg,
                                  width=30)
        load_new_cfg_btn.grid(row=5, column=0, padx=5, pady=5, sticky='nsw')

        #
        # opened instrument connection / "Task Manager"
        #
        self.instr_frame = CustomFrame(self.wizard_window)
        self.instr_frame.title = " opened instrument connections "
        self.instr_frame.grid(row=2, column=0, padx=5, pady=5, sticky='nswe')
        self.instr_frame.columnconfigure(0, weight=1)

        # place quit buttons
        reload_btn = Button(self.wizard_window,
                            text="Reload",
                            command=self.reload_instruments,
                            width=30)
        reload_btn.grid(row=3, column=0, padx=5, pady=5, sticky='nsw')
        quit_btn = Button(self.wizard_window,
                          text="Close",
                          command=self.close_conn_debugger,
                          width=30)
        quit_btn.grid(row=3, column=0, padx=5, pady=5, sticky='nse')

    def reload_instruments(self, *args):
        """ reloads all open connections from resource manager """
        # forget resp. "ungrid" all old frames
        for old_frm_idx, old_frm in enumerate(self.resource_frames):
            old_frm.grid_forget()
            self.instr_frame.rowconfigure(old_frm_idx, weight=0)
        self.resource_frames = []

        # create all new frames
        opened_resources = self._res_mgr.lrm_opened_resources
        for new_frm_idx, (_, orobj) in enumerate(opened_resources.items()):
            frm = self.create_single_resource_row(orobj)
            frm.grid(row=new_frm_idx, column=0, padx=5, pady=5, sticky='nswe')
            self.resource_frames.append(frm)

        # create empty frame if no resources
        if len(opened_resources) == 0:
            lbl = Label(self.instr_frame, text="no open resource found")
            lbl.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')
            self.instr_frame.rowconfigure(0, weight=1)
            self.resource_frames.append(lbl)

    def create_single_resource_row(self, resource: OpenedResource):

        frame = Frame(self.instr_frame)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.columnconfigure(4, weight=1)

        visa_addr = str(resource.resource_obj.lrm_user_resource_name)
        Label(frame, text=visa_addr).grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        num_refs = "Instr. refs: " + str(resource.counter)
        Label(frame, text=num_refs).grid(row=0, column=1, padx=5, pady=5, sticky='nswe')

        def discard_buffers():
            self._res_mgr.discard_resource_buffers(resource.resource_obj)

        Button(frame, text="empty buffers", command=discard_buffers).grid(row=0, column=2, padx=5, pady=5,
                                                                          sticky='nswe')

        def send_reset():
            resource.resource_obj.write("*RST")

        Button(frame, text="send *RST", command=send_reset).grid(row=0, column=3, padx=5, pady=5, sticky='nswe')

        def force_close():
            self._res_mgr.force_close_resource(resource.resource_obj)
            self.reload_instruments()

        Button(frame, text="force close", command=force_close).grid(row=0, column=4, padx=5, pady=5, sticky='nswe')

        return frame

    def close_conn_debugger(self, *args):
        self.wizard_window.destroy()

    def _load_new_instr_cfg(self, *args):
        """ callback for "load new instruments.config" file button
         1. asks for file selection
         2. tries to load file as json
         3. checks if all necessary keys are there
         4. offers user brief overview and if he wants to accept import
         5. copies said file to our internal path
        """
        new_icfg_path = filedialog.askopenfilename(
            parent=self.wizard_window,
            title='Select new instruments.config file for import.',
            filetypes=(('.config settings', '*.config'), ('.json settings', '*.json')))

        # return path is empty when user closes file explorer w/o selecting file
        if not new_icfg_path:
            self.wizard_window.focus_force()
            return

        try:
            # will raise JSON errors if file is not proper JSON
            with open(new_icfg_path, 'r') as fp:
                new_icfg_data = json.load(fp)
        except Exception as e:
            messagebox.showerror('file open error', 'Cannot read config file ' + str(new_icfg_path) +
                                 ' as JSON format: ' + str(e))
            self.wizard_window.focus_force()
            return

        try:
            # check top-level data structure
            assert type(new_icfg_data['Visa Library Path']) is str, 'Key "Visa Library Path" must have string value.'
            assert type(new_icfg_data['Instruments']) is dict, 'Key "Instruments" must have a dict value.'
        except (KeyError, AssertionError) as e:
            messagebox.showerror('config file format error',
                                 'Instrument config file must have a dict as top-level data structure with keys "Visa'
                                 ' Library Path" (a string as value) and "Instruments" (a dict as value).'
                                 '\n\n' + str(e))
            self.wizard_window.focus_force()
            return

        try:
            # check instruments dictionary for keys and structure
            for itype, instrs_in_type in new_icfg_data['Instruments'].items():
                assert type(instrs_in_type) is list, 'The content of key ' + str(itype) + ' must be list.'
                for instr in instrs_in_type:
                    assert type(instr) is dict, 'An element of ' + str(itype) + ' is not of dict type.'
                    assert type(instr['visa']) is str, 'In an element of ' + str(itype) + \
                                                       ', key "visa" must have string value.'
                    assert type(instr['class']) is str, 'In an element of ' + str(itype) + \
                                                        ', key "class" must have string value.'
                    assert type(instr['channels']) is list, 'In an element of ' + str(itype) + \
                                                            ', key "channels" must have list value.'
        except (KeyError, AssertionError) as e:
            messagebox.showerror('config file format error',
                                 'Instruments dict in config file must have lists as values and each list must contain'
                                 ' dicts with keys "visa" (a string as value), "class" (a string as value), and'
                                 ' "channels" (a list as value).\n\n' + str(e))
            self.wizard_window.focus_force()
            return

        # here we inform the user about the found configuration and ask for confirmation of import
        info_str = 'Instruments config file at ' + str(new_icfg_path) + ' successfully read. Found:\n' + \
                   ' pyvisa visa-config-string: ' + str(new_icfg_data['Visa Library Path']) + '\n' + \
                   ' instruments types: '
        formatted_itypes = []
        for itype, instrs_in_type in new_icfg_data['Instruments'].items():
            formatted_itypes.append(str(itype) + ' (' + str(len(instrs_in_type)) + ' options)')
        info_str += ', '.join(formatted_itypes)
        self.logger.info(info_str)
        info_str += '\n\nDo you want to import this new instrument configuration into LabExT?'

        answer = messagebox.askyesno('instrument config import', info_str)
        if not answer:
            self.wizard_window.focus_force()
            return

        # copy said file into the LabExT settings directory
        # we do a file-copy operation such that formatting does not get lost
        shutil.copy(new_icfg_path, self.instr_cfg_path)

        # final information of the user
        messagebox.showinfo('instrument config import - restart required',
                            'New configuration import successful. Please restart LabExT to apply the changes.')
        self.close_conn_debugger()

    def _get_available_instr_cfg(self):
        with open(self.instr_cfg_path, 'r') as fp:
            cfg_data = json.load(fp)
        instr_cfg = cfg_data['Instruments']
        ret_list = []
        for k in instr_cfg:
            for v in instr_cfg[k]:
                ret_list.append((k, v['visa'], v['class']))
        return ret_list

    def _open_conn_to_selection(self, *args):
        """
        Opens a connection to the selected instrument in the instrument table, so user can send *RST in the debugger.
        1. gets the type name, the class name, and the visa address of the to connecting instrument
        2. searches in the instrument configuration data for the matching entry
        3. uses the InstrumentAPI of ExperimentManager to create an instance of the object
        4. open the connection to the instrument
        5. forces the open-instrument GUI to reload
        """

        # get information about selected instrument from GUI table
        selected_iid = self.instr_cfg_table.get_tree().focus()
        if not selected_iid:
            messagebox.showinfo('no selection', 'No instrument selected in table.')
            self.wizard_window.focus_force()
            return
        instr_type_name = self.instr_cfg_table.get_tree().set(selected_iid, 0)
        instr_visa = self.instr_cfg_table.get_tree().set(selected_iid, 1)
        instr_cls_name = self.instr_cfg_table.get_tree().set(selected_iid, 2)
        if (not instr_type_name) or (not instr_cls_name) or (not instr_visa):
            return

        with open(self.instr_cfg_path, 'r') as fp:
            cfg_data = json.load(fp)['Instruments']

        # based on the selection in the table, get chosen instrument description from instruments.config
        for icfg in cfg_data[instr_type_name]:
            if icfg['visa'] == instr_visa and icfg['class'] == instr_cls_name:
                chosen_icfg = icfg
                break
        else:
            messagebox.showerror('error', 'Internal error: cannot find instrument config with class: ' + \
                                 str(instr_cls_name) + ' and visa address' + str(instr_visa) + \
                                 '. This means that the coder of these lines screwed up.')
            self.wizard_window.focus_force()
            return

        iinst = self._exp_mgr.instrument_api.create_instrument_obj(instrument_type=instr_type_name,
                                                                   selected_instruments={instr_type_name: chosen_icfg},
                                                                   initialized_instruments=self.manually_opened_instrs)

        try:
            iinst.open()
        except Exception as e:
            messagebox.showerror('connection error',
                                 f'Could not open connection to instrument at:\n  visa address {instr_visa}\n  using '
                                 f'class {instr_cls_name}\n\nError message: ' + str(e))
            self.wizard_window.focus_force()
            return

        # force open instrument connection list to reload to reflect newly opened instrument
        self.reload_instruments()
        self.wizard_window.focus_force()
