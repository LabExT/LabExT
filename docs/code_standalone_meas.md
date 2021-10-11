# Standalone (No-GUI) Measurement
If you want to use a LabExT measurement outside of the GUI (e.g. in scripts), you can instantiate a 
measurement object, provide the needed instruments and start the measurement by calling the `algorithm` function.
manually. The API will then check whether all instruments and parameters are set, and start the measuring process.
This is for example done in all unittests written for the measurements, c.f. `LabExT/Tests/Measurements` folder.

A code example on how to run a measurement standalone is given here:

```python
import matplotlib.pyplot as plt

# import instruments and measurement classes
from LabExT.Instruments.LaserMainframeKeysight import LaserMainframeKeysight
from LabExT.Instruments.PowerMeterN7744A import PowerMeterN7744A
from LabExT.Measurements.InsertionLossSweep import InsertionLossSweep

# define instruments
instrs = {
    'Laser': LaserMainframeKeysight(visa_address="TCPIP0::ief-lab-8164b-1.ee.ethz.ch::inst0", channel=0),
    'Power Meter': PowerMeterN7744A(visa_address="TCPIP0::ief-lab-n7744a-1.ee.ethz.ch::inst0", channel=2)
}

# define parameters
params = InsertionLossSweep.get_default_parameter()
params['wavelength start'].value = 1190.0
params['wavelength stop'].value = 1195.0
params['sweep speed'].value = 0.5

# setup return dictionary
data = InsertionLossSweep.setup_return_dict()

# run the measurement
meas = InsertionLossSweep()
meas.algorithm(None, data=data, instruments=instrs, parameters=params)

# do something with the data
plt.figure()
plt.plot(data['values']['wavelength [nm]'], data['values']['transmission [dBm]'])
plt.show()
```
