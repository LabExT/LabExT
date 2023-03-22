#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY;
for details see LICENSE file.
"""
from __future__ import annotations
import logging

from typing import TYPE_CHECKING, Any, NamedTuple, Tuple, Type
from abc import ABC, abstractclassmethod, abstractmethod, abstractproperty
from functools import wraps
import numpy as np

from LabExT.Movement.config import Axis, Direction

if TYPE_CHECKING:
    from LabExT.Movement.Calibration import Calibration
    from LabExT.Wafer.Device import Device
    from LabExT.Wafer.Chip import Chip


logger = logging.getLogger()


class Coordinate(ABC):
    """
    Abstract base class of a coordinate with X, Y and Z values.

    The base class cannot be initialised directly.
    """
    @classmethod
    def from_list(cls, list: list) -> Type[Coordinate]:
        """
        Returns a new coordinate, created from a list.
        """
        return cls(*list[:3])

    @classmethod
    def from_numpy(cls, array: np.ndarray) -> Type[Coordinate]:
        """
        Returns a new coordinate created from a one-dimensional numpy array.
        """
        if array.ndim != 1:
            raise ValueError("The given array is not a 1D-Array.")

        return cls(*array.tolist()[:3])

    @abstractmethod
    def __init__(self, x=0, y=0, z=0) -> None:
        """
        Constructor.
        """
        self.x = x
        self.y = y
        self.z = z

        self.type: Coordinate = type(self)

    def __str__(self) -> str:
        """
        Prints coordinate rounded to 2 digits
        """
        return "[{:.2f}, {:.2f}, {:.2f}]".format(self.x, self.y, self.z)

    def __add__(self, other) -> Type[Coordinate]:
        """
        Adds two coordinates.
        Returns a new coordinate of the same type.

        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, self.type):
            raise TypeError(
                "Invalid types: {} and {} cannot be added.".format(
                    self.type, type(other)))

        return self.type.from_numpy(self.to_numpy() + other.to_numpy())

    def __sub__(self, other) -> Type[Coordinate]:
        """
        Subtracts two coordinates.
        Returns a new coordinate of the same type.

        Raises TypeError if both coordinates are not the same type.
        """
        if not isinstance(other, self.type):
            raise TypeError(
                "Invalid types: {} and {} cannot be added.".format(
                    self.type, type(other)))

        return self.type.from_numpy(self.to_numpy() - other.to_numpy())

    def __eq__(self, o: object) -> bool:
        """
        Compares two coordinates.

        Two coordinates are equal, if they are of the same type and all
        values are equal.
        """
        if not isinstance(o, self.type):
            return False

        return o.x == self.x and o.y == self.y and o.z == self.z

    def __mul__(self, scalar) -> Type[Coordinate]:
        """
        Multiplies the coordinate by a scalar.
        Returns a new coordinate of the same type.
        """
        return self.type.from_numpy(self.to_numpy() * scalar)

    @property
    def is_zero(self) -> bool:
        """
        Returns True if the coordinate is equal to [0,0,0]
        """
        return np.all(self.to_numpy() == 0)

    def to_list(self) -> list:
        """
        Returns the coordinate as a list.
        """
        return [self.x, self.y, self.z]

    def to_numpy(self) -> np.ndarray:
        """
        Returns the coordinate as a numpy array.
        """
        return np.array(self.to_list())


class StageCoordinate(Coordinate):
    """
    A Coordinate in the coordinate system of a stage.
    """

    def __init__(self, x=0, y=0, z=0) -> None:
        super().__init__(x, y, z)


class ChipCoordinate(Coordinate):
    """
    A Coordinate in the coordinate system of a chip.
    """

    def __init__(self, x=0, y=0, z=0) -> None:
        super().__init__(x, y, z)


