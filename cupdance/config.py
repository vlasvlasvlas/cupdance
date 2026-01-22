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

# --- Cups Instrument Config ---
NOTCH_COUNT = 8      # Musical steps (modes/scales)
SNAP_EPS = 0.03      # Proximity to snap
SMOOTH_ALPHA = 0.20  # EMA Smoothing factor (Lower = floatier, Higher = snappier)
LATCH_TIMEOUT = 1.0  # Seconds to wait before resetting/fading if cup is lost (optional)

# --- Keybinds ---
KEY_QUIT = 'q'
KEY_SAVE_CALIB = 's'

# --- Audio Output (OSC) ---
OSC_IP = "127.0.0.1"
OSC_PORT = 8000
