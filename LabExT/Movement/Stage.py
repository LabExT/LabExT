#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""
from __future__ import annotations

import logging

from functools import wraps
from abc import ABC, abstractmethod
from typing import List, Tuple, Any


class StageError(RuntimeError):
    pass


def assert_stage_connected(func):
    """
    Use this decorator to assert that any method of a stage is only executed
    when the stage is connected.
    """

    @wraps(func)
    def wrapper(stage, *args, **kwargs):
        if not stage.connected:
            raise StageError(
                "Stage not connected: Function {} requires an active stage connection. Make sure that you have called connect() before.".format(
                    func.__name__))

        return func(stage, *args, **kwargs)
    return wrapper


def assert_driver_loaded(func):
    """
    Use this decorator to assert that any method of a stage is only executed
    when the drivers are loaded.
    """

    @wraps(func)
    def wrapper(stage, *args, **kwargs):
        if not stage.driver_loaded:
            raise StageError(
                "Stage driver not loaded: Function {} requires previously loaded drivers.".format(
                    func.__name__))

        return func(stage, *args, **kwargs)
    return wrapper


class Stage(ABC):
    """
    Abstract Interface for Stages in LabExT. 
    Inherit from this class to support new stages.

    Attributes:
        driver_loaded:          Indicates whether the drivers for the stage are loaded.
        driver_specifiable:     Indicates whether the user specifies the drivers,
                                for example, by setting a path where the drivers are stored.
        description:            Optional description of the stage for the GUI
    """
    driver_loaded: bool = False
    driver_specifiable: bool = False
    description: str = ""

    _logger = logging.getLogger()

    @classmethod
    def find_available_stages(cls) -> List[Type[Stage]]:
        """
        Returns a list of stage objects. Each object represents a found stage.
        Note: The stage is not yet connected.
        """
        try:
            return [cls(address) for address in cls.find_stage_addresses()]
        except StageError as err:
            cls._logger.error(
                f"Failed to find available stages for {cls.__name__}: {err}")
            return []

    @classmethod
    def find_stage_addresses(cls) -> list:
        """
        Returns a list of stage locators.
        """
        return []

    @classmethod
    def load_driver(cls, parent=None) -> bool:
        """
        Stage specific method to load any missing drivers.

        Returns True, if successfully loaded and False otherwise.

        Needs to be overwritten.
        """
        raise NotImplementedError

    @abstractmethod
    def __init__(self, address: Any):
        """
        Constructs a new Stage.

        Parameters
        ---------
        address: Any
            Address of Stage

        Attributes
        ----------
        address: Any
            Address of Stage
        connected: bool = False
            Indicates whether the there exists a active connection to the stage.
        """
        self.address: Any = address
        self.connected: bool = False

    def __del__(self):
        if self.connected:
            self.disconnect()

    @abstractmethod
    def __str__(self) -> str:
        """
        Returns the stage in string representation.
        """
        pass

    @property
    def address_string(self) -> str:
        """
        Returns the address of the stage as string.
        Example: 'usb:id:123456789'
        """
        raise NotImplementedError

    @property
    def identifier(self) -> str:
        """
        Returns a identifier for given stage.
        
        The identifier is used to uniquely distinguish two stages of the same type.
        In most cases the identifier is equal to the address of the stage. 
        """
        raise NotImplementedError

    @property
    def is_stopped(self) -> bool:
        """
        Indicates whether the stage is not moving, i.e. has come to a stop.
        """
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        Creates a connection to the Stage.

        Returns
        -------
        bool
            Indicates whether the connection was successful.
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Closes the current connection with the Stage.

        Returns
        -------
        bool
            Indicates whether the connection was successfully closed.
        """
        pass

    @abstractmethod
    def set_speed_xy(self, umps: float) -> None:
        """
        Sets the speed in X and Y direction

        Parameters
        ----------
        umps: float
            Speed in micrometers per second (um/s)
        """
        pass

    @abstractmethod
    def set_speed_z(self, umps: float) -> None:
        """
        Sets the speed in Z direction

        Parameters
        ----------
        umps: float
            Speed in micrometers per second (um/s)
        """
        pass

    @abstractmethod
    def get_speed_xy(self) -> float:
        """
        Returns the current set speed in X and Y direction.

        Returns
        -------
        float
            Speed in micrometers per second (um/s)
        """
        pass

    @abstractmethod
    def get_speed_z(self) -> float:
        """
        Returns the current set speed in Z direction.

        Returns
        -------
        float
            Speed in micrometers per second (um/s)
        """
        pass

    @abstractmethod
    def set_acceleration_xy(self, umps2: float) -> None:
        """
        Sets the acceleration in X and Y direction

        Parameters
        ----------
        umps2: float
            Acceleration in micrometers per square second (um/s^2)
        """
        pass

    @abstractmethod
    def get_acceleration_xy(self) -> float:
        """
        Returns the current set acceleration in X and Y direction.

        Returns
        -------
        float
            Acceleration in micrometers per square second (um/s^2)
        """
        pass

    @abstractmethod
    def get_status(self) -> Tuple[Any, Any, Any]:
        """
        Returns the status of the stage in all axes.

        Returns `None` if the stage does not respond.
        The semantics of the status codes may differ from stage to stage; they do not have to follow a uniform format.

        Example: If all three axes move, a stage could return `(STEPPING, STEPPING, STEPPING)`.

        Returns
        -------
        tuple
            A triple with the status of all three axes.
        """
        pass

    @abstractmethod
    def get_position(self) -> List[float]:
        """
        Returns the position of the stage in X,Y and Z.

        Returns
        -------
        list
            List of three floats representing a 3D point of the position of the stage.
        """
        pass

    @abstractmethod
    def move_relative(
        self,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        wait_for_stopping: bool = True
    ) -> None:
        """
        Orders the stage to move relative to the current position.

        Parameters
        ----------
        x: float = 0
            Relative offset in X direction.
        y: float = 0
            Relative offset in Y direction.
        z: float = 0
            Relative offset in Z direction.
        wait_for_stopping: bool = True
            If true, the method's call is blocked until the stage has reached the target position,
            i.e., all axes are stopped.
        """
        pass

    @abstractmethod
    def move_absolute(
        self,
        x: float = None,
        y: float = None,
        z: float = None,
        wait_for_stopping: bool = True
    ) -> None:
        """
        Orders the stage to move absolute to a given position.

        If a axis of the target coordinate is `None`,
        the stage keeps the current position of this axis constant.

        Parameters
        ----------
        x: float = None
            Absolute position in X direction
        y: float = None
            Absolute position in Y direction
        z: float = None
            Absolute position in Z direction
        wait_for_stopping: bool = True
            If true, the method's call is blocked until the stage has reached the target position,
            i.e., all axes are stopped.
        """
        pass