class CoordinatePairing(NamedTuple):
    calibration: Type[Calibration]
    stage_coordinate: Type[StageCoordinate]
    device: Type[Device]
    chip_coordinate: Type[ChipCoordinate]

    @classmethod
    def load(
        cls,
        pairing: dict,
        device: Type[Device] = None,
        calibration: Type[Calibration] = None
    ) -> Type[CoordinatePairing]:
        """
        Creates a new coordinate pairing for given data.

        Parameters
        ----------
        pairing : dict
            Pairing consisting of stage and chip coordinate
        device : Device = None
            Devices associated with the pairing
        calibration : Calibration
            Calibration associated with the pairing

        Raises
        ------
        ValueError
            If pairing is not well-formed.

        Returns
        -------
        CoordinatePairing based on the given data
        """
        if "stage_coordinate" not in pairing or "chip_coordinate" not in pairing:
            raise ValueError(
                f"Cannot create coordinate paring. Stage and Chip coordinate are required.")

        return cls(
            calibration=calibration,
            stage_coordinate=StageCoordinate.from_list(
                pairing["stage_coordinate"]),
            device=device,
            chip_coordinate=StageCoordinate.from_list(
                pairing["chip_coordinate"]))

    def dump(self, include_device_id: bool = True) -> dict:
        """
        Returns the pairing as dict.

        Includes device ID if required.
        """
        pairing = {
            "stage_coordinate": self.stage_coordinate.to_list(),
            "chip_coordinate": self.chip_coordinate.to_list()}

        if not include_device_id:
            return pairing

        if self.device:
            pairing["device_id"] = self.device.id
        return pairing


class Transformation(ABC):
    """
    Abstract interface for transformations.

    The base class cannot be initialised directly.
    """

    @abstractclassmethod
    def load(cls, data: Any, *args, **kwargs) -> Type[Transformation]:
        """
        Creates a new Transformation from data
        """
        pass

    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractproperty
    def is_valid(self) -> bool:
        """
        Returns True if the transformation is valid.
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initializes the transformation.
        """
        pass

    @abstractmethod
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a coordinate in chip space to stage space.
        """
        pass

    @abstractmethod
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a coordinate in stage space to chip space.
        """
        pass

    def dump(self, *args, **kwargs) -> Any:
        """
        Dumps transformation into storable format.
        """
        pass


class TransformationError(RuntimeError):
    pass


def assert_valid_transformation(func):
    """
    Decorator to assert that a transformation is valid.

    Raises
    ------
    TransformationError
        If transformation is not valid.
    """
    @wraps(func)
    def warp(transformation, *args, **kwargs):
        if not transformation.is_valid:
            raise TransformationError(
                "Cannot transform with invalid transformation.")

        return func(transformation, *args, **kwargs)
    return warp


