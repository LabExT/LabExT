#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
from collections import OrderedDict
from tkinter import Toplevel, Label, Checkbutton, Button, Text, IntVar, Entry, Frame
from tkinter.scrolledtext import ScrolledText

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled


class CommentsEditor:
    """
    Allows the user to edit the comments given to a recorded measurement.
    """

    default_comment = "add comment here..."
    default_flags = ["Important !", "Valid #", "Questionable ?"]

    meas_flags_key = "user flags"
    meas_comment_key = "user comment"
    meas_plot_legend_key = "user plot label"

    def __init__(self, parent, measurement_dict, callback_on_save=None):
        """
        Constructor

        Parameters
        ----------
        parent : Tk
            TKinter window parent.
        measurement_dict : dict
            Dictionary of a recorded measurement to be edited.
        """
        self._root = parent
        self._callback_on_save = callback_on_save

        self.logger = logging.getLogger()
        self.logger.debug("Initializing EditMeasurementWizard.")

        # save measurement dict reference
        self.meas_dict = measurement_dict

        # save entry GUI elements
        self.comment_text = None
        self.flag_cbs = []

        # load comment and flags from meas_dict and extend default values if necessary

        self.available_flags = {}
        for flg in self.meas_dict.get(self.meas_flags_key, []):
            self.available_flags[flg] = IntVar()
            self.available_flags[flg].set(1)
        for flg in self.default_flags:
            if flg not in self.available_flags:
                self.available_flags[flg] = IntVar()
                self.available_flags[flg].set(0)

        self.available_comment = self.meas_dict.get(self.meas_comment_key, "")
        if not self.available_comment:
            self.available_comment = self.default_comment
        self.available_plot_legend = self.meas_dict.get(self.meas_plot_legend_key, "")

        # start GUI
        self.__setup__()

    @staticmethod
    def pprint_meas_dict(meas_dict, first_level=True):
        """ returns pretty formatted text for a measurement dictionary """
        ret_text = ""

        if len(meas_dict) == 0:
            return "< None >\n"

        for cur_key in sorted(meas_dict.keys()):

            # skip values section
            if first_level and cur_key.lower() in \
                    ["values", CommentsEditor.meas_flags_key, CommentsEditor.meas_comment_key]:
                continue

            # add key
            cur_val = meas_dict[cur_key]
            ret_text += str(cur_key)
            ret_text += ": "

            if type(cur_val) is dict or type(cur_val) is OrderedDict:
                # special case: catch value:unit pair dictionaries
                if len(cur_val) == 2 and "value" in cur_val and "unit" in cur_val:
                    ret_text += str(cur_val["value"]) + " " + str(cur_val["unit"])
                    ret_text += "\n"
                    continue

                # special case: catch single value dictionary
                if len(cur_val) == 1 and "value" in cur_val:
                    ret_text += str(cur_val["value"])
                    ret_text += "\n"
                    continue

                # recurse if further dict and add with space infront
                ret_text += "\n"
                sub_text = CommentsEditor.pprint_meas_dict(cur_val, first_level=False)
                sub_text = "  " + sub_text[:-1]  # add first doublespace and cut last \n
                sub_text = sub_text.replace("\n", "\n  ")
                ret_text += sub_text
            else:
                # otherwise, just print
                add_txt = str(cur_val)
                if not add_txt:
                    add_txt = "< None >"
                ret_text += add_txt

            ret_text += "\n"

        return ret_text

    def __setup__(self):
        """
        Setup to toplevel GUI
        """
        # create wizard window, resizeable in columns, fixed with scrollbar in rows
        self.wizard_window = Toplevel(self._root)
        self.wizard_window.title("Edit Comments")
        self.wizard_window.geometry('+%d+%d' % (600, 250))
        self.wizard_window.rowconfigure(1, weight=1)
        self.wizard_window.columnconfigure(0, weight=1)
        self.wizard_window.focus_force()

        # place hint
        hint = "This window shows details about the measurement record. Edit flags and comment below."
        top_hint = Label(self.wizard_window, text=hint)
        top_hint.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # place scrolling frame into top level window
        top_frame = CustomFrame(self.wizard_window)
        top_frame.title = " Recorded Measurement Infos (read only!) "
        top_frame.grid(row=1, column=0, padx=5, pady=5, sticky='nswe')
        top_frame.rowconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=1)

        # format measurement infos
        meas_info_text = self.pprint_meas_dict(self.meas_dict)

        # place multiline text
        text_area = ScrolledText(top_frame, height=30, width=100, wrap='none')
        text_area.insert("1.0", meas_info_text)
        text_area.config(state="disabled")
        text_area.grid(row=0, column=0, padx=5, pady=5, sticky='nswe')

        # place flag and comments area
        comments_area = CustomFrame(self.wizard_window)
        comments_area.title = "Edit Flags, Comment, and Plot Label"
        comments_area.grid(row=2, column=0, padx=5, pady=5, sticky='nswe')
        comments_area.rowconfigure(0, weight=1)
        comments_area.rowconfigure(1, weight=1)
        comments_area.rowconfigure(2, weight=1)

        for flag_idx, flag_text in enumerate(sorted(self.available_flags.keys())):
            flag_variable = self.available_flags[flag_text]
            fcb = Checkbutton(comments_area, text=flag_text, variable=flag_variable, onvalue=1, offvalue=0)
            fcb.grid(row=0, column=flag_idx, padx=5, pady=5, sticky='we')
            self.flag_cbs.append(fcb)
            comments_area.columnconfigure(flag_idx, weight=1)

        self.comment_text = Text(comments_area, height=3, width=100)
        self.comment_text.insert("end", self.available_comment)

        def clearing_cb(event):
            if event.widget.get("1.0", 'end-1c') == self.default_comment:
                event.widget.delete("1.0", "end")
            event.widget.unbind("<Button-1>")

        self.comment_text.bind("<Button-1>", clearing_cb)
        self.comment_text.grid(row=1, column=0, columnspan=len(self.available_flags), padx=5, pady=5, sticky='nswe')

        legend_area = Frame(comments_area)
        legend_area.grid(row=2, column=0, columnspan=len(self.available_flags), padx=5, pady=5, sticky='nswe')

        plot_legend_text = Label(legend_area, text="Plot Label:")
        plot_legend_text.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.plot_legend_entry = Entry(legend_area, width=100)
        self.plot_legend_entry.insert(0, self.available_plot_legend)
        self.plot_legend_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # place save and quit button
        save_btn = Button(self.wizard_window,
                          text="Save Changes! (Ctrl+S)",
                          command=self.save_and_close,
                          width=30)
        save_btn.grid(row=3, column=0, padx=5, pady=5, sticky='e')
        quit_btn = Button(self.wizard_window,
                          text="Discard and close window. (Escape)",
                          command=self.close_editor,
                          width=30)
        quit_btn.grid(row=3, column=0, padx=5, pady=5, sticky='w')

        # set keyboard shortcuts
        self.wizard_window.bind("<Escape>", callback_if_btn_enabled(self.close_editor, quit_btn))
        self.wizard_window.bind("<Control-s>", callback_if_btn_enabled(self.save_and_close, save_btn))

    def save_changes(self):
        """
        Save the changes made to the flags and the comment to file.
        """
        checked_flags = [k for k, v in self.available_flags.items() if v.get() == 1]

        comment_text = self.comment_text.get("1.0", "end-1c")
        if comment_text == self.default_comment:
            comment_text = ""

        legend_text = self.plot_legend_entry.get()

        self.meas_dict[self.meas_flags_key] = checked_flags
        self.meas_dict[self.meas_comment_key] = comment_text
        self.meas_dict[self.meas_plot_legend_key] = legend_text

        with open(self.meas_dict["file_path_known"], "w+") as f:
            # remove all software added keys, all those end in _known
            save_dict = {k: v for k, v in self.meas_dict.items() if not k.endswith("_known")}
            json.dump(save_dict, f, indent=4)

        if self._callback_on_save is not None:
            self._callback_on_save()

    def save_and_close(self, *args):
        self.save_changes()
        self.close_editor()

    def close_editor(self, *args):
        self.wizard_window.destroy()
