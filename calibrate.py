import cv2
import sys
import os

# Ensure we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cupdance import config
from cupdance.cv.capture import CameraStream
from cupdance.ui.calibration import CalibrationUI, save_calibration

def main():
    print("--- CUPDANCE CALIBRATION TOOL ---")
    
    # 1. Calibrate Floor
    print("\n[STEP 1] Calibrating FLOOR Camera")
    cam_floor = CameraStream(src=config.CAM_FLOOR_ID, name="Floor", 
                             width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
    cam_floor.start()
    
    calib_ui_floor = CalibrationUI("Floor Calibration", target_size=(config.WARP_FLOOR_SIZE, config.WARP_FLOOR_SIZE))
    H_floor, pts_floor = calib_ui_floor.run(cam_floor)
    
    cam_floor.stop()
    
    if H_floor is None:
        print("Floor calibration aborted.")
        sys.exit()

    # 2. Calibrate Cups (Optional, skip if ID is same or user wants to skip)
    # For now, let's assume we want to calibrate both if they are distinct or just demo it.
    # In MVP, user might only have 1 cam connected for testing.
    # Let's ask or just try.
    
    print("\n[STEP 2] Calibrating CUPS Camera")
    try:
        cam_cups = CameraStream(src=config.CAM_CUPS_ID, name="Cups", 
                                width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
        cam_cups.start()
        
        calib_ui_cups = CalibrationUI("Cups Calibration", target_size=(config.WARP_CUPS_SIZE, config.WARP_CUPS_SIZE))
        H_cups, pts_cups = calib_ui_cups.run(cam_cups)
        
        cam_cups.stop()
    except Exception as e:
        print(f"Skipping cups calibration (Error: {e})")
        H_cups = None
        pts_cups = None
        
    if H_cups is None:
        print("Cups calibration skipped or aborted.")

    # 3. Save
    data = {
        "floor_homography": H_floor,
        "floor_points": pts_floor,
    }
    
    if H_cups is not None:
        data["cups_homography"] = H_cups
        data["cups_points"] = pts_cups
        
    save_calibration(data)
    print("\nCalibration Complete.")

if __name__ == "__main__":
    main()
