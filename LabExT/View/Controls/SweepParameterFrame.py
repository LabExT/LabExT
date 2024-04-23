#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import re

import numpy as np
import pandas as pd

from typing import TYPE_CHECKING, Dict, List, Tuple, Union, Literal

from tkinter import Tk, StringVar, Label, Entry, OptionMenu, Button, Frame, NORMAL, DISABLED

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.Measurements.MeasAPI.Measparam import MeasParam, MeasParamInt, MeasParamFloat

if TYPE_CHECKING:
    CategoryType = Literal[
        "step_size", "step_count_linear", "step_count_logarithmic", "step_count_repetition", "binary", "list"
    ]

    RangeRepresentation = Tuple[pd.Series, CategoryType]
    JSONRepresentation = Dict[str, RangeRepresentation]
else:
    CategoryType = None
    RangeRepresentation = None
    JSONRepresentation = None


class RangeEntry(Frame):
    """A `Frame` which holds three entry fields and a category selector."""

    def _validate_float(self, mode: str, text: str) -> bool:
        """Allows only ints and floats in the text field.

        Args:
            mode: an integer specifying the type of change ('%d' in tk)
            text: the new value of the entry after the change ('%P' in tk)

        Returns:
            false if there was an invalid insertion, true otherwise
        """
        if int(mode) == 1:
            # mode == 1 means insertion
            optional_fraction = r"[0-9]+(?:[.][0-9]*)?"
            optional_whole = r"[.][0-9]+"
            pattern = r"[+-]?(" + optional_fraction + "|" + optional_whole + r")"
            ret = re.fullmatch(pattern, text)
            return ret is not None
        else:
            return True

    def _validate_int(self, mode: str, text: str) -> bool:
        """Allows only ints in the text field.

        Args:
            mode: an integer specifying the type of change ('%d' in tk)
            text: the new value of the entry after the change ('%P' in tk)

        Returns:
            false if there was an invalid insertion, true otherwise
        """
        if int(mode) == 1:
            # mode == 1 means insertion
            pattern = r"[+-]?[0-9]+"
            return re.fullmatch(pattern, text) is not None
        else:
            return True

    def _validate_step(self, mode: str, text: str) -> bool:
        """Allows only ints or floats in the text field depending on the chosen category.

        Args:
            mode: an integer specifying the type of change ('%d' in tk)
            text: the new value of the entry after the change ('%P' in tk)

        Returns:
            false if there was an invalid insertion, true otherwise
        """
        if self._step_category.get() == self._selection["step_size"]:
            # step size
            return self._get_validation_function()(mode, text)
        else:
            return self._validate_int(mode, text)

    def _get_validation_function(self):
        """Used to choose the correct validation function based on the parameter's type"""
        if type(self._meas_param) == MeasParamInt:
            return self._validate_int
        elif type(self._meas_param) == MeasParamFloat:
            return self._validate_float
        else:
            raise TypeError(f"Invalid sweep parameter {self._meas_param} with type {type(self._meas_param)}")

    def _on_category_change(self, *_) -> None:
        """Called when the user changes the category of the step"""
        if self._step_category.get() == self._selection["step_size"]:
            # step size selected
            self._to_label.config(text="To (included if step size allows it):")
        else:
            self._to_label.config(text="To (included):")
        self.__setup__()

    def __init__(
        self,
        parent: Frame,
        var_master: Tk,
        meas_param: MeasParam,
        default_from: Union[int, float] = 0,
        default_to: Union[int, float] = 1,
        default_step: Union[int, float] = 0.1,
        default_category: CategoryType = "step_size",
        start_enabled: bool = True,
        *args,
        **kwargs,
    ) -> None:
        """Initializes a new RangeEntry.

        Args:
            parent: The Frame this Entry should be drawn into
            var_master: The Tk this entry belongs to. Variables will be children of it.
            meas_param: The measurment parameter this range is associated with. Only float- and int-parameters are valid.
            default_from: The default value for the start of the range. (default: 0)
            default_to: The default value for the end of the range. (default: 1)
            default_step: The default value for the stepsize/no of points in the range. (default: 0.1)
            start_enabled: Whether this entry should start interactable or not.
        """
        super().__init__(parent, *args, **kwargs)

        # needed for results and validate function
        self._meas_param = meas_param
        """The measurement parameter this range is associated with"""

        # set validate function
        self._validate_function = (self.register(self._get_validation_function()), "%d", "%P")
        """A tuple representing the function used for input validation used by tk `Entry`s"""

        # possible categories
        self._selection: Dict[CategoryType, str] = {
            "step_size": "Step size:",
            "step_count_linear": "No. of Points (linear):",
            "step_count_logarithmic": "No. of Points (logarithmic):",
            "step_count_repetition": "Repetitions:",
        }
        """A mapping of the possible categories to the displayed name."""

        # these store the entered content
        self._from = StringVar(master=var_master, value=default_from)
        self._to = StringVar(master=var_master, value=default_to)
        self._step_value = StringVar(master=var_master, value=default_step)
        self._step_category = StringVar(master=var_master, value=self._selection[default_category])

        # labels are changed based on category
        self._from_label = Label(self, text="From:")
        self._to_label = Label(self, text="To (included if step size allows it):")
        self._value_label = Label(self, text=f"Value: {self._meas_param.value}")

        # allows the user to choose category
        self._category_menu = OptionMenu(
            self, self._step_category, *self._selection.values(), command=self._on_category_change
        )

        self._state = NORMAL if start_enabled else DISABLED

        default_entry_width = 10
        # the entry fields
        self._from_entry = Entry(
            self,
            textvariable=self._from,
            width=default_entry_width,
            state=self._state,
            validate="key",
            validatecommand=self._validate_function,
        )
        self._to_entry = Entry(
            self,
            textvariable=self._to,
            width=default_entry_width,
            state=self._state,
            validate="key",
            validatecommand=self._validate_function,
        )
        self._step_entry = Entry(
            self,
            textvariable=self._step_value,
            width=default_entry_width,
            state=self._state,
            validate="key",
            validatecommand=(self.register(self._validate_step), "%d", "%P"),
        )

        self.__setup__()

    def __setup__(self) -> None:
        """Redraws this widget."""
        self._from_label.grid_forget()
        self._from_entry.grid_forget()
        self._to_label.grid_forget()
        self._to_entry.grid_forget()
        self._value_label.grid_forget()
        if self._step_category.get() != self._selection["step_count_repetition"]:
            self._from_label.grid(row=0, column=0, sticky="e")
            self._from_entry.grid(row=0, column=1, sticky="w")
            self._from_entry.config(
                state=(
                    DISABLED if self._step_category.get() == self._selection["step_count_repetition"] else self._state
                )
            )
            self._to_label.grid(row=0, column=2, sticky="e")
            self._to_entry.grid(row=0, column=3, sticky="w")
            self._to_entry.config(
                state=(
                    DISABLED if self._step_category.get() == self._selection["step_count_repetition"] else self._state
                )
            )
        else:
            self._value_label.config(text=f"Value: {self._meas_param.value}")
            self._value_label.grid(row=0, column=3, sticky="e")

        self._category_menu.grid(row=0, column=4, sticky="e")
        self._step_entry.grid(row=0, column=5, sticky="w")

        for i in range(6):
            self.columnconfigure(index=i, weight=1)

    def parse_string(self, s: str, force_int: bool = False) -> Union[int, float]:
        """Parses a string to int or float depending on `self._meas_param`'s type."""
        if force_int:
            return int(float(s))
        return int(s) if type(self._meas_param) == MeasParamInt else float(s)

    def results(self) -> RangeRepresentation:
        """Returns the results of this component as a `RangeRepresentation`.

        Returns:
            A `RangeRepresentation` of the ranges specified by the user

        Raises:
            `ValueError` if the user enters illegal values
        """
        category = self._step_category.get()

        from_ = self.parse_string(self._from.get())
        to = self.parse_string(self._to.get())
        step = self.parse_string(self._step_value.get(), category != self._selection["step_size"])

        if category == self._selection["step_size"]:
            if from_ >= to or step > to - from_:
                raise ValueError(
                    f"Please make sure that 'From'(={from_}) is less than 'To'(={to}) "
                    + f"and 'Step'(={step}) is less than or equal to 'To - From'(={to - from_})."
                )

            if int((to - from_) / step * 10) % 10 != 0:
                logging.info(
                    f"'To-From(={to-from_})' is not a multiple of 'Step(={step})'. "
                    + f"'To(={to})' will not be included."
                )

            step_count = int(np.floor((to - from_) / step))
            return (pd.Series([from_ + i * step for i in range(step_count + 1)]), "step_size")

        elif category == self._selection["step_count_linear"]:
            step_size = (to - from_) / (step - 1)
            return (pd.Series([from_ + i * step_size for i in range(step)]), "step_count_linear")
        elif category == self._selection["step_count_logarithmic"]:
            return (pd.Series(((np.logspace(0, 1, step) - 1) / 9 * (to - from_) + from_)), "step_count_logarithmic")
        else:
            return (pd.Series([self._meas_param.value for _ in range(step)]), "step_count_repetition")

    @property
    def from_(self) -> Union[int, float]:
        """The user-specified starting-value"""
        return self.parse_string(self._from.get())

    @property
    def to(self) -> Union[int, float]:
        """The user-specified end-value"""
        return self.parse_string(self._to.get())

    @property
    def step(self) -> Union[int, float]:
        """The user-specified category-dependent-value"""
        return self.parse_string(self._step_value.get())

    @property
    def category(self) -> CategoryType:
        """The user-specified category-type"""
        return next(
            cat_type for cat_type, cat_name in self._selection.items() if cat_name == self._step_category.get()
        )

    @property
    def enabled(self) -> bool:
        """True if and only if at least one entry is editable"""
        return self._state == NORMAL

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        self._state = NORMAL if enabled else DISABLED

        self._from_entry.config(state=self._state)
        self._to_entry.config(state=self._state)
        self._step_entry.config(state=self._state)
        self._category_menu.config(state=self._state)

    @property
    def meas_param(self) -> MeasParam:
        """Returns a copy of the measurement parameter controlled by this range."""
        return self._meas_param.copy()

    @meas_param.setter
    def meas_param(self, new: MeasParam) -> None:
        """Sets the measurement parameter of controlled by this range."""
        self._meas_param = new
        self.__setup__()


