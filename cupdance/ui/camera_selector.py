import cv2
import numpy as np

class CameraSelector:
    """GUI-based camera selection interface."""
    
    def __init__(self):
        self.cameras = []
        self.selected_floor = None
        self.selected_cups = None
        
    def detect_cameras(self, max_id=10):
        """Detect available cameras."""
        self.cameras = []
        for i in range(max_id):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    self.cameras.append({
                        "id": i,
                        "resolution": f"{w}x{h}",
                        "preview": cv2.resize(frame, (320, 180))
                    })
                cap.release()
        return self.cameras
    
    def run(self):
        """Show camera selection GUI. Returns (floor_cam_id, cups_cam_id)."""
        self.detect_cameras()
        
        if not self.cameras:
            print("[CameraSelector] No cameras detected!")
            return (0, -1)
        
        # Build preview grid
        n_cams = len(self.cameras)
        grid_cols = min(n_cams, 3)
        grid_rows = (n_cams + grid_cols - 1) // grid_cols
        
        cell_w, cell_h = 340, 240
        canvas = np.zeros((grid_rows * cell_h + 100, grid_cols * cell_w, 3), dtype=np.uint8)
        
        # Draw camera previews
        for idx, cam in enumerate(self.cameras):
            row = idx // grid_cols
            col = idx % grid_cols
            x = col * cell_w + 10
            y = row * cell_h + 10
            
            # Draw preview
            canvas[y:y+180, x:x+320] = cam["preview"]
            
            # Draw label
            label = f"[{idx}] Camara {cam['id']} ({cam['resolution']})"
            cv2.putText(canvas, label, (x, y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Instructions
        inst_y = grid_rows * cell_h + 30
        cv2.putText(canvas, "SELECCION DE CAMARAS", (20, inst_y), cv2.FONT_HERSHEY_TRIPLEX, 0.8, (255, 255, 255), 1)
        cv2.putText(canvas, "Presiona el NUMERO de la camara para PISO (0-9)", (20, inst_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 255, 150), 1)
        cv2.putText(canvas, "Luego presiona NUMERO para TAZAS (o ENTER para omitir)", (20, inst_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 255), 1)
        cv2.putText(canvas, "ESC = Cancelar", (20, inst_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        
        cv2.imshow("Seleccion de Camaras", canvas)
        
        # Wait for floor selection
        floor_idx = -1
        while floor_idx < 0:
            key = cv2.waitKey(0) & 0xFF
            if key == 27:  # ESC
                cv2.destroyWindow("Seleccion de Camaras")
                return (0, -1)
            if ord('0') <= key <= ord('9'):
                idx = key - ord('0')
                if idx < len(self.cameras):
                    floor_idx = idx
                    self.selected_floor = self.cameras[idx]["id"]
        
        # Update canvas to show selection
        cv2.putText(canvas, f"PISO: Camara {self.selected_floor} SELECCIONADA", (20, inst_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imshow("Seleccion de Camaras", canvas)
        
        # Wait for cups selection
        cups_idx = -1
        key = cv2.waitKey(0) & 0xFF
        if key == 13:  # ENTER
            self.selected_cups = -1
        elif ord('0') <= key <= ord('9'):
            idx = key - ord('0')
            if idx < len(self.cameras):
                cups_idx = idx
                self.selected_cups = self.cameras[idx]["id"]
        else:
            self.selected_cups = -1
        
        cv2.destroyWindow("Seleccion de Camaras")
        return (self.selected_floor, self.selected_cups if self.selected_cups else -1)


def select_cameras():
    """Convenience function to run camera selection."""
    selector = CameraSelector()
    return selector.run()


if __name__ == "__main__":
    floor, cups = select_cameras()
    print(f"Selected: Floor={floor}, Cups={cups}")
