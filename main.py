import cv2
import time
import sys
import os

# Ensure we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cupdance import config
from cupdance.cv.capture import CameraStream

def main():
    print("--- CUPDANCE MVP STARTING ---")
    
    # 1. Initialize Cameras
    # Note: If you only have 1 cam connected, set correct IDs in config.py
    cam_floor = CameraStream(src=config.CAM_FLOOR_ID, name="Floor", 
                             width=config.CAM_WIDTH, height=config.CAM_HEIGHT, fps=config.CAM_FPS)
    time.sleep(1.0) # Warmup needed for some USB cams

    # (Optional) Second camera
    # cam_cups = CameraStream(src=config.CAM_CUPS_ID, name="Cups", ...)
    # cam_cups.start()

    cam_floor.start()

    print("--- STREAMS RUNNING. Press 'q' to quit. ---")

    prev_time = time.time()
    
    try:
        while True:
            # 2. Read Frames (Non-blocking)
            frame_floor = cam_floor.read()
            
            if frame_floor is None:
                print("Error: No frame from floor camera.")
                break

            # 3. Process (Placeholder)
            # ...
            
            # 4. Display
            # Resize for screen fit if needed
            display_frame = cv2.resize(frame_floor, (640, 360))
            cv2.imshow("Floor Feed (Raw)", display_frame)

            # FPS calc
            curr_time = time.time()
            dt = curr_time - prev_time
            prev_time = curr_time
            # print(f"FPS: {1/dt:.1f}")

            key = cv2.waitKey(1) & 0xFF
            if key == ord(config.KEY_QUIT):
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("--- STOPPING ---")
        cam_floor.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
