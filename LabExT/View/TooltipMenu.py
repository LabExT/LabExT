#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Toplevel, Label

from LabExT.DocumentationEngine.MarkdownCleaner import get_short_docstring


class CreateToolTip(object):
    """
    Creates a tooltip for a given widget.
    """

    def __init__(self, experiment_manager, widget, stringvar, is_treeview=False, item=None):
        """
        Constructor class. It will create a new tooltip helper, that automatically displays a tooltip attached
        to a given widget.
        Parameters
        ----------
        experiment_manager: The experiment manager instance used in LabExt

        widget : The widget where the tooltip will be attached to

        stringvar : Either a stringvar that contains the measurements name (non treeview), or a string containing
                    the measurements name (treeview)

        is_treeview : sets whether the tooltip is attached to a treeview or a non-treeview

        item : optional parameter needed for treeviews, this should be the widget corresponding to the measurement
               stored in stringvar
        """
        # widget is either the parent widget or the tree_view
        # stringvar is either the associated stringvar or the index in the treelist
        self.waittime = 250  # miliseconds
        self.wraplength = 180  # pixels
        self.meas_class_dict = experiment_manager.exp.measurements_classes
        self.widget = widget
        self.id = None
        self.tw = None
        self.set = False
        self.is_treeview = is_treeview
        self.item = item
        if self.is_treeview:
            self.text = self.widget.set(item, 1)
            self.widget.tag_bind(
                str(stringvar), '<ButtonRelease-3>', self.toggle)
        else:
            self.stringvar = stringvar
            self.text = self.stringvar.get()
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)
            self.widget.bind("<Button-1>", self.leave_reset_keep)

    def toggle(self, event=None):
        """
        Toggles the tooltip on or off.
        """
        if self.set:
            self.set = False
            self.hidetip()
        else:
            self.set = True
            self.showtip()

    def enter(self, event=None):
        """
        Wrapper function for the schedule function, so it can be used as a event callback.
        """
        self.schedule()

    def leave(self, event=None):
        """
        Wrapper function for the unschedule function, so it can be used as a event callback. Furthermore, it hides
        the tooltip.
        """
        self.unschedule()
        if event.x == -1 or event.y == -1:
            self.hidetip()

    def leave_reset_keep(self, event=None):
        """
        Unschedule and hides the tooltip.
        """
        if self.is_treeview:
            self.set = False
        self.unschedule()
        self.hidetip()

    def schedule(self):
        """
        Schedules the tooltip by adding it to the widgets waitlist.
        """
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        """
        Removes the tooltip from the corresponding widgets waitlist.
        """
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        """
        Reads out the measurement name, parses the docstring, cleans the docstring and generates a new toplevel
        with attached label.
        """
        x = y = 0
        if self.is_treeview:
            x, y, cx, cy = self.widget.bbox(self.item)
        else:
            x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        self.tw.bind("<Button-1>", self.leave_reset_keep)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))

        try:
            # load docstring from measurement class
            meas_class = self.meas_class_dict[self.text]
            # sanitize docstring for proper markdown display
            sanitized = get_short_docstring(meas_class.__doc__)
        except KeyError:
            # unknown measurement class
            sanitized = ''

        if sanitized == '' or self.text == '\n':
            sanitized = 'No description available.'

        sanitized = sanitized + "\n Press 'F1' for full documentation."

        # display html in HTMLScrolledText widget
        frame = Label(self.tw, text=sanitized, borderwidth=2, relief="groove")
        frame.bind("<Leave>", self.leave_reset_keep)
        frame.pack()

    def change_content(self):
        """
        Callback function to be able to track stringvars.
        """
        self.text = self.stringvar.get()
        self.hidetip()

    def hidetip(self):
        """
        Hides the tooltip by destroying the toplevel.
        """
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
