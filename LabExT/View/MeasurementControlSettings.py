#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
import json
import logging
import os.path
from tkinter import Toplevel, Checkbutton, BooleanVar, Label, StringVar, Entry, Button
from typing import TYPE_CHECKING

from tktooltip import ToolTip

from LabExT.Utils import get_configuration_file_path
from LabExT.View.Controls.CustomFrame import CustomFrame

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.ExperimentManager import ExperimentManager
else:
    Tk = None
    ExperimentManager = None


class MeasurementControlSettings:

    FILENAME = 'meas_control_settings.json'

    def __init__(self):
        self._settings_filepath = get_configuration_file_path(self.FILENAME)

        # default values
        self.finished_meas_limited: bool = False
        self.max_finished_meas: int = 42
        self.displayed_todo_limited: bool = False
        self.max_displayed_todo: int = 42
        self.json_indented: bool = True

        # read values from savefile if it exists
        self.update()

    def _to_dict(self) -> dict:
        return {
            'finished_meas_limited': self.finished_meas_limited,
            'max_finished_meas': self.max_finished_meas,
            'displayed_todo_limited': self.displayed_todo_limited,
            'max_displayed_todo': self.max_displayed_todo,
            'json_indented': self.json_indented
        }

    def save_to_file(self) -> None:
        with open(self._settings_filepath, "w") as f:
            json.dump(self._to_dict(), f)

    def _read_savefile(self) -> dict:
        if not os.path.exists(self._settings_filepath):
            return {}
        with open(self._settings_filepath) as f:
            settings = json.load(f)
        return settings

    def update(self) -> None:
        settings = self._read_savefile()
        self.finished_meas_limited = settings.get('finished_meas_limited', self.finished_meas_limited)
        self.max_finished_meas = settings.get('max_finished_meas', self.max_finished_meas)
        self.displayed_todo_limited = settings.get('displayed_todo_limited', self.displayed_todo_limited)
        self.max_displayed_todo = settings.get('max_displayed_todo', self.max_displayed_todo)
        self.json_indented = settings.get('json_indented', self.json_indented)


