#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import itertools
import json
import logging
import os.path
from typing import TYPE_CHECKING, Union
from tkinter import Frame, Label, Button, messagebox

from LabExT.Experiments.ToDo import ToDo
from LabExT.Utils import get_configuration_file_path, get_visa_address
from LabExT.View.Controls.CustomTable import CustomTable
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentSelector, InstrumentRole
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.Wizard import Wizard, Step
from LabExT.View.TooltipMenu import CreateToolTip

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.Wafer.Chip import Chip
    from LabExT.Wafer.Device import Device
    from LabExT.Measurements.MeasAPI import Measurement
else:
    Tk = None
    ExperimentManager = None
    Chip = None
    Device = None
    Measurement = None


class ExperimentWizard(Wizard):

    def __init__(self, parent: Tk, experiment_manager: ExperimentManager) -> None:
        super().__init__(
            parent=parent,
            width=900,
            height=700,
            on_cancel=self._on_cancel,
            on_finish=self._on_finish,
            with_sidebar=True,
            with_error=True,
            next_button_label="Next Step",
            previous_button_label="Previous Step",
            cancel_button_label="Cancel",
            finish_button_label="Finish",
        )
        self._exp_manager = experiment_manager
        self.experiment = self._exp_manager.exp

        self.step_device_selection = DeviceSelection(self, self._exp_manager)
        self.step_measurement_selection = MeasurementSelection(self, self._exp_manager)
        self.step_instrument_selection = InstrumentSelection(self, self._exp_manager)
        self.step_parameter_selection = ParameterSelection(self, self._exp_manager)
        self._connect_steps()

        self.current_step = self.step_device_selection

    def _connect_steps(self) -> None:
        self.step_device_selection.next_step = self.step_measurement_selection
        self.step_measurement_selection.previous_step = self.step_device_selection
        self.step_measurement_selection.next_step = self.step_instrument_selection
        self.step_instrument_selection.previous_step = self.step_measurement_selection
        self.step_instrument_selection.next_step = self.step_parameter_selection
        self.step_parameter_selection.previous_step = self.step_instrument_selection

    def _on_cancel(self) -> bool:
        self.experiment.device_list.clear()
        self.experiment.selected_measurements.clear()
        return True

    def _on_finish(self) -> bool:
        self.step_parameter_selection.write_parameters()

        # create ToDos
        self.experiment.to_do_list.extend(
            [
                ToDo(device, meas)
                for device, meas in itertools.product(
                    self.experiment.device_list, self.experiment.selected_measurements
                )
            ]
        )

        self.experiment.update()
        self.experiment.device_list.clear()
        self.experiment.selected_measurements.clear()

        return True


class DeviceSelection(Step):

    def __init__(self, wizard: ExperimentWizard, exp_manager: ExperimentManager) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Device Selection", on_next=self._on_next)
        self.exp_manager = exp_manager

        self.device_table: Union[MultiDeviceTable, None] = None

    def build(self, frame: Frame):
        frame.title = "Select Devices"
        self.device_table = MultiDeviceTable(frame, self.exp_manager.chip)

    def _on_next(self) -> bool:
        marked_devices = self.device_table.get_marked_devices()
        if not marked_devices:
            messagebox.showinfo(title="Device Selection", message="Please mark devices to continue.")
            return False
        # todo: maybe add marked devices to wizard instead of exp_manager
        self.exp_manager.exp.device_list = marked_devices
        self.device_table.serialize()
        return True


