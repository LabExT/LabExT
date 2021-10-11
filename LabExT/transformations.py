#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

import numpy as np

from LabExT import rmsd


class Transformation2D:
    """This class performs a 2D coordinate transformation, taking into account
    rotation and translation using the rmsd plugin.
    """

    def __init__(self, mover):
        """Constructor. Initialises local variables.

        Parameters
        ----------
        mover : Mover
            The Mover, which called the transformation.
        """
        self.logger = logging.getLogger()

        self._mover = mover
        self._matrix = None
        self._chip_offset = None
        self._stage_offset = None

    def chip_to_stage_coord(self, chip_pos):
        """
        Transforms a position in chip coordinates to stage coordinates
        """
        position_chip = np.array([chip_pos[0], chip_pos[1]])
        # we translate the position to the origin
        position_stage = position_chip - self._chip_offset

        # we rotate
        position_stage = np.dot(position_stage, self._matrix)
        # we add the stage offset to go back to the stages' origin
        position_stage = position_stage + self._stage_offset

        self.logger.debug('Transformation2D: stages position:' + str(position_stage))

        return position_stage

    def stage_to_chip_coord(self, stage_pos):
        """
        Transforms a position in stage coordinates to chip coordinates
        """
        position_stage = np.array(stage_pos)

        matrix_inverse = np.linalg.inv(self._matrix)

        position_chip = np.dot((position_stage-self._stage_offset), matrix_inverse)

        position_chip = position_chip + self._chip_offset

        return position_chip

    def trafo_algorithm(self, p_1_stage, p_1_chip, p_2_stage, p_2_chip):
        self._stage_coords = np.array([p_1_stage, p_2_stage])
        self._chip_coords = np.array([p_1_chip, p_2_chip])

        # translate coordinates to origin
        self._stage_offset = rmsd.centroid(self._stage_coords)
        self._stage_coords = self._stage_coords - self._stage_offset
        self._chip_offset = rmsd.centroid(self._chip_coords)
        self._chip_coords = self._chip_coords - self._chip_offset

        # calculate rotation matrix using kabsch algorithm
        self._matrix = rmsd.kabsch(self._chip_coords, self._stage_coords)

        # rotate chip_coordinates
        self._chip_coords = np.dot(self._chip_coords, self._matrix)

        self.logger.info('Transformation2D: Stage coord: \n' + str(self._stage_coords) +
                         '\n New chip coord: \n' + str(self._chip_coords) + '\n')
