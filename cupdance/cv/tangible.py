import cv2
import numpy as np
import math

class TangibleSynthProcessor:
    """
    Processes the cups camera using CALIBRATED zone:
    - Uses cups_points from calibration to define the active area
    - Inside that zone:
      - Left 2/3: 4 cup detection circles (2x2 grid)
      - Right 1/3 top: ADSR drawing zone
      - Right 1/3 bottom: Waveform drawing zone
    - Overlays are drawn ON TOP of raw camera feed at correct positions
    """
    
    def __init__(self, frame_size=(1280, 720)):
        self.frame_w, self.frame_h = frame_size
        
        # Calibrated zone (will be set from cups_points)
        self.zone_points = None  # 4 corners from calibration
        self.zone_rect = None    # Bounding rect (x, y, w, h)
        
        # Cup positions (relative to zone, computed on set_zone)
        self.cup_positions = []  # [(cx, cy), ...] in FRAME coordinates
        self.cup_radius = 50
        
        # ADSR/Wave zones (in FRAME coordinates)
        self.adsr_zone = None  # (x, y, w, h)
        self.wave_zone = None  # (x, y, w, h)
        
        # Frozen curves (when user presses freeze key)
        self.frozen_adsr = None  # Normalized 0..1 array
        self.frozen_wave = None  # 256-sample wavetable
        
        # Detection threshold - higher = less sensitive (needs darker lines)
        self.line_thresh = 100  # Adjusted for pencil/marker drawings
        
        # Cup detection state
        self.cup_values = [0.0, 0.0, 0.0, 0.0]  # Rotation 0..1
        self.cup_detected = [False, False, False, False]
        self.cup_marker_pos = [None, None, None, None]  # Marker position for each cup
        
    def set_zone(self, cups_points):
        """
        Set the calibrated zone from cups_points (4 corners).
        This defines where everything is drawn and detected.
        """
        if cups_points is None or len(cups_points) != 4:
            return False
            
        self.zone_points = [(int(p[0]), int(p[1])) for p in cups_points]
        
        # Get bounding rectangle
        xs = [p[0] for p in self.zone_points]
        ys = [p[1] for p in self.zone_points]
        x1, y1 = min(xs), min(ys)
        x2, y2 = max(xs), max(ys)
        w, h = x2 - x1, y2 - y1
        
        self.zone_rect = (x1, y1, w, h)
        
        # Layout inside zone:
        # |  Cup A  |  Cup B  | ADSR  |
        # |  Cup C  |  Cup D  | Wave  |
        
        # Cups take left 2/3, drawing zones take right 1/3
        cup_area_w = int(w * 0.65)
        draw_area_w = w - cup_area_w
        draw_area_x = x1 + cup_area_w
        
        # Cup grid (2x2 in left area)
        cup_cell_w = cup_area_w // 2
        cup_cell_h = h // 2
        
        self.cup_radius = min(cup_cell_w, cup_cell_h) // 2 - 15
        
        self.cup_positions = [
            (x1 + cup_cell_w // 2, y1 + cup_cell_h // 2),          # A: top-left
            (x1 + cup_cell_w + cup_cell_w // 2, y1 + cup_cell_h // 2),  # B: top-right
            (x1 + cup_cell_w // 2, y1 + cup_cell_h + cup_cell_h // 2),  # C: bottom-left
            (x1 + cup_cell_w + cup_cell_w // 2, y1 + cup_cell_h + cup_cell_h // 2)  # D: bottom-right
        ]
        
        # ADSR zone (top half of right 1/3)
        self.adsr_zone = (draw_area_x, y1, draw_area_w, h // 2)
        
        # Waveform zone (bottom half of right 1/3)
        self.wave_zone = (draw_area_x, y1 + h // 2, draw_area_w, h // 2)
        
        print(f"[Tangible] Zone set: rect={self.zone_rect}")
        print(f"[Tangible] Cup positions: {self.cup_positions}")
        print(f"[Tangible] ADSR zone: {self.adsr_zone}")
        print(f"[Tangible] Wave zone: {self.wave_zone}")
        
        return True
    
    def detect_cup_marker(self, roi, cup_idx):
        """
        Detect the marker (handle) in a cup ROI and calculate rotation angle.
        Uses edge detection which works for any color cup handle.
        Returns (value 0..1, marker_position) or (None, None) if not found.
        """
        if roi is None or roi.size == 0:
            return None, None
        
        h, w = roi.shape[:2]
        if h < 10 or w < 10:
            return None, None
        
        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use Canny edge detection - works for any color
        edges = cv2.Canny(blurred, 30, 100)
        
        # Dilate edges to connect them
        edges = cv2.dilate(edges, None, iterations=2)
        
        # Also try to detect the handle by looking for dark regions
        # (handles are often darker than the cup body)
        _, dark_mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
        
        # Combine edge and dark detection
        mask = cv2.bitwise_or(edges, dark_mask)
        
        # Create a mask that excludes the center (cup body)
        center_mask = np.zeros_like(mask)
        cv2.circle(center_mask, (w//2, h//2), int(min(w, h) * 0.25), 255, -1)
        mask = cv2.bitwise_and(mask, cv2.bitwise_not(center_mask))
        
        # Find contours
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not cnts:
            return None, None
        
        # Pick largest contour
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < 50:
            return None, None
        
        # Get centroid
        M = cv2.moments(c)
        if M["m00"] == 0:
            return None, None
        
        px = int(M["m10"] / M["m00"])
        py = int(M["m01"] / M["m00"])
        
        # Calculate angle relative to center
        h, w = roi.shape[:2]
        cx, cy = w // 2, h // 2
        dx = px - cx
        dy = py - cy
        
        angle = math.atan2(dy, dx)
        value = (angle + math.pi) / (2 * math.pi)  # Normalize to 0..1
        
        return value, (px, py)
        
    def extract_curve(self, roi, num_samples=256):
        """
        Extracts a curve from a drawing ROI.
        Returns normalized Y values at regular X intervals.
        """
        if roi is None or roi.size == 0:
            return np.zeros(num_samples)
            
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Threshold to find dark line
        _, thresh = cv2.threshold(gray, self.line_thresh, 255, cv2.THRESH_BINARY_INV)
        
        # Dilate to connect broken lines
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        h, w = thresh.shape
        
        # Sample Y value at each X position
        curve = np.zeros(num_samples, dtype=np.float32)
        
        for i in range(num_samples):
            x = int((i / num_samples) * w)
            col = thresh[:, max(0, x-2):min(w, x+3)]  # 5px wide column
            
            # Find topmost white pixel (line position)
            ys = np.where(col.max(axis=1) > 0)[0]
            
            if len(ys) > 0:
                y_avg = np.mean(ys)
                curve[i] = 1.0 - (y_avg / h)  # Invert: top = high value
            else:
                curve[i] = -1  # Mark as missing
        
        # Interpolate missing values
        valid_mask = curve >= 0
        if np.any(valid_mask):
            xp = np.where(valid_mask)[0]
            fp = curve[valid_mask]
            x_all = np.arange(num_samples)
            curve = np.interp(x_all, xp, fp)
        else:
            curve = np.zeros(num_samples)
        
        return np.clip(curve, 0, 1)
    
    def curve_to_adsr(self, curve):
        """
        Converts a curve to ADSR parameters.
        Assumes curve is normalized 0..1, 256 samples.
        """
        n = len(curve)
        
        # Find peak (end of attack)
        peak_idx = np.argmax(curve)
        peak_val = curve[peak_idx]
        
        # Attack: rise from start to peak
        attack_ratio = peak_idx / n if peak_val > 0.1 else 0.01
        
        # Find sustain level (average of middle section)
        mid_start = max(peak_idx + n//8, n//4)
        mid_end = min(mid_start + n//4, 3*n//4)
        sustain_level = np.mean(curve[mid_start:mid_end]) if mid_end > mid_start else 0.5
        
        # Decay: drop from peak to sustain
        decay_ratio = (mid_start - peak_idx) / n if mid_start > peak_idx else 0.1
        
        # Release: last quarter of curve
        release_start = 3 * n // 4
        release_ratio = (n - release_start) / n
        
        return {
            "attack": max(0.01, attack_ratio * 2.0),      # Scale to seconds
            "decay": max(0.01, decay_ratio * 1.0),
            "sustain": max(0.1, min(1.0, sustain_level)),
            "release": max(0.05, release_ratio * 2.0)
        }
    
    def process(self, frame, freeze_adsr=False, freeze_wave=False):
        """
        Process full frame with calibrated zones.
        All overlays are drawn INSIDE the calibrated zone.
        Returns: 
            - cup_values: List of 4 values (0..1) for each cup rotation
            - adsr_params: dict or None
            - wavetable: 256-sample array or None
            - debug_frame: annotated frame
        """
        if frame is None:
            return [0.0]*4, None, None, None
        
        h, w = frame.shape[:2]
        debug = frame.copy()
        
        # Check if zone is configured
        if self.zone_rect is None or not self.cup_positions:
            # Draw message asking to calibrate
            cv2.putText(debug, "ZONA NO CALIBRADA", (w//2 - 150, h//2), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1.0, (0, 0, 255), 2)
            cv2.putText(debug, "Presiona 'R' para calibrar", (w//2 - 120, h//2 + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            return [0.0]*4, None, None, debug
        
        zx, zy, zw, zh = self.zone_rect
        
        # --- Draw calibrated zone boundary ---
        if self.zone_points:
            pts = np.array(self.zone_points, np.int32)
            cv2.polylines(debug, [pts], True, (0, 255, 255), 2)
        
        # --- Process each cup position ---
        cup_cell_w = int(zw * 0.65) // 2  # Width of each cup cell
        cup_cell_h = zh // 2
        
        for i, (cx, cy) in enumerate(self.cup_positions):
            label = ["A", "B", "C", "D"][i]
            
            # Extract ROI around cup position
            roi_size = self.cup_radius * 2
            roi_x1 = max(0, cx - self.cup_radius)
            roi_y1 = max(0, cy - self.cup_radius)
            roi_x2 = min(w, cx + self.cup_radius)
            roi_y2 = min(h, cy + self.cup_radius)
            
            if roi_x2 > roi_x1 and roi_y2 > roi_y1:
                roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                
                # Detect cup marker
                result = self.detect_cup_marker(roi, i)
                
                if result[0] is not None:
                    value, marker_pos = result
                    self.cup_values[i] = value
                    self.cup_detected[i] = True
                    # Convert marker position to frame coordinates
                    self.cup_marker_pos[i] = (roi_x1 + marker_pos[0], roi_y1 + marker_pos[1])
                    
                    # Draw detected marker and rotation line
                    cv2.circle(debug, self.cup_marker_pos[i], 6, (0, 255, 0), -1)
                    cv2.line(debug, (cx, cy), self.cup_marker_pos[i], (0, 255, 0), 2)
                    
                    # Draw value arc (shows rotation amount)
                    angle_deg = value * 360
                    cv2.ellipse(debug, (cx, cy), (self.cup_radius - 10, self.cup_radius - 10), 
                               -90, 0, angle_deg, (0, 255, 100), 3)
                else:
                    self.cup_detected[i] = False
                    # Show "LATCH" if cup not detected but value retained
                    cv2.putText(debug, "LATCH", (cx - 25, cy + self.cup_radius + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 255), 1)
            
            # Draw cup circle guide
            color = (0, 200, 0) if self.cup_detected[i] else (100, 100, 100)
            cv2.circle(debug, (cx, cy), self.cup_radius, color, 2)
            
            # Draw label and value
            cv2.putText(debug, label, (cx - 8, cy - self.cup_radius - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(debug, f"{self.cup_values[i]:.2f}", (cx - 25, cy + 8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # --- ADSR and Waveform zones ---
        adsr_params = None
        wavetable = None
        
        if self.adsr_zone is not None:
            ax, ay, aw, ah = self.adsr_zone
            
            # Draw ADSR zone
            cv2.rectangle(debug, (ax + 3, ay + 3), (ax + aw - 3, ay + ah - 3), (100, 200, 100), 2)
            cv2.putText(debug, "ADSR", (ax + 10, ay + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 1)
            
            # ADSR axis labels
            cv2.putText(debug, "A", (ax + 5, ay + ah - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
            cv2.putText(debug, "D", (ax + aw//4, ay + ah - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
            cv2.putText(debug, "S", (ax + aw//2, ay + ah - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
            cv2.putText(debug, "R", (ax + 3*aw//4, ay + ah - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
            
            # Extract and process ADSR curve
            if ay >= 0 and ay + ah <= h and ax >= 0 and ax + aw <= w:
                adsr_roi = frame[ay:ay+ah, ax:ax+aw]
                
                if not freeze_adsr or self.frozen_adsr is None:
                    adsr_curve = self.extract_curve(adsr_roi, num_samples=128)
                    self.frozen_adsr = adsr_curve
                else:
                    adsr_curve = self.frozen_adsr
                
                if np.max(adsr_curve) > 0.05:
                    adsr_params = self.curve_to_adsr(adsr_curve)
                    
                    # Draw detected curve
                    for j in range(len(adsr_curve) - 1):
                        x1 = ax + int((j / len(adsr_curve)) * aw)
                        x2 = ax + int(((j+1) / len(adsr_curve)) * aw)
                        y1 = ay + ah - int(adsr_curve[j] * (ah - 30))
                        y2 = ay + ah - int(adsr_curve[j+1] * (ah - 30))
                        cv2.line(debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        if self.wave_zone is not None:
            wx, wy, ww, wh = self.wave_zone
            
            # Draw Waveform zone
            cv2.rectangle(debug, (wx + 3, wy + 3), (wx + ww - 3, wy + wh - 3), (200, 100, 100), 2)
            cv2.putText(debug, "WAVE", (wx + 10, wy + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 1)
            
            # Center line for waveform reference
            cv2.line(debug, (wx, wy + wh//2), (wx + ww, wy + wh//2), (80, 80, 80), 1)
            
            # Extract and process waveform
            if wy >= 0 and wy + wh <= h and wx >= 0 and wx + ww <= w:
                wave_roi = frame[wy:wy+wh, wx:wx+ww]
                
                if not freeze_wave or self.frozen_wave is None:
                    wave_curve = self.extract_curve(wave_roi, num_samples=256)
                    self.frozen_wave = wave_curve
                else:
                    wave_curve = self.frozen_wave
                
                if np.max(wave_curve) > 0.05:
                    wavetable = (wave_curve * 2.0) - 1.0
                    
                    # Draw detected curve
                    for j in range(len(wave_curve) - 1):
                        x1 = wx + int((j / len(wave_curve)) * ww)
                        x2 = wx + int(((j+1) / len(wave_curve)) * ww)
                        y1 = wy + wh - int(wave_curve[j] * (wh - 30))
                        y2 = wy + wh - int(wave_curve[j+1] * (wh - 30))
                        cv2.line(debug, (x1, y1), (x2, y2), (0, 100, 255), 2)
        
        # --- Title and controls ---
        cv2.rectangle(debug, (0, 0), (300, 55), (0, 0, 0), -1)
        cv2.putText(debug, "TANGIBLE SYNTHESIS", (10, 25), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(debug, "F=Freeze ADSR | G=Freeze Wave", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
        
        # Freeze status indicators
        if freeze_adsr:
            cv2.putText(debug, "[ADSR FROZEN]", (w - 150, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        if freeze_wave:
            cv2.putText(debug, "[WAVE FROZEN]", (w - 150, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return self.cup_values, adsr_params, wavetable, debug
    
    def freeze(self, which="both"):
        """Freeze current curves."""
        pass