class MultiDeviceTable(Frame):
    """Shows a table with all devices of the current chip and lets the user select devices."""

    SETTINGS_PATH = get_configuration_file_path("device_selection.json")

    def __init__(self, parent: Frame, chip: Chip) -> None:
        super().__init__()
        self.logger = logging.getLogger()

        self.parent = parent
        self.chip = chip

        self._counter_all = 0
        self._counter_selected = 0

        self.__setup__()

    def __setup__(self):
        """Set up the custom table containing all devices from the chip."""

        # set up columns so that they contain all parameters
        def_columns = ["#", "Selection", "ID", "In", "Out", "Type"]
        columns = set()
        for device in self.chip.devices.values():
            for param in device.parameters:
                columns.add(str(param))

        saved_ids = self.deserialize_to_list()
        devices = []
        for idx, dev in enumerate(self.chip.devices.values()):
            if dev.id in saved_ids:
                row_values = (idx + 1, "marked", dev.id, dev.in_position, dev.out_position, dev.type)
                saved_ids.remove(dev.id)
            else:
                row_values = (idx + 1, " ", dev.id, dev.in_position, dev.out_position, dev.type)
            row_values = (*row_values, [dev.parameters.get(param, "") for param in columns])
            devices.append(row_values)

        info_label = Label(self.parent, text="Highlight one or more rows, then press mark to select these devices")
        info_label.grid(column=0, row=0, padx=5, pady=5, sticky="nswe")

        self.table_frame = CustomFrame(self.parent)
        self.table_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nswe")
        self.table_frame.rowconfigure(0, weight=1)
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        self.device_table = CustomTable(self.table_frame, (def_columns + list(columns)), devices)

        button_frame = Frame(self.parent)
        button_frame.grid(column=0, row=2, sticky="w")

        mark_highlighted_button = Button(button_frame, text="(un)mark highlighted", command=self.mark_selected_items)
        mark_highlighted_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        mark_all_button = Button(button_frame, text="(un)mark all", command=self.mark_all)
        mark_all_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        info_label = Label(self.parent, text="The selected devices will be sorted by the original index.")
        info_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")

    def mark_items_by_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        copied_ids = ids[:]
        tree = self.device_table.get_tree()
        for iid in tree.get_children():
            current_id = str(tree.set(iid, column=2))
            if current_id not in ids:
                continue
            if tree.set(iid, column=1) == " ":
                tree.set(iid, column=1, value="marked")
            else:
                tree.set(iid, column=1, value=" ")
            copied_ids.remove(current_id)
            if not copied_ids:
                break

    def mark_selected_items(self) -> None:
        """Mark or un-mark the currently selected rows."""
        tree = self.device_table.get_tree()
        for iid in tree.selection():
            if tree.set(iid, column=1) == " ":
                tree.set(iid, column=1, value="marked")
            else:
                tree.set(iid, column=1, value=" ")

    def mark_all(self) -> None:
        tree = self.device_table.get_tree()
        value_to_set = "marked" if (self._counter_all % 2 == 0) else " "
        [tree.set(iid, column=1, value=value_to_set) for iid in tree.get_children()]
        self._counter_all += 1

    def deserialize_to_list(self) -> list[str]:
        if not os.path.exists(self.SETTINGS_PATH):
            return []
        with open(self.SETTINGS_PATH, "r") as f:
            stored_device_ids = json.load(f)
        return list(stored_device_ids)

    def serialize(self) -> None:
        with open(self.SETTINGS_PATH, "w") as f:
            json.dump(self.get_marked_device_ids(), f)

    def get_marked_device_ids(self) -> list[str]:
        """Return a list of ids from the marked devices sorted according to the original index."""
        tree = self.device_table.get_tree()
        marked_iid = [iid for iid in tree.get_children() if tree.set(iid, column=1) == "marked"]
        device_indices = [tree.set(iid, column=0) for iid in marked_iid]
        device_ids = [tree.set(iid, column=2) for iid in marked_iid]
        return [_id for _, _id in sorted(zip(device_indices, device_ids))]

    def get_marked_devices(self) -> list[Device]:
        return [self.chip.devices[dev_id] for dev_id in self.get_marked_device_ids()]


class MeasurementSelection(Step):

    def __init__(self, wizard: ExperimentWizard, exp_manager: ExperimentManager) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Measurement Selection", on_next=self._on_next)
        self.exp_manager = exp_manager
        self._measurement_names = exp_manager.exp.measurement_list

        self.meas_table: Union[CustomTable, None] = None

        # this keeps track of the selected measurement names
        self._selected_meas_names = []

    def build(self, frame: CustomFrame):
        frame.title = "Select Measurements"

        # create table
        rows = [(0, meas) for meas in sorted(list(self._measurement_names))]
        self.meas_table = CustomTable(frame, columns=["Order", "Name"], rows=rows)
        tree = self.meas_table.get_tree()
        for idx, iid in enumerate(tree.get_children()):
            tree.item(iid, tags=(str(idx)))
            tree.tag_bind(str(idx), "<ButtonRelease-1>", self.select_item)
            CreateToolTip(experiment_manager=self.exp_manager, widget=tree, stringvar=idx, is_treeview=True, item=iid)

        info_label = Label(frame, text="Order 0 means that the measurement is not selected.")
        info_label.grid(column=0)

    def select_all(self) -> None:
        self._selected_meas_names.clear()
        tree = self.meas_table.get_tree()
        for k, row_id in enumerate(tree.get_children()):
            tree.set(row_id, column=0, value=k + 1)
            self._selected_meas_names.append(tree.set(row_id, column=1))

    def select_item(self, event) -> None:
        """Called when the user selects a measurement in the table. Sets the order of the measurements.

        Parameters
        ----------
        event : Tkinter Event Object
            Python object instance with attributes about the event.
        """
        tree = self.meas_table.get_tree()
        # do nothing to the selection, if the header is clicked
        if tree.identify("region", event.x, event.y) == "heading":
            return

        # get the item, that was clicked on
        clicked_iid = tree.focus()
        meas_name = tree.set(clicked_iid, column=1)

        # determine if item should be selected or deselected
        if meas_name in self._selected_meas_names:
            removed_order = int(tree.set(clicked_iid, column=0))
            self._selected_meas_names.remove(meas_name)
            tree.set(clicked_iid, column=0, value=0)
            # lower for higher order measurements
            iid_to_lower_order = [iid for iid in tree.get_children() if int(tree.set(iid, column=0)) > removed_order]
            [tree.set(iid, column=0, value=int(tree.set(iid, column=0)) - 1) for iid in iid_to_lower_order]
        else:
            self._selected_meas_names.append(meas_name)
            tree.set(clicked_iid, column=0, value=len(self._selected_meas_names))

        if self._selected_meas_names:
            self.next_step_enabled = True

    def _on_next(self) -> bool:
        if not self._selected_meas_names:
            messagebox.showinfo("Warning", "Please select at least one measurement")
            return False
        self.exp_manager.exp.selected_measurements.clear()
        for meas in self._selected_meas_names:
            self.exp_manager.exp.create_measurement_object(meas)
        self._selected_meas_names.clear()
        return True


