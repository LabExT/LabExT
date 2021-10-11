#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


class MeasParam:
    """Implementation of a single measurement parameter.

    Should never be used directly, only the subclasses in this file should be used.

    Attributes:
        value: The value which the parameter represents
        unit (str): What unit the parameter has. Purely visual as a help for the user, does not influence calculations.
        extra_type: Extra type, should be removed in future versions.
    """

    def __init__(self, value=None, unit=None, extra_type=None):
        """Constructor.

        Arguments:
            value: The value which the parameter represents
            unit (str): What unit the parameter has. Purely visual as a help for the user, does not influence calculations.
            extra_type: Extra type, should be removed in future versions.
        """
        self.value = value
        self.unit = unit
        # TODO: consider removing this
        self.extra_type = extra_type

    def as_dict(self):
        """Returns the stored value as part of a dict.
        """
        d = {'value': self.value}
        if self.unit is not None:
            d.update({'unit': self.unit})
        return d

    def __str__(self):
        """Converts this parameter to a string.
        """
        return str(type(self)) + ": " + str(self.value) + " " + str(self.unit)


class MeasParamInt(MeasParam):
    """Implements a MeasParam that represents an integer number.
    """

    def __init__(self, value=None, unit=None, extra_type=None):
        super().__init__(value, unit, extra_type)
        self.value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        if type(new_val) is int:
            self._value = new_val
        else:
            raise ValueError(
                "MeasParamInt needs an integer assigned to value. Tried to assign: " + str(new_val) + " of type "
                + str(type(new_val)))


class MeasParamFloat(MeasParam):
    """Implements a MeasParam that represents a floating-point number.
    """

    def __init__(self, value=None, unit=None, extra_type=None):
        super().__init__(value, unit, extra_type)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        if type(new_val) is float:
            self._value = new_val
        else:
            raise ValueError(
                "MeasParamFloat needs a float assigned to value. Tried to assign: " + str(new_val) + " of type "
                + str(type(new_val)))


class MeasParamString(MeasParam):
    """Implements a MeasParam that represents a string.
    """

    def __init__(self, value=None, unit=None, extra_type=None):
        super().__init__(value, unit, extra_type)


class MeasParamBool(MeasParam):
    """Implements a MeasParam that represents a boolean.

    Gets rendered as a check-box.
    """

    def __init__(self, value=None, unit=None, extra_type=None):
        super().__init__(value, unit, extra_type)


class MeasParamList(MeasParam):
    """Implements a MeasParam that represents a selection as part of a list.

    Aside from the MeasParam arguments, needs the `options` argument, a list of all possible selections. Gets rendered
    as a drop-down menu in LabExT GUI.
    """

    def __init__(self, options, value=None, unit=None, extra_type=None):
        """Constructor.

        Arguments:
            options (list): all the options this MeasParam can take
        """
        super().__init__(value, unit, extra_type)
        self.options = options

    def __str__(self):
        return str(type(self)) + ": " + str(self.options) + " selected: " + str(self.value)


def MeasParamAuto(value=None, unit=None, extra_type=None, selected=None):
    """Automatically chooses the correct type of MeasParam based on the type of the `value` argument.
    """
    if type(value) is str:
        return MeasParamString(value=value, unit=unit, extra_type=extra_type)
    elif type(value) is bool:
        return MeasParamBool(value=value, unit=unit, extra_type=extra_type)
    elif type(value) is list:
        return MeasParamList(options=value, value=selected, unit=unit, extra_type=extra_type)
    elif type(value) is int:
        return MeasParamInt(value=value, unit=unit, extra_type=extra_type)
    else:
        return MeasParamFloat(value=value, unit=unit, extra_type=extra_type)
