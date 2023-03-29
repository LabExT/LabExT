#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2023  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""


from abc import ABC, abstractmethod
import logging
from typing import Type, Dict, List

from LabExT.Measurements.MeasAPI.Measparam import MeasParam
from LabExT.Movement.Transformations import StageCoordinate
from LabExT.Movement.Calibration import Calibration
from LabExT.Instruments.InstrumentAPI import Instrument


class PeakSearcher(ABC):
    """

    """
    name: str = "PeakSearcher"

    @staticmethod
    def get_wanted_stages() -> List[str]:
        """

        """
        return []

    @staticmethod
    def get_wanted_instruments() -> List[str]:
        """

        """
        return []

    @staticmethod
    def get_default_parameters() -> Dict[str, Type[MeasParam]]:
        """

        """
        return {}

    def __init__(self, mover) -> None:
        super().__init__()
        self.logger = logging.getLogger()
        self.mover = mover
        self.instruments = {}
        self.stages = {}
        self._parameters = {}

    @property
    def parameters(self):
        """
        TODO
        """
        if self._parameters == {}:
            self._parameters = self.get_default_parameters()
        return self._parameters

    @parameters.setter
    def parameters(self, new_parameters):
        """

        """
        self._parameters = new_parameters

    def __str__(self) -> str:
        """

        """
        return self.__class__.__name__

    @abstractmethod
    def algortihm(
        self,
        data: dict,
        instruments: Dict[str, Type[Instrument]],
        stages: Dict[str, Type[Calibration]],
        parameters: Dict[str, Type[MeasParam]]
    ) -> Type[StageCoordinate]:
        """

        """
        pass
