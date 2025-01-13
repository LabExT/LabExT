from LabExT.Measurements.MeasAPI import *
import time
import numpy as np

class IL_power_and_wl_sweep_trigger(Measurement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'IL_power_and_wl_sweep_trigger'
        self.settings_path = 'IL_power_and_wl_sweep_trigger_settings.json'
        self.instr_laser = None
        self.labjack = None

    @staticmethod
    def get_default_parameter():
        return {
            'start wavelength': MeasParamFloat(value=1240.0,unit='nm'),
            'stop wavelength': MeasParamFloat(value=1380.0,unit='nm'),
            'wavelength step': MeasParamFloat(value=0.1,unit='nm'),
            'power start': MeasParamFloat(value=0.0,unit='dB'),
            'power stop': MeasParamFloat(value=13.0,unit='dB'),
            'power step': MeasParamFloat(value=1.0, unit='dB'),
            'step delay': MeasParamFloat(value=0.1, unit='s'),
        }

    @staticmethod
    def get_wanted_instrument():
        return ['Laser', 'Power Meter 1', 'Power Meter 2', 'Power Meter 3', 'Power Meter 4']
    
    def algorithm(self, device, data, instruments, parameters):
        # get the parameters
        start_lambda = parameters.get('start wavelength').value
        stop_lambda = parameters.get('stop wavelength').value
        step_lambda = parameters.get('wavelength step').value
        start_power = parameters.get('power start').value
        stop_power = parameters.get('power stop').value
        step_power = parameters.get('power step').value
        step_delay = parameters.get('step delay').value
        

        # get instrument pointers
        self.instr_laser = instruments['Laser']
        self.instr_pms = [instruments[f'Power Meter {1}'], instruments[f'Power Meter {2}'], instruments[f'Power Meter {3}'], instruments[f'Power Meter {4}']]


        # open connection to Laser & PM
         # open connection to power supply
        self.instr_laser.open()
        for pm in self.instr_pms:
            pm.open()
        self.lj = self.instr_pms[0].lj


        # clear errors
        self.instr_laser.clear()
    

        # Ask minimal possible wavelength
        min_lambda = float(self.instr_laser.min_lambda)
        print("The following is the minimum possible lambda:")
        print(min_lambda)

        # Ask maximal possible wavelength
        max_lambda = float(self.instr_laser.max_lambda)
        print("The following is the maximum possible lambda:")
        print(max_lambda)

        
        if start_lambda < min_lambda or start_lambda > max_lambda:
            start_lambda = min_lambda
            parameters['start wavelength'].value = start_lambda
            self.logger.warning('start_lambda has been changed to bottom of range: ' + str(start_lambda))
        
        if stop_lambda < min_lambda or stop_lambda > max_lambda:
            stop_lambda = max_lambda
            parameters['stop wavelength'].value = stop_lambda
            self.logger.warning('stop_lambda has been changed to end of range: ' + str(stop_lambda))

        if start_power < 0 or start_power > 13:
            start_power = 0
            parameters['start power'].value = start_power
            self.logger.warning('start_power has been changed to start of range: ' + str(start_power))

        if stop_power < 0 or stop_power > 13:
            stop_power = 13
            parameters['stop power'].value = stop_power
            self.logger.warning('stop_power has been changed to end of range: ' + str(stop_power))



        # Laser settings
        self.instr_laser.unit = 'dBm'
        self.instr_laser.power = start_power
        self.instr_laser.wavelength = start_lambda
        self.instr_laser.enable = True

        self.logger.info("About to start power and wavelength sweep.")

        power_data = np.arange(start_power, stop_power + step_power, step_power)
        wavelength_data = np.arange(start_lambda,stop_lambda + step_lambda, step_lambda)
        optical_power_result_list0 = []
        optical_power_result_list1 = []
        optical_power_result_list2 = []
        optical_power_result_list3 = []
        wavelength_result_list = []
        power_result_list = []
        print(f'Step Delay: {step_delay}')
        for lam in wavelength_data:
            for pow in power_data:
                self.instr_laser.power = pow
                self.instr_laser.wavelength = lam
                print(f'Wavelength: {lam}')
                time.sleep(step_delay)
                wavelength_result_list.append(self.instr_laser.wavelength)
                power_result_list.append(self.instr_laser.power)
                optical_power_result_list0.append(self.instr_pms[0].fetch_power())
                optical_power_result_list1.append(self.instr_pms[1].fetch_power())
                optical_power_result_list2.append(self.instr_pms[2].fetch_power())
                optical_power_result_list3.append(self.instr_pms[3].fetch_power())


        # convert numpy float32/float64 to python float
        data['values']['tx_wavelength'] = wavelength_result_list
        data['values']['tx_power'] = power_result_list
        #data['values']['optical_power'] = optical_power_result_list
        data['values'][f'transmission AIN0 [dBm]'] = optical_power_result_list0
        data['values'][f'transmission AIN1 [dBm]'] = optical_power_result_list1
        data['values'][f'transmission AIN2 [dBm]'] = optical_power_result_list2
        data['values'][f'transmission AIN3 [dBm]'] = optical_power_result_list3


        self.instr_laser.enable = False
        # close connection
        self.instr_laser.close()
        self.instr_pms[0].close()


        # sanity check if data contains all necessary keys
        self._check_data(data)

        return data