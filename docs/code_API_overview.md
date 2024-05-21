# LabExT-included APIs

## Instrument Drivers

The files in the `InstrumentAPI` folder implement all the basic necessary instrument-related functionality, mainly 
communication via the VISA protocol, error checks, setup and teardown. We subclass our instrument drivers to the 
`Instrument` class. You can use them as is or override them in the child class of your instrument.

### Communication
LabExT uses the VISA protocol to communicate with instruments. We assume that the instruments understand commands 
written according to the SCPI syntax. The two parts - VISA and SCPI - are independent of each other. If your instrument 
dates back to the pre-SCPI era or follows some esoteric syntax, then you can still use LabExT but you might need to 
override all methods defined in `Instrument.py` that use 
`query`, `request`, `command` or `write` and change the command strings. Additionally, you might need to redefine the 
`error_query_string` in your child class. Consult your instruments programming manual for the correct command strings.

The `instrument` class offers the following methods to communicate with your instrument.

#### write
```self.write('SOMETHING')``` sends the string to the instrument without any additional error or completion checks.
#### command
```self.command('SOMETHING')``` uses the `write` method to send the command, waits for the instrument to signal 
completion and then checks the error queue. If any errors arose during communication then a Exception is raised.
#### query
```self.query('SOMETHING?')``` sends the string to the instrument and reads the response.
#### request
```self.request('SOMETHING?')``` sends the string to the instrument, waits for completion, queries the error register 
and then returns the instruments answer.

The class also offers shortcut functions if you're working with multi-channelled instruments. Instead of the above-mentioned 
methods use the corresponding `_channel` version and pass the channel number as well as the command string.  
To receive data in raw byte or ASCII format use the members `query_raw_bytes` and `query_ascii_values`.

Please see [the example on how to implement a new instrument driver](./code_new_instr_example.md) and also the 
[the InstrumentAPI code reference](./reference_InstrumentAPI.md) for a complete listing of the available methods.

## Measurement Algorithms

The files in the `MeasAPI` folder implement the necessary classes for the LabExT GUI to recognize a measurement
and to be able to display the correct GUI elements for parameters and instrument selection.

The default workflow for implementing a new measurement should be:

1. Create a new file in the measurements folder.
2. Import all the needed classes.
3. Create a new subclass of measurement.
4. Implement the new algorithm by overriding the ``algorithm`` member function of the ``Measurement`` class.
5. Track all needed instruments, implement the static ``get_wanted_instrument`` member function of the ``Measurement`` class.
6. Track all needed parameters, implement the static ``get_default_parameter`` member function of the ``Measurement`` class.
7. Verify that the algorithm is correct.

See [the example on how to implement a new measurement](./code_new_meas_example.md) and also the
[MeasAPI code reference](./reference_MeasAPI.md).

!!! info
    Measurement code is also usable outside of the LabExT GUI [as standalone code](./code_standalone_meas.md).

## Export Formats

The files in the `Exporter` folder implement the necessary classes for the LabExT GUI to recognize a new export format. LabExT can be extended to export measurements into any file format, or even upload measurement data to a remote server.

See [the example on how to implement a new export format](./code_new_export_example.md)
<!-- and also the
[MeasAPI code reference](./reference_MeasAPI.md).

!!! info
    Measurement code is also usable outside of the LabExT GUI [as standalone code](./code_standalone_meas.md). -->

