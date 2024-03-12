#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from dataclasses import dataclass, field, asdict, astuple
from typing import List, Type

from LabExT.Movement.Transformations import ChipCoordinate


@dataclass(frozen=True, order=True)
class Device:
    """
    Implementation of a single device on a chip.

    Attributes
    ----------
    id: str
        identifier
    type: str
        device type or general device description
    in_position: List[float], optional
        input position as list of coordinates
    out_position: List[float], optional
        output position as list of coordinates
    parameters: dict, optional
        any additional parameters as written in the chip file
    """

    id: str
    type: str
    in_position: List[float] = field(default_factory=list)
    out_position: List[float] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)

    @property
    def short_str(self) -> str:
        """Return string representation for device"""
        return "ID {} - IN: {} OUT: {}".format(self.id, self.input_coordinate, self.output_coordinate)

    def as_dict(self):
        """Return device as a dictionary."""
        return asdict(self)

    def as_tuple(self):
        """Return device as a tuple."""
        return astuple(self)

    @property
    def input_coordinate(self) -> Type[ChipCoordinate]:
        return ChipCoordinate.from_list(self.in_position)

    @property
    def output_coordinate(self) -> Type[ChipCoordinate]:
        return ChipCoordinate.from_list(self.out_position)
