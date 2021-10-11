#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import math

import numpy as np
from collision import Circle, Poly, tests
from collision import Vector


def angle_between(v1, v2):
    """ Returns the angle in degrees between vectors 'v1' and 'v2'
    """
    return math.degrees(math.asin((v1[0] * v2[1] - v1[1] * v2[0]) / (np.linalg.norm(v1) * np.linalg.norm(v2))))


class StageTrajectory:
    """
    Handles everything related to planing trajectories, in order to provide collision free operation of the stages

    Attributes
    safe_distance : int
        the minimum safety distance between the stages [um]
    stage_arm_diameter : int
        thickness of the stage arm (5mm)
    stage_arm_length : int
        lenght of the stage arm; it can be some arbitrary large number, but needs to be at least as large
        as the real arm length
    safe_tip_distance : int
        another safety distance; used for the case when a stage can't move along the direct path to the target,
        but needs to take a detour
    """

    def __init__(self):
        self.safe_distance = 150  # [um] because fiber diameter is 125um
        self.stage_arm_diameter = 5e3  # 5mm
        self.stage_arm_length = 8e4  # 8cm (just some arbitrary large number
        # which is certainly bigger than the real arm length)
        self.safe_tip_distance = 300  # [um]

        self.logger = logging.getLogger()

    def trajectory_2d_object(self, curr_pos, target_pos):
        """Creates a polygon representation of the stage trajectory, considering that the trajectory
        is not necessarily just a straight line if one positioner (e.g. x-axis) has to travel a longer distance than
        the other positioner (e.g. y-axis)

        :param curr_pos: current position of the stage tip in chip coordinates
        :param target_pos: target position in chip coordinates
        :return trajectory: polygon representation of trajectory (returns 0 if current and target position are equal)
        """
        direct_vec = target_pos - curr_pos
        if np.linalg.norm(direct_vec) == 0:
            return 0
        min_value = min(abs(direct_vec))

        # if the following statement is true we know that the trajectory is parallel to the x-or y-axis
        # therefore we just have one vector
        if min_value == 0:
            vec1 = direct_vec
            vec2 = 0
        else:
            # in the other case the trajectory is divided into to vectors
            # vec1 represents the first part of the movement of the stage. This corresponds
            # to the phase where it moves on a line which lies 45 degrees to the x-axis.
            # This comes from the fact that it moves with the same speed along both axes simultaneously.
            vec1 = np.array([np.sign(direct_vec[0]) * min_value, np.sign(direct_vec[1]) * min_value])
            # Once the movement along one of the axis has finished, the remaining trajectory is a line
            # parallel to either the x-or y-axis
            vec2 = direct_vec - vec1

        # if by coincidence the x and y components of direct_vec are the same,
        # there is no vec2 and the trajectory is just a straight line
        if np.linalg.norm(vec2) == 0:
            vec1_rot = np.array([vec1[1], -vec1[0]])
            vec1_rot = vec1_rot / np.linalg.norm(vec1_rot) * (self.safe_distance / 2)
            vec_p1 = vec1_rot
            vec_p2 = vec1_rot + vec1 + vec1 / np.linalg.norm(vec1) * self.safe_distance
            vec_p3 = -vec1_rot + vec1 + vec1 / np.linalg.norm(vec1) * self.safe_distance
            vec_p4 = -vec1_rot

            p1 = Vector(vec_p1[0], vec_p1[1])
            p2 = Vector(vec_p2[0], vec_p2[1])
            p3 = Vector(vec_p3[0], vec_p3[1])
            p4 = Vector(vec_p4[0], vec_p4[1])

            # creates the trajectory represented by a polygon defined by the points p1 to p4
            trajectory = Poly(Vector(curr_pos[0], curr_pos[1]), [p1, p2, p3, p4])
            return trajectory

        angle = angle_between(vec1, vec2)

        add_length = self.safe_distance * np.tan(np.deg2rad(angle / 2)) * 0.5

        add_vec1 = vec1 / np.linalg.norm(vec1) * add_length
        add_vec2 = vec2 / np.linalg.norm(vec2) * add_length

        vec1_rot = np.array([vec1[1], -vec1[0]])
        vec1_rot = vec1_rot / np.linalg.norm(vec1_rot) * (self.safe_distance / 2)

        # calculate the points which make up the polygon
        vec_p1 = vec1_rot
        vec_p2 = vec1_rot + vec1 + add_vec1
        vec_p3 = vec1_rot + vec1 + add_vec1 + vec2 + add_vec2 + vec2 / np.linalg.norm(vec2) * self.safe_distance
        vec_p4 = -vec1_rot + vec1 - add_vec1 + vec2 - add_vec2 + vec2 / np.linalg.norm(vec2) * self.safe_distance
        vec_p5 = -vec1_rot + vec1 - add_vec1
        vec_p6 = -vec1_rot

        p1 = Vector(vec_p1[0], vec_p1[1])
        p2 = Vector(vec_p2[0], vec_p2[1])
        p3 = Vector(vec_p3[0], vec_p3[1])
        p4 = Vector(vec_p4[0], vec_p4[1])
        p5 = Vector(vec_p5[0], vec_p5[1])
        p6 = Vector(vec_p6[0], vec_p6[1])

        # create the polygon with the previously calculated points
        trajectory = Poly(Vector(curr_pos[0], curr_pos[1]), [p1, p2, p3, p4, p5, p6])
        return trajectory

    def stage_2d_object(self, pos, direction):
        """ Creates a polygon representation of the stage

        :param pos: position of the tip of the stage in chip coordinates
        :param direction: a vector which contains the information how the stage is aligned with respect to the chip
                            (the chip can be rotated and therefore the x-axis of the chip is not necessarily pointing
                            in the same direction as the x-axis of the stage)
        :return stage: polygon representation of chip
        """
        tip_length = self.stage_arm_diameter / 2  # [um] = 2.5mm

        direction = direction / np.linalg.norm(direction)
        direction_rot = np.array([direction[1], -direction[0]])

        # calculate points which make up the polygon
        p1 = Vector(0, 0)
        tmp = tip_length * direction + tip_length * direction_rot
        p2 = Vector(tmp[0], tmp[1])
        tmp = self.stage_arm_length * direction + tip_length * direction_rot
        p3 = Vector(tmp[0], tmp[1])
        tmp = self.stage_arm_length * direction - tip_length * direction_rot
        p4 = Vector(tmp[0], tmp[1])
        tmp = tip_length * direction - tip_length * direction_rot
        p5 = Vector(tmp[0], tmp[1])

        # create the polygon with the previously calculated points
        stage = Poly(Vector(pos[0], pos[1]), [p1, p2, p3, p4, p5])
        return stage

    def move_on_safe_trajectory(self, *args):
        """Moves the stages on a safe trajectory to avoid collision

        :param args[0]: left x target position in stage coordinates
        :param args[1]: left y target position in stage coordinates
        :param args[2]: right x target position in stage coordinates
        :param args[3]: right y target position in stage coordinates
        :param args[4]: instance of mover
        :return: True if target points were reached successfully otherwise False

        RuntimeError: ->if left and right target positions are too close to each other
                      ->if it's impossible to reach target positions
        """
        mover = args[4]

        # the position of the two target points in chip coordinates
        target_left_pos = mover._transformer_left.stage_to_chip_coord([args[0], args[1]])
        target_right_pos = mover._transformer_right.stage_to_chip_coord([args[2], args[3]])

        target_left_pos = np.array(target_left_pos)
        target_right_pos = np.array(target_right_pos)

        reached_target_left = False
        reached_target_right = False

        # current position of stages in stage coordinates
        # curr_pos[0] = x position of left stage
        # curr_pos[1] = y position of left stage
        # curr_pos[2] = x position of right stage
        # curr_pos[3] = y position of right stage
        curr_pos = mover.get_absolute_stage_coords()
        # convert current positions to chip coordinate
        curr_left_pos = mover._transformer_left.stage_to_chip_coord([curr_pos[0], curr_pos[1]])
        curr_right_pos = mover._transformer_right.stage_to_chip_coord([curr_pos[2], curr_pos[3]])

        # these two vectors contain the information how the two stages are aligned with respect to the chip coordinates
        left_direction = mover._transformer_left.stage_to_chip_coord([curr_pos[0] - 5000, curr_pos[1]]) - curr_left_pos
        right_direction = mover._transformer_right.stage_to_chip_coord([curr_pos[2] - 5000, curr_pos[3]]) - curr_right_pos

        # check if the two target points are too close to each other/identical (with euclidean distance)
        if np.linalg.norm(target_left_pos - target_right_pos) < self.safe_distance:
            msg = 'Two target points are too close to each other'
            self.logger.error(msg)
            raise RuntimeError(msg)

        # create the 2D projection of the stages onto the chip at their final position
        left_stage_end = self.stage_2d_object(target_left_pos, left_direction)
        right_stage_end = self.stage_2d_object(target_right_pos, right_direction)

        # create circles representing the target points with appropriate radius
        left_target = Circle(Vector(target_left_pos[0], target_left_pos[1]), self.safe_distance / 2)
        right_target = Circle(Vector(target_right_pos[0], target_right_pos[1]), self.safe_distance / 2)

        # check if each end position has enough distance to each end stage poly
        if tests.collide(left_stage_end, right_target) or tests.collide(right_stage_end, left_target):
            msg = 'At least one stage and the other end point collides'
            self.logger.error(msg)
            raise RuntimeError(msg)

        # check if end stage polys are not intersecting
        if tests.collide(left_stage_end, right_stage_end):
            msg = 'Stages would be colliding at end point. Refusing to move.'
            self.logger.error(msg)
            raise RuntimeError(msg)

        for i in range(5):

            # --------------------------------------------------------------
            # case1: both stages haven't reached their target positions yet
            # --------------------------------------------------------------
            if not reached_target_left and not reached_target_right:
                # update the current position
                curr_pos = mover.get_absolute_stage_coords()
                curr_left_pos = mover._transformer_left.stage_to_chip_coord([curr_pos[0], curr_pos[1]])
                curr_right_pos = mover._transformer_right.stage_to_chip_coord([curr_pos[2], curr_pos[3]])

                # update the 2D projection of the stages onto the chip (because it depends on the current position)
                left_stage = self.stage_2d_object(curr_left_pos, left_direction)
                right_stage = self.stage_2d_object(curr_right_pos, right_direction)

                # create two polygons representing the trajectories of the left and right stage
                left_stage_trajectory = self.trajectory_2d_object(curr_left_pos, target_left_pos)
                right_stage_trajectory = self.trajectory_2d_object(curr_right_pos, target_right_pos)

                if tests.collide(left_stage, right_stage_trajectory):
                    # since the left stage and the right stage trajectory overlap, check if right stage and
                    # left stage trajectory overlap
                    if tests.collide(right_stage, left_stage_trajectory):

                        # find out if stage x-positions are overlapping
                        s = right_direction
                        v = curr_left_pos - curr_right_pos
                        c_left_onto_right = np.dot(v, s)

                        if c_left_onto_right + self.safe_tip_distance > 0:
                            # current position of the right stage in the coordinate system of the left stage
                            curr_right_pos_in_left_stage_coord = mover._transformer_left.chip_to_stage_coord(
                                curr_right_pos)

                            # untangle the situation by moving left stage back far enough
                            new_target = [curr_right_pos_in_left_stage_coord[0] - self.safe_tip_distance * 2, curr_pos[1]]
                            mover.left_stage.move_absolute(new_target)

                            # update the current position
                            curr_pos = mover.get_absolute_stage_coords()
                            curr_left_pos = mover._transformer_left.stage_to_chip_coord([curr_pos[0], curr_pos[1]])

                        # set in-between target point for left stage at target y position but current x position
                        # this results in the left stage being on the correct y position
                        tmp_target = np.array([curr_left_pos[0], target_left_pos[1]])
                        left_stage_trajectory = self.trajectory_2d_object(curr_left_pos, tmp_target)
                        if tests.collide(left_stage_trajectory, right_stage):
                            msg = 'Left stage trajectory and right stage still overlapping. ' + \
                                  'According to Imre, this should never happen during algorithm execution.'
                            self.logger.error(msg)
                            raise RuntimeError(msg)
                        tmp_target = mover._transformer_left.chip_to_stage_coord(tmp_target)
                        mover.left_stage.move_absolute(tmp_target)
                        # start anew
                        continue

                    # since there is no collision between right stage and left stage trajectory, the left stage
                    # can move to it's target position
                    mover.left_stage.move_absolute([args[0], args[1]])
                    reached_target_left = True
                    # update current position
                    continue

                # since there is no collision between the right stage trajectory and left stage, the right stage
                # can move to it's target
                mover.right_stage.move_absolute([args[2], args[3]])
                reached_target_right = True
                continue

            # ---------------------------------------------------------------------------
            # case2: right stage hasn't reached the target yet but left stage already has
            # ---------------------------------------------------------------------------
            if not reached_target_right and reached_target_left:

                # update the current position
                curr_pos = mover.get_absolute_stage_coords()
                curr_left_pos = mover._transformer_left.stage_to_chip_coord([curr_pos[0], curr_pos[1]])
                curr_right_pos = mover._transformer_right.stage_to_chip_coord([curr_pos[2], curr_pos[3]])

                # update the 2D projection of the stages onto the chip (because it depends on the current position)
                left_stage = self.stage_2d_object(curr_left_pos, left_direction)

                # create polygon representing the right stage trajectory
                right_stage_trajectory = self.trajectory_2d_object(curr_right_pos, target_right_pos)

                if tests.collide(right_stage_trajectory, left_stage):

                    # find out if stage x-positions are overlapping
                    s = left_direction
                    v = curr_right_pos - curr_left_pos
                    c_right_onto_left = np.dot(v, s)

                    if c_right_onto_left + self.safe_tip_distance > 0:
                        # current position of the left stage in the coordinates of the right stage
                        curr_left_pos_in_right_stage_coord = mover._transformer_right.chip_to_stage_coord(curr_left_pos)

                        new_target = [curr_left_pos_in_right_stage_coord[0] + self.safe_tip_distance * 2, curr_pos[3]]
                        mover.right_stage.move_absolute(new_target)

                        # update current position
                        continue

                    # set in-between target point for right stage at target y position but current x position
                    # this results in the right stage being on the correct y position
                    tmp_target = np.array([curr_right_pos[0], target_right_pos[1]])
                    right_stage_trajectory = self.trajectory_2d_object(curr_right_pos, tmp_target)
                    if tests.collide(right_stage_trajectory, left_stage):
                        msg = 'Left stage trajectory and right stage still overlapping. ' + \
                                  'According to Imre, this should never happen during algorithm execution.'
                        self.logger.error(msg)
                        raise RuntimeError(msg)
                    tmp_target = mover._transformer_right.chip_to_stage_coord(tmp_target)
                    mover.right_stage.move_absolute(tmp_target)
                    # update current position
                    continue

                mover.right_stage.move_absolute([args[2], args[3]])
                reached_target_right = True
                # update current position
                continue

            # ----------------------------------------------------------------------------
            # case3: left stage hasn't reached the target yet, but right stage already has
            # ----------------------------------------------------------------------------
            if not reached_target_left and reached_target_right:

                # update the current position
                curr_pos = mover.get_absolute_stage_coords()
                curr_left_pos = mover._transformer_left.stage_to_chip_coord([curr_pos[0], curr_pos[1]])
                curr_right_pos = mover._transformer_right.stage_to_chip_coord([curr_pos[2], curr_pos[3]])

                # update the 2D projection of the stages onto the chip (because it depends on the current position)
                right_stage = self.stage_2d_object(curr_right_pos, right_direction)

                # create polygon representing the left stage trajectory
                left_stage_trajectory = self.trajectory_2d_object(curr_left_pos, target_left_pos)

                if tests.collide(right_stage, left_stage_trajectory):

                    # find out if stage x-positions are overlapping
                    s = right_direction
                    v = curr_left_pos - curr_right_pos
                    c_left_onto_right = np.dot(v, s)

                    if c_left_onto_right + self.safe_tip_distance > 0:
                        # current position of the right stage in left stage coordinates
                        curr_right_pos_in_left_stage_coord = mover._transformer_left.chip_to_stage_coord(curr_right_pos)
                        new_target = [curr_right_pos_in_left_stage_coord[0] - self.safe_tip_distance * 2, curr_pos[1]]
                        mover.left_stage.move_absolute(new_target)

                        # update current position
                        continue

                    # set in-between target point for left stage at target y position but current x position
                    # this results in the left stage being on the correct y position
                    tmp_target = np.array([curr_left_pos[0], target_left_pos[1]])
                    left_stage_trajectory = self.trajectory_2d_object(curr_left_pos, tmp_target)
                    if tests.collide(left_stage_trajectory, right_stage):
                        msg = 'Left stage trajectory and right stage still overlapping. ' + \
                                  'According to Imre, this should never happen during algorithm execution.'
                        self.logger.error(msg)
                        raise RuntimeError(msg)
                    tmp_target = mover._transformer_left.chip_to_stage_coord(tmp_target)
                    mover.left_stage.move_absolute(tmp_target)
                    # update current position
                    continue

                mover.left_stage.move_absolute([args[0], args[1]])
                reached_target_left = True

            # ------------------------------------------------------
            # case4: both stages have reached their target positions
            # ------------------------------------------------------
            if reached_target_left and reached_target_right:
                return

        raise RuntimeError("Did not reach targets at end of safe trajectory algorithm.")
