import numpy as np
from .base import Synth, Envelope

class CustomDrawSynth(Synth):
    """
    A synth that uses user-drawn waveforms and ADSR curves.
    The wavetable and envelope are updated externally from CV detection.
    """
    def __init__(self, sr=44100):
        super().__init__(sr)
        
        # Default wavetable (sine)
        t = np.linspace(0, 2*np.pi, 256, dtype=np.float32)
        self.wavetable = np.sin(t)
        
        # Playback position in wavetable
        self.phase = 0.0
        self.freq = 220.0
        
        # Envelope
        self.envelope = Envelope(sr, attack=0.01, decay=0.1, sustain=0.7, release=0.3)
        self.envelope.trigger()  # Start playing
        
        self.params = {
            "pitch": 0.5,
            "brightness": 0.5
        }
        
    def set_wavetable(self, table):
        """Update the wavetable from CV detection."""
        if table is not None and len(table) > 0:
            # Normalize to -1..1
            self.wavetable = np.array(table, dtype=np.float32)
            # Ensure proper range
            self.wavetable = np.clip(self.wavetable, -1.0, 1.0)
    
    def set_adsr(self, adsr_dict):
        """Update envelope from CV detection."""
        if adsr_dict:
            self.envelope.attack = adsr_dict.get("attack", 0.01)
            self.envelope.decay = adsr_dict.get("decay", 0.1)
            self.envelope.sustain = adsr_dict.get("sustain", 0.7)
            self.envelope.release = adsr_dict.get("release", 0.3)
    
    def set_param(self, name, value):
        self.params[name] = value
        
        if name == "pitch":
            # Map 0..1 to frequency
            self.freq = 55.0 * (2.0 ** (value * 4.0))
            
    def generate(self, num_frames):
        # 1. Read from wavetable with interpolation
        table_len = len(self.wavetable)
        phase_increment = self.freq * table_len / self.sr
        
        samples = np.zeros(num_frames, dtype=np.float32)
        
        for i in range(num_frames):
            # Linear interpolation between samples
            idx = self.phase
            idx0 = int(idx) % table_len
            idx1 = (idx0 + 1) % table_len
            frac = idx - int(idx)
            
            sample = self.wavetable[idx0] * (1 - frac) + self.wavetable[idx1] * frac
            samples[i] = sample
            
            self.phase = (self.phase + phase_increment) % table_len
        
        # 2. Apply envelope
        env = self.envelope.generate(num_frames)
        samples = samples * env
        
        # 3. Make stereo
        stereo = np.column_stack((samples, samples))
        
        return stereo * self.gain
