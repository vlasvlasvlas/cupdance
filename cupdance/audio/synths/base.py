import numpy as np
from abc import ABC, abstractmethod

class Synth(ABC):
    def __init__(self, sample_rate=44100):
        self.sr = sample_rate
        self.gain = 0.5
        self.params = {} # Current parameter values (0..1 usually)

    @abstractmethod
    def set_param(self, name, value):
        """Update a synthesis parameter (0.0 to 1.0)"""
        pass

    @abstractmethod
    def generate(self, num_frames):
        """
        Produce a chunk of audio.
        Returns: numpy array of shape (num_frames, 2) for stereo.
        """
        return np.zeros((num_frames, 2), dtype=np.float32)

class Oscillator:
    """Helper for standard waveforms"""
    def __init__(self, sr=44100, freq=440, waveform='sine'):
        self.sr = sr
        self.phase = 0.0
        self.freq = freq
        self.waveform = waveform

    def next(self, num_frames):
        t = np.arange(num_frames) / self.sr
        # Simple non-vectorized phase accumulation for continuity?
        # Vectorized is faster but phase continuity between blocks needs care.
        
        # Vectorized phase
        phase_increment = (self.freq * 2 * np.pi) / self.sr
        phases = self.phase + np.arange(num_frames) * phase_increment
        self.phase = (phases[-1] + phase_increment) % (2 * np.pi)
        
        if self.waveform == 'sine':
            return np.sin(phases)
        elif self.waveform == 'square':
            return np.sign(np.sin(phases))
        elif self.waveform == 'saw':
            # normalized 0..2pi -> -1..1
            return 2.0 * (phases / (2*np.pi) - np.floor(0.5 + phases / (2*np.pi)))
        elif self.waveform == 'tri':
            # 2/pi * asin(sin(x)) approximation
            return 2/np.pi * np.arcsin(np.sin(phases))
        return np.zeros(num_frames)


class Envelope:
    """Simple ADSR Envelope Generator"""
    def __init__(self, sr=44100, attack=0.01, decay=0.1, sustain=0.7, release=0.3):
        self.sr = sr
        self.attack = attack  # seconds
        self.decay = decay
        self.sustain = sustain  # level 0..1
        self.release = release
        
        self.state = "idle"  # idle, attack, decay, sustain, release
        self.level = 0.0
        self.time_in_state = 0.0
        
    def trigger(self):
        """Start the envelope (note on)"""
        self.state = "attack"
        self.time_in_state = 0.0
        
    def release_note(self):
        """Release the envelope (note off)"""
        self.state = "release"
        self.time_in_state = 0.0
        
    def generate(self, num_frames):
        """Generate envelope values for num_frames samples"""
        out = np.zeros(num_frames, dtype=np.float32)
        
        for i in range(num_frames):
            dt = 1.0 / self.sr
            
            if self.state == "attack":
                self.level += dt / max(self.attack, 0.001)
                if self.level >= 1.0:
                    self.level = 1.0
                    self.state = "decay"
                    
            elif self.state == "decay":
                self.level -= dt / max(self.decay, 0.001) * (1.0 - self.sustain)
                if self.level <= self.sustain:
                    self.level = self.sustain
                    self.state = "sustain"
                    
            elif self.state == "sustain":
                self.level = self.sustain
                
            elif self.state == "release":
                self.level -= dt / max(self.release, 0.001) * self.sustain
                if self.level <= 0.0:
                    self.level = 0.0
                    self.state = "idle"
                    
            out[i] = self.level
            
        return out
