import cv2
import numpy as np
import math
from cupdance import config

class VisualRenderer:
    def __init__(self, width=1000, height=1000):
        self.width = width
        self.height = height
        self.center = (width // 2, height // 2)
        
        # Custom Organic Palettes (256 colors each, BGR format)
        self.palettes = {
            "neon": self._create_gradient([(20, 20, 20), (255, 0, 128), (0, 255, 255), (255, 255, 255)]),
            "ocean": self._create_gradient([(10, 30, 50), (50, 100, 150), (100, 200, 200), (200, 255, 255)]),
            "fire": self._create_gradient([(20, 10, 10), (60, 30, 180), (80, 150, 255), (200, 230, 255)]),
            "forest": self._create_gradient([(10, 30, 10), (30, 100, 50), (50, 180, 80), (150, 220, 120)]),
            "twilight": self._create_gradient([(20, 10, 40), (80, 40, 100), (150, 100, 150), (220, 180, 200)])
        }
        self.palette_names = list(self.palettes.keys())
        self.current_palette_idx = 0
        
        # UI State smoothing
        self.cup_radii = [0.0] * 4
        
        # Labels for Cups
        self.cup_labels = ["PITCH", "TIMBRE", "HARMONY", "METAL"]
    
    def _create_gradient(self, colors):
        """Create a 256-color gradient LUT from key colors."""
        n_colors = len(colors)
        lut = np.zeros((256, 3), dtype=np.uint8)
        
        for i in range(256):
            # Find which segment we're in
            segment = (i * (n_colors - 1)) / 255.0
            idx = int(segment)
            frac = segment - idx
            
            if idx >= n_colors - 1:
                lut[i] = colors[-1]
            else:
                # Linear interpolation between colors
                c1 = np.array(colors[idx])
                c2 = np.array(colors[idx + 1])
                lut[i] = (c1 * (1 - frac) + c2 * frac).astype(np.uint8)
        
        return lut
    
    def apply_palette(self, gray_img, palette_name):
        """Apply custom palette to grayscale image."""
        lut = self.palettes.get(palette_name, self.palettes["neon"])
        # Create BGR output
        out = np.zeros((*gray_img.shape, 3), dtype=np.uint8)
        for c in range(3):
            out[:, :, c] = lut[gray_img, c]
        return out
    
    def draw_control_panel(self, canvas, synth_names, current_palette, freeze_states=None):
        """
        Draws a comprehensive control panel on the right side of the canvas.
        """
        panel_w = 250
        panel_x = self.width - panel_w - 10
        panel_y = 50
        line_h = 22
        
        # Panel background
        overlay = canvas.copy()
        cv2.rectangle(overlay, (panel_x - 10, panel_y - 10), (self.width - 5, self.height - 50), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)
        
        # Title
        cv2.putText(canvas, "PANEL DE CONTROL", (panel_x, panel_y), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (255, 255, 255), 1)
        y = panel_y + 35
        
        # Section: SYNTHS
        cv2.putText(canvas, "SINTETIZADORES:", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 200, 100), 1)
        y += line_h
        for i, name in enumerate(synth_names):
            cup_label = ["Taza A", "Taza B", "Taza C", "Taza D"][i] if i < 4 else f"CH{i+1}"
            cv2.putText(canvas, f"  {cup_label}: {name}", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
            y += line_h
        
        y += 10
        
        # Section: PALETTE
        cv2.putText(canvas, f"PALETA: {current_palette.upper()}", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 150, 200), 1)
        y += line_h
        cv2.putText(canvas, "  (Controlada por Taza B)", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1)
        y += line_h + 10
        
        # Section: CONTROLS
        cv2.putText(canvas, "CONTROLES:", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 100), 1)
        y += line_h
        controls = [
            ("Q", "Salir"),
            ("B", "Capturar fondo"),
            ("C", "Calibrar camaras"),
            ("TAB", "Cambiar cam activa"),
            ("[ ]", "Brillo -/+"),
            ("; '", "Contraste -/+"),
        ]
        for key, desc in controls:
            cv2.putText(canvas, f"  {key}", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 100), 1)
            cv2.putText(canvas, f"= {desc}", (panel_x + 50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            y += line_h
        
        y += 10
        
        # Section: TANGIBLE SYNTHESIS
        cv2.putText(canvas, "SINTESIS TANGIBLE:", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 100, 150), 1)
        y += line_h
        
        freeze_adsr = freeze_states.get("adsr", False) if freeze_states else False
        freeze_wave = freeze_states.get("wave", False) if freeze_states else False
        
        adsr_status = "CONGELADO" if freeze_adsr else "EN VIVO"
        wave_status = "CONGELADO" if freeze_wave else "EN VIVO"
        
        cv2.putText(canvas, f"  F = ADSR ({adsr_status})", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 255, 150) if not freeze_adsr else (255, 150, 150), 1)
        y += line_h
        cv2.putText(canvas, f"  G = Waveform ({wave_status})", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 255, 150) if not freeze_wave else (255, 150, 150), 1)
        y += line_h + 10
        
        # Section: ZONES
        cv2.putText(canvas, "ZONAS DEL PISO:", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 200), 1)
        y += line_h
        zones = ["Q1: Arriba-Izq", "Q2: Arriba-Der", "Q3: Abajo-Izq", "Q4: Abajo-Der"]
        for z in zones:
            cv2.putText(canvas, f"  {z}", (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1)
            y += 18

    def draw_knob(self, canvas, center, radius, value, label, color=(255, 255, 255)):
        """
        Draws a vector-style potentiometer.
        value: 0.0 to 1.0
        """
        x, y = center
        
        # 1. Background Arc (270 degrees)
        # Start at 135 deg, end at 45 deg (clockwise)
        # Wrapper for ellipse: angle=0 is right. 
        # Start angle: 135 (bottom leftish), End angle: 405 (bottom rightish)
        # OpenCv ellipses take params in degrees.
        
        # Draw background track (dim)
        cv2.ellipse(canvas, center, (radius, radius), 90, 45, 315, (60, 60, 60), 4, cv2.LINE_AA)
        
        # 2. Active Arc
        # Map 0..1 to 45..315 degrees (270 deg range)
        end_angle = 45 + (value * 270)
        
        # Color based on value intensity?
        active_color = (
            int(color[0] * (0.5 + 0.5*value)), 
            int(color[1]), 
            int(color[2])
        )
        
        cv2.ellipse(canvas, center, (radius, radius), 90, 45, end_angle, active_color, 6, cv2.LINE_AA)
        
        # 3. Indicator Line/Needle
        # Angle in radians for line endpoint
        # OpenCV ellipse uses degrees where 0 is 3 o'clock?
        # Actually start_angle parameter is relative to 'angle' rotation.
        # Let's verify: 
        # angle=90 rotates the whole ellipse 90deg clockwise. 0 becomes 6 o'clock.
        # So 45 deg start is 7:30 o'clock. 
        
        # Manual math for needle
        # 0 value -> 135 degrees Cartesian (Top Left) if Y is up?
        # Screen coords: Y down. 0 deg is Right. 90 is Down.
        # We want knob to start Bottom-Left (135 deg) and go clockwise to Bottom-Right (45 deg).
        # Actually standard knob: 
        # 7 o'clock to 5 o'clock.
        # 7 o'clock = 120 deg? (90 + 30).
        # Let's stick to the ellipse visual which worked nicely above.
        
        # 4. Label
        font_scale = 0.5
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.putText(canvas, label, (x - tw//2, y + radius + 25), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (180, 180, 180), 1, cv2.LINE_AA)
        
        # Value Text
        val_str = f"{int(value*100)}%"
        (vw, vh), _ = cv2.getTextSize(val_str, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.putText(canvas, val_str, (x - vw//2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_fader(self, canvas, pos, width, height, value, label, active=True):
        """
        Draws a vertical fader.
        """
        x, y = pos
        color = (0, 255, 0) if active else (100, 100, 100)
        
        # Track
        cv2.rectangle(canvas, (x, y), (x + width, y + height), (40, 40, 40), -1)
        cv2.rectangle(canvas, (x, y), (x + width, y + height), (80, 80, 80), 1)
        
        # Fill
        fill_h = int(value * height)
        cv2.rectangle(canvas, (x, y + height - fill_h), (x + width, y + height), color, -1)
        
        # Label
        cv2.putText(canvas, label, (x, y + height + 15), cv2.FONT_HERSHEY_TRIPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)

    def render(self, live_grid, mem_grid, cup_values, matches, audio_state=None, synth_names=None, freeze_states=None):
        """
        Generates the SOTA output frame.
        synth_names: list of 4 synth names for display
        freeze_states: dict with 'adsr' and 'wave' booleans
        """
        # Default synth names
        if synth_names is None:
            synth_names = ["ChipSynth", "MoogSynth", "ExoticSynth", "CustomDraw"]
        
        # 1. Base Canvas
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 2. Fluid Floor (Soft Grid)
        combined_energy = (live_grid * 0.4) + (mem_grid * 0.8)
        combined_energy = np.clip(combined_energy, 0, 1)
        fluid = cv2.resize(combined_energy, (self.width, self.height), interpolation=cv2.INTER_CUBIC)
        fluid_8u = (fluid * 255).astype(np.uint8)
        
        # Select palette based on Cup B value
        p_idx = int(cup_values[1] * len(self.palette_names)) % len(self.palette_names)
        palette_name = self.palette_names[p_idx]
        color_bg = self.apply_palette(fluid_8u, palette_name)
        
        # Darker background overall for UI clarity
        canvas = cv2.addWeighted(canvas, 0, color_bg, 0.8, 0)
        
        # 2.5 Draw Grid Overlay (4 Quadrants + 16x16 sub-grid)
        grid_color_main = (80, 80, 80)  # Main quadrant dividers
        grid_color_sub = (40, 40, 40)   # 16x16 subtle lines
        
        # 4 Quadrant dividers (thick)
        cv2.line(canvas, (self.width//2, 0), (self.width//2, self.height), grid_color_main, 2)
        cv2.line(canvas, (0, self.height//2), (self.width, self.height//2), grid_color_main, 2)
        
        # 16x16 sub-grid (thin, subtle)
        cell_w = self.width // 16
        cell_h = self.height // 16
        for i in range(1, 16):
            if i == 8:  # Skip center lines (already drawn thicker)
                continue
            cv2.line(canvas, (i * cell_w, 0), (i * cell_w, self.height), grid_color_sub, 1)
            cv2.line(canvas, (0, i * cell_h), (self.width, i * cell_h), grid_color_sub, 1)
        
        # Quadrant Labels
        cv2.putText(canvas, "Q1", (self.width//4 - 20, self.height//4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        cv2.putText(canvas, "Q2", (3*self.width//4 - 20, self.height//4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        cv2.putText(canvas, "Q3", (self.width//4 - 20, 3*self.height//4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        cv2.putText(canvas, "Q4", (3*self.width//4 - 20, 3*self.height//4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        
        # 3. Vector Potentiometers (Cups)
        # Layout: 4 Corners
        margin = 150
        positions = [
            (margin, margin),               
            (self.width - margin, margin),  
            (margin, self.height - margin), 
            (self.width - margin, self.height - margin)  
        ]
        
        colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100)]
        
        for i, pos in enumerate(positions):
            val = cup_values[i]
            # Draw Knob
            self.draw_knob(canvas, pos, 60, val, self.cup_labels[i], color=colors[i])
            
            # Draw Connection Lines (Matches)
            # ... (Logic similar to before, but cleaner lines)

        # 4. Match Connections
        match_pairs = {
            "AB": (0, 1), "AC": (0, 2), "AD": (0, 3),
            "BC": (1, 2), "BD": (1, 3), "CD": (2, 3)
        }
        for name, (i, j) in match_pairs.items():
            if matches.get(name, False):
                pt1 = positions[i]
                pt2 = positions[j]
                cv2.line(canvas, pt1, pt2, (255, 255, 255), 2, cv2.LINE_AA)
                
                # Center label
                mid = ((pt1[0]+pt2[0])//2, (pt1[1]+pt2[1])//2)
                cv2.circle(canvas, mid, 5, (255,255,255), -1)

        # 5. Mixer UI (Center Bottom?) or Right Side?
        # Let's put it Bottom Center 
        # 4 Faders
        
        mix_w = 30
        mix_h = 100
        spacing = 50
        start_x = self.center[0] - (spacing * 1.5) - (mix_w // 2)
        start_y = self.height - 180
        
        # Dummy audio data if not provided (assume full vol if None)
        vols = [1.0, 1.0, 1.0, 1.0] 
        mutes = [False, False, False, False]
        # In real usage, pass audio_sys state to render()

        labels = ["CH1", "CH2", "CH3", "CH4"]
        
        for i in range(4):
            # Dynamic visual feedback from floor/cups?
            # Or static setting?
            # Let's visualize the CURRENT LEVEL of that channel.
            # For now just max.
            
            x = int(start_x + (i * spacing))
            active = not mutes[i]
            self.draw_fader(canvas, (x, start_y), mix_w, mix_h, vols[i], labels[i], active)


        # 6. Match Flash Effects
        # Count active matches for intensity
        active_count = sum(1 for v in matches.values() if v)
        
        if active_count >= 6:  # ABCD
            # Intense white flash with pulsing border
            pulse = int((np.sin(cv2.getTickCount() / cv2.getTickFrequency() * 10) + 1) * 10) + 10
            cv2.rectangle(canvas, (0,0), (self.width, self.height), (255, 255, 255), pulse)
            cv2.putText(canvas, "HARMONY", (self.center[0]-180, self.center[1]), cv2.FONT_HERSHEY_TRIPLEX, 2.5, (255,255,255), 3)
        elif active_count >= 3:  # Triple match
            cv2.rectangle(canvas, (10,10), (self.width-10, self.height-10), (200, 200, 100), 8)
            cv2.putText(canvas, "ALIGNMENT", (self.center[0]-150, self.center[1]), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (200,200,100), 2)
        elif active_count >= 1:  # Pair match
            cv2.rectangle(canvas, (20,20), (self.width-20, self.height-20), (100, 150, 100), 4)
        
        # Header & Palette Name
        palette_name = self.palette_names[p_idx].upper()
        cv2.putText(canvas, f"CUPDANCE OS v2.0 | {palette_name}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        
        # On-screen Help (Bottom)
        help_lines = [
            "CONTROLES: Q=Salir | B=Capturar fondo | C=Calibrar | TAB=Cambiar cam",
            "CAMARA: [ ] Brillo | ; ' Contraste | TANGIBLE: F=Freeze ADSR | G=Freeze Wave"
        ]
        y_start = self.height - 50
        for i, line in enumerate(help_lines):
            cv2.putText(canvas, line, (20, y_start + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
        
        # 7. Control Panel (Right side)
        self.draw_control_panel(canvas, synth_names, palette_name, freeze_states)

        return canvas
