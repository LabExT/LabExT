#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from abc import ABC, abstractmethod
from typing import NamedTuple, Type
import numpy as np


class Transformation(ABC):
    """
    Abstract interface for transformations.
    """

    @abstractmethod
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def is_valid(self):
        """
        Returns True if the transformation is valid.
        """
        pass

    @abstractmethod
    def chip_to_stage(self, chip_coordinate):
        """
        Transforms a coordinate in chip space to stage space.
        """
        pass

    @abstractmethod
    def stage_to_chip(self, stage_coordinate):
        """
        Transforms a coordinate in stage space to chip space.
        """
        pass


class CoordinatePairing(NamedTuple):
    calibration: object
    stage_coordinate: list
    device: object
    chip_coordinate: list


class SinglePointFixation(Transformation):
    """
    Performs a translation based on a fixed single point.
    """

    def __init__(self) -> None:
        self._chip_coordinate = None
        self._stage_coordinate = None
        self._offset = None

    def __str__(self) -> str:
        if self._offset is None:
            return "No single point fixed"

        return "Stage-Coordinate {} fixed with Chip-Coordinate {}".format(
            self._stage_coordinate, self._chip_coordinate)

    @property
    def is_valid(self):
        """
        Returns True if single point transformation is defined.
        """
        return self._offset is not None

    def update(self, pairing: Type[CoordinatePairing]):
        """
        Updates the offset based on a coordinate pairing.
        """
        if pairing.chip_coordinate is None or pairing.stage_coordinate is None:
            raise ValueError("Incomplete Pairing")

        self._chip_coordinate = np.array(pairing.chip_coordinate)
        self._stage_coordinate = np.array(pairing.stage_coordinate)

        self._offset = self._stage_coordinate - self._chip_coordinate

    def chip_to_stage(self, chip_coordinate):
        """
        Translates chip coordinate to stage coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return np.array(chip_coordinate) + self._offset

    def stage_to_chip(self, stage_coordinate):
        """
        Translates stage coordinate to chip coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return np.array(stage_coordinate) - self._offset
