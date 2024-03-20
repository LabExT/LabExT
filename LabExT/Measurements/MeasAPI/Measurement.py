#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from typing import List, Dict

from typing import TYPE_CHECKING, List, Dict, Tuple, Optional

import uuid

from LabExT.Measurements.MeasAPI.Measparam import MeasParam

if TYPE_CHECKING:
    from LabExT.Experiments.StandardExperiment import StandardExperiment
    from LabExT.ExperimentManager import ExperimentManager
    from LabExT.Instruments.InstrumentAPI.InstrumentAPI import Instrument
else:
    StandardExperiment = None
    ExperimentManager = None
    Instrument = None


MEAS_PARAMS_TYPE = Dict[str, MeasParam]


class Measurement:
    """Super class for measurement algorithms for LabExT.

    Aside from being an "interface" for measurement algorithm code, this class offers some basic functionality for
    executing measurements. It holds the currently set measurement parameters and the selected instruments (description
    and pointers to driver instances).

    To get a running measurement, change the properties: `name` and `settings_path`. You need to specify the requested
    instrument types in `get_wanted_instrument` and a set of default parameters in `get_default_parameter`.
    The measurement algorithm needs to be implemented in the `algorithm` method. See their respective reference below.
    For a How-To on implementing a new measurement algorithm, see
    [the New Measurement Algorithm page](./code_new_meas_example.md).

    Attributes:
        check_param (str): Class attribute. Will affect what the measure function does on missing
            parameters: `'Raise'` Raises an exception, `'Debug'` Generates a log entry (This will most likely lead to an
            exception in the algorithm),  `'Auto'` Fills the missing parameter with its default value.
        check_instr (str): Class attribute. Will affect what the measure function does on missing instruments:
            `'Raise'` Raises and exception, `'Debug'` Generates a log entry (This will most likely lead to an exception
            in the algorithm), `'Ignore'` Do Nothing
        name (str): Name of the measurement, typically similar of equal to the class name.
        settings_path (str): File name of the settings file of this measurement, can be anything and should end in
            '.json'.
        selected_instruments (dict): Set by the LabExT GUI after instrument selection stage. Keys is an instrument type,
            values is one instrument description dictionary from instruments.config (i.e. a VISA address, a driver
            class name, channel information and optionally some more constructor arguments for the driver).
    """

    check_param = 'Raise'
    check_instr = 'Raise'

    def __init__(self, 
                 experiment: Optional[StandardExperiment] = None, 
                 experiment_manager: Optional[ExperimentManager] = None):
        """Constructor of a measurement.

        The arguments are automatically filled when using the measurement with the LabExT GUI. For standalone use, the
        arguments do not need to be provided.

        Arguments:
            experiment (LabExT.Experiments.StandardExperiment): Reference to the experiment instance. Optional, but can
                be used to enable live-plotting during measurements.
            experiment_manager (LabExT.ExperimentManager): Ref to the main experiment manager of LabExT, the root
                object which interconnects all parts of LabExT. Used to access all loaded instruments. Optional for
                stand-alone usage outside the LabExT GUI.
        """
        self._experiment = experiment
        self._experiment_manager = experiment_manager

        """
        Measurement attributes, to be overridden by subclass.
        --> FILL THESE PARAMETERS IN YOUR SUBCLASS!
        """
        self.name = 'ExampleMeasurementName'
        self.settings_path = 'example_meas_save_file_name.json'

        """
        Measurement class internal use
        """

        self.selected_instruments: Dict[str, Dict] = {}
        """Dict of strings of instrument roles as defined in instruments.config"""

        self._parameters: Dict[str, MeasParam] = {}
        """Dict of measurement parameters, values are MeasParam() instances"""

        self._instruments: Dict[Tuple[str, str], Instrument] = {}
        """Dict for initialized instruments, format: (role_name, instr_class_name): instr_object"""

        self._instr_pointer = None
        """Only used internally in class Measurement"""

        self.wanted_instruments: List[str] = []
        """List of strings of instrument types as defined in instruments.config"""

        self.logger = logging.getLogger()
        """Logger object, use this to log to console and log file"""

        self._id: uuid.UUID = uuid.uuid4()
        """A random id for the measurement. It is based on the measurement name and the parameters."""

    @property
    def id(self) -> uuid.UUID:
        """Returns a unique ID for this measurement based on its name and its parameters.
        
        Measurements with the same name and parameters will have the same id.
        """
        return self._id

    @property
    def parameters(self) -> Dict[str, MeasParam]:
        """`dict` of `MeasParam`: access the currently set parameters for this measurement. If no parameters were set,
        the default parameters are taken. Key is the parameters name and the Value is a `MeasParam` instance.
        """
        if self._parameters == {}:
            self._parameters = self.get_default_parameter()
        return self._parameters

    @parameters.setter
    def parameters(self, new_param):
        self._parameters = new_param

    @property
    def instruments(self) -> Dict[Tuple[str, str], Instrument]:
        """`dict` of `Instrument`: Holds the instances of the instrument drivers after calling `init_instruments()`,
        otherwise returns an empty dict. Keys are a 2-tuple of strings: (type, driver name): type is the type
        requested in `get_wanted_instrument()` and the driver name is the class name of the instruments driver. The
        values are pointers to initialized instrument drivers.
        """
        return self._instruments

    @instruments.setter
    def instruments(self, new_intrs: Dict[Tuple[str, str], Instrument]):
        self._instruments = new_intrs

    def get_name_with_id(self) -> str:
        """Returns the measurements `name` property and the unique id for this measurement's instance.
        """
        return str(self.name) + " (shortened id = " + self.id.hex[-5:] + ")"

    def init_instruments(self):
        """Instantiates instrument drivers according to `self.selected_instruments` and saves them in `self.instruments`

        This method gets called from the LabExT GUI and does not need to be invoked by the user.

        Raises:
            RuntimeError: In case any instrument could not be initilized. Sometimes initialization fails silently...
        """
        for instr_class in self.get_wanted_instrument():
            self._experiment_manager.instrument_api.create_instrument_obj(instr_class,
                                                                          self.selected_instruments,
                                                                          self.instruments)
        # check that all instruments were correctly initialized, if this is not the case, we raise an Exception
        if not all(inst is not None for inst in self.instruments.values()):
            raise RuntimeError('Instruments were not initialized correctly.')

    def get_instrument(self, instrument_type: str) -> Instrument:
        """Returns the pointer to the initialized instrument for the given instrument type.

        Use this function within self.algorithm() to get the pointer to the instrument driver you can use for
        instrument interaction.

        Arguments:
            instrument_type (str): The type string of the instrument requested.
                Must be in the list specified in `get_wanted_instrument.()`.

        Raises:
            ValueError: If the instrument with the given type cannot be found in the dict of the initialized
                instruments.
            RuntimeError: If the instrument with the given type is not initialized yet.

        Returns:
            Instrument: Initialised instrument driver.
        """
        for (itype, _), instr in self.instruments.items():
            if itype == instrument_type:
                if instr is not None:
                    return instr
                else:
                    raise RuntimeError("Instrument with type " + str(instrument_type) + " not initialized.")
        else:
            raise ValueError("No instrument with type " + str(instrument_type) + " in dict of initialized instruments.")

    def _get_data_from_all_instruments(self) -> Dict[str, Dict]:
        """Gets the settings of all instruments used in the measurement.

        Called from a standard experiment routine from LabExT to save all involved instrument's meta data and settings.
        """
        inst_data = {}

        for cat, i in self.instruments.items():
            self.logger.debug("getting params from: " + str(cat) + " actual class: " + str(i.__class__.__name__))
            inst_data[cat[0]] = i.get_instrument_parameter()

        return inst_data

    @staticmethod
    def get_default_parameter() -> Dict[str, MeasParam]:
        """The dictionary of all parameters required in this measurement at their default value.

        Inside the `algorithm`, you can access all parameters via the `parameters` argument which is the same
        structured dictionary as specified here but with the parameter values as chosen in the GUI.

        This method must be overriden for any working measurement implementation. See
        [the New Measurement Algorithm page](./code_new_meas_example.md).

        Returns:
            dict: keys are parameter names (strings), its values are instances of `MeasParam` or any of its
                subclasses

        """
        raise NotImplementedError()

    @staticmethod
    def get_non_sweepable_parameters() -> Dict[str, MeasParam]:
        """A `dict` mapping names of the parameters that are explicitly non-sweepable to the corresponding `MeasParam`.
        
        If all parameters are sweepable this method should return an empty `dict`.
        The default implementation also returns an empty `dict`.
        
        Returns:
            dict[str, MeasParam]: names of the parameters that aren't sweepable mapped to the corresponding parameters
        """
        return dict()

    @staticmethod
    def get_wanted_instrument() -> List[str]:
        """The list of all instrument types (strings) required in this measurement.

        Inside the `algorithm`, you can access the instantiated instrument driver classes by accessing the
        `instruments` argument which is a dict. The list you return in this method will be the keys of said dict.

        If you want to use more than one instrument of the same type, you can add a number after the instrument type.
        So to include two lasers and one power meter, I would return: `['Laser 1', 'Laser 2', 'PowerMeter']`.

        This method must be overriden for any working measurement implementation. See
        [the New Measurement Algorithm page](./code_new_meas_example.md).

        Returns:
            list: the elements are strings of instrument types as available in instruments.config
        """
        raise NotImplementedError()

    #
    # Measurement Routine and Helper Functions
    #

    def measure(self, device, data, **kwargs):
        """Gathers the parameters and instruments set via GUI and executes `self.algorithm()` with correct arguments.

        First checks whether all the needed contents are present, and if so starts execution of the algorithm. This
        function can take some optional arguments, namely parameters and instruments, to override the already saved
        ones.

        Furthermore, there are modes in place to fill missing parameters automatically. The flags check_instr and
        check_param can take various (static) values, that will dictate how measurement will handle missing parameters
        and instruments.

        There should be no need for a sub-class to overwrite this method.

        Arguments:
            device (Device): Device instance on which the measurement is performed. Allows to adapt measurement
                algorithm according to some device property.
            data (dict): Dictionary in which we store the result of the measurement.
            **kwargs: `'instruments'` An optional dict of instrument drivers. `'parameters'` An optional dict of
                some parameters. Can be filled partially!

        Raises:
            ValueError: If some instrument or parameter is missing and the check_ flags are set to `'Raise'`.
        """
        # update the attributes of measurement class, if allowed
        allowed_keys = {"parameters", "instruments"}
        self.__dict__.update((k, v) for k, v in kwargs.items() if k in allowed_keys)

        # check instruments
        for i in self.get_wanted_instrument():
            for (itype, _), instr in self.instruments.items():
                if itype == i:
                    if instr is not None:
                        break
                    else:
                        if type(self).check_instr == 'Debug':
                            self.logger.warning("Instrument " + i + " not initialized.")
                        elif type(self).check_param == 'Raise':
                            raise ValueError("Instrument not initialized: " + i)
            else:
                if type(self).check_instr == 'Debug':
                    self.logger.warning("Instrument " + i + " not found.")
                elif type(self).check_param == 'Raise':
                    raise ValueError("Instrument not found: " + i)

        # remove class name from key, s.t. the algorithm method has direct access via the names:
        instr_dict_no_classnames = {k: v for (k, _), v in self.instruments.items()}

        # check parameters
        for k, v in self.get_default_parameter().items():
            if k not in self._parameters:
                if type(self).check_param == 'Debug':
                    self.logger.warning("Did not find parameter " + k)
                elif type(self).check_param == 'Auto':
                    self._parameters[k] = v
                elif type(self).check_param == 'Raise':
                    raise ValueError("Parameter not found: " + k)

        return self.algorithm(device, data, instr_dict_no_classnames, self.parameters)

    def algorithm(self, device, data, instruments, parameters):
        """The main body of the measurement algorithm to be performed.

        Generally includes the following steps:
            1. read all parameters to variables
            2. read all instrument driver instances to local variables
            3. do preliminary checks, e.g. if the desired parameters are possible with the selected instruments
            4. save the used parameters in the `data['measurement settings']` dictionary
            5. set instrument settings according to chosen parameters
            6. execute the measurement routine
            7. read back data from the instruments and store it in the `data['values']` dictionary
            8. (recommended) check if you have populated all fields in the `data` dictionary by using
                `self._check_data(data)`

        This method must be overriden for any working measurement implementation. See
        [the New Measurement Algorithm page](./code_new_meas_example.md).

        Arguments:
            device (Device): Device instance on which the measurement is performed. Allows to adapt measurement
                algorithm according to some device property.
            data (dict): Dictionary in which we store the result of the measurement.
            instruments (dict): Dictionary with the instr. types as keys and the instrument driver instances as values.
            parameters (dict): Dictionary of all parameters. Keys are parameters names, values are `MeasParam`
                instances.
        """
        raise NotImplementedError

    @classmethod
    def setup_return_dict(cls) -> Dict[str, Dict]:
        """Gives the absolute bare minimum of keys which need to be filled in `data` dictionary in an `algorithm()` run.

        Returns:
            dict: The minimum set of keys for a `data` dictionary necessary to populate during a call of `algorithm()`.
        """
        data = {'measurement settings': {}, 'values': {}}
        return data

    def _check_data(self, data):
        """Checks if all necessary fields are present in the `data` dict.

        Use this method at the very end of an `algorithm()` implementation to check if you did not forget to fill any
        important field in the `data` dictionary.

        Prints a warning to the log if a mandatory key is present but does not contain any data.

        Arguments:
            data (dict):  Dictionary with data to be tested on completeness.

        Raises:
            ValueError: If a mandatory key is not present.
        """
        if 'values' not in data:
            raise ValueError(
                "Data Error - No value specified in data['values']")
        if not isinstance(data['values'], dict):
            raise TypeError(
                "Data Error - data['values'] is not of type dict.")
        if len(data['values']) == 0:
            self.logger.warning(
                "Data Warning for measurement {:s} - data['values'] dict is empty.".format(self.name)
            )
        if 'measurement settings' not in data:
            raise ValueError(
                "Data Error - No value specified in data['measurement settings']")
        if not isinstance(data['measurement settings'], dict):
            raise TypeError(
                "Data Error - data['measurement settings'] is not of type dict.")
        if len(data['measurement settings']) == 0:
            self.logger.warning(
                "Data Warning for measurement {:s} - data['measurement settings'] dict is empty.".format(self.name)
            )

    #
    # Side Window open function
    #

    def open_side_windows(self):
        """Include any code you want to be executed on the "open side windows" button for the measurement.
        """
        self.logger.warning('There are no side windows defined but open_side_windows() was called.')

    def store_new_param(self, new_params):
        """Used as callback function for the GUI to set parameters of the measurement.
        """
        self.parameters = new_params
