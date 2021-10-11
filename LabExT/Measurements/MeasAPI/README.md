# Measurement API
## Import
To import the measurement API simply import all needed elements by:

``from LabExT.Measurements.MeasAPI import [IMPORTS] ``
## Classes
The measurement API defines the Measurement Class as well as the new MeasParam Class
### Measurement
The class ``Measurement`` acts as a superclass for all measurements. It defines some
utility functions and should be used as a superclass for every measurement.

| Attribute | Type | Description |
|---|---|---|
| check_param | ``['Raise', 'Debug', 'Auto']`` | Sets the action performed when a parameter is missing. ``Raise`` will raise an exception, ``Debug`` will make a log entry and ``Auto`` will fill in the default value. |
| check_instr | ``['Raise', 'Debug', 'Ignore']`` | Sets the action performed when a instrument is missing. ``Raise`` will raise an exception, ``Debug`` will make a log entry and ``Ignore`` will ignore the issue. |

| Functions | Arguments | Return Type | Needs to be provided by user  | Description |
|---|---|---|---|---|
| get_name_with_id |  | ``Str`` | No | Returns the measurements name, with the ID attached. |
| init_instruments |   | ``None`` | No | Calls the instruments API to setup all instruments defined in ``selected_instruments`` |
| get_instrument   | ``intrument_type: Str`` | ``Instrument`` | No | Returns the initialized instrument of the given class. |
| get_default_parameter  |   | ``Dict`` | Yes | Returns a dict of all parameters, where the key is the parameter name. Entries should be of type ``MeasParam``. |
| get_wanted_instrument | | ``List`` | Yes | Returns a list of the wanted instrument types. |
| measure | ``device: Device``: The device under test <br><br> ``data: Dict``: Where the result is stored <br><br> ``instruments: Dict``: an optional dict of instruments, to overwrite the initialized ones <br><br> ``parameters: Dict``: an optional dict of parameters, to overwrite the set ones | ``Dict`` | No | This function is to be called when executing the algorithm. It checks parameter integrity and whether the instruments are initialized. Calls the algorithm at the very end. |
| algorithm | ``device: Device``: The device under test <br><br> ``data: Dict``: Where the result is stored <br><br> ``instruments: Dict``: a dict of instruments <br><br> ``parameters: Dict``: a dict of parameters | ``Dict`` | Yes | This is the main algorithm. All parameters and instruments are passed as parameters to this function, handled by the LabExT backend. The user should fully implement the algorithm in this function.

### MeasParam
The class ``MeasParam`` acts as a direct superclass to all measurement parameters.

| Attribute | Type | Description |
|---|---|---|
| Value | Any | The value this parameter represents. |
| Unit | ``Str`` | The values unit |

| Function | Description |
|---|---|
| constructor | Value and Unit should be provided. If not, they are set to ``None`` |
| as_dict | Returns a dict with this ``MeasParam`` as the only member |

#### MeasParamInt
Represents a integer value.

#### MeasParamFloat
Represents a float value.

#### MeasParamString
Represents a string value.

#### MeasParamBool
Represents a bool value.

#### MeasParamList
Represents a bool list. Has a different constructor, that takes a list as argument to define all options. Will be rendered as a dropdown menu. The value will be one of the list elements.

#### MeasParamAuto
Automatically chooses the correct type of ``MeasParam``.


## How to build your own Measurement
To build your own measurement, you need to make sure the following criteria are met:
- All ``measurement`` member functions that are marked as 'user provided' need to be implemented.
- The algorithm needs to be correct.
- The measurement needs to be a standalone file, resting in the 'Measurements' folder.

The default workflow should be:
1) Create a new file in the measurements folder.
2) Import all the needed classes.
3) Create a new subclass of measurement.
4) Implement the new algorithm by overriding the ``Algorithm`` member function of the ``Measurement`` class.
5) Track all needed instruments, implement the static ``get_wanted_instrument`` member function of the ``Measurement`` class.
6) Track all needed parameters, implement the static ``get_default_parameter`` member function of the ``Measurement`` class.
7) Verify that the algorithm is correct.

## Standalone (No-GUI) Measurement
With the removal of the TK dependency, standalone measurements are easier. A user can now instantiate a 
measurement object, provide the needed instruments and start the measurement by calling the ``measure`` function
manually. The API will then check whether all instruments and parameters are set, and start the measuring process.
This is for example done in all unittests written for the measurements, c.f. `LabExT/Tests/Measurements` folder.

A code example on how to run a measurement standalone is given here:

```python
import matplotlib.pyplot as plt

# import instruments and measurement classes
from LabExT.Instruments.LaserSacher import LaserSacher
from LabExT.Instruments.PowerMeterN7744A import PowerMeterN7744A
from LabExT.Measurements.InsertionLoss1180 import InsertionLoss1180

# define instruments
instrs = {
    'Laser': LaserSacher(visa_address="ASRL/dev/ttySLController::INSTR", channel=None),
    'Power Meter 1': PowerMeterN7744A(visa_address="TCPIP0::ief-lab-n7744a-1.ee.ethz.ch::inst0", channel=3),
    'Power Meter 2': PowerMeterN7744A(visa_address="TCPIP0::ief-lab-n7744a-1.ee.ethz.ch::inst0", channel=2)
}

# define parameters
params = InsertionLoss1180.get_default_parameter()
params['use auxiliary second power meter for differential measurement'].value = True
params['wavelength start'].value = 1190.0
params['wavelength stop'].value = 1195.0
params['sweep speed'].value = 0.5

# setup return dictionary
data = InsertionLoss1180.setup_return_dict()

# run the measurement
meas = InsertionLoss1180()
meas.algorithm(None, data=data, instruments=instrs, parameters=params)

# do something with the data
plt.figure()
plt.plot(data['values']['wavelength [nm]'], data['values']['transmission [dBm]'])
plt.show()
```
