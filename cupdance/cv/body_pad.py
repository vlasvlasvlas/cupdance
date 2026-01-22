import cv2
import numpy as np
import time

class BodyPad:
    """
    Convierte el piso en un Kaoss Pad / Octapad gigante para el cuerpo.
    
    Layout (como Octapad 2x4 o Grid 4x4):
    
    2x4 Mode (8 pads):
    ┌─────┬─────┬─────┬─────┐
    │  1  │  2  │  3  │  4  │
    ├─────┼─────┼─────┼─────┤
    │  5  │  6  │  7  │  8  │
    └─────┴─────┴─────┴─────┘
    
    4x4 Mode (16 pads):
    ┌────┬────┬────┬────┐
    │ 1  │ 2  │ 3  │ 4  │
    ├────┼────┼────┼────┤
    │ 5  │ 6  │ 7  │ 8  │
    ├────┼────┼────┼────┤
    │ 9  │ 10 │ 11 │ 12 │
    ├────┼────┼────┼────┤
    │ 13 │ 14 │ 15 │ 16 │
    └────┴────┴────┴────┘
    
    Cada pad detecta:
    - Trigger (cuerpo entró al pad)
    - Velocity (qué tan rápido entró)
    - Position XY (posición relativa dentro del pad para modulation)
    - Pressure (área ocupada = intensidad)
    - Release (cuerpo salió del pad)
    """
    
    def __init__(self, grid_size=512, mode="2x4"):
        self.grid_size = grid_size
        self.mode = mode  # "2x4" (8 pads) or "4x4" (16 pads)
        
        if mode == "2x4":
            self.cols = 4
            self.rows = 2
        else:  # 4x4
            self.cols = 4
            self.rows = 4
        
        self.num_pads = self.rows * self.cols
        self.pad_w = grid_size // self.cols
        self.pad_h = grid_size // self.rows
        
        # Pad states
        self.pad_active = [False] * self.num_pads      # Is body in this pad?
        self.pad_triggered = [False] * self.num_pads   # Just triggered this frame?
        self.pad_released = [False] * self.num_pads    # Just released this frame?
        self.pad_pressure = [0.0] * self.num_pads      # Area occupied (0-1)
        self.pad_velocity = [0.0] * self.num_pads      # Entry velocity (0-1)
        self.pad_position = [(0.5, 0.5)] * self.num_pads  # XY position within pad (0-1, 0-1)
        
        # For velocity calculation
        self.prev_pressure = [0.0] * self.num_pads
        self.trigger_time = [0.0] * self.num_pads
        
        # Hold/Retrigger settings
        self.retrigger_cooldown = 0.15  # seconds before can retrigger same pad
        self.trigger_threshold = 0.05   # minimum pressure to trigger
        self.release_threshold = 0.02   # pressure below this = release
        
        # Musical mapping (MIDI notes for each pad)
        # Default: Pentatonic scale across pads
        self.scale_name = "Pentatonic"  # Current scale name for display
        if mode == "2x4":
            # 8 pads: C minor pentatonic across 2 octaves
            self.pad_notes = [48, 51, 53, 55,   # C3, Eb3, F3, G3
                              58, 60, 63, 65]   # Bb3, C4, Eb4, F4
        else:
            # 16 pads: Full chromatic or drums
            self.pad_notes = [36, 38, 42, 46,   # Kick, Snare, HH closed, HH open
                              48, 50, 52, 53,   # C3, D3, E3, F3
                              55, 57, 59, 60,   # G3, A3, B3, C4
                              62, 64, 65, 67]   # D4, E4, F4, G4
        
        # Colors for visualization
        self.pad_colors_off = [
            (80, 40, 40), (40, 80, 40), (40, 40, 80), (80, 80, 40),
            (80, 40, 80), (40, 80, 80), (60, 60, 60), (100, 50, 30),
            (30, 100, 50), (50, 30, 100), (100, 100, 30), (30, 100, 100),
            (100, 30, 100), (70, 70, 70), (90, 60, 40), (40, 60, 90)
        ]
        
    def get_pad_rect(self, pad_idx):
        """Get the rectangle (x1, y1, x2, y2) for a pad."""
        row = pad_idx // self.cols
        col = pad_idx % self.cols
        x1 = col * self.pad_w
        y1 = row * self.pad_h
        x2 = x1 + self.pad_w
        y2 = y1 + self.pad_h
        return x1, y1, x2, y2
    
    def process(self, motion_mask):
        """
        Process a motion mask (binary image) to detect body position on pads.
        
        Args:
            motion_mask: Binary mask (0/255) of detected motion, size grid_size x grid_size
            
        Returns:
            events: List of (event_type, pad_idx, velocity, position, pressure)
        """
        if motion_mask is None:
            return []
        
        # Ensure 2D grayscale
        if motion_mask.ndim == 3:
            motion_mask = cv2.cvtColor(motion_mask, cv2.COLOR_BGR2GRAY)
        
        # Ensure correct size
        if motion_mask.shape[0] != self.grid_size or motion_mask.shape[1] != self.grid_size:
            motion_mask = cv2.resize(motion_mask, (self.grid_size, self.grid_size))
        
        # Normalize to 0-1
        mask_norm = motion_mask.astype(np.float32) / 255.0
        
        events = []
        current_time = time.time()
        
        for i in range(self.num_pads):
            x1, y1, x2, y2 = self.get_pad_rect(i)
            
            # Ensure valid region
            if y2 <= y1 or x2 <= x1:
                continue
            if y2 > mask_norm.shape[0] or x2 > mask_norm.shape[1]:
                continue
                
            pad_region = mask_norm[y1:y2, x1:x2]
            
            # Ensure 2D
            if pad_region.ndim != 2 or pad_region.size == 0:
                continue
            
            # Calculate pressure (percentage of pad covered)
            pressure = np.mean(pad_region)
            
            # Calculate center of mass (position within pad)
            if pressure > 0.01:
                # Find centroid of motion in this pad
                indices = np.where(pad_region > 0.3)
                if len(indices) == 2 and len(indices[0]) > 0:
                    ys = indices[0]
                    xs = indices[1]
                    cx = np.mean(xs) / self.pad_w  # 0-1
                    cy = np.mean(ys) / self.pad_h  # 0-1
                    self.pad_position[i] = (cx, cy)
            
            # Store previous state
            was_active = self.pad_active[i]
            
            # Reset frame-specific flags
            self.pad_triggered[i] = False
            self.pad_released[i] = False
            
            # Detect trigger (entry)
            if not was_active and pressure > self.trigger_threshold:
                # Check cooldown
                if current_time - self.trigger_time[i] > self.retrigger_cooldown:
                    self.pad_active[i] = True
                    self.pad_triggered[i] = True
                    self.trigger_time[i] = current_time
                    
                    # Calculate velocity from pressure rise
                    velocity = min(1.0, (pressure - self.prev_pressure[i]) * 10)
                    velocity = max(0.3, velocity)  # Minimum velocity
                    self.pad_velocity[i] = velocity
                    
                    events.append({
                        "type": "trigger",
                        "pad": i,
                        "note": self.pad_notes[i],
                        "velocity": velocity,
                        "position": self.pad_position[i],
                        "pressure": pressure
                    })
            
            # Detect release (exit)
            elif was_active and pressure < self.release_threshold:
                self.pad_active[i] = False
                self.pad_released[i] = True
                
                events.append({
                    "type": "release",
                    "pad": i,
                    "note": self.pad_notes[i],
                    "velocity": 0,
                    "position": self.pad_position[i],
                    "pressure": 0
                })
            
            # Update pressure
            self.pad_pressure[i] = pressure
            self.prev_pressure[i] = pressure
        
        return events
    
    def get_active_pads(self):
        """Returns list of currently active pad indices."""
        return [i for i in range(self.num_pads) if self.pad_active[i]]
    
    def get_pad_data(self, pad_idx):
        """Get all data for a specific pad."""
        return {
            "active": self.pad_active[pad_idx],
            "pressure": self.pad_pressure[pad_idx],
            "velocity": self.pad_velocity[pad_idx],
            "position": self.pad_position[pad_idx],
            "note": self.pad_notes[pad_idx]
        }
    
    def get_xy_modulation(self):
        """
        Get overall XY modulation from all active pads (like Kaoss Pad).
        Returns weighted average position of body across all active pads.
        """
        total_pressure = 0
        weighted_x = 0
        weighted_y = 0
        
        for i in range(self.num_pads):
            if self.pad_active[i]:
                p = self.pad_pressure[i]
                x1, y1, x2, y2 = self.get_pad_rect(i)
                
                # Global position (0-1 across entire floor)
                local_x, local_y = self.pad_position[i]
                global_x = (x1 + local_x * self.pad_w) / self.grid_size
                global_y = (y1 + local_y * self.pad_h) / self.grid_size
                
                weighted_x += global_x * p
                weighted_y += global_y * p
                total_pressure += p
        
        if total_pressure > 0:
            return (weighted_x / total_pressure, weighted_y / total_pressure, total_pressure)
        return (0.5, 0.5, 0)  # Center with no pressure
    
    def draw_overlay(self, frame):
        """
        Draw the pad grid overlay on a frame.
        """
        overlay = frame.copy()
        
        for i in range(self.num_pads):
            x1, y1, x2, y2 = self.get_pad_rect(i)
            
            # Pad color based on state
            if self.pad_active[i]:
                # Active: bright color scaled by pressure
                base_color = self.pad_colors_off[i % len(self.pad_colors_off)]
                intensity = 0.5 + self.pad_pressure[i] * 0.5
                color = tuple(int(c * intensity * 3) for c in base_color)
                color = tuple(min(255, c) for c in color)
                thickness = -1  # Filled
                
                # Draw filled rectangle with transparency
                cv2.rectangle(overlay, (x1+2, y1+2), (x2-2, y2-2), color, thickness)
                
                # Draw position indicator (where body center is)
                px, py = self.pad_position[i]
                cx = int(x1 + px * self.pad_w)
                cy = int(y1 + py * self.pad_h)
                cv2.circle(overlay, (cx, cy), 15, (255, 255, 255), 3)
                
            else:
                # Inactive: dim outline
                color = self.pad_colors_off[i % len(self.pad_colors_off)]
                cv2.rectangle(overlay, (x1+2, y1+2), (x2-2, y2-2), color, 2)
            
            # Pad number and note
            note_name = self._midi_to_name(self.pad_notes[i])
            cv2.putText(overlay, f"{i+1}", (x1+10, y1+30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(overlay, note_name, (x1+10, y1+55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Pressure bar
            if self.pad_pressure[i] > 0.01:
                bar_h = int(self.pad_pressure[i] * (self.pad_h - 20))
                cv2.rectangle(overlay, (x2-15, y2-10-bar_h), (x2-5, y2-10), (0, 255, 0), -1)
        
        # Blend overlay
        result = cv2.addWeighted(frame, 0.4, overlay, 0.6, 0)
        
        # Title
        cv2.putText(result, f"BODY PAD ({self.mode})", (10, 25), 
                   cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 255, 255), 1)
        
        # XY Modulation display
        x, y, p = self.get_xy_modulation()
        if p > 0:
            cv2.putText(result, f"XY: ({x:.2f}, {y:.2f}) P:{p:.2f}", 
                       (10, self.grid_size - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return result
    
    def _midi_to_name(self, midi_note):
        """Convert MIDI note to name."""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = notes[midi_note % 12]
        return f"{note}{octave}"
    
    def set_scale(self, root=48, scale_type="pentatonic"):
        """
        Set musical scale for pads.
        
        Args:
            root: MIDI root note (48 = C3)
            scale_type: "pentatonic", "major", "minor", "chromatic", "drums"
        """
        self.scale_name = scale_type.capitalize()  # Store for display
        
        intervals = {
            "pentatonic": [0, 3, 5, 7, 10],  # Minor pentatonic
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "chromatic": list(range(12)),
            "drums": None  # Special case
        }
        
        if scale_type == "drums":
            # GM Drum map subset
            self.pad_notes = [36, 38, 42, 46, 41, 43, 45, 47,
                              48, 49, 51, 52, 53, 55, 57, 59][:self.num_pads]
        else:
            scale = intervals.get(scale_type, intervals["pentatonic"])
            notes = []
            octave = 0
            idx = 0
            while len(notes) < self.num_pads:
                note = root + octave * 12 + scale[idx % len(scale)]
                notes.append(note)
                idx += 1
                if idx % len(scale) == 0:
                    octave += 1
            self.pad_notes = notes


class BodyKaoss:
    """
    Extended BodyPad with Kaoss Pad-style XY effects.
    The entire floor becomes one big XY surface for effects modulation.
    """
    
    def __init__(self, grid_size=512):
        self.grid_size = grid_size
        
        # Global XY position (0-1)
        self.x = 0.5
        self.y = 0.5
        self.pressure = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        
        # Previous values for velocity calculation
        self.prev_x = 0.5
        self.prev_y = 0.5
        
        # Smoothing
        self.smooth_factor = 0.3
        
    def process(self, motion_mask):
        """
        Process motion mask to get XY position and pressure.
        """
        if motion_mask is None:
            return
        
        # Resize if needed
        if motion_mask.shape[0] != self.grid_size:
            motion_mask = cv2.resize(motion_mask, (self.grid_size, self.grid_size))
        
        # Ensure 2D
        if motion_mask.ndim != 2:
            if motion_mask.ndim == 3:
                motion_mask = cv2.cvtColor(motion_mask, cv2.COLOR_BGR2GRAY)
            else:
                return
        
        mask_norm = motion_mask.astype(np.float32) / 255.0
        
        # Calculate pressure (total coverage)
        self.pressure = np.mean(mask_norm)
        
        if self.pressure > 0.01:
            # Find center of mass
            indices = np.where(mask_norm > 0.3)
            if len(indices) == 2 and len(indices[0]) > 0:
                ys = indices[0]
                xs = indices[1]
                raw_x = np.mean(xs) / self.grid_size
                raw_y = np.mean(ys) / self.grid_size
                
                # Smooth
                self.x = self.x * (1 - self.smooth_factor) + raw_x * self.smooth_factor
                self.y = self.y * (1 - self.smooth_factor) + raw_y * self.smooth_factor
                
                # Velocity
                self.velocity_x = (self.x - self.prev_x) * 60  # Approx per second
                self.velocity_y = (self.y - self.prev_y) * 60
                
                self.prev_x = self.x
                self.prev_y = self.y
    
    def get_fx_params(self):
        """
        Map XY position to effect parameters.
        Returns dict of effect values.
        """
        return {
            "filter_cutoff": self.x,          # X = Filter cutoff
            "filter_resonance": self.y,       # Y = Resonance
            "delay_time": 1.0 - self.y,       # Y inverted = Delay time
            "delay_feedback": self.x,         # X = Delay feedback
            "reverb_size": self.y,            # Y = Reverb size
            "reverb_mix": self.x * 0.5,       # X = Reverb wet
            "distortion": self.pressure,      # Pressure = Distortion
            "pitch_bend": (self.x - 0.5) * 2, # X centered = Pitch bend (-1 to 1)
            "mod_speed": self.velocity_x,     # Movement = Mod speed
            "mod_depth": abs(self.velocity_y) # Movement = Mod depth
        }
    
    def draw_overlay(self, frame):
        """Draw XY crosshair and pressure indicator."""
        overlay = frame.copy()
        
        h, w = overlay.shape[:2]
        
        # Draw grid
        for i in range(1, 4):
            x = int(w * i / 4)
            y = int(h * i / 4)
            cv2.line(overlay, (x, 0), (x, h), (40, 40, 40), 1)
            cv2.line(overlay, (0, y), (w, y), (40, 40, 40), 1)
        
        # Draw crosshair at current position
        cx = int(self.x * w)
        cy = int(self.y * h)
        
        # Crosshair size based on pressure
        size = int(20 + self.pressure * 100)
        color = (0, int(255 * self.pressure), 255)
        
        cv2.line(overlay, (cx - size, cy), (cx + size, cy), color, 2)
        cv2.line(overlay, (cx, cy - size), (cx, cy + size), color, 2)
        cv2.circle(overlay, (cx, cy), size // 2, color, 2)
        
        # Labels
        cv2.putText(overlay, "KAOSS MODE", (10, 25), cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 255, 255), 1)
        cv2.putText(overlay, f"X:{self.x:.2f} Y:{self.y:.2f} P:{self.pressure:.2f}", 
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Effect hints
        cv2.putText(overlay, "FILTER ->", (w - 100, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        cv2.putText(overlay, "REVERB", (w // 2 - 30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        return cv2.addWeighted(frame, 0.5, overlay, 0.5, 0)
