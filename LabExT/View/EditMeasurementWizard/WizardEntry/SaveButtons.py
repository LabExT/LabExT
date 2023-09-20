"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Button, Frame

from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController, WizardEntryView
from LabExT.View.EditMeasurementWizard.WizardEntry.FinishedError import WizardFinishedError
from LabExT.Experiments.ToDo import ToDo
from LabExT.Wafer.Device import Device
from LabExT.Measurements.MeasAPI.Measurement import Measurement

#############
# Controllers
#############


class SaveButtonsController(WizardEntryController):

    def results(self):
        dev: Device = self._main_controller.model.results[0]
        meas: Measurement = self._main_controller.model.results[1]['measurement']

        t = ToDo(device=dev, measurement=meas)
        self._main_controller._experiment.to_do_list.append(t)
        self._main_controller._experiment.update()
        self._main_controller.view.scrollable_frame.unbound_mouse_wheel()
        self._main_controller.escape_event(0)

        raise WizardFinishedError()

    def deserialize(self, settings: dict) -> None:
        return None

    def serialize(self, settings: dict) -> None:
        return None

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntrySaveButtons(self._stage, parent, self._main_controller)


####################
# View
####################


class WizardEntrySaveButtons(WizardEntryView):

    def _main_title(self) -> str:
        return "Save"

    def _content(self) -> Button:
        close_button = Button(self._content_frame,
                              text="Discard and close window.",
                              command=lambda: self.controller.escape_event(0),
                              width=30)
        close_button.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        self.continue_button.config(text="Save Measurement to Queue!",
                                    font=("bold",),
                                    width=30)

        return close_button

    def results(self):
        return None
