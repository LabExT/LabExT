#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from abc import ABC, abstractmethod
from typing import List, NamedTuple, Type
import numpy as np
from scipy.spatial.transform import Rotation


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


class KabschRotation(Transformation):
    """
    Estimate a rotation to optimally align two sets of vectors.

    Find a rotation between a chip frame and stage frame which best aligns a set of vectors a and b observed in these frames.
    The following loss function is minimized to solve for the rotation matrix:

    L(C) = 1/2 * \sum_{i=0}^n w_i ||a_i - Cb_i||^2
 
    where w_i are the weights corresponding to each vector.
    The rotation is estimated with Kabsch algorithm.

    a = vector of chip coordinates
    b = vector of stage coordinates

    We are not using weights right now (w_i = 1 for all i)
    """

    MIN_NUMBER_OF_POINTS_2D = 2
    MIN_NUMBER_OF_POINTS_3D = 3

    def __init__(self) -> None:
        self.pairings = []

        self._chip_coordinates = np.empty((0,3), float)
        self._stage_coordinates = np.empty((0,3), float)

        self._rotation = None
        self._rmsd = None

        self._chip_offset = None
        self._stage_offset = None

    def __str__(self) -> str:
        if not self.is_valid:
            return "No rotation is defined"

        return "Rotation defined with Root-Squard-Mean-Distance: {}".format(self._rmsd)


    @property
    def is_valid(self):
        """
        Returns True if Kabsch transformation is defined.
        """
        return self._rotation is not None

    
    def update(self, pairing: Type[CoordinatePairing], is_3d_rotation=True):
        """
        Updates the transformation by adding a new pairing.
        """
        if not isinstance(pairing, CoordinatePairing):
            raise ValueError("Use a CoordinatePairing object to update the rotation. ")

        if pairing.chip_coordinate is None or pairing.stage_coordinate is None:
            raise ValueError("Incomplete Pairing")

        if pairing.device is None:
            raise ValueError("Your Pairing must contain a device, which was used to create it.")

        if any(p.device == pairing.device for p in self.pairings):
            raise ValueError("A pairing with this device has already been saved.")

        self.pairings.append(pairing)

        self._chip_coordinates = np.append(
            self._chip_coordinates, 
            np.array([self._normalize_vector(pairing.chip_coordinate)]),
            axis=0)
        self._stage_coordinates = np.append(
            self._stage_coordinates, 
            np.array([self._normalize_vector(pairing.stage_coordinate)]),
            axis=0)

        min_number_of_points = self.MIN_NUMBER_OF_POINTS_3D if is_3d_rotation else self.MIN_NUMBER_OF_POINTS_2D
        if len(self.pairings) >= min_number_of_points:
            self._chip_offset = self._chip_coordinates.mean(axis=0)
            self._stage_offset = self._stage_coordinates.mean(axis=0)

            self._rotation, self._rmsd = Rotation.align_vectors(
                (self._chip_coordinates - self._chip_offset),
                (self._stage_coordinates - self._stage_offset))

    def _normalize_vector(self, input):
        """
        Checks if vector is 2 or 3 dimensional. If it is 2, it will expand it to a 3D vecor by adding
        a zero for z.
        """
        vector = np.array(input)
        if vector.shape != (2,) and vector.shape != (3,):
            raise ValueError("Coordinates must be 2 or 3 dimensional vectors. ")

        if vector.shape == (2,):
            vector = np.append(vector, 0)

        return vector


    def chip_to_stage(self, chip_coordinate):
        """
        Transforms a position in chip coordinates to stage coordinates
        """



    def stage_to_chip(self, stage_coordinate):
        """
        Transforms a position in stage coordinates to chip coordinates
        """
       
