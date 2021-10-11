#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, messagebox, Toplevel, Label

from LabExT.Experiments.StandardExperiment import calc_measurement_key
from LabExT.View.CommentsEditor import CommentsEditor
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.CustomTtkWidgets import CustomScrollbar, CustomCheckboxTreeview
from LabExT.View.Controls.PlotControl import PlotData


class MeasurementTable(CustomFrame):
    """Table in MainWindow containing finished and imported
    measurements.
    """

    def __init__(self,
                 parent,
                 experiment_manager,
                 total_col_width,
                 do_changed_callbacks=True,
                 allow_only_single_meas_name=True):
        """Constructor

        Parameters
        ----------
        parent : Tk
            Tkinter parent window.
        experiment_manager : ExperimentManager
            Instance of current ExperimentManager.
        total_col_width : int
            Width of the columns.
        do_changed_callbacks : bool
            (optional, default True) set to False if you don't want to trigger axis_changed
            calls when selection / content changes. This applies for the table in the Exporter class.
            Can intermediately be set to False to temporarily prevent updating the plots on table changes.
        allow_only_single_meas_name : bool
            (optional, default True) if this is set to True, the Table grays out all rows NOT having the same
            measurement name as the currently selected one. Within the Exporter class, this behavior is NOT needed,
            whereas in the main GUI, this behavior is needed.
        """
        super(MeasurementTable,
              self).__init__(parent)  # call parent constructor

        self.logger = logging.getLogger()

        self._root = parent
        self._total_col_width = total_col_width
        self._experiment_manager = experiment_manager
        self._measurements = self._experiment_manager.exp.measurements
        self._do_changed_callbacks = do_changed_callbacks
        self._allow_only_one_meas_name = allow_only_single_meas_name

        # keep track of displayed measurements
        self._hashes_of_meas = {}
        self._selected_meas_name = None

        # caching for plotting
        self._plotted_data = {}
        self._plotted_x_axis = ""
        self._plotted_y_axis = ""

        # tooltip related
        self._tooltip_toplevel = None
        self._tooltipped_iid = None

        self.__setup__()  # setup the main window content

    def __setup__(self):
        """Add the measurement table to the frame.
        """

        # set column names and percentage of total widths
        def_columns = ['Timestamp', 'Flags', 'Plot Label', 'Comment']
        pct_columns_width = [0.15, 0.05, 0.2, 0.6]

        # create widgets
        self._tree = CustomCheckboxTreeview(
            self,
            columns=def_columns,
            show='tree headings',
            selectmode='browse',
            checkbox_callback=self.select_item,
            double_click_callback=self.open_comment_editor
        )
        vsb = CustomScrollbar(self, orient="vertical", command=self._tree.yview)
        hsb = CustomScrollbar(self, orient="horizontal", command=self._tree.xview)

        # configure widgets and place in grid
        self._tree.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        self._tree.grid(column=0, row=0, sticky='nsew', in_=self)
        vsb.grid(column=1, row=0, sticky='wns', in_=self)
        hsb.grid(column=0, row=1, sticky='ew', in_=self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # adjust the column names
        for col_name, col_width_pct in zip(def_columns, pct_columns_width):
            self._tree.heading(col_name, text=col_name)
            self._tree.column(col_name, width=int(self._total_col_width * col_width_pct))

        # subscribe to changes of the measurements list
        self._measurements.item_added.append(self.regenerate)
        self._measurements.item_removed.append(self.regenerate)
        self._measurements.on_clear.append(self.regenerate)

        # run tooltip callback on mouse motion
        self._tree.bind("<Motion>", self.handle_tooltip)
        self._tree.bind("<Leave>", self.hidetip)

    @staticmethod
    def get_meas_values(meas_dict):
        ts = meas_dict['timestamp_known']
        flag_symbols = [v[-1] for v in meas_dict.get(CommentsEditor.meas_flags_key, [])]
        flag_text = ", ".join(flag_symbols)
        legend_text = meas_dict.get(CommentsEditor.meas_plot_legend_key, "")
        comment_text = meas_dict.get(CommentsEditor.meas_comment_key, "").split("\n")[0]
        return ts, flag_text, legend_text, comment_text

    def regenerate(self, *args, **kwargs):
        """
        Tells the tree-view to update its data from the measurements list.
        """

        leftover_hashes = [k for k in self._hashes_of_meas.keys()]
        new_hashes = []

        for meas in self._measurements:

            meas_hash = calc_measurement_key(meas)

            if meas_hash in self._hashes_of_meas.keys():
                # measurement already present in tree, simply update values
                self._tree.item(meas_hash, values=self.get_meas_values(meas))
                leftover_hashes.remove(meas_hash)
                continue
            else:
                # we will add the measurement to the table, save the hash to the list
                self._hashes_of_meas[meas_hash] = meas

            # add device node to tree if necessary
            dev_rec = str(meas["device"]["type"]) + \
                      " - ID " + str(meas["device"]["id"]) + \
                      " - chip " + str(meas["chip"]["name"])
            if dev_rec not in self._tree.get_children():
                dev_rec = self._tree.insert(parent="", index="end", iid=dev_rec, text=dev_rec, values=())
                # expand device node to see newly added measurement lines
                self._tree.item(dev_rec, open=True)

            # add measurement record to device node, note we use the measurement hash as iid!
            meas_txt = meas['name_known']
            meas_vals = self.get_meas_values(meas)
            self._tree.insert(parent=dev_rec, index="end", iid=meas_hash, text=meas_txt, values=meas_vals)
            new_hashes.append(meas_hash)
            # compare this meas name to currently selected meas name (if there is any)
            # and disable entry (gray background) if measurements names do not match
            # -> new item cannot be selected by plot_new_meas later
            if self._selected_meas_name is not None:
                if meas['name_known'] != self._selected_meas_name:
                    self._tree.disable_item(meas_hash)

        # these measurements are not in the measurements list anymore
        # remove them from the tree and the hashes list
        self._tree.delete(*leftover_hashes)
        for h in leftover_hashes:
            self._hashes_of_meas.pop(h)

        # clean up "abandonned" device entries
        for dev_rec in self._tree.get_children():
            if len(self._tree.get_children(dev_rec)) == 0:
                self._tree.delete(dev_rec)

        # plot all newly added measurements if boolean flat "plot_new_meas" is True
        plot_new_meas = kwargs.get("plot_new_meas", False)
        if plot_new_meas:
            for mh in new_hashes:
                self.click_on_meas_by_hash(meas_hash=mh)

    @property
    def selected_measurements(self):
        """Returns a dictionary with all measurements in it which are selected with the checkboxes"""
        checked_iids = self._tree.get_checked()
        return {k: self._hashes_of_meas[k] for k in checked_iids}

    def select_item(self, item_iid, new_state):
        """Called when the user selects a measurement in the table.
        Selects or deselects (if previously selected) the measurement
        and call the MainWindow to set the axis.

        Parameters
        ----------
        item_iid : str
            tkinter iid string for item in TreeView
        new_state : bool
            True if new state is checked, False if new state is UNchecked
        """

        # How plottings works:
        # 1. click on item calls select_item
        # 2. update axis_set with the new available data vector names
        # 3. calls main_window._axis_options_changed to update the options for the dropdowns
        # 4. this calls main_window._axis_changed which 1. sets the axis labels and 2. calls MeasurementTable.repaint
        # 5. here we finally assemble the PlotData and append it to exp.selec_plot_collection to display the curves
        # The extra plots window is also based on the _selection list and needs to be notified if updates happen

        current_selection = self.selected_measurements

        # As soon as first measurement is selected, we have to disable all rows which contain measurements
        # which do NOT have the same measurement name
        if self._selected_meas_name is None and len(item_iid) > 0 and self._allow_only_one_meas_name:

            # save the name of the first selected measurement
            if item_iid in self._hashes_of_meas:
                self._selected_meas_name = self._hashes_of_meas[item_iid]['name_known']
            else:
                # device level was selected, pick first measurement in tree's children
                children = self._tree.get_children(item_iid)
                sel_child = children[0]
                self._selected_meas_name = self._hashes_of_meas[sel_child]['name_known']

            # disable all rows which do NOT carry the selected name
            for iid, meas in self._hashes_of_meas.items():
                if meas['name_known'] != self._selected_meas_name:
                    self._tree.disable_item(iid)

            if self._do_changed_callbacks:
                # update plot title in main window to selected measurement name
                self._experiment_manager.main_window.set_selec_plot_title(self._selected_meas_name)

        # allow selection of ALL measurements once nothing is selected anymore
        if len(current_selection) == 0:
            for iid, meas in self._hashes_of_meas.items():
                self._tree.enable_item(iid)
            self._selected_meas_name = None
            if self._do_changed_callbacks:
                # update plot title in main window
                self._experiment_manager.main_window.set_selec_plot_title("")  # empty title

        # re-query tree for all now selected measurements
        current_selection = self.selected_measurements

        # get set of all axis labels available in the selected measurements
        axis_set = set()
        axis_set.update(
            [key for meas in current_selection.values() for key in meas['values'].keys()]
        )

        if self._do_changed_callbacks:
            # update possible selections in main_window
            self._experiment_manager.main_window._axis_options_changed(axis_set, self._selected_meas_name)

            # Check if we have the extra plot window open. if yes, notify it.
            extra_plots = self._experiment_manager.main_window.extra_plots
            if extra_plots is not None and extra_plots.is_opened():
                extra_plots.axis_options_changed()

    def click_on_all(self):
        for chld_dev in self._tree.get_children():
            for chld_meas in self._tree.get_children(item=chld_dev):
                self._tree._exec_click_on_item(chld_meas)

    def click_on_meas_by_hash(self, meas_hash):
        """ simulate a click on a checkbox given a hash of a measurement """
        for chld_dev in self._tree.get_children():
            for chld_meas in self._tree.get_children(item=chld_dev):
                if chld_meas == meas_hash:
                    self._tree._exec_click_on_item(chld_meas)

    def show_all_plots(self):
        """ check all possible items """
        # disable callbacks during unchecking to avoid continuous replotting
        self._do_changed_callbacks = False
        # go through all children and uncheck them
        for chld_dev in self._tree.get_children():
            for chld_meas in self._tree.get_children(item=chld_dev):
                self._tree.check_item(chld_meas)
        # enable callbacks again and redraw once
        self._do_changed_callbacks = True
        self.select_item("", False)

    def hide_all_plots(self, only_these_hashes=None):
        """ uncheck all items and hide all plots """
        # disable callbacks during unchecking to avoid continuous replotting
        self._do_changed_callbacks = False
        # go through all children and uncheck them
        for chld_dev in self._tree.get_children():
            for chld_meas in self._tree.get_children(item=chld_dev):
                if only_these_hashes is not None:
                    # if only_these_hashes is given, filter hash with given list
                    if chld_meas in only_these_hashes:
                        self._tree.uncheck_item(chld_meas)
                else:
                    # if list is not given, unconditionally uncheck chld_meas)
                    self._tree.uncheck_item(chld_meas)
        # enable callbacks again and redraw once
        self._do_changed_callbacks = True
        self.select_item("", False)

    def repaint(self, x_axis, y_axis):
        """Plots the selected measurements with respect to x_axis and
        y_axis.

        Parameters
        ----------
        x_axis : string
            Selected x_axis
        y_axis : string
            Selected y_axis
        """

        if (x_axis != self._plotted_x_axis) or (y_axis != self._plotted_y_axis):
            # axis selection changed, we need to replot everything
            self.logger.debug('Axis selection changed to x:%s y:%s. Clearing all plots.', x_axis, y_axis)
            self._experiment_manager.exp.selec_plot_collection.clear()
            self._plotted_data.clear()

        self._plotted_x_axis = x_axis
        self._plotted_y_axis = y_axis

        target_plotted_meas = self.selected_measurements
        current_plotted_data = self._plotted_data.copy()

        # plot all which are not yet plotted
        for meas_iid, meas in target_plotted_meas.items():

            # check if already plotted
            if meas_iid in current_plotted_data:
                continue

            # plot the data
            try:
                x_data = meas['values'][x_axis]
                y_data = meas['values'][y_axis]
            except KeyError:
                self.logger.error('In record %s could not find these axes: x:%s y:%s',
                                  meas['name_known'], x_axis, y_axis)
                messagebox.showerror(
                    'Error',
                    'Please set the correct data for both axes. '
                    'Please check that you have not selected two different types of measurements.'
                )
                continue

            # find plotting label (first line of user's comment is set as label)
            user_given_plot_legend = meas.get(CommentsEditor.meas_plot_legend_key, "")
            if user_given_plot_legend:
                plot_label = user_given_plot_legend
            else:
                ts_time_only = meas['timestamp_known'].split("_")[-1]
                plot_label = str(meas['device']['type']) + " - id" + str(meas['device']['id']) + " - " + ts_time_only

            plot_data = PlotData(x_data, y_data, label=plot_label)

            # draw the data collection
            self._experiment_manager.exp.selec_plot_collection.append(plot_data)

            # add plot data to plotted list
            self._plotted_data[meas_iid] = plot_data

        # remove all which are not selected anymore
        for meas_iid, plot_data in current_plotted_data.items():

            # check if still selected, if yes we do not remove the plot
            if meas_iid in target_plotted_meas:
                continue

            # remove plot data from plot and update local list
            self._experiment_manager.exp.selec_plot_collection.remove(plot_data)
            self._plotted_data.pop(meas_iid)

    def open_comment_editor(self, item_iid):
        """ opens the comment editor """
        if item_iid in self._hashes_of_meas:

            def redraw_table_and_plot():
                """ on closing of the CommentsEditor, this gets executed as cb """
                self.regenerate()
                if self._tree.is_item_checked(item=item_iid):
                    # if the the edited measurement is currently plotted, toggle plot to update legend text
                    self.click_on_meas_by_hash(item_iid)  # toggle plot off
                    self.click_on_meas_by_hash(item_iid)  # toggle plot on

            CommentsEditor(parent=self._root,
                           measurement_dict=self._hashes_of_meas[item_iid],
                           callback_on_save=redraw_table_and_plot)

    def handle_tooltip(self, event):
        """ Callback for any mouse-movement. Decide to show or hide tooltip. """
        _iid = self._tree.identify_row(event.y)
        # dont do anything when iid did not change (reduces flickering)
        if self._tooltipped_iid == _iid:
            return
        if _iid in self._hashes_of_meas:
            self._tooltipped_iid = _iid
            self.showtip(self._hashes_of_meas[_iid])
        else:
            self._tooltipped_iid = None
            self.hidetip(None)

    def showtip(self, meas_dict):
        """ Given a meas_dict, shows the tooltip for it. """

        # format text to show
        show_dict = {k: v for k, v in meas_dict.items() if k in [
            "measurement settings", "device"]}
        show_text = CommentsEditor.pprint_meas_dict(show_dict)
        if show_text.endswith("\n"):
            show_text = show_text[:-1]

        # close any previous tooltips
        self.hidetip(None)

        # find location for tooltip
        x, y, cx, cy = self.bbox("insert")
        x += self._tree.winfo_rootx() + self._tree.winfo_width() + 25
        y += self._tree.winfo_rooty() + 20

        # creates a toplevel window
        self._tooltip_toplevel = Toplevel(self)

        # Leaves only the label and removes the app window
        self._tooltip_toplevel.wm_overrideredirect(True)
        self._tooltip_toplevel.wm_geometry("+%d+%d" % (x, y))
        label = Label(self._tooltip_toplevel, text=show_text, justify='left',
                      background="#ffffff", relief='solid', borderwidth=1)
        label.pack(ipadx=1)

    def hidetip(self, event):
        tw = self._tooltip_toplevel
        self._tooltip_toplevel = None
        if tw:
            tw.destroy()
