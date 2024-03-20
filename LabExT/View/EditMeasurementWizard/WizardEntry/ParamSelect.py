"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame
from typing import Tuple, Union

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController, WizardEntryView

from LabExT.Measurements.MeasAPI.Measurement import Measurement


#############
# Controllers
#############


class ParameterSelectController(WizardEntryController):

    def results(self):
        try:
            self._view.results()
        except ValueError as ve:
            raise ValueError(f"Invalid data was entered:\n{str(ve)}")

    def deserialize(self, settings: dict) -> None:
        content: ParameterTable = self._view.content
        content.deserialize_from_dict(settings=settings)

    def serialize(self, settings: dict) -> None:
        prev_res: Measurement = self._main_controller.model.results[self._stage - 2]['measurement']

        if prev_res is not None:
            content: ParameterTable = self._view.content
            content.serialize_to_dict(settings)
        else:
            self._logger.warning(
                "Measurement is not defined. Cannot serialize measurement parameters.")

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntryParameterSelect(self._stage, parent, self._main_controller)


####################
# View
####################


class WizardEntryParameterSelect(WizardEntryView):

    def _main_title(self) -> str:
        return "Select Measurement Parameters"

    def _content(self) -> Union[CustomFrame, Tuple]:
        prev_res: Measurement = self.controller.model.results[self.stage - 2]['measurement']
        table = ParameterTable(self._content_frame,
                               store_callback=prev_res.store_new_param)
        table.title = f'Parameters of {prev_res.name}'
        table.parameter_source = prev_res.get_default_parameter()

        return self._content_frame.add_widget(table, row=0, column=0, padx=5, pady=5, sticky='we')

    def results(self):
        content: ParameterTable = self.content
        content.check_parameter_validity()

        prev_res: Measurement = self.controller.model.results[self.stage - 2]['measurement']
        for param_name, param in content._parameter_source.items():
            prev_res.parameters[param_name].value = param.value

        return None