class BinaryEntry(Label):
    pass


class ListEntry(Label):
    def __init__(self, options: List, *args, **kwargs) :
        super().__init__(*args, **kwargs)
        self.options = options.copy()


class SweepParameterFrame(CustomFrame):
    """A table allowing the user to choose parameters to sweep and set their ranges."""

    def __init__(
        self,
        parent: Frame,
        string_var_master: Tk,
        parameters: Dict[str, MeasParam],
        entry_width: int = 10,
        *args,
        **kwargs,
    ):
        """Creates a new `SweepParameterFrame`.

        Args:
            parent: The Frame this object should be drawn into
            string_var_master: The Tk window this object is inside of (Used for StringVars which need a
                Tk as master)
            parameter: The parameters that are available to sweep or `None`
            entry_width: The width of the input fields for the ranges
            *args: Will be passed to TK initializer
            **kwargs: Will be passed to TK initializer
        """
        super().__init__(parent, *args, **kwargs)

        self._parameters: Dict[str, MeasParam] = parameters.copy() if parameters is not None else dict()

        self._remaining_parameters: List[str] = list(self._parameters.keys())

        self._logger.debug(f"Setting up SweepParameterFrame with parameters: {self._remaining_parameters}")

        self._ranges: List[Tuple[OptionMenu, Union[RangeEntry, BinaryEntry, ListEntry], StringVar]] = list()

        self._minus_button = Button(self, text="-", command=self.on_minus)
        self._plus_button = Button(self, text="+", command=self.on_plus)

        self._entry_width = entry_width

        self._var_master = string_var_master

        self.__setup__()  # draw the table

    def on_minus(self, *_):
        """Called when the minus button is clicked.

        Args:
            _: positional arguments needed for tk to be able to use this function as a command argument.
        """
        # Invariant of class: minus button only drawn if plus was hit at least once
        assert len(self._ranges) > 0

        # remove gui components of last entry
        self._ranges[-1][1].destroy()
        self._ranges[-1][0].destroy()

        self._children.remove(self._ranges[-1][1])
        self._children.remove(self._ranges[-1][0])

        self._ranges = self._ranges[:-1]

        # make sure the newly unlocked menu option is added to remaining params
        if len(self._ranges) > 0:
            newly_ramining = self._ranges[-1][2].get()
            self._logger.debug(
                f"Adding '{newly_ramining}' to remaining parameters"
                + f"(before update = {self._remaining_parameters})"
            )
            self._remaining_parameters.append(newly_ramining)

        # redraw
        self.__setup__()

    def on_plus(self, *_):
        """Called when the plus button is clicked.

        Args:
            _: positional arguments needed for tk to be able to use this function as a command argument.
        """
        # Invariant of class: plus button only drawn if there are at least two params left
        # (one being the one in the option menu and one being the one being newly "locked in")
        assert len(self._remaining_parameters) > 1

        # remove previously selected parameter from selection ("lock it in")
        if len(self._ranges) > 0:
            param_to_remove = self._ranges[-1][2].get()
            self._remaining_parameters.remove(param_to_remove)

        # setting the text on the newly created option menu to the name of the first remaining param
        default_text = self._remaining_parameters[0]

        # populating gui elements
        text = StringVar(self._var_master, default_text)
        menu = OptionMenu(self, text, *self._remaining_parameters, command=self._check_entry_type)

        entry = self._get_param_entry(default_text)

        self._ranges.append((menu, entry, text))

        # redraw
        self.__setup__()

    def _check_entry_type(self, *_) -> object:
        """Checks if entry types match the new parameter's `sweep_type`.

        Called when an option menu changes.

        Args:
            _: positional arguments needed for tk.
        """
        for index, (_, entry, text) in enumerate(self._ranges):
            self._logger.debug(f"Checking entry type for '{text.get()}'")
            new_entry = self._get_param_entry(text.get())

            # skip parameters for which entry type is correct
            if type(new_entry) == type(entry):
                continue

            entry.destroy()
            self._children.remove(entry)
            # tuples don't allow item assignments
            self._ranges[index] = (self._ranges[index][0], new_entry, self._ranges[index][2])

        _, entry, text = self._ranges[-1]
        if type(entry) == RangeEntry:
            entry.meas_param = self._parameters[text.get()]

        # redraw
        self.__setup__()

    def _get_param_entry(self, param_name: str) -> Union[Entry, Label]:
        """Returns the entry needed based on the `sweep_type` of the parameter.

        Args:
            param_name: the name of the parameter.
        """
        if self._parameters[param_name].sweep_type == "binary":
            return BinaryEntry(master=self, text="Will be True and False.")
        elif self._parameters[param_name].sweep_type == "list":
            return ListEntry(
                options=self._parameters[param_name].options,
                master=self,
                text="Will cycle through all list options.")
        elif self._parameters[param_name].sweep_type == "range":
            param_value_low = self._parameters[param_name].value
            param_value_high = 2 * (abs(param_value_low) + 1)
            param_value_step = (param_value_high - param_value_low) / 10
            return RangeEntry(
                parent=self,
                var_master=self._var_master,
                meas_param=self._parameters[param_name],
                default_from=param_value_low,
                default_to=param_value_high,
                default_step=param_value_step,
                start_enabled=True,
            )
        else:
            raise AssertionError(
                "SweepParameterFrame should not receive parameters"
                + "whose sweep type differ from 'binary' and 'range' and 'list'."
            )

    def __setup__(self):
        self.clear()  # remove all existing ui controls from the table

        # draw entries
        for i, (menu, range_entry, _) in enumerate(self._ranges):
            # lock option menus
            menu.config(state=DISABLED)
            self.add_widget(menu, row=i, column=0, sticky="w")

            if type(range_entry) == RangeEntry:
                range_entry.enabled = True
                range_entry.__setup__()
            self.add_widget(range_entry, row=i, column=1, sticky="e")

        # unlock last option menu
        if len(self._ranges) > 0:
            self._ranges[-1][0].config(state=NORMAL)

        # add buttons for adding and removing range entries
        button_frame = Frame(self)
        if len(self._ranges) > 0:
            # minus button only drawn if at least one entry exists
            self._minus_button = Button(button_frame, text="-", command=self.on_minus)
            self._minus_button.grid(row=0, column=0, sticky="e")
        if len(self._remaining_parameters) > 1:
            # plus button only drawn if at least two parameters remain (current selection + 1)
            self._plus_button = Button(button_frame, text="+", command=self.on_plus)
            self._plus_button.grid(row=0, column=1, sticky="w")

        if len(self._ranges) == 0 and len(self._remaining_parameters) == 0:
            label = Label(button_frame, text="No sweepable parameters for this measurement.")
            label.grid(row=0, column=0, sticky="e")

        self.add_widget(button_frame, row=len(self._ranges), column=0, sticky="w")

        # fix width of components
        for i in range(len(self._ranges) + 1):
            self.columnconfigure(i, weight=1)
            self.columnconfigure(i, pad=0)

    def results(self, out_dict: JSONRepresentation = None) -> JSONRepresentation:
        """Returns the result of this frame"""
        if out_dict is None:
            out_dict = dict()

        for _, range_entry, text in self._ranges:
            if type(range_entry) == RangeEntry:
                out_dict[text.get()] = range_entry.results()
            elif type(range_entry) == BinaryEntry:
                out_dict[text.get()] = (pd.Series([True, False]), "binary")
            elif type(range_entry) == ListEntry:
                out_dict[text.get()] = (pd.Series(range_entry.options), "list")
            else:
                raise ValueError('Unknown range entry type: ' + str(range_entry))
        return out_dict

    def serialize(
        self, settings: Dict[str, Tuple[Union[int, float], Union[int, float], Union[int, float], CategoryType]]
    ) -> None:
        """Writes the json representation of the sweepable parameters to `settings`."""
        for key in settings.copy().keys():
            del settings[key]

        for _, range_entry, text in self._ranges:
            if type(range_entry) == RangeEntry:
                settings[text.get()] = (range_entry.from_, range_entry.to, range_entry.step, range_entry.category)
            else:
                settings[text.get()] = (0, 0, 0, "binary")

    def deserialize(
        self, settings: Dict[str, Tuple[Union[int, float], Union[int, float], Union[int, float], CategoryType]]
    ) -> None:
        """Reads the json representation of the sweepable parameters from `settings`.

        Args:
            settings: The dictionary with the settings used to populate this frame.
        """
        self._logger.debug(f"Deserializing from {settings}")
        prev_text: str = ""  # needed to update self._remaining_parameters while going through loop
        for text, data in settings.copy().items():
            # check for duplicate entries
            if text == prev_text:
                self._logger.warning(f"Inconsistent cache file: {text} occurs multiple times")
                continue

            # make sure settings from previous runs don't exist
            if text not in self._remaining_parameters:
                del settings[text]
                continue

            # "lock in" selection of previous option menu
            if prev_text != "":
                self._remaining_parameters.remove(prev_text)
            prev_text = text

            # populate entries
            var = StringVar(self._var_master, text)
            menu = OptionMenu(self, var, *self._remaining_parameters, command=self._check_entry_type)
            if data[3] == "binary":
                # get the label from function to not retype the code
                entry = self._get_param_entry(text)
            else:
                entry = RangeEntry(
                    parent=self,
                    var_master=self._var_master,
                    meas_param=self._parameters[text],
                    default_from=data[0],
                    default_to=data[1],
                    default_step=data[2],
                    default_category=data[3],
                )

            self._ranges.append((menu, entry, var))

        self.__setup__()
