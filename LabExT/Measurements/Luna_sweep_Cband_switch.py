from LabExT.Measurements.MeasAPI import *
import pandas as pd
import os

class LUNA_sweep_Cband_switch(Measurement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'Luna_sweep'
        self.settings_path = 'Luna_sweep_settings.json'
        self.ova = None

    @staticmethod
    def get_default_parameter():
        return {
            'Switch Port: M = 1': MeasParamInt(value=1, unit='N Port'),
            'Switch Port: M = 2': MeasParamInt(value=2, unit='N Port'),
            'Switch Port: M = 3': MeasParamInt(value=3, unit='N Port'),
            'Switch Port: M = 4': MeasParamInt(value=4, unit='N Port'),
            'center wavelength': MeasParamFloat(value=1550.0, unit='nm'),
            'wavelength range': MeasParamList(
                options = ['0.63', '1.27', '2.54', '5.09', '10.22', '20.58', '41.72', '85.78'],
                unit = 'nm'
            ),
            'Plot Measurement Type': MeasParamList(
                options = ["INSERTION_LOSS", "GROUP_DELAY", 'CHROMATIC_DISPERSION', 'POLARIZATION_DEPENDENT_LOSS', 'POLARIZATION_MODE_DISPERSION', 'LINEAR_PHASE_DEVIATION', 'QUADRATIC_PHASE_DEVIATION', 'JONES_MATRIX_ELEMENT_AMPLITUDES', 'JONES_MATRIX_ELEMENT_PHASES', 'TIME_DOMAIN_AMPLITUDE', 'TIME_DOMAIN_WAVELENGTH', 'MIN_MAX_LOSS', 'SECOND_ORDER_PMD', 'PHASE_RIPPLE_LINEAR', 'PHASE_RIPPLE_QUADRATIC']
            ),
            'DUT L': MeasParamFloat(value=0.0, unit='m'),
            'enable averaging': MeasParamBool(value=False),
            'number of averages': MeasParamInt(value=1, unit='scans'),
            'save_all_data': MeasParamBool(value=False),
            'filepath': MeasParamString(value='C:\\Users\\Luna\\Documents\\test.txt'),
            'Measurement Type': MeasParamList(
                options= ["Transmission", "Reflection"]
            )
        }
    
    @staticmethod
    def get_wanted_instrument():
        return ['OVA', 'Switch']
    
    def algorithm(self, device, data, instruments, parameters):
        self.ova = instruments["OVA"]
        self.ova.open()
        print("Connecting to Switch")
        self.switch = instruments["Switch"] 
        self.switch.open()
        print("Switch connected")
        self.switch.connect([(1, self.parameters['Switch Port: M = 1'].value), (2, self.parameters['Switch Port: M = 2'].value), (3, self.parameters['Switch Port: M = 3'].value), (4, self.parameters['Switch Port: M = 4'].value)])
        print("Switch channels set to: M1 = {}, M2 = {}, M3 = {}, M4 = {}".format(
            self.parameters['Switch Port: M = 1'].value,
            self.parameters['Switch Port: M = 2'].value,
            self.parameters['Switch Port: M = 3'].value,
            self.parameters['Switch Port: M = 4'].value
        ))
        self.switch.close()

        center_wavelength = parameters.get('center wavelength').value
        wl_range = parameters.get('wavelength range').value
        plot_data_type = parameters.get('Plot Measurement Type').value
        save_all_data = parameters.get('save_all_data').value
        filepath = parameters.get('filepath').value
        DUT_L = parameters.get('DUT L').value
        meas_type = parameters.get('Measurement Type').value
        enable_averaging = parameters.get('enable averaging').value
        num_averages = max(1, int(parameters.get('number of averages').value))

        os.remove(filepath)  # Remove the file after reading if not needed anymore

        with open(filepath, 'w') as f:
            pass  # No content is written, resulting in an empty file

        self.logger.debug("Starting Luna sweep measurement")
        print("Starting Luna sweep measurement")
        
        if save_all_data:
            filesize = 0
            num_tries = 0
            while filesize == 0:
                num_tries += 1
                print(f"Attempt {num_tries} to run the OVA measurement...")
                result, new_dut_L = self.ova.grab_data(
                    dut_L = DUT_L,
                    center_wavelength = center_wavelength,
                    wl_range = wl_range,
                    plot_data_type = plot_data_type,
                    save_all_data = save_all_data,
                    filepath = filepath,
                    meas_type = meas_type,
                    enable_averaging = enable_averaging,
                    num_averages = num_averages
                )
                filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        else:
            result, new_dut_L = self.ova.grab_data(
                dut_L = DUT_L,
                center_wavelength = center_wavelength,
                wl_range = wl_range,
                plot_data_type = plot_data_type,
                save_all_data = save_all_data,
                filepath = filepath,
                meas_type = meas_type,
                enable_averaging = enable_averaging,
                num_averages = num_averages
            )

        self.logger.debug("Finished Luna sweep measurement")
        print("Finished Luna sweep measurement")

        if save_all_data:
            df = pd.read_csv(filepath, delimiter="\t", skiprows=7, header=0)
            for col in df.columns:
                data['values'][col] = df[col].tolist()
        else:
            if plot_data_type == "INSERTION_LOSS":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Insertion Loss (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "GROUP_DELAY":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Group Delay (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "CHROMATIC_DISPERSION":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Chromatic Dispersion (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "POLARIZATION_DEPENDENT_LOSS":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Polarization Dependent Loss (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "POLARIZATION_MODE_DISPERSION":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Polarization Mode Dispersion (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "LINEAR_PHASE_DEVIATION":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Linear Phase Deviation(dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "QUADRATIC_PHASE_DEVIATION":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Quadratic Phase Deviation (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "JONES_MATRIX_ELEMENT_AMPLITUDES":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Jones Matrix Element Amplitudes A'] = result[0, 1, :].tolist()
                data['values']['Jones Matrix Element Amplitudes B'] = result[1, 1, :].tolist()
                data['values']['Jones Matrix Element Amplitudes C'] = result[2, 1, :].tolist()
                data['values']['Jones Matrix Element Amplitudes D'] = result[3, 1, :].tolist()
            elif plot_data_type == "JONES_MATRIX_ELEMENT_PHASES":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Jones Matrix Element Phases A'] = result[0, 1, :].tolist()
                data['values']['Jones Matrix Element Phases B'] = result[1, 1, :].tolist()
                data['values']['Jones Matrix Element Phases C'] = result[2, 1, :].tolist()
                data['values']['Jones Matrix Element Phases D'] = result[3, 1, :].tolist()
            elif plot_data_type == "TIME_DOMAIN_AMPLITUDE":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Time Domain Amplitude (dB)'] = result[0, 1, :].tolist()
            elif plot_data_type == "TIME_DOMAIN_WAVELENGTH":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Time Domain Wavelength (nm)'] = result[0, 1, :].tolist()
            elif plot_data_type == "MIN_MAX_LOSS":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Min Insertion Loss (dB)'] = result[0, 1, :].tolist()
                data['values']['Max Insertion Loss (dB)'] = result[1, 1, :].tolist()
            elif plot_data_type == "SECOND_ORDER_PMD":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Second Order PMD'] = result[0, 1, :].tolist()
            elif plot_data_type == "PHASE_RIPPLE_LINEAR":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Phase Ripple Linear'] = result[0, 1, :].tolist()
            elif plot_data_type == "PHASE_RIPPLE_QUADRATIC":
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['Phase Ripple Quadratic'] = result[0, 1, :].tolist()
            else:
                data['values']['wavelength [nm]'] = result[0, 0, :].tolist()
                data['values']['transmission (dB)'] = result[0, 1, :].tolist()

        return data