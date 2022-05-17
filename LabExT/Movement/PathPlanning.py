

from typing import Tuple, Type
from abc import ABC, abstractmethod

import numpy as np

from LabExT.Movement.Transformations import ChipCoordinate

class PathPlanning:

    def __init__(
        self,
        start_target_coordinates: Tuple[Type[ChipCoordinate], Type[ChipCoordinate]]
    ) -> None:
        pass




class PotentialField(PathPlanning):

    GRID_SIZE = 10.0
    FIBER_RADIUS = 125.0

    def __init__(
        self,
        start_target_coordinates: Tuple[Type[ChipCoordinate], Type[ChipCoordinate]]
    ) -> None:
        pass


        chip_outline = ((-500, 2000), (-500, 1500))
        
        x_coords = np.arange(chip_outline[0][0], chip_outline[0][1] + grid_size, grid_size)
        y_coords = np.arange(chip_outline[1][0], chip_outline[1][1] + grid_size, grid_size)
        cx, cy = np.meshgrid(x_coords, y_coords)