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
    id: str
    in_position: List[float] = field(default_factory=list)
    out_position: List[float] = field(default_factory=list)
    type: str = ''
    parameters: dict = field(default_factory=dict)

    def as_dict(self):
        return asdict(self)

    def as_tuple(self):
        return astuple(self)
