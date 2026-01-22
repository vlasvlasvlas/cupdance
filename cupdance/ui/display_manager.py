"""
Display Manager - Maneja todas las ventanas de visualización
Separa la lógica de detección de la visualización
"""
import cv2
import numpy as np

class DisplayManager:
    """
    Gestiona las 2 ventanas principales + 1 opcional:
    1. PISO: Video real + overlay de pads (o debug)
    2. TAZAS: Video real + overlay de zonas calibradas
    3. VISUALES: Arte generativo (opcional)
    """
    
    def __init__(self):
        # View modes
        self.floor_view_mode = "overlay"  # "overlay" or "debug"
        self.cups_view_mode = "overlay"   # "overlay" or "debug"
        self.show_visuals = False          # Optional visual window
        
        # Debug info
        self.show_fps = True
        self.show_values = True
        
        # Camera control state (for display)
        self.active_cam = "floor"
        self.floor_brightness = 0
        self.floor_contrast = 1.0
        self.cups_brightness = 0
        self.cups_contrast = 1.0
    
    def update_cam_controls(self, active_cam, floor_br, floor_co, cups_br, cups_co):
        """Update camera control state for display."""
        self.active_cam = active_cam
        self.floor_brightness = floor_br
        self.floor_contrast = floor_co
        self.cups_brightness = cups_br
        self.cups_contrast = cups_co
        
    def toggle_floor_view(self):
        """Toggle between overlay and debug view for floor."""
        self.floor_view_mode = "debug" if self.floor_view_mode == "overlay" else "overlay"
        return self.floor_view_mode
    
    def toggle_cups_view(self):
        """Toggle between overlay and debug view for cups."""
        self.cups_view_mode = "debug" if self.cups_view_mode == "overlay" else "overlay"
        return self.cups_view_mode
    
    def toggle_visuals(self):
        """Toggle optional visuals window."""
        self.show_visuals = not self.show_visuals
        if not self.show_visuals:
            cv2.destroyWindow("3. VISUALES")
        return self.show_visuals
    
    def render_floor_overlay(self, video_frame, floor_points, body_pad, body_kaoss, mode="pad"):
        """
        Render floor camera with pad/kaoss overlay.
        Shows FULL camera view with calibrated zone highlighted and grid overlay.
        
        Args:
            video_frame: ORIGINAL full video from floor camera (not warped)
            floor_points: 4 calibration corner points
            body_pad: BodyPad instance
            body_kaoss: BodyKaoss instance  
            mode: "pad" or "kaoss"
        """
        if video_frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Ensure 3 channels
        if len(video_frame.shape) == 2:
            display = cv2.cvtColor(video_frame, cv2.COLOR_GRAY2BGR)
        else:
            display = video_frame.copy()
        
        h, w = display.shape[:2]
        
        # Draw calibrated zone boundary
        if floor_points and len(floor_points) == 4:
            pts = np.array(floor_points, np.int32)
            
            # Semi-transparent fill for active zone
            overlay = display.copy()
            cv2.fillPoly(overlay, [pts], (40, 40, 40))
            display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
            
            # Draw zone boundary
            cv2.polylines(display, [pts], True, (0, 255, 255), 3)
            
            # Draw grid INSIDE calibrated zone using perspective
            if mode == "pad":
                display = self._draw_pad_grid_perspective(display, pts, body_pad)
            else:
                display = self._draw_kaoss_perspective(display, pts, body_kaoss)
        
        # === HEADER ===
        header_h = 60
        cv2.rectangle(display, (0, 0), (w, header_h), (20, 20, 20), -1)
        
        # Title with mode
        if mode == "pad":
            mode_text = f"BODY PAD - {body_pad.rows}x{body_pad.cols} pads - {body_pad.scale_name}"
            mode_color = (100, 255, 100)
        else:
            mode_text = "KAOSS XY - Mueve para modular efectos"
            mode_color = (255, 100, 255)
        
        cv2.putText(display, "1. PISO", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display, mode_text, (120, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1)
        
        # Camera controls
        active_indicator = ">" if self.active_cam == "floor" else " "
        ctrl_text = f"{active_indicator}Br:{self.floor_brightness:+d} Co:{self.floor_contrast:.1f}"
        ctrl_color = (0, 255, 255) if self.active_cam == "floor" else (120, 120, 120)
        cv2.putText(display, ctrl_text, (w - 160, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, ctrl_color, 1)
        
        # Keyboard shortcuts
        shortcuts = "[V] Vista  [M] Pad/Kaoss  [S] Escala  [P] Layout  [B] Fondo  [TAB] Cam"
        cv2.putText(display, shortcuts, (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 200, 150), 1)
        
        # === FOOTER - Active pads ===
        footer_h = 40
        cv2.rectangle(display, (0, h - footer_h), (w, h), (20, 20, 20), -1)
        
        if mode == "pad":
            # Show active pads
            active_pads = [i+1 for i in range(body_pad.num_pads) if body_pad.pad_active[i]]
            if active_pads:
                active_text = f"ACTIVOS: {', '.join(map(str, active_pads))}"
                cv2.putText(display, active_text, (10, h - 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                cv2.putText(display, "Pisa dentro de la zona para activar pads", (10, h - 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        else:
            # Show XY position
            fx = body_kaoss.get_fx_params()
            xy_text = f"X: {fx['x']:.2f}  Y: {fx['y']:.2f}  Presion: {fx['pressure']:.2f}"
            cv2.putText(display, xy_text, (10, h - 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 255), 1)
        
        return display
    
    def _draw_pad_grid_perspective(self, display, zone_pts, body_pad):
        """Draw pad grid with perspective matching the calibrated zone."""
        # Get bounding box of zone
        x_coords = zone_pts[:, 0]
        y_coords = zone_pts[:, 1]
        
        # Create grid lines using perspective interpolation
        rows, cols = body_pad.rows, body_pad.cols
        
        # Interpolate points along edges
        def lerp_points(p1, p2, t):
            return (int(p1[0] + t * (p2[0] - p1[0])), int(p1[1] + t * (p2[1] - p1[1])))
        
        # Zone corners: 0=TL, 1=TR, 2=BR, 3=BL (assumed order)
        tl, tr, br, bl = zone_pts[0], zone_pts[1], zone_pts[2], zone_pts[3]
        
        # Draw vertical lines
        for i in range(cols + 1):
            t = i / cols
            top = lerp_points(tl, tr, t)
            bot = lerp_points(bl, br, t)
            color = (0, 255, 255) if i == 0 or i == cols else (100, 200, 200)
            cv2.line(display, top, bot, color, 2 if i == 0 or i == cols else 1)
        
        # Draw horizontal lines
        for i in range(rows + 1):
            t = i / rows
            left = lerp_points(tl, bl, t)
            right = lerp_points(tr, br, t)
            color = (0, 255, 255) if i == 0 or i == rows else (100, 200, 200)
            cv2.line(display, left, right, color, 2 if i == 0 or i == rows else 1)
        
        # Draw pad labels and states
        for pad_idx in range(body_pad.num_pads):
            row = pad_idx // cols
            col = pad_idx % cols
            
            # Calculate center of this cell using bilinear interpolation
            t_col = (col + 0.5) / cols
            t_row = (row + 0.5) / rows
            
            top_pt = lerp_points(tl, tr, t_col)
            bot_pt = lerp_points(bl, br, t_col)
            center = lerp_points(top_pt, bot_pt, t_row)
            
            # Pad state
            is_active = body_pad.pad_active[pad_idx]
            
            if is_active:
                # Draw filled circle for active pad
                cv2.circle(display, center, 30, (0, 255, 0), -1)
                cv2.circle(display, center, 30, (255, 255, 255), 3)
            
            # Pad number
            num_color = (0, 0, 0) if is_active else (255, 255, 255)
            cv2.putText(display, str(pad_idx + 1), (center[0] - 10, center[1] + 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, num_color, 2)
            
            # Note name (small, below number)
            note = body_pad.pad_notes[pad_idx]
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            note_name = note_names[note % 12] + str(note // 12 - 1)
            note_color = (100, 255, 100) if is_active else (150, 150, 150)
            cv2.putText(display, note_name, (center[0] - 15, center[1] + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, note_color, 1)
        
        return display
    
    def _draw_kaoss_perspective(self, display, zone_pts, body_kaoss):
        """Draw Kaoss XY surface with perspective matching the calibrated zone."""
        # Draw crosshairs
        tl, tr, br, bl = zone_pts[0], zone_pts[1], zone_pts[2], zone_pts[3]
        
        def lerp_points(p1, p2, t):
            return (int(p1[0] + t * (p2[0] - p1[0])), int(p1[1] + t * (p2[1] - p1[1])))
        
        # Center crosshair
        center_top = lerp_points(tl, tr, 0.5)
        center_bot = lerp_points(bl, br, 0.5)
        center_left = lerp_points(tl, bl, 0.5)
        center_right = lerp_points(tr, br, 0.5)
        
        cv2.line(display, center_top, center_bot, (255, 100, 255), 1)
        cv2.line(display, center_left, center_right, (255, 100, 255), 1)
        
        # Draw current position
        fx = body_kaoss.get_fx_params()
        if fx['pressure'] > 0.01:
            # Map XY to zone
            pos_top = lerp_points(tl, tr, fx['x'])
            pos_bot = lerp_points(bl, br, fx['x'])
            pos = lerp_points(pos_top, pos_bot, fx['y'])
            
            radius = int(20 + fx['pressure'] * 30)
            cv2.circle(display, pos, radius, (255, 0, 255), -1)
            cv2.circle(display, pos, radius, (255, 255, 255), 2)
        
        # Axis labels
        cv2.putText(display, "FILTER", center_top, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 255), 1)
        cv2.putText(display, "REVERB", (center_right[0] - 60, center_right[1]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 255), 1)
        
        return display
    
    def render_floor_debug(self, video_frame, warped_frame, motion_mask, floor_points, body_pad, features):
        """
        Render technical debug view for floor detection.
        Shows: motion mask, pad activations, detection values
        """
        if motion_mask is None:
            return np.zeros((512, 512, 3), dtype=np.uint8)
        
        # Convert mask to color
        if len(motion_mask.shape) == 2:
            display = cv2.cvtColor(motion_mask, cv2.COLOR_GRAY2BGR)
        else:
            display = motion_mask.copy()
        
        h, w = display.shape[:2]
        
        # Draw pad grid lines
        pad_w = w // body_pad.cols
        pad_h = h // body_pad.rows
        
        for i in range(1, body_pad.cols):
            x = i * pad_w
            cv2.line(display, (x, 0), (x, h), (0, 255, 255), 2)
        
        for i in range(1, body_pad.rows):
            y = i * pad_h
            cv2.line(display, (0, y), (w, y), (0, 255, 255), 2)
        
        # Draw pad info
        for i in range(body_pad.num_pads):
            x1, y1, x2, y2 = body_pad.get_pad_rect(i)
            
            # Pad number
            cv2.putText(display, f"P{i+1}", (x1 + 5, y1 + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Pressure value
            pressure = body_pad.pad_pressure[i]
            cv2.putText(display, f"{pressure:.2f}", (x1 + 5, y1 + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Active indicator
            if body_pad.pad_active[i]:
                cv2.rectangle(display, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (0, 255, 0), 3)
                cv2.putText(display, "ON", (x1 + 5, y2 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Header
        cv2.rectangle(display, (0, 0), (w, 40), (0, 0, 0), -1)
        cv2.putText(display, "1. PISO - DEBUG", (10, 28), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Footer with features
        cv2.rectangle(display, (0, h - 30), (w, h), (0, 0, 0), -1)
        q_text = f"Q1:{features.get('q1_density',0):.2f} Q2:{features.get('q2_density',0):.2f} " \
                 f"Q3:{features.get('q3_density',0):.2f} Q4:{features.get('q4_density',0):.2f}"
        cv2.putText(display, q_text, (10, h - 8), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return display
    
    def render_cups_overlay(self, video_frame, tangible_proc, cups_points):
        """
        Render cups camera with tangible synthesis overlay.
        Everything is drawn INSIDE the calibrated zone.
        """
        if video_frame is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8)
        
        display = video_frame.copy()
        h, w = display.shape[:2]
        
        # Draw calibrated zone boundary (always visible)
        if cups_points and len(cups_points) == 4:
            pts = np.array(cups_points, np.int32)
            cv2.polylines(display, [pts], True, (0, 255, 255), 3)
        
        # Draw cup circles at calibrated positions
        if tangible_proc.cup_positions:
            for i, (cx, cy) in enumerate(tangible_proc.cup_positions):
                label = ["A", "B", "C", "D"][i]
                radius = tangible_proc.cup_radius
                
                # Circle color based on detection
                if tangible_proc.cup_detected[i]:
                    color = (0, 255, 0)  # Green = detected
                    # Draw rotation indicator
                    value = tangible_proc.cup_values[i]
                    angle_deg = value * 360
                    cv2.ellipse(display, (cx, cy), (radius - 10, radius - 10),
                               -90, 0, angle_deg, (0, 255, 100), 4)
                    
                    # Draw marker position
                    if tangible_proc.cup_marker_pos[i]:
                        mx, my = tangible_proc.cup_marker_pos[i]
                        cv2.circle(display, (mx, my), 8, (0, 0, 255), -1)
                        cv2.line(display, (cx, cy), (mx, my), (0, 0, 255), 2)
                else:
                    color = (100, 100, 100)  # Gray = not detected
                
                # Draw circle
                cv2.circle(display, (cx, cy), radius, color, 2)
                
                # Label
                cv2.putText(display, label, (cx - 15, cy - radius - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                
                # Value
                val_text = f"{tangible_proc.cup_values[i]:.2f}"
                cv2.putText(display, val_text, (cx - 25, cy + 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                # Status
                status = "OK" if tangible_proc.cup_detected[i] else "LATCH"
                status_color = (0, 255, 0) if tangible_proc.cup_detected[i] else (0, 100, 255)
                cv2.putText(display, status, (cx - 25, cy + radius + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
        
        # Draw ADSR zone
        if tangible_proc.adsr_zone:
            ax, ay, aw, ah = tangible_proc.adsr_zone
            cv2.rectangle(display, (ax, ay), (ax + aw, ay + ah), (100, 255, 100), 2)
            cv2.putText(display, "ADSR", (ax + 10, ay + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
            
            # Draw detected curve if exists
            if tangible_proc.frozen_adsr is not None and np.max(tangible_proc.frozen_adsr) > 0.05:
                curve = tangible_proc.frozen_adsr
                for j in range(len(curve) - 1):
                    x1 = ax + int((j / len(curve)) * aw)
                    x2 = ax + int(((j + 1) / len(curve)) * aw)
                    y1 = ay + ah - int(curve[j] * (ah - 10))
                    y2 = ay + ah - int(curve[j + 1] * (ah - 10))
                    cv2.line(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw Wave zone
        if tangible_proc.wave_zone:
            wx, wy, ww, wh = tangible_proc.wave_zone
            cv2.rectangle(display, (wx, wy), (wx + ww, wy + wh), (255, 100, 100), 2)
            cv2.putText(display, "WAVE", (wx + 10, wy + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 100, 100), 2)
            
            # Center line
            cv2.line(display, (wx, wy + wh // 2), (wx + ww, wy + wh // 2), (80, 80, 80), 1)
            
            # Draw detected curve if exists
            if tangible_proc.frozen_wave is not None and np.max(tangible_proc.frozen_wave) > 0.05:
                curve = tangible_proc.frozen_wave
                for j in range(len(curve) - 1):
                    x1 = wx + int((j / len(curve)) * ww)
                    x2 = wx + int(((j + 1) / len(curve)) * ww)
                    y1 = wy + wh - int(curve[j] * (wh - 10))
                    y2 = wy + wh - int(curve[j + 1] * (wh - 10))
                    cv2.line(display, (x1, y1), (x2, y2), (0, 100, 255), 2)
        
        # Header with instructions
        cv2.rectangle(display, (0, 0), (w, 55), (0, 0, 0), -1)
        cv2.putText(display, "2. TAZAS - TANGIBLE SYNTH", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show camera controls status
        active_indicator = "*" if self.active_cam == "cups" else ""
        ctrl_text = f"{active_indicator}Br:{self.cups_brightness:+d} Co:{self.cups_contrast:.1f}"
        ctrl_color = (0, 255, 255) if self.active_cam == "cups" else (150, 150, 150)
        cv2.putText(display, ctrl_text, (w - 150, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, ctrl_color, 1)
        
        cv2.putText(display, "[N]Vista [F]ADSR [G]Wave [TAB]Cam activa [;'][[]] Ajustar", 
                   (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 255, 150), 1)
        
        # Footer with cup meanings
        cv2.rectangle(display, (0, h - 40), (w, h), (0, 0, 0), -1)
        cv2.putText(display, "A=Pitch | B=Timbre | C=Filter | D=FX | Dibuja curvas ADSR y WAVE con marcador oscuro", 
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return display
    
    def render_cups_debug(self, video_frame, tangible_proc, cups_points):
        """
        Technical debug view for cups - shows detection details.
        """
        if video_frame is None:
            return np.zeros((720, 1280, 3), dtype=np.uint8)
        
        display = video_frame.copy()
        h, w = display.shape[:2]
        
        # Draw calibrated zone with fill
        if cups_points and len(cups_points) == 4:
            pts = np.array(cups_points, np.int32)
            overlay = display.copy()
            cv2.fillPoly(overlay, [pts], (50, 50, 0))
            display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
            cv2.polylines(display, [pts], True, (0, 255, 255), 3)
        
        # Zone rect info
        if tangible_proc.zone_rect:
            zx, zy, zw, zh = tangible_proc.zone_rect
            cv2.putText(display, f"Zone: {zx},{zy} {zw}x{zh}", (10, h - 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Cup detection details
        y_offset = 60
        for i in range(4):
            label = ["A", "B", "C", "D"][i]
            detected = tangible_proc.cup_detected[i]
            value = tangible_proc.cup_values[i]
            
            status = "DETECTED" if detected else "NOT FOUND"
            color = (0, 255, 0) if detected else (0, 0, 255)
            
            text = f"Cup {label}: {status} | Value: {value:.3f}"
            cv2.putText(display, text, (10, y_offset + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Header
        cv2.rectangle(display, (0, 0), (350, 50), (0, 0, 0), -1)
        cv2.putText(display, "2. TAZAS - DEBUG", (10, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return display
    
    def _draw_pad_overlay(self, frame, body_pad):
        """Draw semi-transparent pad grid over video."""
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        for i in range(body_pad.num_pads):
            x1, y1, x2, y2 = body_pad.get_pad_rect(i)
            
            if body_pad.pad_active[i]:
                # Active pad - fill with color
                pressure = body_pad.pad_pressure[i]
                base_color = body_pad.pad_colors_off[i % len(body_pad.pad_colors_off)]
                color = tuple(int(c * (1 + pressure * 2)) for c in base_color)
                color = tuple(min(255, c) for c in color)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
                
                # Position indicator
                px, py = body_pad.pad_position[i]
                cx = int(x1 + px * (x2 - x1))
                cy = int(y1 + py * (y2 - y1))
                cv2.circle(overlay, (cx, cy), 20, (255, 255, 255), 3)
            else:
                # Inactive - just outline
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (100, 100, 100), 2)
            
            # Pad label
            note_name = body_pad._midi_to_name(body_pad.pad_notes[i])
            cv2.putText(overlay, f"{i+1}", (x1 + 10, y1 + 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(overlay, note_name, (x1 + 10, y1 + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Blend
        result = cv2.addWeighted(frame, 0.5, overlay, 0.5, 0)
        
        # Active pads footer
        active = body_pad.get_active_pads()
        if active:
            footer = f"Active: {', '.join([str(p+1) for p in active])}"
            cv2.putText(result, footer, (10, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return result
    
    def _draw_kaoss_overlay(self, frame, body_kaoss):
        """Draw Kaoss-style XY crosshair over video."""
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Grid lines
        for i in range(1, 4):
            x = int(w * i / 4)
            y = int(h * i / 4)
            cv2.line(overlay, (x, 40), (x, h), (60, 60, 60), 1)
            cv2.line(overlay, (0, y), (w, y), (60, 60, 60), 1)
        
        # XY position
        cx = int(body_kaoss.x * w)
        cy = int(body_kaoss.y * h)
        pressure = body_kaoss.pressure
        
        if pressure > 0.01:
            # Crosshair
            size = int(30 + pressure * 100)
            color = (0, int(200 * pressure + 55), 255)
            
            cv2.line(overlay, (cx - size, cy), (cx + size, cy), color, 3)
            cv2.line(overlay, (cx, cy - size), (cx, cy + size), color, 3)
            cv2.circle(overlay, (cx, cy), size // 2, color, 2)
            
            # Velocity trails
            vx = int(body_kaoss.velocity_x * 20)
            vy = int(body_kaoss.velocity_y * 20)
            cv2.arrowedLine(overlay, (cx, cy), (cx + vx, cy + vy), (255, 255, 0), 2)
        
        # Blend
        result = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)
        
        # XY values footer
        cv2.putText(result, f"X:{body_kaoss.x:.2f} Y:{body_kaoss.y:.2f} P:{pressure:.2f}",
                   (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Effect hints
        cv2.putText(result, "FILTER", (w - 80, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        cv2.putText(result, "REVERB", (w // 2 - 30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        return result