class InstrumentSelection(Step):

    SETTINGS_FILE_PREFIX = "ExperimentWizard_instr_"

    def __init__(self, wizard: ExperimentWizard, exp_manager: ExperimentManager) -> None:
        super().__init__(
            wizard=wizard,
            builder=self.build,
            title="Instrument Selection",
            on_previous=self._on_previous,
            on_next=self._on_next,
        )
        self.exp_manager = exp_manager

        self._selectors: dict[InstrumentSelector, Measurement] = {}

    @property
    def selectors(self) -> dict[InstrumentSelector, Measurement]:
        return self._selectors

    def build(self, frame: Frame):
        frame.title = "Select Instruments"

        for measurement in self.exp_manager.exp.selected_measurements:
            instr_table = InstrumentSelector(frame)
            self._selectors.update({instr_table: measurement})

            instr_table.title = measurement.name
            instr_table.grid(column=0, columnspan=2, padx=5, pady=5, sticky="w")

            instr_table.instrument_source = {
                instr_type: InstrumentRole(self.wizard, get_visa_address(instr_type))
                for instr_type in measurement.get_wanted_instrument()
            }

            instr_table.deserialize(self.SETTINGS_FILE_PREFIX + measurement.settings_path)

    def _serialize_instr_selection(self):
        for selector, measurement in self.selectors.items():
            selector.serialize(self.SETTINGS_FILE_PREFIX + measurement.settings_path)

    def _on_previous(self) -> bool:
        self.exp_manager.exp.selected_measurements.clear()
        for measurement in self.selectors.values():
            measurement.selected_instruments.clear()
        return True

    def _on_next(self) -> bool:
        self._serialize_instr_selection()

        for selector, measurement in self.selectors.items():
            measurement.selected_instruments.clear()

            for role, val in selector.instrument_source.items():
                if role in measurement.selected_instruments and measurement.selected_instruments[role] == val.choice:
                    messagebox.showinfo(title="Error", message="You cannot choose the same instrument twice")
                    return False
                measurement.selected_instruments.update({role: val.choice})
            try:
                measurement.init_instruments()
            except Exception as exc:
                messagebox.showerror(
                    title="Instrument error!", message=f"The instrument definition was not successful. Reason {exc}"
                )
                return False

        return True


class ParameterSelection(Step):

    def __init__(self, wizard: ExperimentWizard, exp_manager: ExperimentManager) -> None:
        super().__init__(wizard=wizard, builder=self.build, title="Parameter Selection", finish_step_enabled=True)
        self.exp_manager = exp_manager

        self.parameter_tables: dict[str, ParameterTable] = {}  # measurement name as keys

    def build(self, frame: Frame):
        frame.title = "Select Parameters"

        for measurement in self.exp_manager.exp.selected_measurements:

            param_table = ParameterTable(frame)
            param_table.title = f"Parameters {measurement.name}"
            param_table.parameter_source = measurement.get_default_parameter()
            param_table.deserialize(measurement.settings_path)
            param_table.grid(column=0, padx=5, pady=5, sticky="w")

            self.parameter_tables.update({measurement.name: param_table})

    def write_parameters(self) -> None:
        for meas_name, table in self.parameter_tables.items():
            table_as_dict = {}
            measurement = next((meas for meas in self.exp_manager.exp.selected_measurements if meas.name == meas_name))
            table.serialize_to_dict(settings=table_as_dict)
            for param_name, param_value in table_as_dict["data"].items():
                measurement.parameters[param_name].value = param_value

            table.serialize(file_name=measurement.settings_path)
