from LabExT.Measurements.MeasAPI import *
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

class LUNA_sweep_Oband_OFDR(Measurement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'Luna_sweep'
        self.settings_path = 'Luna_sweep_settings.json'
        self.ova = None

    @staticmethod
    def get_default_parameter():
        return {
            'center wavelength': MeasParamFloat(value=1298.0, unit='nm'),
            'wavelength range': MeasParamList(
                options = ['0.88', '1.76', '3.53', '7.08', '14.25', '28.82', '58.97'],
                unit = 'nm'
            ),
            'Start DUT L': MeasParamFloat(value=0.2, unit='m'),
            'End DUT L': MeasParamFloat(value=10.0, unit='m'), 
            'Step DUT L': MeasParamFloat(value=0.4, unit='m'),
            'Group Index': MeasParamFloat(value=1.5, unit=''),
            'save_all_data': MeasParamBool(value=False),
            'filepath': MeasParamString(value='C:\\Users\\gtufocl\\Documents\\test.txt')
        }
    
    @staticmethod
    def get_wanted_instrument():
        return ['OVA']
    
    def algorithm(self, device, data, instruments, parameters):
        self.ova = instruments["OVA"]
        self.ova.open()

        center_wavelength = parameters.get('center wavelength').value
        wl_range = parameters.get('wavelength range').value
        plot_data_type = 'TIME_DOMAIN_AMPLITUDE'
        save_all_data = parameters.get('save_all_data').value
        filepath = parameters.get('filepath').value
        start_DUT_L = parameters.get('Start DUT L').value
        end_DUT_L = parameters.get('End DUT L').value
        step_DUT_L = parameters.get('Step DUT L').value
        group_index = parameters.get('Group Index').value
        meas_type = "Reflection"

        self.logger.debug("Starting Luna sweep measurement")

        for DUT_L in np.arange(start_DUT_L, end_DUT_L, step_DUT_L):
            print(f'DUT_L: {DUT_L}')

            result, new_dut_L = self.ova.grab_data(
                dut_L = DUT_L,
                center_wavelength = center_wavelength,
                wl_range = wl_range,
                plot_data_type = plot_data_type,
                save_all_data = save_all_data,
                filepath = filepath,
                meas_type = meas_type,
                group_index = group_index,
                X_axis_units = 4 # 4 = length, 0 = wavelength
            )

            x_temp = np.array(result[0, 0, :].tolist())
            y_temp = np.array(result[0, 1, :].tolist())
            min_x = np.min(x_temp)
            max_x = np.max(x_temp)
            middle_x = (min_x + max_x) / 2 
            step_size_x = x_temp[1] - x_temp[0]
            if DUT_L == start_DUT_L:
                min_idx = np.argmin(np.abs(x_temp - middle_x + step_DUT_L/2))
                max_idx = np.argmin(np.abs(x_temp - middle_x - step_DUT_L/2 + step_size_x))
                x = x_temp[min_idx:max_idx] - middle_x + step_DUT_L/2
                y = y_temp[min_idx:max_idx]
            else:
                min_idx = np.argmin(np.abs(x_temp - middle_x + step_DUT_L/2))
                max_idx = np.argmin(np.abs(x_temp - middle_x - step_DUT_L/2 + step_size_x))
                x_temp = x_temp[min_idx:max_idx] - middle_x + step_DUT_L/2 + np.max(x)
                y_temp = y_temp[min_idx:max_idx]
                x = np.concatenate((x, x_temp))
                y = np.concatenate((y, y_temp))

        data['values']['Length [m]'] = x.tolist()
        data['values']['Time Domain Amplitude (dB)'] = y.tolist()   

        self.logger.debug("Finished Luna sweep measurement")
        
        return data