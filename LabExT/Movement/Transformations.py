#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from abc import ABC, abstractmethod, abstractproperty
from enum import Enum
from typing import NamedTuple, Type
from LabExT import rmsd
import numpy as np
from scipy.spatial.transform import Rotation


def make_3d_coordinate(coordinate, set_z=0):
    """
    Returns a always a 3D coordinate as np.array.
    Adds a zero.
    """
    coordinate = np.array(coordinate)
    if coordinate.shape == (2,) or coordinate.shape == (3,):
        return np.append(
            coordinate,
            set_z) if coordinate.shape == (
            2,
        ) else coordinate
    else:
        raise ValueError(
            "Invalid Coordinate: Please pass a 2d or 3d coordinate")


class Transformation(ABC):
    """
    Abstract interface for transformations.
    """

    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractproperty
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

        self._chip_coordinate = make_3d_coordinate(pairing.chip_coordinate)
        self._stage_coordinate = make_3d_coordinate(pairing.stage_coordinate)

        self._offset = self._stage_coordinate - self._chip_coordinate

    def chip_to_stage(self, chip_coordinate):
        """
        Translates chip coordinate to stage coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return make_3d_coordinate(chip_coordinate) + self._offset

    def stage_to_chip(self, stage_coordinate):
        """
        Translates stage coordinate to chip coordinate
        """
        if not self.is_valid:
            raise RuntimeError("Cannot translate with invalid fixation. ")

        return make_3d_coordinate(stage_coordinate) - self._offset


class Dimension(Enum):
    TWO = 2
    THREE = 3


class KabschRotation(Transformation):
    """
    Estimate a rotation to optimally align two sets of vectors.

    Find a rotation to align a set of stage coordinates with a set of chip coordinates.
    For more information see Kabsch Algorithm.

    We require 2 points for a 2D transformation (z-values are zero) and 3 points for a 3D transformation.
    More points are possible and may increase the accuracy.
    """

    MIN_POINTS = {
        Dimension.TWO: 2,
        Dimension.THREE: 3
    }

    def __init__(self) -> None:
        self.pairings = []

        self._rotation_dimension = Dimension.THREE

        self._chip_coordinates = np.empty((0, 3), float)
        self._stage_coordinates = np.empty((0, 3), float)

        self._rotation = None
        self._rmsd = None

        self._chip_offset = None
        self._stage_offset = None

    def __str__(self) -> str:
        if not self.is_valid:
            return "No valid rotation defined ({}/{} Points set)".format(
                len(self.pairings), self.MIN_POINTS[self._rotation_dimension])

        return "Rotation defined with {} Points".format(len(self.pairings))

    @property
    def is_valid(self) -> bool:
        """
        Returns True if Kabsch transformation is defined.
        """
        return len(self.pairings) >= self.MIN_POINTS[self._rotation_dimension]

    @property
    def rmsd(self):
        """
        Returns RMSD of rotation
        """
        return self._rmsd if self.is_valid else "-"

    @property
    def is_3D(self):
        return self._rotation_dimension == Dimension.THREE

    @property
    def is_2D(self):
        return self._rotation_dimension == Dimension.TWO

    def change_rotation_dimension(self, dimension: Dimension) -> None:
        """
        Changes rotation dimension to specified dimension.
        """
        if dimension not in Dimension:
            raise ValueError(
                "Cannot change dimension: Invalid dimension {}".format(dimension))

        self._rotation_dimension = dimension
        self._recalculate_rotation()

    def update(self, pair: Type[CoordinatePairing]) -> None:
        """
        Updates the transformation by adding a new pairing.
        """
        if not isinstance(pair, CoordinatePairing) or not all(pair):
            raise ValueError(
                "Use a complete CoordinatePairing object to update the rotation. ")

        if any(p.device == pair.device for p in self.pairings):
            raise ValueError(
                "A pairing with this device has already been saved.")

        self.pairings.append(pair)

        self._chip_coordinates = np.append(
            self._chip_coordinates,
            [make_3d_coordinate(pair.chip_coordinate)],
            axis=0)
        self._stage_coordinates = np.append(
            self._stage_coordinates,
            [make_3d_coordinate(pair.stage_coordinate)],
            axis=0)

        self._recalculate_rotation()

    def chip_to_stage(self, chip_coordinate):
        """
        Transforms a position in chip coordinates to stage coordinates
        """
        if not self.is_valid:
            raise RuntimeError("Cannot rotation with invalid transformation. ")

        chip_coordinate = make_3d_coordinate(chip_coordinate)

        if self.is_3D:
            return self._rotation.apply(
                chip_coordinate - self._chip_offset,
                inverse=True) + self._stage_offset

        if self.is_2D:
            return np.append(self._rotation.inv().as_matrix()[:2, :2].dot(
                (chip_coordinate - self._chip_offset)[:2]) + self._stage_offset[:2], chip_coordinate[2])

        return chip_coordinate

    def stage_to_chip(self, stage_coordinate):
        """
        Transforms a position in stage coordinates to chip coordinates
        """
        if not self.is_valid:
            raise RuntimeError("Cannot rotation with invalid transformation. ")

        stage_coordinate = make_3d_coordinate(stage_coordinate)

        if self.is_3D:
            return self._rotation.apply(
                stage_coordinate - self._stage_offset) + self._chip_offset

        if self.is_2D:
            return np.append(self._rotation.as_matrix()[:2, :2].dot(
                (stage_coordinate - self._stage_offset)[:2]) + self._chip_offset[:2], stage_coordinate[2])

        return stage_coordinate

    #
    #   Helper
    #

    def _recalculate_rotation(self):
        """
        TODO
        """
        if self._chip_coordinates.size == 0 or self._stage_coordinates.size == 0:
            return

        # Replace z coordinate with zeros for 2d transformation
        chip_coordinates = self._chip_coordinates if self.is_3D else np.append(
            self._chip_coordinates[:, :2], np.zeros((len(self.pairings), 1)), axis=1)
        stage_coordinates = self._stage_coordinates if self.is_3D else np.append(
            self._stage_coordinates[:, :2], np.zeros((len(self.pairings), 1)), axis=1)

        # Calculate mean for each set
        self._chip_offset = chip_coordinates.mean(axis=0)
        self._stage_offset = stage_coordinates.mean(axis=0)

        # Create Rotation with centered vectors
        self._rotation, self._rmsd = Rotation.align_vectors(
            (chip_coordinates - self._chip_offset),
            (stage_coordinates - self._stage_offset))

        self._ref_matrix = rmsd.kabsch(
            (chip_coordinates - self._chip_offset),
            (stage_coordinates - self._stage_offset))
