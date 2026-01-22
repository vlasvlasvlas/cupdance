import numpy as np
from .base import Synth, Oscillator

class ExoticSynth(Synth):
    def __init__(self, sr=44100):
        super().__init__(sr)
        self.carrier = Oscillator(sr, freq=440, waveform='sine')
        self.modulator = Oscillator(sr, freq=1200, waveform='sine')
        
        self.params = {"pitch": 0.5, "metal": 0.5}

    def set_param(self, name, value):
        self.params[name] = value
        if name == "pitch":
             freq = 110.0 * (2.0 ** (value * 3.0)) 
             self.carrier.freq = freq
             
        elif name == "metal":
             # Modulator ratio
             ratio = 1.0 + (value * 5.5) # 1.0 to 6.5
             self.modulator.freq = self.carrier.freq * ratio

    def generate(self, num_frames):
        c = self.carrier.next(num_frames)
        m = self.modulator.next(num_frames)
        
        # Ring Modulation: Carrier * Modulator
        sig = c * m
        
        # Or FM: sin(c + m * index) ... sticking to RingMod for "Metal" sound
        
        stereo = np.column_stack((sig, sig))
        return stereo * self.gain
