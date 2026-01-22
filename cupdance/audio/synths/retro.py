import numpy as np
from .base import Synth, Oscillator

class RetroSynth(Synth):
    def __init__(self, sr=44100):
        super().__init__(sr)
        self.osc1 = Oscillator(sr, freq=110, waveform='saw')
        self.osc2 = Oscillator(sr, freq=110, waveform='saw')
        
        # Params
        self.params = {"pitch": 0.5, "detune": 0.5}

    def set_param(self, name, value):
        self.params[name] = value
        if name == "pitch":
             freq = 55.0 * (2.0 ** (value * 4.0)) 
             detune_amt = 0.005 + (self.params["detune"] * 0.02)
             
             self.osc1.freq = freq * (1.0 - detune_amt)
             self.osc2.freq = freq * (1.0 + detune_amt)

    def generate(self, num_frames):
        out1 = self.osc1.next(num_frames)
        out2 = self.osc2.next(num_frames)
        
        # Wide Stereo: Osc1 Left, Osc2 Right
        mix_L = out1 * 0.7
        mix_R = out2 * 0.7
        
        stereo = np.column_stack((mix_L, mix_R))
        return stereo * self.gain
