"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame
from typing import TYPE_CHECKING, Tuple, Union

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.SweepParameterFrame import SweepParameterFrame
from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController, WizardEntryView

if TYPE_CHECKING:
    from LabExT.Measurements.MeasAPI.Measurement import Measurement
else:
    Measurement = None


#############
# Controllers
#############


class SweepParameterSelectController(WizardEntryController):

    def results(self):
        return self._view.results()

    def deserialize(self, settings: dict) -> None:
        content: SweepParameterFrame = self._view.content
        content.deserialize(settings=settings)

    def serialize(self, settings: dict) -> None:
        content: SweepParameterFrame = self._view.content
        content.serialize(settings=settings)

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntrySweepSelect(self._stage, parent, self._main_controller)


####################
# View
####################


class WizardEntrySweepSelect(WizardEntryView):

    def _main_title(self) -> str:
        return "Select Sweep Parameters"

    def _content(self) -> Union[CustomFrame, Tuple]:
        prev_res: Measurement = self.controller.model.results[self.stage - 3]['measurement']
        sweepable_parameters = {param_name: param for param_name, param in prev_res.parameters.items()
                                if param.sweep_type is not None
                                and param_name not in prev_res.get_non_sweepable_parameters().keys()}
        frame = SweepParameterFrame(parent=self._content_frame,
                                    string_var_master=self.controller.view.wizard_window,
                                    parameters=sweepable_parameters)

        return self._content_frame.add_widget(frame, row=0, column=0, padx=5, pady=5, sticky='we')

    def results(self):
        content: SweepParameterFrame = self.content
        return content.results()
