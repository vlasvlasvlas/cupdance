import cv2
import numpy as np
import json
import os

class CalibrationUI:
    def __init__(self, window_name, target_size=(800, 800)):
        self.window_name = window_name
        self.target_size = target_size
        self.points = []
        self.complete = False

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to select points."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append((x, y))
                print(f"[{self.window_name}] Point {len(self.points)}: {x}, {y}")

    def run(self, cap):
        """
        Main loop for the calibration UI.
        Blocks until calibration is complete or user cancels.
        """
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print(f"[{self.window_name}] INSTRUCTIONS:")
        print("  1. Click the TOP-LEFT corner.")
        print("  2. Click the TOP-RIGHT corner.")
        print("  3. Click the BOTTOM-RIGHT corner.")
        print("  4. Click the BOTTOM-LEFT corner.")
        print("  (Press 'r' to reset points, 'q' to abort)")

        while True:
            frame = cap.read()
            if frame is None:
                # If camera is slow to start or disconnected
                cv2.waitKey(10)
                continue
            
            display = frame.copy()
            
            # visual feedback: Text
            cv2.putText(display, "CALIBRATION MODE: " + self.window_name, (20, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # Draw points
            for i, p in enumerate(self.points):
                # Circle
                cv2.circle(display, p, 5, (0, 0, 255), -1)
                # Label (1,2,3,4)
                cv2.putText(display, str(i+1), (p[0]+10, p[1]-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Draw lines connecting points so far
                if i > 0:
                     cv2.line(display, self.points[i-1], p, (255, 0, 0), 2)

            # Close the loop logic visually if 4 points
            if len(self.points) == 4:
                 cv2.line(display, self.points[3], self.points[0], (255, 0, 0), 2)

            cv2.imshow(self.window_name, display)

            key = cv2.waitKey(1) & 0xFF
            
            # --- Logic to Finalize ---
            if len(self.points) == 4:
                # Calculate Homography
                src_pts = np.float32(self.points)
                dst_pts = np.float32([
                    [0, 0],
                    [self.target_size[0], 0],
                    [self.target_size[0], self.target_size[1]],
                    [0, self.target_size[1]]
                ])
                H = cv2.getPerspectiveTransform(src_pts, dst_pts)
                
                # Show Preview
                warped = cv2.warpPerspective(frame, H, self.target_size)
                cv2.imshow(self.window_name + " Preview", warped)
                
                print(f"[{self.window_name}] 4 points selected. Showing Preview.")
                print("  Press 's' to SAVE and use this calibration.")
                print("  Press 'r' to RESET and try again.")
                
                # Inner loop for confirmation
                while True:
                    k2 = cv2.waitKey(0) & 0xFF
                    
                    if k2 == ord('s'):
                        cv2.destroyWindow(self.window_name)
                        cv2.destroyWindow(self.window_name + " Preview")
                        return H, self.points
                    
                    if k2 == ord('r'):
                        self.points = []
                        cv2.destroyWindow(self.window_name + " Preview")
                        print(f"[{self.window_name}] Resetting points.")
                        break
                    
                    if k2 == ord('q'):
                         cv2.destroyWindow(self.window_name)
                         cv2.destroyWindow(self.window_name + " Preview")
                         return None, None
            
            # Global Reset or Quit
            if key == ord('r'):
                self.points = []
            
            if key == ord('q'):
                cv2.destroyWindow(self.window_name)
                return None, None

def load_calibration(path=None):
    # Try multiple paths
    paths_to_try = [
        path,
        "cupdance/calibration.json",
        "calibration.json"
    ]
    
    for p in paths_to_try:
        if p and os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                print(f"[Calibration] Loaded from {p}")
                return data
    
    return {}

def save_calibration(data, path="calibration.json"):
    # Convert numpy arrays to lists for JSON serialization
    serialized_data = {}
    for k, v in data.items():
        if isinstance(v, np.ndarray):
            serialized_data[k] = v.tolist()
        else:
            serialized_data[k] = v
            
    with open(path, 'w') as f:
        json.dump(serialized_data, f, indent=4)
        print(f"Calibration saved to {path}")
