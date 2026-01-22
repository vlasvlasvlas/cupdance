import cv2
import numpy as np

class FloorProcessor:
    """
    Separación FIGURA-FONDO simple.
    Usa threshold para detectar la figura (persona) sobre el fondo.
    El usuario ajusta brillo/contraste de cámara para optimizar.
    """
    def __init__(self, size=(800, 800), grid_size=16):
        self.size = size
        self.grid_size = grid_size
        self.smooth_grid = np.zeros((grid_size, grid_size), dtype=np.float32)
        
        # Threshold - ajustable con teclas + / -
        self.threshold = 127  # Punto medio
        self.invert = False   # Si True, detecta claro sobre oscuro
        
        # Centro de masa para Kaoss
        self.center_x = 0.5
        self.center_y = 0.5
        self.total_coverage = 0.0
        
    def process(self, frame_warped):
        """
        Detecta FIGURA sobre FONDO usando threshold simple.
        Retorna máscara binaria de donde hay figura.
        """
        gray = cv2.cvtColor(frame_warped, cv2.COLOR_BGR2GRAY)
        
        # Blur suave para reducir ruido
        gray = cv2.GaussianBlur(gray, (15, 15), 0)
        
        # Threshold binario - separa oscuro de claro
        if self.invert:
            # Figura clara sobre fondo oscuro
            _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        else:
            # Figura oscura sobre fondo claro (más común)
            _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY_INV)
        
        # Limpiar ruido
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, None, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, None, iterations=3)
        
        # Calcular centro de masa de la figura
        h, w = mask.shape
        mask_norm = mask.astype(np.float32) / 255.0
        self.total_coverage = np.mean(mask_norm)
        
        if self.total_coverage > 0.01:
            # Encontrar centro de masa
            indices = np.where(mask > 127)
            if len(indices[0]) > 0:
                self.center_y = np.mean(indices[0]) / h
                self.center_x = np.mean(indices[1]) / w
        
        # Downscale a grid para zonas
        grid_raw = cv2.resize(mask, (self.grid_size, self.grid_size), interpolation=cv2.INTER_AREA)
        grid_norm = grid_raw.astype(np.float32) / 255.0
        
        # Suavizado temporal
        self.smooth_grid = self.smooth_grid * 0.6 + grid_norm * 0.4
        
        # Datos por cuadrante
        mid = self.grid_size // 2
        quad_data = {
            "q1_density": np.mean(self.smooth_grid[0:mid, 0:mid]),
            "q2_density": np.mean(self.smooth_grid[0:mid, mid:]),
            "q3_density": np.mean(self.smooth_grid[mid:, 0:mid]),
            "q4_density": np.mean(self.smooth_grid[mid:, mid:]),
            "center_x": self.center_x,
            "center_y": self.center_y,
            "coverage": self.total_coverage
        }
        
        return self.smooth_grid, quad_data, mask
    
    def set_threshold(self, value):
        """Ajustar umbral de separación figura-fondo (0-255)."""
        self.threshold = max(0, min(255, value))
    
    def toggle_invert(self):
        """Invertir detección (claro vs oscuro)."""
        self.invert = not self.invert
        return self.invert
