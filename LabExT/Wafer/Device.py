#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from dataclasses import dataclass, field, asdict, astuple
from typing import List


@dataclass(frozen=True, order=True)
class Device:
    """
    Implementation of a single device on a chip.

    Attributes
    ----------
    id: str
        identifier
    in_position: List[float]
        input position as list of coordinates
    out_position: List[float]
        output position as list of coordinates
    type: str
        device type or general device description
    parameters: dict
        any additional parameters as written in the chip file
    """
    id: str
    in_position: List[float] = field(default_factory=list)
    out_position: List[float] = field(default_factory=list)
    type: str = ''
    parameters: dict = field(default_factory=dict)

    def as_dict(self):
        """ Return device as a dictionary. """
        return asdict(self)

    def as_tuple(self):
        """ Return device as a tuple. """
        return astuple(self)
