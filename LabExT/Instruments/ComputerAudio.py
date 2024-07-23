#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Instruments.InstrumentAPI import Instrument
import wave
import pyaudio
import wavio
import numpy as np

class ComputerAudio(Instrument):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CHUNK = 1024
    
    def open(self):
        return
    
    def gen_tone(self, audio_file, rate=44100, T=3, f=100.0):
        t = np.linspace(0, T, int(T*rate), endpoint=False)
        x = np.sin(2*np.pi * f * t)
        wavio.write(audio_file, x, rate, sampwidth=3)

    def play_audio(self, audio_file):
        with wave.open(audio_file, 'rb') as wf:
            # Instantiate PyAudio and initialize PortAudio system resources (1)
            p = pyaudio.PyAudio()

            # Open stream (2)
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            # Play samples from the wave file (3)
            while len(data := wf.readframes(self.CHUNK)):  # Requires Python 3.8+ for :=
                stream.write(data)

            # Close stream (4)
            stream.close()

            # Release PortAudio system resources (5)
            p.terminate()