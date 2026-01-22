import numpy as np

class LFO:
    """Low Frequency Oscillator for modulation effects."""
    def __init__(self, sr=44100, rate=2.0, waveform='sine'):
        self.sr = sr
        self.rate = rate  # Hz
        self.waveform = waveform
        self.phase = 0.0
        
    def set_rate(self, rate):
        self.rate = max(0.01, rate)
        
    def generate(self, num_frames):
        """Generate LFO values (0..1 range)."""
        phase_increment = self.rate / self.sr
        phases = self.phase + np.arange(num_frames) * phase_increment * 2 * np.pi
        self.phase = (phases[-1] + phase_increment * 2 * np.pi) % (2 * np.pi)
        
        if self.waveform == 'sine':
            return (np.sin(phases) + 1.0) / 2.0
        elif self.waveform == 'triangle':
            return np.abs((phases / np.pi) % 2 - 1)
        elif self.waveform == 'saw':
            return (phases / (2 * np.pi)) % 1.0
        elif self.waveform == 'square':
            return (np.sin(phases) > 0).astype(float)
        return np.zeros(num_frames)


class NoteTrigger:
    """Detects threshold crossings to trigger note events."""
    def __init__(self, threshold=0.5, hysteresis=0.05):
        self.threshold = threshold
        self.hysteresis = hysteresis
        self.is_above = False
        
    def check(self, value):
        """Returns: (triggered, released) booleans."""
        triggered = False
        released = False
        
        if not self.is_above and value > self.threshold + self.hysteresis:
            self.is_above = True
            triggered = True
        elif self.is_above and value < self.threshold - self.hysteresis:
            self.is_above = False
            released = True
            
        return triggered, released


class MoogFilter:
    """Simple Moog-style ladder filter approximation."""
    def __init__(self, sr=44100):
        self.sr = sr
        self.cutoff = 1000.0  # Hz
        self.resonance = 0.5  # 0..1
        
        # State for 4-pole filter
        self.y = [0.0, 0.0, 0.0, 0.0]
        
    def set_cutoff(self, freq):
        self.cutoff = max(20, min(freq, self.sr * 0.49))
        
    def set_resonance(self, res):
        self.resonance = max(0, min(res, 0.95))
        
    def process(self, samples):
        """Apply filter to audio samples."""
        out = np.zeros_like(samples)
        
        # Simple one-pole coefficient
        # fc normalized 0..1
        fc = self.cutoff / self.sr
        g = fc * 1.8  # Approximation
        
        for i, x in enumerate(samples):
            # Feedback
            fb = self.resonance * 4.0 * self.y[3]
            input_val = x - fb
            
            # 4 cascaded one-poles
            self.y[0] += g * (np.tanh(input_val) - self.y[0])
            self.y[1] += g * (self.y[0] - self.y[1])
            self.y[2] += g * (self.y[1] - self.y[2])
            self.y[3] += g * (self.y[2] - self.y[3])
            
            out[i] = self.y[3]
            
        return out
