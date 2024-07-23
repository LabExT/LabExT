from LabExT.Measurements.MeasAPI import *
import pandas as pd
import time

class VibrationTest(Measurement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # calling parent constructor

        self.name = 'Vibration Test'
        self.settings_path = 'vib_settings.json'

    @staticmethod
    def get_default_parameter():
        return {
            'frequency': MeasParamFloat(value=100.0, unit='Hz'),
            'duration': MeasParamFloat(value=3.0, unit='s'),
            'center wavelength': MeasParamFloat(value=1550.0, unit='nm'),
            'wavelength range': MeasParamList(
                options = ['0.63', '1.27', '2.54', '5.09', '10.22', '20.58', '41.72', '85.78'],
                unit = 'nm'
            ),
            'DUT L': MeasParamFloat(value=0.0, unit='m'),
            'Plot Measurement Type': MeasParamList(
                options = ["INSERTION_LOSS", "GROUP_DELAY", 'CHROMATIC_DISPERSION', 'POLARIZATION_DEPENDENT_LOSS', 'POLARIZATION_MODE_DISPERSION', 'LINEAR_PHASE_DEVIATION', 'QUADRATIC_PHASE_DEVIATION', 'JONES_MATRIX_ELEMENT_AMPLITUDES', 'JONES_MATRIX_ELEMENT_PHASES', 'TIME_DOMAIN_AMPLITUDE', 'TIME_DOMAIN_WAVELENGTH', 'MIN_MAX_LOSS', 'SECOND_ORDER_PMD', 'PHASE_RIPPLE_LINEAR', 'PHASE_RIPPLE_QUADRATIC']
            ),
            'save_all_data': MeasParamBool(value=False),
            'filepath': MeasParamString(value='C:\\Users\\Luna\\Documents\\test.txt')
        }
    
    @staticmethod
    def get_wanted_instrument():
        return ["AUDIO", "OVA"]
    
    def algorithm(self, device, data, instruments, parameters):

        self.audio = instruments["AUDIO"]
        self.ova = instruments["OVA"]
        self.ova.open()
        
        frequency = parameters.get("frequency").value
        duration = parameters.get("duration").value
        audio_file = "temp.wav"

        center_wavelength = parameters.get('center wavelength').value
        wl_range = parameters.get('wavelength range').value
        plot_data_type = parameters.get('Plot Measurement Type').value
        save_all_data = parameters.get('save_all_data').value
        filepath = parameters.get('filepath').value
        DUT_L = parameters.get('DUT L').value

        self.audio.gen_tone(audio_file, rate=44100, T=duration, f=frequency)

        self.audio.play_audio(audio_file)

        self.ova.grab_data(
            dut_L = DUT_L,
            center_wavelength = center_wavelength,
            wl_range = wl_range,
            plot_data_type = plot_data_type,
            save_all_data = save_all_data,
            filepath = filepath,
        )

        df = pd.read_csv(filepath, delimiter="\t", skiprows=7, header=0)
        for col in df.columns:
            data['values'][col] = df[col].tolist()

        return data