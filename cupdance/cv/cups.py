import cv2
import numpy as np
import math
from cupdance import config

def lerp(a, b, t):
    return a * (1.0 - t) + b * t

class CupsProcessor:
    def __init__(self, size=(600, 600)):
        self.size = size
        self.roi_size = size[0] // 2
        
        # Values (0..1)
        self.raw_values = [0.0] * 4    # Last detected raw value
        self.smooth_values = [0.0] * 4 # EMA smoothed value
        self.snapped_values = [0.0] * 4 # Final output (with notch snap)
        
        # Latch / Occlusion handling
        # If cup is not seen, we hold the value for a while.
        # But actually, for "Latch" in a performance instrument, 
        # usually we want it to HOLD FOREVER until moved again.
        # So we just don't update if result is None.
        
        # Center of each ROI (relative to the ROI itself)
        # Assuming the cups are centered in their quadrants.
        # Future improvement: allow click-to-calibrate cup centers
        self.cup_center_roi = (self.roi_size // 2, self.roi_size // 2)
        
        # Velocity tracking
        self.prev_values = [0.0] * 4
        self.velocities = [0.0] * 4  # Rate of change (dv/dt)
        self.velocity_smooth = 0.3   # EMA for velocity smoothing

    def get_angle(self, roi):
        """
        Detects the marker in the ROI and calculates angle.
        Uses HSV color detection for better lighting robustness.
        Returns value 0..1 or None if not found.
        """
        # 1. Convert to HSV for robust color detection
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 2. Detect dark/black markers (low value channel)
        # Also can detect colored markers if needed
        # Black: any Hue, any Sat, low Value
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 60])  # Allow low-brightness pixels
        
        mask = cv2.inRange(hsv, lower_black, upper_black)
        
        # Optional: detect bright colored markers instead
        # For red marker: lower_red = np.array([0, 100, 100]), upper_red = np.array([10, 255, 255])
        
        # 3. Clean up mask
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        mask = cv2.dilate(mask, None, iterations=1)
        
        # 4. Find Contours
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not cnts:
            return None
        
        # 5. Pick Largest Contour (The marker)
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < 50:
            return None
            
        # 6. Centroid
        M = cv2.moments(c)
        if M["m00"] == 0:
             return None
             
        px = int(M["m10"] / M["m00"])
        py = int(M["m01"] / M["m00"])
        
        # 6. Calc Angle relative to cup center
        cx, cy = self.cup_center_roi
        dx = px - cx
        dy = py - cy
        
        # atan2 returns -pi to +pi
        angle = math.atan2(dy, dx) 
        
        # Normalize to 0..1
        # -pi -> 0, 0 -> 0.5, pi -> 1
        # Shift so 0 is typically "Right" or "Top" depending on preference
        # Here: 0 is Right (3 o'clock), growing clockwise? 
        # Screen coords: Y is down. 
        # dy>0 (down), dx>0 (right) -> Quadrant 1 (Bottom Right on screen) -> Angle +
        value = (angle + math.pi) / (2 * math.pi)
        
        return value, (px, py)

    def process(self, frame_warped):
        """
        Input: Warped cups frame (square)
        Output: 
          - values: List [vA, vB, vC, vD] (0..1)
          - debug_rois: List of ROIs with visualization
        """
        if frame_warped is None:
             return [0]*4, []

        h, w = self.size
        mid_x = w // 2
        mid_y = h // 2
        
        # Define ROIs (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
        # Order A, B, C, D
        # A: Top-Left
        # B: Top-Right
        # C: Bottom-Left (Usually ordered row by row)
        # Let's align with user prompt: A,B,C,D
        
        rois_coords = [
            (0, 0, mid_x, mid_y),       # A
            (mid_x, 0, w, mid_y),       # B
            (0, mid_y, mid_x, h),       # C
            (mid_x, mid_y, w, h)        # D
        ]
        
        current_values = []
        debug_rois = []
        
        for i, (x1, y1, x2, y2) in enumerate(rois_coords):
            roi = frame_warped[y1:y2, x1:x2].copy()
            
            # 1. Detection (Raw)
            result = self.get_angle(roi)
            
            # 2. Latch Logic: Only update raw if detected
            if result:
                val, center = result
                self.raw_values[i] = val
                
                # Visual Debug: Line from center to marker
                cv2.circle(roi, center, 5, (0, 0, 255), -1)
                cv2.line(roi, self.cup_center_roi, center, (255, 0, 0), 2)
            else:
                # Occluded: Keep self.raw_values[i] as is (Latch)
                # Visual Debug: Show "LATCHED" state?
                cv2.putText(roi, "LATCH", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

            # 3. Smoothing (EMA)
            # v_smooth = v_smooth * (1-alpha) + v_raw * alpha
            # Handle wrap-around?? If angle goes 0.99 -> 0.01, smoothing will sweep through 0.5.
            # Angle wrap handling is complex. For 0..1 linear knobs (cup dance?), maybe it's fine.
            # But cups are rotary. Ideally we smooth in polar coords or handle wrap.
            # MVP: Simple smoothing, assume no frantic wrapping.
            
            # To handle wrap properly: shortest distance.
            # diff = raw - smooth
            # if diff > 0.5: diff -= 1.0
            # if diff < -0.5: diff += 1.0
            # smooth += diff * alpha
            
            raw = self.raw_values[i]
            smooth = self.smooth_values[i]
            
            diff = raw - smooth
            if diff > 0.5: diff -= 1.0
            elif diff < -0.5: diff += 1.0
            
            new_smooth = smooth + (diff * config.SMOOTH_ALPHA)
            
            # Wrap result back to 0..1
            if new_smooth < 0.0: new_smooth += 1.0
            elif new_smooth > 1.0: new_smooth -= 1.0
            
            self.smooth_values[i] = new_smooth
            
            # 4. Notch Snapping
            # Notches are at k/N. Find nearest.
            v = self.smooth_values[i]
            notches = [k / config.NOTCH_COUNT for k in range(config.NOTCH_COUNT)]
            
            # Find closest notch explicitly handling wrap for 0 and 1 boundary? 
            # 0 and 1 are the same notch. 
            # Let's simple check min distance.
            # nearest = min(notches, key=lambda x: min(abs(x-v), 1-abs(x-v)))
            
            # Robust nearest notch
            nearest = 0
            min_dist = 999
            for n in notches:
                # Distance on circle
                d = abs(n - v)
                if d > 0.5: d = 1.0 - d
                if d < min_dist:
                    min_dist = d
                    nearest = n
            
            # Snap if close
            if min_dist < config.SNAP_EPS:
                # Smooth snap: lerp towards it? Or hard snap?
                # User said "snap a notches". Let's Hard snap or fast lerp.
                final_val = nearest
            else:
                final_val = v
                
            self.snapped_values[i] = final_val
            
            current_values.append(final_val)
            
            # Visualization text
            # Show Snapped Value large
            cv2.putText(roi, f"{final_val:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            # Show raw small
            cv2.putText(roi, f"R:{raw:.2f}", (self.roi_size-60, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
            
            debug_rois.append(roi)
        
        # Calculate velocities (rate of change)
        for i in range(4):
            # Handle wrap-around for velocity too
            diff = current_values[i] - self.prev_values[i]
            if diff > 0.5: diff -= 1.0
            elif diff < -0.5: diff += 1.0
            
            # Smooth velocity
            raw_vel = abs(diff) * 60.0  # Scale to approx units per second (assuming 60fps)
            self.velocities[i] = self.velocities[i] * (1 - self.velocity_smooth) + raw_vel * self.velocity_smooth
            
            self.prev_values[i] = current_values[i]
            
        return current_values, debug_rois, self.velocities
