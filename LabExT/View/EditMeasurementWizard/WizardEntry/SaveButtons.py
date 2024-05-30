"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import pandas as pd

from tkinter import Button, Frame

from LabExT.View.EditMeasurementWizard.WizardEntry.Base import WizardEntryController, WizardEntryView
from LabExT.View.EditMeasurementWizard.WizardEntry.FinishedError import WizardFinishedError
from LabExT.Experiments.ToDo import ToDo, DictionaryWrapper
from LabExT.Wafer.Device import Device
from LabExT.Measurements.MeasAPI.Measurement import Measurement
from LabExT.Measurements.MeasAPI.Measparam import MeasParamInt

from LabExT.View.Controls.SweepParameterFrame import JSONRepresentation


def create_parameter_sweep_todos(
    experiment, sweep_ranges: JSONRepresentation, measurement: Measurement, device: Device
) -> None:
    """Creates `ToDo`s for all necessary configurations of swept parameters.

    Args:
        experiment: The experiment to add the `ToDo`s to
        sweep_ranges: The results of the sweep parameter stage
        measurement: The measurement to perform
        device: The device the measurement should be performed on
    """
    dataframes_per_parameter = [
        pd.DataFrame(series, columns=[param_name]) for param_name, (series, _) in sweep_ranges.items()
    ]

    parameters = dataframes_per_parameter[0]
    for dataframe in dataframes_per_parameter[1:]:
        parameters = parameters.merge(dataframe, how="cross")

    parameters.columns = pd.MultiIndex.from_tuples([("measurement settings", c) for c in parameters.columns])

    # used to store summary dict
    dict_wrap = DictionaryWrapper()

    for index, row in parameters.iterrows():
        # create new object
        meas_class_name: str = type(measurement).__name__
        new_meas = experiment.create_measurement_object(meas_class_name)

        new_meas.instruments = measurement.instruments.copy()
        new_meas.selected_instruments = measurement.selected_instruments.copy()

        new_meas.parameters = measurement.parameters.copy()
        for (_, name), value in zip(row.index, row):
            new_param = measurement.parameters[name].copy()
            if type(new_param) == MeasParamInt:
                new_param.value = int(value)
            else:
                new_param.value = value
            new_meas.parameters[name] = new_param

        parameters.loc[index, ("metadata", "id")] = str(new_meas.id.hex)
        parameters.loc[index, ("metadata", "name")] = str(new_meas.name)

        experiment.to_do_list.append(
            ToDo(
                device=device,
                measurement=new_meas,
                part_of_sweep=True,
                sweep_parameters=parameters,
                dictionary_wrapper=dict_wrap,
            )
        )

    parameters["metadata", "finished"] = False


#############
# Controllers
#############


class SaveButtonsController(WizardEntryController):
    def results(self):
        dev: Device = self._main_controller.model.results[0]
        meas: Measurement = self._main_controller.model.results[1]["measurement"]
        sweepable: JSONRepresentation = self._main_controller.model.results[self._stage - 1]

        if len(sweepable) > 0:
            create_parameter_sweep_todos(self._main_controller._experiment, sweepable, meas, dev)
        else:
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
        close_button = Button(
            self._content_frame,
            text="Discard and close window.",
            command=lambda: self.controller.escape_event(0),
            width=30,
        )
        close_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.continue_button.config(text="Save Measurement to Queue!", font=("bold",), width=30)

        return close_button

    def results(self):
        return None
