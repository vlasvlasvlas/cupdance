import cv2
import numpy as np
import json
import os

class SetupWizard:
    """
    GUI Wizard for initial setup:
    1. Camera selection with previews
    2. Floor zone definition (4-point click)
    3. Cups zone definition (with preview of regions)
    """
    
    def __init__(self, config_path="cupdance/calibration.json"):
        self.config_path = config_path
        self.cameras = []
        self.floor_cam_id = None
        self.cups_cam_id = None
        self.floor_points = None
        self.cups_points = None
        
        # UI State
        self.current_step = 1
        self.click_points = []
        
    def detect_cameras(self, max_id=5):
        """Detect available cameras with previews."""
        self.cameras = []
        print("[Wizard] Detectando camaras...")
        for i in range(max_id):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    print(f"  Camara {i}: {w}x{h} - OK")
                    self.cameras.append({
                        "id": i,
                        "resolution": f"{w}x{h}",
                        "preview": cv2.resize(frame, (320, 180)),
                        "cap": cap  # Keep open for live preview
                    })
                else:
                    cap.release()
        print(f"[Wizard] {len(self.cameras)} camaras encontradas")
        return len(self.cameras)
    
    def run_step1_cameras(self):
        """Step 1: Select cameras with live previews."""
        if not self.cameras:
            self.detect_cameras()
        
        if not self.cameras:
            print("[Wizard] No cameras found!")
            return False
        
        window_name = "PASO 1: Seleccion de Camaras"
        cv2.namedWindow(window_name)
        
        selected = {"floor": None, "cups": None}
        
        def on_click(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                # Determine which camera was clicked
                for idx, cam in enumerate(self.cameras):
                    col = idx % 3
                    row = idx // 3
                    cx = col * 340 + 10
                    cy = row * 220 + 10
                    if cx <= x <= cx + 320 and cy <= y <= cy + 180:
                        if selected["floor"] is None:
                            selected["floor"] = cam["id"]
                        elif selected["cups"] is None and cam["id"] != selected["floor"]:
                            selected["cups"] = cam["id"]
        
        cv2.setMouseCallback(window_name, on_click)
        
        while True:
            # Build canvas
            n_cams = len(self.cameras)
            cols = min(n_cams, 3)
            rows = (n_cams + cols - 1) // cols
            canvas = np.zeros((rows * 220 + 150, cols * 340 + 20, 3), dtype=np.uint8)
            
            # Update previews and draw
            for idx, cam in enumerate(self.cameras):
                ret, frame = cam["cap"].read()
                if ret:
                    cam["preview"] = cv2.resize(frame, (320, 180))
                
                col = idx % 3
                row = idx // 3
                x = col * 340 + 10
                y = row * 220 + 10
                
                canvas[y:y+180, x:x+320] = cam["preview"]
                
                # Border based on selection
                border_color = (80, 80, 80)
                if selected["floor"] == cam["id"]:
                    border_color = (0, 255, 0)  # Green for floor
                    cv2.putText(canvas, "PISO", (x + 130, y + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                elif selected["cups"] == cam["id"]:
                    border_color = (255, 100, 0)  # Blue for cups
                    cv2.putText(canvas, "TAZAS", (x + 120, y + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)
                
                cv2.rectangle(canvas, (x-2, y-2), (x+322, y+182), border_color, 2)
                
                # Label
                label = f"Camara {cam['id']} ({cam['resolution']})"
                cv2.putText(canvas, label, (x, y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Instructions
            inst_y = rows * 220 + 30
            cv2.putText(canvas, "PASO 1: SELECCION DE CAMARAS (2 clicks)", (20, inst_y), cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 255, 255), 1)
            
            if selected["floor"] is None:
                cv2.putText(canvas, "1. Click en la camara para el PISO (verde)", (20, inst_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
                cv2.putText(canvas, "   Luego click en otra camara para TAZAS", (20, inst_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            elif selected["cups"] is None:
                cv2.putText(canvas, f"PISO: Camara {selected['floor']} OK", (20, inst_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
                cv2.putText(canvas, "2. AHORA click en otra camara para TAZAS (azul)", (20, inst_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
                cv2.putText(canvas, "   (o ENTER si no usas camara de tazas)", (20, inst_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
            else:
                cv2.putText(canvas, f"PISO: Cam {selected['floor']} | TAZAS: Cam {selected['cups']}", (20, inst_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
                cv2.putText(canvas, ">> Presiona ENTER para continuar", (20, inst_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 100), 1)
            
            cv2.putText(canvas, "ESC = Cancelar", (20, inst_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                self.cleanup_cameras()
                cv2.destroyWindow(window_name)
                return False
            
            if key == 13 and selected["floor"] is not None:  # ENTER
                self.floor_cam_id = selected["floor"]
                # Important: selected["cups"] can be 0 (valid cam), so check for None explicitly
                self.cups_cam_id = selected["cups"] if selected["cups"] is not None else -1
                print(f"[Wizard] Step 1 complete: floor={self.floor_cam_id}, cups={self.cups_cam_id}")
                cv2.destroyWindow(window_name)
                return True
        
    def run_step2_floor_zone(self):
        """Step 2: Define floor zone with 4 clicks."""
        if self.floor_cam_id is None:
            return False
        
        # Find the floor camera
        floor_cap = None
        for cam in self.cameras:
            if cam["id"] == self.floor_cam_id:
                floor_cap = cam["cap"]
                break
        
        if floor_cap is None:
            floor_cap = cv2.VideoCapture(self.floor_cam_id)
        
        window_name = "PASO 2: Zona del Piso (Click 4 esquinas)"
        cv2.namedWindow(window_name)
        
        points = []
        
        def on_click(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
                points.append((x, y))
        
        cv2.setMouseCallback(window_name, on_click)
        
        while True:
            ret, frame = floor_cap.read()
            if not ret:
                continue
            
            canvas = frame.copy()
            
            # Draw existing points
            for i, pt in enumerate(points):
                cv2.circle(canvas, pt, 8, (0, 255, 0), -1)
                cv2.putText(canvas, str(i+1), (pt[0]+10, pt[1]+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Draw lines between points
            if len(points) >= 2:
                for i in range(len(points) - 1):
                    cv2.line(canvas, points[i], points[i+1], (0, 255, 0), 2)
                if len(points) == 4:
                    cv2.line(canvas, points[3], points[0], (0, 255, 0), 2)
            
            # Instructions
            h = canvas.shape[0]
            cv2.rectangle(canvas, (0, h-80), (canvas.shape[1], h), (0, 0, 0), -1)
            cv2.putText(canvas, "PASO 2: DEFINIR ZONA DEL PISO", (20, h-55), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (255, 255, 255), 1)
            
            if len(points) < 4:
                cv2.putText(canvas, f"Click en esquina {len(points)+1} de 4 (sentido horario)", (20, h-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            else:
                cv2.putText(canvas, "ENTER = Continuar | R = Reiniciar puntos | B = Capturar fondo", (20, h-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                cv2.destroyWindow(window_name)
                return False
            
            if key == ord('r'):  # Reset
                points.clear()
            
            if key == 13 and len(points) == 4:  # ENTER
                self.floor_points = points
                cv2.destroyWindow(window_name)
                return True
    
    def cleanup_cameras(self):
        """Release all camera captures."""
        for cam in self.cameras:
            if "cap" in cam:
                cam["cap"].release()
    
    def save_config(self):
        """Save configuration to JSON."""
        # Compute floor homography
        H_floor = None
        if self.floor_points:
            src = np.float32(self.floor_points)
            dst = np.float32([[0, 0], [512, 0], [512, 512], [0, 512]])
            H_floor = cv2.getPerspectiveTransform(src, dst)
        
        # Compute cups homography
        H_cups = None
        if self.cups_points:
            src = np.float32(self.cups_points)
            dst = np.float32([[0, 0], [256, 0], [256, 256], [0, 256]])
            H_cups = cv2.getPerspectiveTransform(src, dst)
        
        config = {
            "floor_cam_id": self.floor_cam_id,
            "cups_cam_id": self.cups_cam_id,
            "floor_points": self.floor_points,
            "floor_homography": H_floor.tolist() if H_floor is not None else None,
            "cups_points": self.cups_points,
            "cups_homography": H_cups.tolist() if H_cups is not None else None
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def run(self):
        """Run the complete setup wizard."""
        print("[Wizard] Starting setup wizard...")
        
        if not self.run_step1_cameras():
            print("[Wizard] Cancelled at step 1")
            self.cleanup_cameras()
            return None
        
        if not self.run_step2_floor_zone():
            print("[Wizard] Cancelled at step 2")
            self.cleanup_cameras()
            return None
        
        # Debug: show what cups_cam_id is
        print(f"[Wizard] After step 2: floor_cam={self.floor_cam_id}, cups_cam={self.cups_cam_id}")
        
        # Step 3: Cups zone (if cups camera selected)
        if self.cups_cam_id is not None and self.cups_cam_id >= 0:
            print(f"[Wizard] Running step 3 for cups camera {self.cups_cam_id}...")
            if not self.run_step3_cups_zone():
                print("[Wizard] Cancelled at step 3")
                self.cleanup_cameras()
                return None
        else:
            print(f"[Wizard] Skipping step 3 (no cups camera selected)")
        
        self.cleanup_cameras()
        config = self.save_config()
        print(f"[Wizard] Configuration saved!")
        return config
    
    def run_step3_cups_zone(self):
        """Step 3: Define cups zone with 4 clicks."""
        print(f"[Wizard] Step 3: Cups camera ID = {self.cups_cam_id}")
        
        # Find the cups camera
        cups_cap = None
        for cam in self.cameras:
            if cam["id"] == self.cups_cam_id:
                cups_cap = cam["cap"]
                print(f"[Wizard] Found cups camera in cache")
                break
        
        if cups_cap is None or not cups_cap.isOpened():
            print(f"[Wizard] Opening cups camera fresh...")
            cups_cap = cv2.VideoCapture(self.cups_cam_id)
            if not cups_cap.isOpened():
                print(f"[Wizard] ERROR: Could not open cups camera {self.cups_cam_id}")
                return False
        
        window_name = "PASO 3: Zona de Tazas (Click 4 esquinas)"
        cv2.namedWindow(window_name)
        
        points = []
        
        def on_click(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
                points.append((x, y))
        
        cv2.setMouseCallback(window_name, on_click)
        
        while True:
            ret, frame = cups_cap.read()
            if not ret:
                continue
            
            canvas = frame.copy()
            
            # Draw existing points
            for i, pt in enumerate(points):
                cv2.circle(canvas, pt, 8, (0, 200, 255), -1)
                cv2.putText(canvas, str(i+1), (pt[0]+10, pt[1]+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            
            # Draw lines between points
            if len(points) >= 2:
                for i in range(len(points) - 1):
                    cv2.line(canvas, points[i], points[i+1], (0, 200, 255), 2)
                if len(points) == 4:
                    cv2.line(canvas, points[3], points[0], (0, 200, 255), 2)
            
            # Instructions
            h = canvas.shape[0]
            cv2.rectangle(canvas, (0, h-80), (canvas.shape[1], h), (0, 0, 0), -1)
            cv2.putText(canvas, "PASO 3: DEFINIR ZONA DE TAZAS", (20, h-55), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (255, 255, 255), 1)
            
            if len(points) < 4:
                cv2.putText(canvas, f"Click en esquina {len(points)+1} de 4 (sentido horario)", (20, h-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
            else:
                cv2.putText(canvas, "ENTER = Continuar | R = Reiniciar puntos", (20, h-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                cv2.destroyWindow(window_name)
                return False
            
            if key == ord('r'):  # Reset
                points.clear()
            
            if key == 13 and len(points) == 4:  # ENTER
                self.cups_points = points
                cv2.destroyWindow(window_name)
                return True


if __name__ == "__main__":
    run_setup()
