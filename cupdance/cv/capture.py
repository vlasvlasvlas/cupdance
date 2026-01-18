import cv2
from threading import Thread
import time

class CameraStream:
    """
    Threaded camera capture to ensure the main loop is never blocked by I/O.
    Always returns the most recent complete frame.
    """
    def __init__(self, src=0, name="Camera", width=1280, height=720, fps=30):
        self.src = src
        self.name = name
        
        # Initialize the video stream
        self.stream = cv2.VideoCapture(src)
        
        # Configure camera (attempts to set these values)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.stream.set(cv2.CAP_PROP_FPS, fps)
        
        # Read the first frame to ensure connection
        (self.grabbed, self.frame) = self.stream.read()
        
        # Thread control
        self.stopped = False
        self.thread = None

        if not self.grabbed:
            print(f"[{self.name}] CRITICAL: Could not open camera source {src}")
        else:
            print(f"[{self.name}] Initialized. Resolution: {self.stream.get(3)}x{self.stream.get(4)} @ {self.stream.get(5)}FPS")

    def start(self):
        """Starts the thread to read frames from the video stream."""
        if self.stopped:
            return self

        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True # Daemonize thread
        self.thread.start()
        return self

    def update(self):
        """Loop meant to be run in a separate thread."""
        while True:
            if self.stopped:
                self.stream.release()
                return

            # Read the next frame from the stream
            (grabbed, frame) = self.stream.read()
            
            # If we can't grab a frame, we might have lost connection
            if not grabbed:
                # In a robust system, we might try to reconnect here
                self.stopped = True
                continue
            
            # Update the shared frame buffer
            self.frame = frame

    def read(self):
        """Returns the most recent frame processed."""
        return self.frame

    def stop(self):
        """Indicates that the thread should be stopped."""
        self.stopped = True
        if self.thread is not None:
            self.thread.join()
