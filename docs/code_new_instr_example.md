# Example: Simple OSA Driver

For this example on how to get started, we'll be looking at a simple measurement using an Optical 
Spectrum Analyzer (OSA). We will need to do two things:

1. Implement the measurement in a new measurement class which we will call `ReadOSA`
2. and interface the OSA via the instrument driver class called `OpticalSpectrumAnalyzerAQ6370C`

This how-to describes the coding of the simple driver for the OSA. For this example we will use the
[Yokagawa AQ6370C model](https://tmi.yokogawa.com/eu/solutions/discontinued/aq6370c-optical-spectrum-analyzer/) -
it will be interfaced via the instrument driver class called `OpticalSpectrumAnalyzerAQ6370C`. It implements the 
instrument driver matching the measurement written in the [Measurement coding How-To](./code_new_meas_example.md).

You can find the final file of the instrument driver at
[LabExT/Instruments/OpticalSpectrumAnalyzerAQ6370C.py](https://github.com/LabExT/LabExT/). We encourage
you to read this code file in parallel while we explain the various parts here.

## Instrument Manuals
At the beginning of writing an instrument drivers, you should search and download the user and programmer manuals for 
instrument in question. For the AQ6370C, it's the following two files:

* [User Manual (IMAQ6370C-01EN.pdf)](https://cdn.tmi.yokogawa.com/IMAQ6370C-01EN.pdf)
* [Remote Control Manual (IMAQ6370C-17EN.pdf)](https://cdn.tmi.yokogawa.com/1/6057/files/IMAQ6370C-17EN.pdf)

Now we are ready to implement a sub-class of `Instrument` as our driver:

## Instrument Driver

The point of an instrument driver is to offer a Python class which implements single or groups of
[SCPI commands](https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments) in its properties
or methods. Common operations on the instrument should be grouped together so they are easily accessible in 
LabExT's measurements.

All instrument drivers are subclasses of `Instrument`. You only need to implement any instrument-specific functionality.
Let's start by writing the three most basic members: `__init__`, `open` and `close`.

### Basic members

#### \_\_init\_\_
```python
def __init__(self, *args, **kwargs):
    # call Instrument constructor, creates VISA instrument
    super().__init__(*args, **kwargs)

    self.sens_modes = ['NHLD', 'NAUT', 'MID', 'HIGH1', 'HIGH2', 'HIGH3', 'NORM']
    self._sweep_modes = ['SING', 'REP', 'AUTO', 'SEGM']
    self._traces = ['TRA', 'TRB', 'TRC', 'TRD', 'TRE', 'TRF', 'TRG']

    self._net_timeout_ms = kwargs.get("net_timeout_ms", 30000)

    self.networked_instrument_properties.extend([
        'startwavelength',
        'stopwavelength',
        'centerwavelength',
        'sweepresolution',
        'n_points',
        'sens_mode',
        '_sweep_mode',
        '_active_trace'
    ])
```
The constructor takes `*args` and `**kwargs` as arguments. `*args` includes the VISA address and (optional) channel, 
`**kwargs` miscellaneous other parameters (such as a specific timeout or gpib address). We pass those on to the parent 
constructor which initializes the instrument instance and sets various member variables. Then we define ourselves certain 
members for later use. In this case we'll create `self.sens_modes` (which includes the sensitivity modes the OSA supports), 
`self._sweep_modes` (sweep modes the instrument supports) and `self._traces` (same). Note that the 
latter two are private and will only be used within the class. We also extend the (in the parent constructor created member) 
`self.networked_instrument_properties` and add the names of all the member functions. (We're getting ahead of ourselves, 
we'd normally add these after having implemented them.)  

#### open
We call the parent member `open` and then add any additional functionality we need. The Yokagawa OSA requires different 
terminators than standard, so we set those. Furthermore we need to follow its authentication procedure which must run as 
such: write 'open "anonymous"'; read 'AUTHENTICATE CRAM-MD5.'; write an empty string, read 'ready'. These instrument 
specific settings and procedures can all be found in the instruments programming manual.

```python
    def open(self):
        """
        Open the connection to the instrument. Automatically re-uses any old connection if it is already open.

        :return: None
        """
        super().open()

        self._inst.read_termination = '\r\n'

        authentication = self._inst.query('open "anonymous"')
        ready = self._inst.query(" ")

        if authentication != 'AUTHENTICATE CRAM-MD5.' or ready != 'ready':
            raise InstrumentException('Authentication failed')
```

!!! note
    We do not override the `close` method as the Yokagawa OSA does not require any specific steps to close a
    connection, so we don't need to implement `close` but simply inherit it from the parent.

### Instrument-specific functionality

The rest of the instrument driver class can be coarsely divided into two categories: properties/setters (set or query 
instrument parameters/settings) and execution routines (set up and run something on the instrument). 
We'll implement an example for both.

#### property/setter: centerwavelength
To query the current center wavelength, we can use the `request` method from the `Instrument` class. The corresponding 
SCPI command is `:SENS:WAV:CENT?`. Responses are sent as strings, so we convert to float. The OSA returns values in units
of meters, we internally always use nanometers so we convert by multiplying with one billion.
Additionally we add the `@property` decorator.
```python
@property
def centerwavelength(self):
    """
    Returns current center wavelength [nm].
    :return: center wavelength in nm
    """
    return float(self.request(':SENS:WAV:CENT?')) * 1e9
```

To set a new center wavelength, we use the `command` method from the `Instrument` class. The SCPI command is 
`:SENS:WAV:CENT <wl>nm` where `<wl>` corresponds to the new center wavelength in nm rounded to three decimal places.
As an precaution, we check whether the new parameter is in the valid range for our OSA model and 
by using the `command` method of `Instrument` which includes error checking functionality.
Additionally, we add the `@centerwavelength.setter` decorator.
```python
@centerwavelength.setter
def centerwavelength(self, centerwavelength_nm):
    """
    Sets center wavelength
    :param centerwavelength_nm: wavelength in nm
    """
    if not 600 <= centerwavelength_nm <= 1700:
        raise ValueError('Center wavelength is out of range. Must be between 600 nm and 1700 nm.')

    self.command(':SENS:WAV:CENT {center:0.3f}nm'.format(center=centerwavelength_nm))
```

!!! note
    The rest of the properties (`span`, `sweepresolution`, `n_points`, and others) are implemented in a similar manner
    using their respective SCPI commands.

#### method: get_data
These routines can be implemented just like the property/setter above. Simply lose the decorator. For example, to query 
the data collected during a run of the OSA, we would proceed as such: 

- set the correct data format `self.command('FORMAT:DATA ASCII')`
- query the x-data `self.query_ascii_values(':TRAC:DATA:X? <some trace>')`
- query the y-data `self.query_ascii_values(':TRAC:DATA:Y? <some trace>')`

As the OSA returns the data in pure ASCII format, we use the `query_ascii_values` method from the `Instrument` class and 
save the returned data either to a numpy array or a list according to our preferences. Additionally, we do any needed 
unit conversions.

```python
def get_data(self):
    """
    Get the spectrum data of the measurement. Units depend on the setting on the instrument.
    :return: 2D list with [X-axis Data, Y-Axis Data]
    """
    # Make sure the correct data format is used
    # set data format to ascii
    self.command('FORMAT:DATA ASCII')
    # find the currently active trace
    act_trace = self._active_trace
    
    # get the wavelength data of the active trace in ascii format
    wavelength_samples = self.query_ascii_values(':TRAC:DATA:X? {trace}'.format(
        trace=act_trace),
        container=np.ndarray) * 1e9 # data is returned in unit [m], we want it in [nm]
    # get the power data of the active trace in ascii format
    power_samples = self.query_ascii_values(':TRAC:DATA:Y? {trace}'.format(
        trace=act_trace),
        container=list)

    return [wavelength_samples.tolist(), power_samples]
```

Aside from the `get_data` method, the driver also implements the `run` method: It triggers a single wavelength
sweep and waits until the instrument finished acquiring data.

### instruments.config

Finally, we have to adapt the instrument.config of LabExT. Let's assume we have one of these Yokogawa OSAs
attached on the network at IP 12.23.34.65. As described on the [configuration page](./settings_configuration.md),
we extend the instruments.config OSA class section with the following line:
```json
{"visa": "TCPIP0::12.23.34.65::10001::SOCKET", "class": "OpticalSpectrumAnalyzerAQ6370C", "channels": []}
```
As described in the remote control manual of the OSA, the network interface runs with over a simple TCP/IP socket
on the port 10001. In the `class` part, we write the name of the driver class we just wrote above. 

Don't forget to load your new `instruments.config` in the `Settings -> Instruments Connection Debugger` menu!
