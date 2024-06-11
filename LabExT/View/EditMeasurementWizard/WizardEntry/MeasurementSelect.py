"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, OptionMenu, StringVar

from typing import TYPE_CHECKING, Dict, Union

from LabExT.Utils import get_visa_address

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.InstrumentSelector import InstrumentRole
from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryView, WizardEntryController

if TYPE_CHECKING:
    from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
    from LabExT.Measurements.MeasAPI.Measurement import Measurement
else:
    EditMeasurementWizardController = None
    Measurement = None

#############
# Controllers
#############


class MeasurementSelectController(WizardEntryController):

    def results(self):
        selected_name: str = self._view.results()
        results: Dict[str, Union[Dict, Measurement]] = {
            "measurement": None, "available_instruments": {}}

        if selected_name == self._default_text:
            raise ValueError(
                "No measurement selected. Please select a valid Measurement to continue.")

        results["measurement"] = self._main_controller._experiment.create_measurement_object(
            selected_name)

        for role_name in results["measurement"].get_wanted_instrument():
            io_set = get_visa_address(role_name)

            results["available_instruments"][role_name] = InstrumentRole(
                self._main_controller.view.wizard_window, io_set)

        return results

    def deserialize(self, settings: dict) -> None:
        if 'selected_measurement' not in settings.keys():
            return

        if settings['selected_measurement'] in self._main_controller.experiment_manager.exp.measurement_list:
            meas_name: StringVar = self._view.meas_name
            meas_name.set(settings['selected_measurement'])
        else:
            msg = 'Measurement name loaded from settings file ({:s}) is not available ' + \
                  'in the current experiment. Not setting a default.'
            self._logger.info(msg.format(settings['selected_measurement']))

    def serialize(self, settings: dict) -> None:
        settings['selected_measurement'] = self._view.results()

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntryMeasurementSelect(self._stage, parent, self._main_controller)

    def __init__(self, stage: int, controller: EditMeasurementWizardController, parent: Frame) -> None:
        super().__init__(stage, controller, parent)
        self._default_text = "..."

####################
# View
####################


class WizardEntryMeasurementSelect(WizardEntryView):
    def _main_title(self) -> str:
        return "Select Measurement"

    def _content(self) -> CustomFrame:
        meas_list = list(
            self.controller.experiment_manager.exp.measurement_list.copy())
        meas_list.sort()

        self.meas_name = StringVar(self.controller.root, "...")
        menu = self._content_frame.add_widget(
            OptionMenu(self._content_frame, self.meas_name, *meas_list),
            row=0, column=0, padx=5, pady=5, sticky='w')
        return menu

    def results(self):
        return self.meas_name.get()