class AxesRotation(Transformation):
    """
    Defines a transformation to rotate a chip coordinate to a stage coordinate.
    This allows relative movements in the chip coordinate system for all stages.

    Functionality:
    If correctly defined, a 3x3 signed permutation matrix is defined.
    - Chip-to-Stage: Given a chip coordinate, this is multiplied on the right by the matrix to obtain a stage coordinate.
    - Stage-to-Chip: Given a stage coordinate, this is multiplied on the right by the inverse matrix to obtain a chip coordinate.
    """

    @classmethod
    def load(cls, mapping: dict) -> Type[AxesRotation]:
        """
        Creates a new axes rotation transformation based on axes mapping.

        Parameters
        ----------
        mapping: Dict[str, (str, str)]
            Mapping from a chip axis to a tuple with direction and stage axis

        Raises
        ------
        TransformationError
            If mapping is not well-formed
            If mapping does not define a valid axes rotation

        Returns
        -------
        AxesRotation
            A valid axes rotation based on the mapping.
        """
        if len(mapping) != 3:
            raise TransformationError(
                "Cannot create axes rotation. "
                f"Axis mapping must consist of 3 mappings, got mapping with {len(mapping)} mappings.")

        axes_rotation = cls()
        for chip_axis, (direction, stage_axis) in mapping.items():
            try:
                chip_axis = Axis[chip_axis]
                direction = Direction[direction]
                stage_axis = Axis[stage_axis]
            except KeyError as err:
                raise TransformationError(
                    f"The parameter is not defined: {err}. "
                    "Make sure to pass a mapping of valid directions and axes.")

            axes_rotation.update(chip_axis, direction, stage_axis)

        if not axes_rotation.is_valid:
            raise TransformationError(
                "Cannot create axes rotation from stored mapping. Mapping is invalid")

        return axes_rotation

    def __init__(self) -> None:
        self.initialize()

    def initialize(self) -> None:
        """
        Initalises the transformation by defining an identity matrix as a rotation matrix
        and defining the associated mapping.
        """
        self.matrix = np.identity(len(Axis))
        self.mapping = {
            Axis.X: (Direction.POSITIVE, Axis.X),
            Axis.Y: (Direction.POSITIVE, Axis.Y),
            Axis.Z: (Direction.POSITIVE, Axis.Z),
        }

    def update(
            self,
            chip_axis: Axis,
            direction: Direction,
            stage_axis: Axis) -> None:
        """
        Updates the axes rotation matrix.
        Replaces the column vector of given chip with signed (direction) i-th unit vector (i is stage)

        Parameters
        ----------
        chip_axis: Axis
            Chip Axis which is to be assigned a Stage Axis.
            The value of the enum defines which column of the rotation matrix is to be changed.
        direction: Direction
            Defines the direction of the assigned stage axis.
        stage_axis: Axis
            Stage Axis which is to be assigned to the Chip Axis.
            The value of the enum defines which row of the rotation matrix is to be changed.

        Raises
        ------
        ValueError
           If stage_axis, chip_axis or direction is not an instance of the required enum.
        """
        if not (isinstance(chip_axis, Axis) and isinstance(stage_axis, Axis)):
            raise ValueError("Unknown axes given for calibration.")

        if not isinstance(direction, Direction):
            raise ValueError("Unknown direction given for calibration.")

        self.mapping[chip_axis] = (direction, stage_axis)

        # Replacing column of chip with signed (direction) i-th unit vector (i
        # is stage)
        self.matrix[:, chip_axis.value] = np.eye(
            1, 3, stage_axis.value) * direction.value

    @property
    def is_valid(self) -> bool:
        """
        Checks if given matrix is a permutation matrix.
        A matrix is a permutation matrix if the sum of each row and column is exactly 1.
        """
        abs_matrix = np.absolute(self.matrix)
        return (
            abs_matrix.sum(
                axis=0) == 1).all() and (
            abs_matrix.sum(
                axis=1) == 1).all()

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Rotates the chip coordinate according to the axes rotation.
        i.e axes_rotation.dot(chip_coordinate)

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the current rotation is not a permutation matrix.
        """
        return StageCoordinate.from_numpy(
            self.matrix.dot(chip_coordinate.to_numpy()))

    @assert_valid_transformation
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Rotates the stage coordinate according to the inverse axes rotation.
        i.e np.linalg.inv(axes_rotation).dot(chip_coordinate)

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the current rotation is not a permutation matrix.
        """
        return ChipCoordinate.from_numpy(
            np.linalg.inv(self.matrix).dot(stage_coordinate.to_numpy()))

    def dump(self) -> dict:
        """
        Returns the axes rotation as an axis mapping in a dict
        """
        return {
            chip_axis.name: (direction.name, stage_axis.name)
            for chip_axis, (direction, stage_axis) in self.mapping.items()}


