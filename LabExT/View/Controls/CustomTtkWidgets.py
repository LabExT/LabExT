#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import tkinter.ttk as ttk
from tkinter import NORMAL, DISABLED

from ttkwidgets import CheckboxTreeview


class DisableMixin(object):

    def state(self, statespec=None):
        if statespec:
            e = super().state(statespec)
            if 'disabled' in e:
                self.bindtags(self.tags)
            elif '!disabled' in e:
                self.tags = self.bindtags()
                self.bindtags(['xxx'])
            return e
        else:
            return super().state()

    def disable(self):
        self.state(('disabled',))

    def enable(self):
        self.state(('!disabled',))

    def is_disabled(self):
        return 'disabled' in self.state()

    def is_enabled(self):
        return not self.is_disabled()

    def config(self, *args, **kwargs):
        """
        As this is a ttk widget, we override the state configuration here.
        """
        if 'state' in kwargs:
            # catch state configuration
            if kwargs['state'] == NORMAL:
                self.enable()
            elif kwargs['state'] == DISABLED:
                self.disable()
            else:
                raise ValueError("Unknown state to change to: " + repr(kwargs['state']))

            del kwargs['state']

        # propagate method call to ttk.XY widgets
        super().config(*args, **kwargs)


class CustomTreeview(DisableMixin, ttk.Treeview):
    pass


class CustomScrollbar(DisableMixin, ttk.Scrollbar):
    pass


class CustomCheckboxTreeview(CheckboxTreeview):
    """
    Small adaption of CheckboxTreeview which allows setting a callback on checkbox changes.

    Code directly adapted from https://github.com/RedFantom/ttkwidgets/blob/master/ttkwidgets/checkboxtreeview.py
    """

    def __init__(self, *args, checkbox_callback=None, double_click_callback=None, **kwargs):
        super(CustomCheckboxTreeview, self).__init__(*args, **kwargs)
        self._checkbox_callback = checkbox_callback
        self._double_click_callback = double_click_callback
        # make disabled rows with gray background
        self.tag_configure("disabled", background='#E6E6E6')
        # enable the double-click callback
        if double_click_callback is not None:
            self.bind("<Double-Button-1>", self._double_click, True)

    def insert(self, parent, index, iid=None, **kw):
        """ force new items to be unchecked """
        ret = super().insert(parent, index, iid=iid, **kw)
        self.change_state(ret, "unchecked")
        return ret

    def disable_item(self, item_iid):
        self.change_state(item_iid, "unchecked")
        self.tag_add(item_iid, "disabled")

    def enable_item(self, item_iid):
        self.tag_del(item_iid, "disabled")

    def change_state(self, item, state):
        # only change state if item is not disabled
        tags = self.item(item, "tags")
        if "disabled" not in tags:
            states = ("checked", "unchecked", "tristate")
            new_tags = [t for t in tags if t not in states]
            new_tags.append(state)
            self.item(item, tags=tuple(new_tags))

    def check_item(self, item):
        """ check an item, i.e. click on it only if its unchecked """
        if self.tag_has("unchecked", item):
            self._exec_click_on_item(item)

    def uncheck_item(self, item):
        """ uncheck an item, i.e. click on it only if its checked """
        if self.tag_has("checked", item):
            self._exec_click_on_item(item)

    def is_item_checked(self, item):
        """ return True if the item is currently checked """
        if self.tag_has("checked", item):
            return True
        else:
            return False

    def _double_click(self, event):
        """Call the double-click event with selected item."""
        item = self.identify_row(event.y)
        if item:
            self._double_click_callback(item)

    def _box_click(self, event):
        """Check or uncheck box when clicked."""
        x, y, widget = event.x, event.y, event.widget
        elem = widget.identify("element", x, y)
        if "image" in elem:
            # a box was clicked
            item = self.identify_row(y)
            self._exec_click_on_item(item=item)

    def _exec_click_on_item(self, item):
        """ execute effects of a click on a given item """
        # if item is disabled, do not react to click on checkbox
        if self.tag_has("disabled", item):
            return
        # propagate changes
        if self.tag_has("unchecked", item) or self.tag_has("tristate", item):
            self._check_ancestor(item)
            self._check_descendant(item)
            # launch callback after all changes propagated
            if self._checkbox_callback is not None:
                self._checkbox_callback(item, True)
        else:
            self._uncheck_descendant(item)
            self._uncheck_ancestor(item)
            # launch callback after all changes propagated
            if self._checkbox_callback is not None:
                self._checkbox_callback(item, False)
