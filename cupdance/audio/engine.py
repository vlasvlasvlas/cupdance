import sounddevice as sd
import numpy as np
import threading
import time
from cupdance.utils.config_manager import cfg
# We will import synths dynamically later, for now just placeholder
# from cupdance.audio.synths.chip import ChipSynth 

class AudioEngine:
    def __init__(self):
        self.config = cfg.get_audio_config()
        self.sr = self.config.get("sample_rate", 44100)
        self.blocksize = self.config.get("buffer_size", 512)
        
        self.stream = None
        self.active_synths = [] # List of Synth objects (4 channels?)
        self.master_vol = self.config.get("master_volume", 0.8)
        
        # Thread lock for audio callback safety
        self.lock = threading.Lock()
        
        # Mute states
        self.mutes = [False, False, False, False]
        self.vols = [1.0, 1.0, 1.0, 1.0]
        
        # Visualization buffer (for oscilloscope)
        self.viz_buffer = np.zeros(512)
        self.global_mute = False

    def callback(self, outdata, frames, time, status):
        """Audio processing callback (runs in high priority thread)"""
        if status:
            print(status)
            
        # Clear buffer
        outdata.fill(0)
        
        # Global mute check
        if self.global_mute:
            self.viz_buffer = np.zeros(min(frames, 512))
            return
        
        # Mix Synths
        # Since we are in a tight loop, avoid complex locks if possible, 
        # but Python GIL makes this tricky anyway.
        
        if self.lock.acquire(blocking=False):
            try:
                mixed = np.zeros((frames, 2), dtype=np.float32)
                
                for i, synth_inst in enumerate(self.active_synths):
                    if i < 4 and self.mutes[i]: continue
                    
                    # Generate audio
                    audio_chunk = synth_inst.generate(frames)
                    
                    # Apply channel vol
                    vol = self.vols[i] if i < 4 else 1.0
                    mixed += audio_chunk * vol
                
                # Master Vol & Clip
                mixed *= self.master_vol
                np.clip(mixed, -1.0, 1.0, out=mixed)
                
                outdata[:] = mixed
                
                # Update visualization buffer (mono sum)
                self.viz_buffer = (mixed[:, 0] + mixed[:, 1]) / 2.0
            except Exception as e:
                print(f"[Audio] Error in callback: {e}")
            finally:
                self.lock.release()
        else:
            # If locked (loading synth?), output silence
            pass

    def start(self):
        print(f"[Audio] Starting Engine @ {self.sr}Hz")
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sr,
                blocksize=self.blocksize,
                channels=2,
                callback=self.callback
            )
            self.stream.start()
        except Exception as e:
            print(f"[Audio] FAILED to start stream: {e}")

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            
    def set_synth(self, channel_idx, synth_instance):
        with self.lock:
            # Ensure list size
            while len(self.active_synths) <= channel_idx:
                self.active_synths.append(None) # Placeholder
            self.active_synths[channel_idx] = synth_instance

    def set_param(self, channel_idx, param_name, value):
        # Thread-safe parameter update? 
        # Usually atomic assignment is fine in Python.
        if channel_idx < len(self.active_synths):
            s = self.active_synths[channel_idx]
            if s:
                s.set_param(param_name, value)
    
    def toggle_mute(self, channel_idx):
        """Toggle mute for a channel."""
        if channel_idx < 4:
            self.mutes[channel_idx] = not self.mutes[channel_idx]
            status = "MUTED" if self.mutes[channel_idx] else "UNMUTED"
            print(f"[Mixer] Channel {channel_idx + 1}: {status}")
    
    def toggle_global_mute(self):
        """Toggle global mute."""
        self.global_mute = not self.global_mute
        status = "SILENCIO" if self.global_mute else "SONANDO"
        print(f"[Audio] {status}")
        return self.global_mute
    
    def get_viz_buffer(self):
        """Get audio buffer for visualization."""
        return self.viz_buffer.copy()
    
    def get_mutes(self):
        """Return mute states."""
        return self.mutes.copy()
    
    def get_volumes(self):
        """Return volume levels."""
        return self.vols.copy()
