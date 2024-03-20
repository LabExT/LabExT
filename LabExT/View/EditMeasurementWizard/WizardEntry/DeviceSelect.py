"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Label
from typing import TYPE_CHECKING, Tuple

from LabExT.View.Controls.AdhocDeviceFrame import AdhocDeviceFrame
from LabExT.View.Controls.DeviceTable import DeviceTable
from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryView, WizardEntryController

from LabExT.Wafer.Device import Device

if TYPE_CHECKING:
    from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
else:
    EditMeasurementWizardController = None

#############
# Controllers
#############


class AdhocDeviceSelectController(WizardEntryController):

    def results(self):
        return self._view.results()

    def serialize(self, settings: dict) -> None:
        content: AdhocDeviceFrame = self._view.content
        content.serialize_to_dict(settings)

    def deserialize(self, settings: dict) -> None:
        content: AdhocDeviceFrame = self._view.content
        content.deserialize_from_dict(settings)

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntryAdhocDeviceSelect(self._stage, parent, self._main_controller)


class ChipDeviceSelectController(WizardEntryController):

    def results(self):
        dev: Device = self._view.results()

        if dev is None:
            raise ValueError(
                "No device selected. Please select a device to continue.")

        # content of chip device view is tuple of table and label
        # see below
        self._view.content[1]['text'] = "Selected device: " + str(dev)

        return dev

    def serialize(self, settings: dict) -> None:
        content: DeviceTable = self._view.content[0]
        settings['dev_id'] = content.get_selected_device().id

    def deserialize(self, settings: dict) -> None:
        try:
            dev_id = settings['dev_id']
        except KeyError:
            return

        content: DeviceTable = self._view.content[0]

        # Does nothing if dev_id is not available
        content.set_selected_device(dev_id)

        dev: Device = content.get_selected_device()
        if dev is not None:
            self._view.content[1]['text'] = "Pre-selected device: " + str(dev)
        else:
            msg = 'Device ID loaded from settings file ({}) is not available ' + \
                  'in the current chip. Not setting a default.'
            self._logger.info(msg.format(dev_id))

    def _define_view(self, parent: Frame) -> WizardEntryView:
        return WizardEntryChipDeviceSelect(self._stage, parent, self._main_controller)

    def __init__(self, stage: int, controller: EditMeasurementWizardController, parent: Frame) -> None:
        super().__init__(stage, controller, parent)


############
# Views
############


class WizardEntryDeviceSelect(WizardEntryView):
    def _main_title(self) -> str:
        return "Select Device"


class WizardEntryAdhocDeviceSelect(WizardEntryDeviceSelect):
    def _content(self) -> CustomFrame:
        res = self._content_frame.add_widget(
            AdhocDeviceFrame(self._content_frame),
            row=0, column=0, padx=0, pady=0, sticky="we")
        res.title = "Define ad-hoc Device"
        return res

    def results(self):
        return self.content.get_custom_device()


class WizardEntryChipDeviceSelect(WizardEntryDeviceSelect):
    def _content(self) -> Tuple[DeviceTable, Label]:
        table = self._content_frame.add_widget(
            DeviceTable(self._content_frame,
                        self.controller.experiment_manager.chip),
            row=0, column=0, padx=5, pady=5, sticky='we')
        label = self._content_frame.add_widget(
            Label(self._content_frame, text="Selected Device: "),
            row=1, column=0, padx=5, pady=5, sticky='w')
        return (table, label)

    def results(self):
        return self.content[0].get_selected_device()
