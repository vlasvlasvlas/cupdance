import numpy as np
from .base import Synth, Oscillator

class ChipSynth(Synth):
    def __init__(self, sr=44100):
        super().__init__(sr)
        self.osc1 = Oscillator(sr, freq=110, waveform='square')
        self.osc2 = Oscillator(sr, freq=220, waveform='saw') # "Saw" for NES-like triangle bass effect? 8bit usually square/pulse.
        
        # Params
        # 0: Pitch/Freq
        # 1: Filter/Tone (PWM width?)
        # 2: Detune
        # 3: Decay/Release
        self.params = {
            "pitch": 0.5,
            "timbre": 0.5,
            "detune": 0.0,
            "decay": 0.5
        }
        
    def set_param(self, name, value):
        self.params[name] = value
        
        # Map params directly to internals
        if name == "pitch":
            # Map 0..1 to 55Hz..880Hz
            freq = 55.0 * (2.0 ** (value * 4.0)) # 4 octaves
            self.osc1.freq = freq
            self.osc2.freq = freq * (1.0 + self.params["detune"]*0.1) # slight detune
            
        elif name == "detune":
            # Update osc2 immediately?
            base = self.osc1.freq
            self.osc2.freq = base * (1.0 + value*0.1)

    def generate(self, num_frames):
        # 1. Generate Oscillators
        out1 = self.osc1.next(num_frames)
        out2 = self.osc2.next(num_frames)
        
        # 2. Mix
        mix = (out1 + out2) * 0.5
        
        # 3. Apply easy "bitcrush" or quantization for style?
        # clip
        mix = np.clip(mix, -1.0, 1.0)
        
        # 4. Stereo Expansion (Fake)
        # Left = Mix, Right = Mix slightly delayed? Or just dual mono for chip.
        stereo = np.column_stack((mix, mix))
        
        # 5. Master Gain
        return stereo * self.gain
