# Sound Design Guide for Cupdance SOTA

## Overview
Cupdance uses a custom Python-based audio engine (`cupdance.audio.engine`). It generates audio in real-time using NumPy arrays. To create new sounds, you simply write new Python classes that inherit from `Synth`.

## creating a New Synth

### 1. The Template
Create a new file in `cupdance/audio/synths/mysynth.py`:

```python
import numpy as np
from .base import Synth, Oscillator

class MySynth(Synth):
    def __init__(self, sr=44100):
        super().__init__(sr)
        # Initialize Oscillators
        self.osc = Oscillator(sr, freq=440, waveform='sine')
        
        # Define Parameters (that you want to map to cups)
        self.params = {
            "pitch": 0.5,
            "mod": 0.0
        }

    def set_param(self, name, value):
        self.params[name] = value
        
        # Define how params affect sound
        if name == "pitch":
             # Map 0..1 to Frequency (Exponential usually best)
             freq = 55.0 * (2.0 ** (value * 4.0)) 
             self.osc.freq = freq
             
        elif name == "mod":
             # Example: Gain modulation
             self.gain = value

    def generate(self, num_frames):
        # 1. Get raw signal
        sig = self.osc.next(num_frames)
        
        # 2. Process (Filter, Effects)
        # ...
        
        # 3. Output Stereo
        stereo = np.column_stack((sig, sig))
        return stereo * self.gain
```

### 2. Registering
1. Import your synth in `main.py`.
2. Assign it to a slot:
   ```python
   s5 = MySynth()
   audio_sys.set_synth(0, s5) # Replaces Channel 1
   ```

## Built-in Oscillators
The `Oscillator` class supports:
- `'sine'`
- `'square'`
- `'saw'` (Sawtooth)
- `'tri'` (Triangle)

## Performance Tips
- Use **Vectorized NumPy operations**. Do not use `for` loops inside `generate()`.
- Keep `generate()` fast! It runs every ~10ms.
