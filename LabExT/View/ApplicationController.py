#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from abc import ABC, abstractmethod


class ApplicationController(ABC):
    @abstractmethod
    def __init__(self, parent, experiment_manager) -> None:
        self.parent = parent
        self.experiment_manager = experiment_manager
