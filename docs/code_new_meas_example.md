# Example: Simple OSA Measurement

For this example on how to get started, we'll be looking at a simple measurement using an Optical 
Spectrum Analyzer (OSA). We will need to do two things:

1. Implement the measurement in a new measurement class which we will call `ReadOSA`
2. and interface the OSA via the instrument driver class called `OpticalSpectrumAnalyzerAQ6370C`

This how-to describes the coding of the measurement class.
You can find the final file at [LabExT/Measurements/ReadOSA.py](https://github.com/LabExT/LabExT/). We encourage
you to read this code file in parallel while we explain the various parts here.

## Measurement File
The example measurement will have one purpose: To capture the optical spectrum as recorded at the OSA and return the 
data collected.

Lets start by creating a new file - `ReadOSA.py` - in `LabExT/LabExT/Measurements`. The file should include 
the measurement class with the same name `ReadOSA`. A raw skeleton is of the form
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Measurements.MeasAPI import *


class ReadOSA(Measurement):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'ReadOSA'
        self.settings_path = 'ReadOSA_settings.json'
        self.instr_osa = None
    
```

A lot of the needed functionality is already implemented in the `Measurement` class, located at 
`LabExt/LabExT/Measurements/MeasAPI/Measurement.py`, 
which the new measurement must subclass. A measurement **must** include the following methods:  

- constructor (`__init__`): must call the parent constructor, define the measurement name (`self.name`), settings path 
  (`self.settings_path`) and the instruments instances used in the measurement (in this case only `self.instr_osa`). 
  The instrument will then dynamically be set to an instance of the instrument class which we will implement later.
- method `get_default_parameter`: returns the wanted parameters.
- method `get_wanted_instrument`: returns the wanted instrument types.
- method `algorithm`: conducts the actual measurement.

### get_default_parameter
Takes no arguments and returns the default parameters. This method sets the types, units and default values of the parameters 
used by the measurement. An example is:
```python
'OSA center wavelength': MeasParamFloat(value=1550.0, unit='nm')
```
The default parameters are organised in a python dictionary, where the key-value-pair corresponds to name and parameter instance.
The parameter types are defined in `LabExT/LabExT/Measuremens/MeasAPI/MeasAPI.py`, please see its documentation for an introduction. 
Set the parameter as seen above: The default wavelength that the spectrum recorded at the OSA should be centered around 
is (in our case) 1550 nm, thus we create a `MeasParamFloat` instance with value of 1550.0 and unit of 'nm'.
For our case, we also want to indicate other parameters, such as span, the resolution bandwidth and the number of steps 
on the wavelength axis. So, the final parameter section looks like:
```python
    @staticmethod
    def get_default_parameter():
        return {
            # osa settings
            'OSA center wavelength': MeasParamFloat(value=1550.0, unit='nm'),
            'OSA span': MeasParamFloat(value=2.0, unit='nm'),
            'no of points': MeasParamInt(value=2000),
            'sweep resolution': MeasParamFloat(value=0.08, unit='nm')
        }
```

This method does not require a class instance, so we make it a staticmethod.

!!! hint
    Depending on the `MeasParam` kind you choose, LabExT will offer the user different GUI elements for entering the
    parameters: `Float`, `Int` and  `String` get a text box, `Bool` gets a checkbox, `List` gets a dropdown menu.

### get_wanted_instrument
Takes no arguments and returns a list of the wanted instrument types. The instrument types are set in 
`~/.labext/instruments.config`, 
which consists of a dictionary with key-value-pairs where the instrument types correspond to the keys and a list of the 
available instruments to the value. Please see the [configuration page](./settings_configuration.md) for an introduction.

As this measurement requires only one instrument, we return the one-element list with just requiring the `OSA` type.
```python
    @staticmethod
    def get_wanted_instrument():
        return ['OSA']
```  
This method does not require a class instance, so we make it a staticmethod.

### algorithm
Finally, we implement the measurement algorithm in the `algorithm` method.

It takes the four arguments detailed below. This function will be called by the `StandardExperiment` 
located in `LabExT/LabExT/Experiments/StandardExperiment.py` when this measurement is run via the GUI.

- device: name of the device set in the GUI. Unused here.
- data: dictionary pre-filled with information set in the GUI. In the dict stored at `data['values']` we should add 
    lists of our measured data vectors. In the dict at `data['measurement settings']` we should store the final used
    measurement parameters. See [the data dict documentation](./code_data_dict.md) for further details.
- instruments: list of instruments, in this case a one-element dict consisting of an instance of the OSA class.
- parameters: dictionary of parameters, similar to the dict returned by `get_default_parameter` but filled with the values 
set via the GUI.
  
As a rule of thumb, the algorithm method implementation should follow these points:

1. read necessary parameters and save them to local variables. Note that to get the parameter value you have to access 
   the `.value` member of the MeasParam class instance (`MeasParamFloat`, 
   `MeasParamInt`, etc.).
2. write the measurement parameters into the measurement settings (will be saved into the result JSON file at the end).
3. get instrument pointers and open instrument connections.
4. set instrument parameters.
5. run your measurement routine and receive data.
6. save data.
7. close instrument connections
8. return data.

#### 1. read parameters
For easy of use, we read out the parameters from the `parameters` argument to local variables.
```python
    def algorithm(self, device, data, instruments, parameters):
        # get osa parameters
        osa_center_wl_nm = float(parameters.get('OSA center wavelength').value)
        osa_span_nm = float(parameters.get('OSA span').value)
        sweep_resolution_nm = float(parameters.get('sweep resolution').value)
        no_points = int(parameters.get('no of points').value)
```

#### 2. check and save parameters
Some measurements require some checks on the parameters, e.g. if a desired laser wavelength is outside of the
achievable range of your actual laser instrument.

Here we don't need to do checks and can directly save the used parameters into the output dictionary `data`. See
[the data dict documentation](./code_data_dict.md) for further details.
```python
        # write the measurement parameters into the measurement settings
        for pname, pparam in parameters.items():
            data['measurement settings'][pname] = pparam.as_dict()
```

#### 3. open instrument connection
We then retrieve the instrument driver instance and open the network connection to it:
```python
        self.instr_osa = instruments['OSA']
        self.instr_osa.open()
```

#### 4. set instrument parameters
We can now communicate with the instrument, lets set its properties. We want to set the span, the
center wavelength, the resolution bandwidth, and the number of points. As we use property-setters 
in the instrument driver, these lines actually will cause SCPI messages to be sent to the instrument.
```python
        # set instrument parameters
        self.instr_osa.span = osa_span_nm
        self.instr_osa.centerwavelength = osa_center_wl_nm
        self.instr_osa.sweepresolution = sweep_resolution_nm
        self.instr_osa.n_points = no_points
```

#### 5. run measurement and read data
Finally we advice the instrument to trigger a new sweep and to read the data into the variables
`x_data_nm` and `y_data_dbm`:

```python
        # everything is set up, run the sweep
        self.logger.info('OSA running sweep')
        self.instr_osa.run()

        sleep(0.5)

        # pull data from OSA
        x_data_nm, y_data_dbm = self.instr_osa.get_data()
        self.logger.info('OSA data received')
```

The `run()` method of the instrument driver triggers a new measurement on the OSA and then waits until
the wavelength sweep is completed. After a small wait, the `get_data()` then retrieves the measured data from the instrument.

#### 6. save the data
We must save the data in the `data['values']` dictionary under appropriate names. See
[the data dict documentation](./code_data_dict.md) for further details.
```python
        # copy the read data over to the json
        data['values']['wavelength [nm]'] = x_data_nm
        data['values']['transmission [dBm]'] = y_data_dbm
```

#### 7. close instrument connections
We tell the VISA library to close the connection to the instrument:
```python
        # close instrument connection
        self.instr_osa.close()
        self.logger.info('closed connection to OSA')
```

#### 8. check and return data
To make sure that we have filled all required keys of the `data` dictionary, we call a check and finally
return the data dict.
```python
        # check data for sanity
        self._check_data(data)
        return data
```

## Docstring
To give the user of this measurement an idea on how to use this class, we also write the docstring for this measurement 
class. The docstring will automatically be parsed and shown in the help when you press F1 inside LabExT.
You should include a basic description, an example laboratory setup for when this measurement could be helpful
and a description of all parameters.

The docstring must be formatted in **markdown**. Ours looks like this:
````markdown
## ReadOSA

This class performs a measurement that sets up and runs a single sweep at an OSA and returns the data collected.
Data returned corresponds to a 'snapshot' of the OSAs screen after a sweep.

### Example Setup

```
DUT -> OSA
```

The only instrument required for this measurement is an OSA, either a APEX, Yokagawa or HP model. This measurement
can for example be used in longterm measurements where a signal generator and laser are operated manually.

### OSA Parameters
- **OSA center wavelength**: Center wavelength of the OSA in [nm]. Stays fixed throughout the measurement if
autocenter is disabled.
- **auto center**: If selected, the OSA runs a sweep and determines the center wavelength by itself. If disabled,
then the wavelength set in 'OSA center frequency' is used.
- **OSA span**: Span of the OSA in [nm]. Determines in which region the spectrum is recorded. The optical power at
all wavelengths within [$f_{center} - \frac{span}{2}$, $f_{center} + \frac{span}{2}$] are recorded.
- **number of points**: Number of points the OSA records. Should be bigger than span / sweep resolution
- **sweep resolution**: Resolution of the OSA sweep in [nm]. Allowed values are dependent on the OSA model.
Yokagawa AQ6370C: 0.02 nm and 2 nm, HP70951A: > 0.08 nm, APEX: > 4e-5 nm.
````

This concludes the measurement class implementation for the `ReadOSA` functionality.

!!! todo
    What is left to do is the instrument driver: All instrument specific functionality is implemented into the
    instrument driver class. See [the instrument How-To](./code_new_instr_example.md) for a hands-on introduction on
    how to do so.
