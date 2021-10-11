# The `data` Dictionary

In this section, we describe the dictionary which describes one measurement execution, including data and all
meta-data. This dictionary is written to every .JSON save file LabExT creates. Naturally, some parts need to be
filled during the `algorithm` method of each [Measurement](./reference_MeasAPI.md). 

## General Structure

The  dictionary argument `data` passed into the `algorithm` of a measurement contains all data and meta-data of one
measurement execution. These are the most important key-value pairs:

-   `'measurement name' : <name of the measurement, string>`
-   `'timestamp' : <timestamp in ISO-format, string>`
-   `'device' : {<device information, dict>}`
-   `'instruments' : {<instruments, dict>}`
-   `'measurement settings' : {<measurement specific settings, dict>}` (provide this in `Measurement.algorithm()`!)
-   `'values' : {<measured values, dict>}` (provide this in `Measurement.algorithm()`!)

The user is free to add other key-value pairs to the dictionary in the `algorithm` method. This dictionary is saved
during and directly after the measurement on the disk in the `.json` format.

!!! note
    When writing your own Measurement, you only need to fill the `'values'` and `'measurement settings'` keys  
    in the implementation of the `algorithm()` method. The [Measurement class](./reference_MeasAPI.md) provides a simple
    function that checks if all necessary data objects are there. You can use it in the `algorithm()` method by
    calling `self._check_data(data)`.

## Values

The value of the key-value pair 'values':{} is a dictionary that contains the measured data. Any string can be used as
a key, the value has to be a list. This leads to the following structure:

```python
data['values']['resistance [Ohm]'] = [1, 2, 3, 4]
data['values']['current [A]'] = [5, 6, 7, 8]
data['values']['voltage [V]'] = [10, 20, 30, 40]
```

Upon selection of a measurement in the measurement-table, the user can choose which two data-sets (resistance, current,
voltage) should be plotted against each other in the axes selection dropdown menus. The LabExT GUI allows to plot any
two lists against each other in the `data['values']` dict.

!!! attention
    If two lists are plotted and are not of the same lengths, LabExT will cut the samples of the longer list and not 
    plot them.

## Device

The value of the key-value pair 'device':{} is a dictionary that contains all available information about the device on
which the measurement was taken. This part gets filled automatically by the LabExT GUI. Itr includes (but is not
limited to) the following:

```python
data['device']['id'] = 123
data['device']['in_position'] = [-234.52, 564.2]
data['device']['out_position'] = [-14.52, 525.3]
data['device']['type'] = 'MZM'
```

## Instruments

The value of the key-value pair 'instruments':{} is a dictionary that contains all available information about the
instruments and their settings. The keys of the dictionary are the instrument names and the value is another dictionary
that contains all the instrument's settings.

This part gets filled automatically by the LabExT GUI which reads out all properties from all involved instruments.
This could look like the following:

```python
data['instruments']['Power Meter']['wavelength'] = 1560.00
data['instruments']['Power Meter']['unit'] = 'dBm'
data['instruments']['Power Meter']['range'] = 10
data['instruments']['Power Meter']['averagetime'] = 0.00025
```

## Measurement settings

The value of the key-value pair 'measurement settings':{} is a dictionary that contains all available information about
the measurement and its settings. The keys of the dictionary are the names of the settings, and the values are in turn
again a dict with value and units:

```python
data['measurement settings']['wavelength start'] = {'value': 1520.0, 'unit': 'nm'}
data['measurement settings']['wavelength stop'] = {'value': 1600.0, 'unit': 'nm'}
data['measurement settings']['sweep speed'] = {'value': 20.0, 'unit': 'nm/s'}
```

!!! note
    You should fill the measurement settings from inside `algorithm()` with the final parameters you used. We decided
    to not automatically copy them as some parameters might need to be adjusted programmatically.


## Custom Additions

As stated before, the user can freely add new key-value pairs, which then will get saved with all the other values.
For instance, you can add something like:

```python
data['custom preference'] = 'some value'
```
