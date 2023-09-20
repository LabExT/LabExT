"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame
from typing import TYPE_CHECKING, List, Tuple, Union, Dict
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentSelector
from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController, WizardEntryView


if TYPE_CHECKING:
    from LabExT.View.Controls.InstrumentSelector import InstrumentRole
    from LabExT.Measurements.MeasAPI.Measurement import Measurement
else:
    InstrumentRole = None
    Measurement = None


class InstrumentSelectController(WizardEntryController):

    def results(self):
        # get the chosen experiment descriptor dicts for each role and save it to the measurement
        previous_result = self._main_controller.model.results[self._stage - 1]
        instruments: List[Tuple[str, InstrumentRole]
                          ] = previous_result["available_instruments"].items()
        measurement: Measurement = previous_result["measurement"]

        for role_name, role_instrs in instruments:
            measurement.selected_instruments[role_name] = role_instrs.choice

        # initialize instruments
        try:
            measurement.init_instruments()
        except Exception as e:
            raise ValueError(
                "Could not initialize instruments. Reason: " + repr(e))

        return None

    def deserialize(self, settings: dict) -> None:
        content: InstrumentSelector = self._view.content
        content.deserialize_from_dict(settings)

    def serialize(self, settings: dict) -> None:
        content: InstrumentSelector = self._view.content
        content.serialize_to_dict(settings)

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntryInstrumentSelect(self._stage, parent, self._main_controller)


class WizardEntryInstrumentSelect(WizardEntryView):

    def _main_title(self) -> str:
        return "Select Instruments"

    def _content(self) -> Union[CustomFrame, Tuple]:
        previous_result: Dict[str,
                              Measurement] = self.controller.model.results[self.stage - 1]

        selector = InstrumentSelector(self._content_frame)
        selector.title = f'Instruments of {previous_result["measurement"].name}'
        selector.instrument_source = previous_result['available_instruments']

        self._content_frame.add_widget(
            selector, row=0, column=0, padx=5, pady=5, sticky='we')

        return selector

    def results(self):
        return None
