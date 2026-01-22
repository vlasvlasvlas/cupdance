import numpy as np
from .base import Synth, Oscillator
from cupdance.audio.modulation import LFO, MoogFilter

class MoogSynth(Synth):
    def __init__(self, sr=44100):
        super().__init__(sr)
        self.osc1 = Oscillator(sr, freq=110, waveform='saw')
        self.osc2 = Oscillator(sr, freq=55, waveform='saw') # Sub oscillator
        
        # Moog Filter
        self.filter = MoogFilter(sr)
        self.filter.set_cutoff(800)
        self.filter.set_resonance(0.6)
        
        # LFO for filter modulation
        self.lfo = LFO(sr, rate=1.5, waveform='sine')
        self.lfo_depth = 0.3  # How much LFO affects filter
        
        self.params = {
            "pitch": 0.5,
            "filter": 0.5,
            "resonance": 0.5,
            "lfo_rate": 0.3
        }

    def set_param(self, name, value):
        self.params[name] = value
        
        if name == "pitch":
             freq = 55.0 * (2.0 ** (value * 4.0)) 
             self.osc1.freq = freq
             self.osc2.freq = freq / 2.0
             
        elif name == "filter":
             # Map 0..1 to 100..5000 Hz
             cutoff = 100 + (value * 4900)
             self.filter.set_cutoff(cutoff)
             
        elif name == "resonance":
             self.filter.set_resonance(value * 0.9)
             
        elif name == "lfo_rate":
             self.lfo.set_rate(0.1 + value * 10.0)

    def generate(self, num_frames):
        # 1. Generate Oscillators
        raw1 = self.osc1.next(num_frames)
        raw2 = self.osc2.next(num_frames)
        
        # Mix with sub
        sig = (raw1 + 0.5 * raw2) * 0.7
        
        # 2. LFO modulation of filter
        lfo_vals = self.lfo.generate(num_frames)
        
        # Modulate cutoff
        base_cutoff = self.filter.cutoff
        for i, lfo_v in enumerate(lfo_vals):
            mod_cutoff = base_cutoff * (1.0 + (lfo_v - 0.5) * self.lfo_depth)
            self.filter.set_cutoff(mod_cutoff)
        
        # Reset to base
        self.filter.set_cutoff(base_cutoff)
        
        # 3. Apply Filter
        sig = self.filter.process(sig)
        
        # 4. Stereo
        stereo = np.column_stack((sig, sig))
        
        return stereo * self.gain