class SinglePointOffset(Transformation):
    """
    Transformation to convert chip coordinates into stage coordinates and vice versa.

    The transformation requires a correct stage-axis rotation (90 degrees) beforehand, meaning that stage and chip axes are identical after the rotation.

    Functionality:
    - Input is a single stage-chip coordinate pair.
    - The chip coordinate is rotated by the axis rotation to then calculate an offset between the rotated chip coordinate and the stage coordinate. This offset is stored.
    - Stage-To-Chip: The offset is added to the given stage coordinate. The sum is then rotated to a chip coordinate.
    - Chip-To-Stage: The give chip coordinate is rotated into the stage coordinate system and then the offset is subtracted.

    Note: The transformation assumes that the stage and chip axes are parallel. This is not the case in reality, so this transformation is only an approximation.
    """

    @classmethod
    def load(
        cls,
        pairing: Any,
        chip: Type[Chip],
        axes_rotation: Type[AxesRotation]
    ) -> Type[SinglePointOffset]:
        """
        Creates a new single point transformation based on pairing.

        Parameters
        ----------
        pairing : dict
            pairing for stage and chip coordinate
        axes_rotation : AxesRotation
            axes rotation associated with the transformation
        chip : Chip
            chip instance associated with this transformation

        Raises
        ------
        TransformationError
            If pairing is not well-formed
            If pairing does not define a valid transformation

        Returns
        -------
        SinglePointOffset
            A valid single point transformation based on the pairing.
        """
        _device_id = pairing.get("device_id")
        device = chip.devices.get(_device_id)
        if device is None:
            raise TransformationError(
                f"Could not find Device with ID {_device_id} for given chip {chip}")

        try:
            pairing = CoordinatePairing.load(pairing, device=device)
        except Exception as err:
            raise TransformationError(
                f"Could not create pairing for {pairing}: {err}")

        transformation = cls(axes_rotation)
        transformation.update(pairing)

        if not transformation.is_valid:
            raise TransformationError(
                "Cannot create single point offset from stored pairing. Pairing is invalid")

        return transformation

    def __init__(self, axes_rotation: Type[AxesRotation]) -> None:
        self.axes_rotation: Type[AxesRotation] = axes_rotation

        if not self.axes_rotation.is_valid:
            raise RuntimeError("The given axes rotation is invalid.")

        self.initialize()

    def initialize(self):
        """
        Initalises the transformation by unsetting all coordinates and offsets.
        """
        self.pairing = None
        self.stage_offset: Type[StageCoordinate] = None

    def __str__(self) -> str:
        if self.stage_offset is None:
            return "No single point fixed"

        return "Stage-Coordinate {} fixed with Chip-Coordinate {}".format(
            self.pairing.stage_coordinate, self.pairing.chip_coordinate)

    @property
    def is_valid(self):
        """
        Returns True if single point transformation is defined, i.e. a offset is defined.
        """
        return self.stage_offset is not None and self.axes_rotation.is_valid

    def update(self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the offset based on a coordinate pairing.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate

        Raises
        ------
        ValueError
           If pairing is incomplete, i.e. stage coordinate or chip coordinate is missing.
        """
        if pairing.chip_coordinate is None or pairing.stage_coordinate is None:
            raise ValueError("Incomplete Pairing")

        self.pairing = pairing
        self.stage_offset = self.axes_rotation.chip_to_stage(
            pairing.chip_coordinate) - pairing.stage_coordinate

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a chip coordinate into a stage coordinate.
        Rotates the given chip coordinate to a stage cooridnate and subtracts the stage offset.

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the offset is not defined.
        """
        return self.axes_rotation.chip_to_stage(
            chip_coordinate) - self.stage_offset

    @assert_valid_transformation
    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a stage coordinate into a chip coordinate.
        Adds the stage offset to the given stage coordinate and rotates the result to a chip coordinate.

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid, i.e. the offset is not defined.
        """
        return self.axes_rotation.stage_to_chip(
            stage_coordinate + self.stage_offset)

    def dump(self) -> dict:
        """
        Returns the single point transformation as pairing.
        """
        if not self.pairing:
            return {}

        return self.pairing.dump(include_device_id=True)


class KabschRotation(Transformation):
    """
    Estimate a rotation to optimally align two sets of vectors.
    Find a rotation to align a set of stage coordinates with a set of chip coordinates.
    For more information see Kabsch Algorithm.
    We require 3 points for a 3D transformation.
    More points are possible and may increase the accuracy.
    """

    MIN_POINTS = 3

    @classmethod
    def load(
        cls,
        pairings: list,
        chip: Type[Chip],
        axes_rotation: Type[KabschRotation]
    ) -> Type[Transformation]:
        """
        Creates a new kabsch rotation based on pairings.

        Parameters
        ----------
        pairings : list
            pairings for stage and chip coordinates
        axes_rotation : AxesRotation
            axes rotation associated with the transformation
        chip : Chip
            chip instance associated with this rotation

        Raises
        ------
        TransformationError
            If pairings are not well-formed
            If pairings do not define a valid transformation

        Returns
        -------
        KabschRotation
            A valid kabsch rotation based on the pairings.
        """
        kabsch_rotation = cls(axes_rotation)
        for pairing in pairings:
            device = chip.devices.get(pairing["device_id"])
            if device is None:
                raise TransformationError(
                    f"Could not find Device with ID {pairing['device_id']} for given chip {chip}")

            try:
                pairing = CoordinatePairing.load(pairing, device=device)
            except Exception as err:
                raise TransformationError(
                    f"Could not create pairing for {pairing}: {err}")

            kabsch_rotation.update(pairing)

        if not kabsch_rotation.is_valid:
            raise TransformationError(
                "Cannot create kabsch rotation from stored pairings. Rotation is invalid.")

        return kabsch_rotation

    def __init__(self, axes_rotation: Type[AxesRotation]) -> None:
        self.axes_rotation = axes_rotation

        if not self.axes_rotation.is_valid:
            raise RuntimeError("The given axes rotation is invalid.")

        self.initialize()

    def initialize(self) -> None:
        """
        Initalises the transformation by unsetting all coordinates and offsets.
        """
        self.pairings = []

        # Both will be 3xN matrices
        self.chip_coordinates = np.empty((3, 0), float)
        self.stage_coordinates = np.empty((3, 0), float)

        self.rotation_to_chip = None
        self.translation_to_chip = None

        self.rotation_to_stage = None
        self.translation_to_stage = None

    def __str__(self) -> str:
        if not self.is_valid:
            return "No valid rotation defined ({}/{} Points set)".format(
                len(self.pairings), self.MIN_POINTS)

        return f"Rotation defined with {len(self.pairings)} Points"

    @property
    def is_valid(self) -> bool:
        """
        Returns True if Kabsch transformation is defined, i.e. if more than 3 pairings are defined.
        """
        return len(self.pairings) >= self.MIN_POINTS

    def update(self, pairing: Type[CoordinatePairing]) -> None:
        """
        Updates the transformation by adding a new pairing.
        Add the stage coordinate and chip coordinates to a matrix and recalculates the rotation.

        Parameters
        ----------
        pairing: CoordinatePairing
            A coordinate pairing between a stage and chip coordinate

        Raises
        ------
        ValueError
           If the pairing is not well defined or a pairing for the chip has already been set.
        """
        if not isinstance(pairing, CoordinatePairing) or (
                pairing.device is None or pairing.chip_coordinate is None or pairing.stage_coordinate is None):
            raise ValueError(
                "Use a complete CoordinatePairing object to update the rotation. ")

        if any(p.device == pairing.device for p in self.pairings):
            raise ValueError(
                "A pairing with this device has already been saved.")

        self.pairings.append(pairing)

        self.chip_coordinates = np.append(
            self.chip_coordinates,
            np.array([pairing.chip_coordinate.to_numpy()]).T,
            axis=1)
        self.stage_coordinates = np.append(
            self.stage_coordinates,
            np.array([pairing.stage_coordinate.to_numpy()]).T,
            axis=1)

        if not self.is_valid:
            return

        # Calculate the rotation. Note: The first argument is the start set,
        # the second argument is the target set.
        #
        # INPUT: chip coordinates as start set and stage coordinate as target set
        # OUTPUT: R, t, R^-1, t' s.t.
        # -> R * Chip-Coordinates + t = Stage-Coordinates
        # -> R^-1 * Stage-Coordinates + t' = Chip-Coordinates

        self.rotation_to_stage, self.translation_to_stage, self.rotation_to_chip, self.translation_to_chip = rigid_transform_with_orientation_preservation(
            S=self.chip_coordinates, T=self.stage_coordinates, axes_rotation=self.axes_rotation.matrix)

    def get_z_plane_angles(self) -> Tuple[float, float, float]:
        """
        Calculates the angle between the XY plane
        and the plane reconstructed by the Kabsch.

        Returns
        -------
        radiant, degree, percentage
            Angle in Radiant, Degree and Percentage
            between XY plane and Chip plane.
        """
        if not self.is_valid:
            return None

        xy_plane_normal = np.array([0, 0, 1])
        chip_plane_normal = self.rotation_to_stage.dot(xy_plane_normal)

        cos = np.abs(xy_plane_normal.dot(chip_plane_normal)) / \
            (np.linalg.norm(chip_plane_normal))

        angle_rad = np.arccos(cos)
        angle_deg = np.rad2deg(angle_rad)
        angle_per = np.tan(angle_rad) * 100

        return angle_rad, angle_deg, angle_per

    @assert_valid_transformation
    def chip_to_stage(
            self,
            chip_coordinate: Type[ChipCoordinate]) -> Type[StageCoordinate]:
        """
        Transforms a chip coordinate into a stage coordinate.

        Parameters
        ----------
        chip_coordinate: ChipCoordinate

        Returns
        -------
        stage_coordinate: StageCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid.
        """
        return StageCoordinate.from_numpy((
            self.rotation_to_stage.dot(chip_coordinate.to_numpy()) +
            self.translation_to_stage.T).flatten())

    def stage_to_chip(
            self,
            stage_coordinate: Type[StageCoordinate]) -> Type[ChipCoordinate]:
        """
        Transforms a stage coordinate into a chip coordinate.

        Parameters
        ----------
        stage_coordinate: StageCoordinate

        Returns
        -------
        chip_coordinate: ChipCoordinate

        Raises
        ------
        TransformationError: RuntimeError
            If transformation is not valid.
        """
        return ChipCoordinate.from_numpy((
            self.rotation_to_chip.dot(stage_coordinate.to_numpy()) +
            self.translation_to_chip.T).flatten())

    def dump(self) -> Any:
        """
        Returns a list of pairings defining the rotation.
        """
        return [
            p.dump(include_device_id=True) for p in self.pairings]


def rigid_transform_with_orientation_preservation(
    S: np.ndarray,
    T: np.ndarray,
    axes_rotation: np.ndarray = None
) -> None:
    """
    Calculates a rotation matrix that provides optimal rotation with respect
    to least squares error between two sets of 3D coordinates.

    The algorithm tries to maintain the orientation of the unit vectors after rotation.
    The axis rotation previously defined by the user is taken as the ground truth.
    Each unit vector is applied from the matrix and the scalar point is used to determine
    whether the unit vector points in the same direction after the axis rotation and after the rotation. If not, it is inverted.

    Parameters
    ----------
    target_dataset : np.ndarray
        3xN dataset of N 3-D coordinates (later referenced as T)
    start_dataset : np.ndarray
        3xN dataset of N-3D coordinates (later referenced as S)
    axes_rotation : np.ndarray
        3x3 ground truth axes rotation used for orientation preservation

    The algorihm computes a matrix R and translation vector t, such that:
        RS + t = T

    More details: https://github.com/nghiaho12/rigid_transform_3D/blob/master/rigid_transform_3D.py
    """
    if axes_rotation is not None and axes_rotation.shape != (3, 3):
        raise ValueError(
            f"Axes rotation matrix must be 3x3, got shape {axes_rotation.shape}")

    if not S.shape == T.shape:
        raise ValueError("Start and target dataset must have the same shape")

    target_num_rows, target_num_cols = T.shape
    start_num_rows, start_num_cols = S.shape

    if target_num_rows != 3:
        raise ValueError(
            f"Target dataset is not Nx3, got shape {target_num_rows}x{target_num_cols}")

    if start_num_rows != 3:
        raise ValueError(
            f"Start dataset is not Nx3, got shape {start_num_rows}x{start_num_cols}")

    # Centroid col wise
    t_centroid = np.mean(T, axis=1, keepdims=True)
    s_centroid = np.mean(S, axis=1, keepdims=True)

    # Subtract Centroid
    T_c = T - t_centroid
    S_c = S - s_centroid

    # Calculate accumulating matrix H = ST^T
    H = S_c @ np.transpose(T_c)

    # Calculate SVD: [U, S, V] = SVD(H)
    U, _, V = np.linalg.svd(H)

    # Calculate R
    R = V.T @ U.T

    # special reflection case
    if np.linalg.det(R) < 0:
        logger.info("det(R) < R, reflection detected!, correcting for it ...")
        V[2, :] *= -1
        R = V.T @ U.T

    # autocorrect orientation
    if axes_rotation is not None:
        correction_matrix = np.identity(3)
        for i, unit_vector in enumerate(
                [np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])]):
            ground_truth = axes_rotation @ unit_vector
            if ground_truth.dot(R @ unit_vector) < 0:
                correction_matrix[i, i] = -1

        R = R @ correction_matrix

    R_inv = np.linalg.inv(R)

    # Find translation for start to target: RS + t = T <=> t = T - RS
    t_start_to_target = t_centroid - R @ s_centroid

    # Find translation for traget to start: R^-1T + t = S <=> t = S - R^-1T
    t_target_to_start = s_centroid - R_inv @ t_centroid

    return R, t_start_to_target, R_inv, t_target_to_start
