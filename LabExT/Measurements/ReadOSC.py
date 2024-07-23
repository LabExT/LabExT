from typing import Dict
from LabExT.Measurements.MeasAPI import *
import pandas as pd
import time

from LabExT.Measurements.MeasAPI.Measparam import MeasParam

class ReadOSC(Measurement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'ReadOSC'
        self.settings_path = 'ReadOSC_settings.json'
        self.instr_osc = None

    @staticmethod
    def get_default_parameter() -> Dict[str, MeasParam]:
        return {
            'center frequency': MeasParamFloat(value=100.0, unit='Hz'),
            'amplitude': MeasParamFloat(value=1.0, unit='V'),
            'duration': MeasParamFloat(value=3.0, unit='s'),
            'save_all_data': MeasParamBool(value=False),
            'filepath': MeasParamString(value='C:\\Users\\Luna\\Documents\\test.txt')
        }
    
    @staticmethod
    def get_wanted_instrument() -> list:
        return ['OSC']
    
    def algorithm(self, device, data, instruments, parameters):
        self.instr_osc = instruments['OSC']
        self.instr_osc.open()
        # print(self.instr_osc.idn())
        print(self.instr_osc._inst.query('*IDN?'))
        # 
        # self.instr_osc.write("DAT:STOP 1000")
        settings = self.instr_osc._inst.query('DAT?')
        print(settings)

        time.sleep(1)
        data = self.instr_osc._inst.query_binary_values('CURV?', datatype='h', is_big_endian=True)
        # print(settings)

        # time_data, wave_data = self.instr_osc.get_waveform()

        data['values']['time (s)'] = [1]
        # data['values']['voltage (V)'] = wave_data

        return data