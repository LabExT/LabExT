#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TypedDict, Literal, Optional


class ChipDict(TypedDict("SpacesInKeys", {"description file path": str}), total=False):
    name: str


class ErrorDict(TypedDict("SpacesInKeys", {"type": str}), total=False):
    desc: str
    traceback: str


class SoftwareDict(TypedDict("SpacesInKeys", {"git rev": str}), total=False):
    name: Literal["LabExT"]
    version: str
    computer: str


class SweepInformation(TypedDict):
    part_of_sweep: bool
    sweep_association: Optional[dict]


class MeasurementDict(
    TypedDict(
        "SpacesInKeys",
        {
            "experiment settings": dict,
            "measurement id long": str,
            "measurement name": str,
            "measurement name and id": str,
            "measurement settings": dict,
            "search for peak": Optional[dict],
            "timestamp end": str,
            "timestamp start": str,
        },
        total=False,
    ),
    total=False,
):
    """This class is only used for typechecking.

    If instantiated at runtime the objects are regular `dict`s.
    """

    chip: ChipDict
    device: dict
    error: ErrorDict
    file_path_known: str
    finished: bool
    instruments: dict[str, dict]
    name_known: str
    software: SoftwareDict
    sweep_information: SweepInformation
    timestamp: str
    timestamp_iso_known: str
    timestamp_known: str
    values: dict
