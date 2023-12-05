"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from typing import TYPE_CHECKING

from tkinter import Frame

from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController
from LabExT.View.EditMeasurementWizard.WizardEntry.DeviceSelect import AdhocDeviceSelectController, ChipDeviceSelectController
from LabExT.View.EditMeasurementWizard.WizardEntry.MeasurementSelect import MeasurementSelectController
from LabExT.View.EditMeasurementWizard.WizardEntry.InstrumentSelect import InstrumentSelectController
from LabExT.View.EditMeasurementWizard.WizardEntry.ParamSelect import ParameterSelectController
from LabExT.View.EditMeasurementWizard.WizardEntry.SweepParameterSelect import SweepParameterSelectController
from LabExT.View.EditMeasurementWizard.WizardEntry.SaveButtons import SaveButtonsController

if TYPE_CHECKING:
    from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
else:
    EditMeasurementWizardController = None


def wizard_entry_controller_factory(stage_number: int, device_avail: bool, parent: Frame, controller: EditMeasurementWizardController) -> WizardEntryController:
    if stage_number == 0:
        if device_avail:
            return ChipDeviceSelectController(stage_number, controller, parent)
        else:
            return AdhocDeviceSelectController(stage_number, controller, parent)
    elif stage_number == 1:
        return MeasurementSelectController(stage_number, controller, parent)
    elif stage_number == 2:
        return InstrumentSelectController(stage_number, controller, parent)
    elif stage_number == 3:
        return ParameterSelectController(stage_number, controller, parent)
    elif stage_number == 4:
        return SweepParameterSelectController(stage_number, controller, parent)
    elif stage_number == 5:
        return SaveButtonsController(stage_number, controller, parent)
    elif stage_number >= 6:
        raise ValueError("Stages complete.")
    else:
        logging.debug(
            "This should not be possible unless there is a negative stage_number.")
        raise ValueError(f"Unknown stage with number {stage_number}")
