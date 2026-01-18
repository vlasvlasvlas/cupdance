import cv2

# --- Camera Settings ---
# Cam indices (Checking 0 and 1, usually built-in and external)
CAM_FLOOR_ID = 0 
CAM_CUPS_ID = 1

# Resolution (720p is a good balance for performance/quality)
CAM_WIDTH = 1280
CAM_HEIGHT = 720
CAM_FPS = 60  # Try to request 60fps

# --- Processing & Warp ---
# Normalized views dimensions
WARP_FLOOR_SIZE = 800
WARP_CUPS_SIZE = 600

# --- Keybinds ---
KEY_QUIT = 'q'
KEY_SAVE_CALIB = 's'