class MeasurementControlSettingsView:
    """ Modify how measurement storing and tracking is handled """

    def __init__(self, parent: Tk, experiment_manager: ExperimentManager):
        self._root = parent
        self.exp_manager = experiment_manager
        self.logger = logging.getLogger()

        self._settings = MeasurementControlSettings()

        self.settings_frame = None
        self.limit_finished_meas_button = None

        self.measurements_limited = BooleanVar(self._root, value=self._settings.finished_meas_limited)
        self.measurements_limited.trace("w", self.measurements_checkbox_changed)
        self.measurement_limit = StringVar(self._root, value=str(self._settings.max_finished_meas))
        self.measurement_limit_label = None
        self.measurement_limit_field = None

        self.todos_limited = BooleanVar(self._root, value=self._settings.displayed_todo_limited)
        self.todos_limited.trace("w", self.todos_checkbox_changed)
        self.todo_limit = StringVar(self._root, value=str(self._settings.max_displayed_todo))
        self.todo_limit_label = None
        self.todo_limit_field = None

        self.no_json_indentation = BooleanVar(self._root, value=not self._settings.json_indented)

        # draw GUI
        self.__setup__()

    def measurements_checkbox_changed(self, *args) -> None:
        if self.measurements_limited.get():
            self.measurement_limit_label.config(state="normal")
            self.measurement_limit_field.config(state="normal")
        else:
            self.measurement_limit_label.config(state="disabled")
            self.measurement_limit_field.config(state="disabled")

    def todos_checkbox_changed(self, *args) -> None:
        if self.todos_limited.get():
            self.todo_limit_label.config(state="normal")
            self.todo_limit_field.config(state="normal")
        else:
            self.todo_limit_label.config(state="disabled")
            self.todo_limit_field.config(state="disabled")

    def _validate_entries(self) -> None:
        max_meas = int(self.measurement_limit.get())
        if max_meas <= 0:
            raise ValueError(f'The maximum number of measurement displayed cannot be lower than 1. Got {max_meas}')
        max_todos = int(self.todo_limit.get())
        if max_todos <= 1:
            raise ValueError(f'The maximum number of ToDos displayed cannot be lower than 1. Got {max_todos}')

    def save_and_close(self) -> None:
        self._validate_entries()
        self._settings.finished_meas_limited = self.measurements_limited.get()
        self._settings.max_finished_meas = int(self.measurement_limit.get())
        self._settings.displayed_todo_limited = self.todos_limited.get()
        self._settings.max_displayed_todo = int(self.todo_limit.get())
        self._settings.json_indented = not self.no_json_indentation.get()

        self._settings.save_to_file()
        self.exp_manager.main_window.update_tables()
        self.window.destroy()

    def __setup__(self):
        """ Set up toplevel GUI """
        self.window = Toplevel(self._root)
        self.window.title("Measurement Control Settings")
        self.window.geometry('%dx%d+%d+%d' % (500, 250, 300, 300))
        self.window.rowconfigure(3, weight=1)
        self.window.rowconfigure(4, weight=1)
        self.window.rowconfigure(5, weight=1)
        self.window.columnconfigure(0, weight=1)
        self.window.focus_force()

        settings_frame = CustomFrame(self.window)
        settings_frame.title = "Measurement Control Settings"
        settings_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nswe")
        settings_frame.columnconfigure(index=0, weight=1)
        settings_frame.rowconfigure(index=0, weight=1)
        settings_frame.rowconfigure(index=1, weight=1)

        # finished measurements
        limit_finished_meas_button = Checkbutton(
            settings_frame,
            text='Limit the number of finished measurements',
            variable=self.measurements_limited
        )
        limit_finished_meas_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ToolTip(
            limit_finished_meas_button,
            msg="Once the limit is reached, the oldest finished measurement is removed from the GUI.\n"
                "This does not affect the saved measurement files. Limiting the number of stored measurements "
                "can substantially improve the performance.",
            delay=1.0
        )

        self.measurement_limit_label = Label(settings_frame, text="Maximum number of stored measurements")
        self.measurement_limit_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.measurement_limit_field = Entry(settings_frame, textvariable=self.measurement_limit, width=5)
        self.measurement_limit_field.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        if self.measurements_limited.get():
            self.measurement_limit_label.config(state="normal")
            self.measurement_limit_field.config(state="normal")
        else:
            self.measurement_limit_label.config(state="disabled")
            self.measurement_limit_field.config(state="disabled")

        # measurement queue
        limit_displayed_todos_button = Checkbutton(
            settings_frame,
            text="Limit the number of displayed ToDo items",
            variable=self.todos_limited,
        )
        limit_displayed_todos_button.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ToolTip(
            limit_displayed_todos_button,
            msg="Reducing the number of ToDos displayed in the queue does not affect the actual planned "
                "measurements. If the max number of displayed ToDos is smaller than the length of the queue, only the "
                "first few and the last few ToDos will be shown. \n"
                "Limiting the number of displayed ToDos can substantially improve the performance.",
            delay=1.0
        )

        self.todo_limit_label = Label(settings_frame, text="Maximum number of displayed ToDos")
        self.todo_limit_label.config(state="disabled")
        self.todo_limit_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")

        self.todo_limit_field = Entry(settings_frame, textvariable=self.todo_limit, width=5)
        self.todo_limit_field.config(state="disabled")
        self.todo_limit_field.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        if self.todos_limited.get():
            self.todo_limit_label.config(state="normal")
            self.todo_limit_field.config(state="normal")
        else:
            self.todo_limit_label.config(state="disabled")
            self.todo_limit_field.config(state="disabled")

        no_indentation_button = Checkbutton(
            settings_frame,
            text="Save json files without indentation",
            variable=self.no_json_indentation
        )
        no_indentation_button.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        ToolTip(
            no_indentation_button,
            msg="Having no indentation in the json file can save approximately 20% of storage space",
            delay=1.0
        )

        cancel_button = Button(self.window, text="Cancel", command=self.window.destroy)
        cancel_button.grid(row=2, column=0, padx=5, pady=5)

        save_button = Button(self.window, text='Save and Close', command=self.save_and_close)
        save_button.grid(row=2, column=0, padx=5, pady=5, sticky="e")
