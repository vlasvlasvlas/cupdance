"""
Display Manager V2 - Interfaz COMPRENSIBLE
==========================================
Todo tiene leyenda, fondo oscuro, explicación.
"""
import cv2
import numpy as np


class DisplayManagerV2:
    def __init__(self):
        self.active_cam = "floor"
        self.floor_brightness = 0
        self.floor_contrast = 1.0
        self.cups_brightness = 0
        self.cups_contrast = 1.0
        self.floor_mode = "pad"
        self.show_debug = False
        self.performance_mode = False
        self.global_mute = False
        self.show_help = True  # Mostrar ayuda por defecto
        
        self.FLOOR_WIN = "PISO"
        self.CUPS_WIN = "TAZAS"
        self.audio_buffer = np.zeros(256)
        self.current_preset = "MOOG"  # Preset de sonido activo
    
    def position_windows(self):
        cv2.namedWindow(self.FLOOR_WIN, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.CUPS_WIN, cv2.WINDOW_NORMAL)
        cv2.moveWindow(self.FLOOR_WIN, 50, 50)
        cv2.moveWindow(self.CUPS_WIN, 700, 50)
    
    def set_mute_state(self, muted):
        self.global_mute = muted
    
    def update_audio_buffer(self, buffer):
        if buffer is not None and len(buffer) > 0:
            step = max(1, len(buffer) // 256)
            self.audio_buffer = np.abs(buffer[::step][:256])
    
    def toggle_performance_mode(self):
        self.performance_mode = not self.performance_mode
        return self.performance_mode
    
    def toggle_help(self):
        self.show_help = not self.show_help
        return self.show_help
    
    def update_controls(self, active_cam, floor_br, floor_co, cups_br, cups_co):
        self.active_cam = active_cam
        self.floor_brightness = floor_br
        self.floor_contrast = floor_co
        self.cups_brightness = cups_br
        self.cups_contrast = cups_co
    
    def set_floor_mode(self, mode):
        self.floor_mode = mode
    
    def _draw_text_with_bg(self, display, text, pos, font_scale=0.6, color=(255,255,255), thickness=1):
        """Dibuja texto con fondo negro para que se lea."""
        x, y = pos
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        cv2.rectangle(display, (x-2, y-th-4), (x+tw+4, y+4), (0, 0, 0), -1)
        cv2.putText(display, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
    
    # =========================================================================
    # PISO
    # =========================================================================
    
    def render_floor(self, frame, floor_points, body_pad, body_kaoss):
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        display = frame.copy()
        h, w = display.shape[:2]
        
        # Grid de zonas
        if floor_points and len(floor_points) == 4:
            pts = np.array(floor_points, np.int32)
            cv2.polylines(display, [pts], True, (0, 255, 255), 2)
            
            if self.floor_mode == "pad":
                self._draw_pad_grid(display, pts, body_pad)
            else:
                self._draw_kaoss_grid(display, pts, body_kaoss)
        
        # Mute
        if self.global_mute:
            self._draw_mute_banner(display)
        
        # UI
        if not self.performance_mode:
            self._draw_floor_header(display, body_pad)
            self._draw_floor_footer(display)
            
            # AYUDA si está activa
            if self.show_help:
                self._draw_floor_help(display, body_pad)
        
        return display
    
    def _draw_floor_help(self, display, body_pad):
        """Panel de ayuda explicando cómo funciona."""
        h, w = display.shape[:2]
        
        # Panel semi-transparente a la derecha
        panel_w = 280
        panel_x = w - panel_w - 10
        panel_y = 60
        panel_h = 200
        
        overlay = display.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        display[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w] = cv2.addWeighted(
            display[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w], 0.3, 
            overlay[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w], 0.7, 0
        )
        cv2.rectangle(display, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 255, 255), 1)
        
        # Título
        cv2.putText(display, "COMO FUNCIONA:", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Explicación
        lines = [
            "1. Detecta MOVIMIENTO en el piso",
            "2. Divide en ZONAS numeradas",
            "3. Zona VERDE = detecta algo",
            "4. Zona GRIS = sin movimiento",
            "",
            f"Modo: {body_pad.num_pads} zonas",
            "Cada zona = nota musical",
            "",
            "H = Ocultar/Mostrar ayuda"
        ]
        
        y = panel_y + 50
        for line in lines:
            cv2.putText(display, line, (panel_x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y += 18
    
    def _draw_mute_banner(self, display):
        h, w = display.shape[:2]
        cv2.rectangle(display, (0, h//2 - 30), (w, h//2 + 30), (0, 0, 150), -1)
        cv2.putText(display, "SILENCIO - Presiona 0 para activar sonido", (w//2 - 250, h//2 + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    def _draw_pad_grid(self, display, zone_pts, body_pad):
        tl, tr, br, bl = zone_pts[0], zone_pts[1], zone_pts[2], zone_pts[3]
        
        def lerp(p1, p2, t):
            return (int(p1[0] + t * (p2[0] - p1[0])), int(p1[1] + t * (p2[1] - p1[1])))
        
        rows, cols = body_pad.rows, body_pad.cols
        
        # Líneas del grid
        for i in range(cols + 1):
            t = i / cols
            cv2.line(display, lerp(tl, tr, t), lerp(bl, br, t), (0, 255, 255), 1)
        for i in range(rows + 1):
            t = i / rows
            cv2.line(display, lerp(tl, bl, t), lerp(tr, br, t), (0, 255, 255), 1)
        
        # Pads con estado CLARO
        for pad_idx in range(body_pad.num_pads):
            row = pad_idx // cols
            col = pad_idx % cols
            
            t_col = (col + 0.5) / cols
            t_row = (row + 0.5) / rows
            top_pt = lerp(tl, tr, t_col)
            bot_pt = lerp(bl, br, t_col)
            center = lerp(top_pt, bot_pt, t_row)
            
            is_active = body_pad.pad_active[pad_idx]
            pressure = body_pad.pad_pressure[pad_idx] if hasattr(body_pad, 'pad_pressure') else 0
            
            # Círculo con color indicando presión
            if is_active:
                # Verde brillante cuando activo
                intensity = int(150 + pressure * 105)
                cv2.circle(display, center, 35, (0, intensity, 0), -1)
                cv2.circle(display, center, 35, (255, 255, 255), 2)
                text_color = (0, 0, 0)
                status = "ON"
            else:
                cv2.circle(display, center, 35, (40, 40, 40), 2)
                text_color = (150, 150, 150)
                status = ""
            
            # Número de zona
            self._draw_text_with_bg(display, str(pad_idx + 1), (center[0] - 10, center[1] + 8), 
                                    0.9, text_color if is_active else (150, 150, 150), 2)
    
    def _draw_kaoss_grid(self, display, zone_pts, body_kaoss):
        tl, tr, br, bl = zone_pts[0], zone_pts[1], zone_pts[2], zone_pts[3]
        
        def lerp(p1, p2, t):
            return (int(p1[0] + t * (p2[0] - p1[0])), int(p1[1] + t * (p2[1] - p1[1])))
        
        # Cruz central
        cv2.line(display, lerp(tl, tr, 0.5), lerp(bl, br, 0.5), (255, 0, 255), 1)
        cv2.line(display, lerp(tl, bl, 0.5), lerp(tr, br, 0.5), (255, 0, 255), 1)
        
        # Etiquetas en los bordes
        self._draw_text_with_bg(display, "OSCURO", lerp(tl, bl, 0.2), 0.5, (255, 100, 255))
        self._draw_text_with_bg(display, "BRILLANTE", lerp(tr, br, 0.2), 0.5, (255, 100, 255))
        self._draw_text_with_bg(display, "CERRADO", lerp(bl, br, 0.9), 0.5, (255, 100, 255))
        self._draw_text_with_bg(display, "ABIERTO", lerp(tl, tr, 0.1), 0.5, (255, 100, 255))
        
        # Posición actual
        if body_kaoss.pressure > 0.01:
            pos_top = lerp(tl, tr, body_kaoss.x)
            pos_bot = lerp(bl, br, body_kaoss.x)
            pos = lerp(pos_top, pos_bot, body_kaoss.y)
            radius = int(20 + body_kaoss.pressure * 30)
            cv2.circle(display, pos, radius, (255, 0, 255), -1)
    
    def _draw_floor_header(self, display, body_pad):
        h, w = display.shape[:2]
        
        # Fondo
        cv2.rectangle(display, (0, 0), (w, 55), (0, 0, 0), -1)
        
        # Modo
        if self.floor_mode == "pad":
            mode = f"PISO: {body_pad.num_pads} ZONAS"
            desc = "Pisa una zona para activar nota"
            color = (100, 255, 100)
        else:
            mode = "PISO: MODO LIBRE"
            desc = "Mueve tu cuerpo para modular"
            color = (255, 100, 255)
        
        cv2.putText(display, mode, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(display, desc, (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        
        # Cámara activa
        if self.active_cam == "floor":
            self._draw_text_with_bg(display, "[ACTIVA] W/S=Brillo A/D=Contraste", (w - 320, 30), 0.5, (0, 255, 0))
        else:
            self._draw_text_with_bg(display, "TAB = Activar", (w - 150, 30), 0.5, (100, 100, 100))
    
    def _draw_floor_footer(self, display):
        h, w = display.shape[:2]
        cv2.rectangle(display, (0, h-30), (w, h), (0, 0, 0), -1)
        cv2.putText(display, "M=Zonas/Libre | P=8/16 | H=Ayuda | ESPACIO=Performance | 0=Mute | Q=Salir",
                   (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    
    # =========================================================================
    # TAZAS
    # =========================================================================
    
    def render_cups(self, frame, cups_points, tangible_proc):
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        display = frame.copy()
        h, w = display.shape[:2]
        
        # Zona calibrada
        if cups_points and len(cups_points) == 4:
            pts = np.array(cups_points, np.int32)
            cv2.polylines(display, [pts], True, (0, 255, 255), 2)
        
        # Perillas con leyenda clara
        self._draw_cups(display, tangible_proc)
        
        # Zonas de dibujo
        self._draw_drawing_zones(display, tangible_proc)
        
        # Mute
        if self.global_mute:
            self._draw_mute_banner(display)
        
        # Debug
        if self.show_debug:
            self._draw_debug_overlay(display, tangible_proc)
        
        # UI
        if not self.performance_mode:
            self._draw_cups_header(display)
            self._draw_cups_footer(display, tangible_proc)
            
            if self.show_help:
                self._draw_cups_help(display)
        
        return display
    
    def _draw_cups_help(self, display):
        """Panel de ayuda para tazas."""
        h, w = display.shape[:2]
        
        panel_w = 250
        panel_x = 10
        panel_y = 60
        panel_h = 180
        
        overlay = display.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        display[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w] = cv2.addWeighted(
            display[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w], 0.3, 
            overlay[panel_y:panel_y+panel_h, panel_x:panel_x+panel_w], 0.7, 0
        )
        cv2.rectangle(display, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (0, 255, 255), 1)
        
        cv2.putText(display, "4 PERILLAS:", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        lines = [
            "A = TONO (grave-agudo)",
            "B = COLOR (oscuro-brillante)", 
            "C = FILTRO (cerrado-abierto)",
            "D = EFECTO (seco-metalico)",
            "",
            "Gira las tazas para cambiar",
            "Verde = detecta taza",
            "Naranja = ultimo valor",
            "",
            "H = Ocultar/Mostrar ayuda"
        ]
        
        y = panel_y + 45
        for line in lines:
            cv2.putText(display, line, (panel_x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
            y += 16
    
    def _draw_cups(self, display, tangible_proc):
        if not tangible_proc.cup_positions:
            return
        
        # Nombres descriptivos
        cup_info = [
            ("A", "TONO", "grave-agudo"),
            ("B", "COLOR", "oscuro-brillo"),
            ("C", "FILTRO", "cerrado-abierto"),
            ("D", "EFECTO", "seco-metalico")
        ]
        
        for i, (cx, cy) in enumerate(tangible_proc.cup_positions):
            label, name, desc = cup_info[i]
            radius = tangible_proc.cup_radius
            value = tangible_proc.cup_values[i]
            detected = tangible_proc.cup_detected[i]
            
            # Color: verde = detectando, naranja = usando último valor
            if detected:
                color = (0, 200, 0)
                status = "OK"
            else:
                color = (0, 100, 200)
                status = "HOLD"
            
            # Círculo exterior
            cv2.circle(display, (cx, cy), radius, color, 3)
            
            # Arco de valor (como un dial)
            angle = int(value * 270) - 135
            cv2.ellipse(display, (cx, cy), (radius - 6, radius - 6),
                       0, -135, angle, (0, 255, 100), 5)
            
            # Marcador rojo si detecta
            if detected and tangible_proc.cup_marker_pos[i]:
                mx, my = tangible_proc.cup_marker_pos[i]
                cv2.circle(display, (mx, my), 6, (0, 0, 255), -1)
            
            # Etiqueta con fondo - ahora más descriptiva
            self._draw_text_with_bg(display, f"{label}: {name}", (cx - 50, cy - radius - 25), 0.5, (255, 255, 0))
            self._draw_text_with_bg(display, f"{value:.0%}", (cx - 20, cy + 8), 0.6, (255, 255, 255), 2)
            self._draw_text_with_bg(display, status, (cx - 20, cy + radius + 20), 0.4, color)
    
    def _draw_drawing_zones(self, display, tangible_proc):
        if tangible_proc.adsr_zone:
            ax, ay, aw, ah = tangible_proc.adsr_zone
            cv2.rectangle(display, (ax, ay), (ax + aw, ay + ah), (100, 255, 100), 2)
            self._draw_text_with_bg(display, "FORMA DEL SONIDO", (ax + 5, ay + 20), 0.45, (100, 255, 100))
            self._draw_text_with_bg(display, "Dibuja curva aqui", (ax + 5, ay + ah - 10), 0.35, (150, 255, 150))
            
            if tangible_proc.frozen_adsr is not None:
                curve = tangible_proc.frozen_adsr
                if np.max(curve) > 0.05:
                    for j in range(len(curve) - 1):
                        x1 = ax + int((j / len(curve)) * aw)
                        x2 = ax + int(((j + 1) / len(curve)) * aw)
                        y1 = ay + ah - int(curve[j] * (ah - 30))
                        y2 = ay + ah - int(curve[j + 1] * (ah - 30))
                        cv2.line(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        if tangible_proc.wave_zone:
            wx, wy, ww, wh = tangible_proc.wave_zone
            cv2.rectangle(display, (wx, wy), (wx + ww, wy + wh), (100, 100, 255), 2)
            self._draw_text_with_bg(display, "ONDA SONORA", (wx + 5, wy + 20), 0.45, (100, 100, 255))
            self._draw_text_with_bg(display, "Dibuja forma aqui", (wx + 5, wy + wh - 10), 0.35, (150, 150, 255))
            
            cv2.line(display, (wx, wy + wh//2), (wx + ww, wy + wh//2), (60, 60, 100), 1)
            
            if tangible_proc.frozen_wave is not None:
                curve = tangible_proc.frozen_wave
                if np.max(curve) > 0.05:
                    for j in range(len(curve) - 1):
                        x1 = wx + int((j / len(curve)) * ww)
                        x2 = wx + int(((j + 1) / len(curve)) * ww)
                        y1 = wy + wh - int(curve[j] * (wh - 30))
                        y2 = wy + wh - int(curve[j + 1] * (wh - 30))
                        cv2.line(display, (x1, y1), (x2, y2), (100, 100, 255), 2)
            
            # Osciloscopio
            osc_y = wy + wh + 5
            osc_h = 40
            if osc_y + osc_h < display.shape[0] - 50:
                cv2.rectangle(display, (wx, osc_y), (wx + ww, osc_y + osc_h), (0, 150, 150), 1)
                self._draw_text_with_bg(display, "AUDIO EN VIVO", (wx + 5, osc_y + 14), 0.35, (0, 200, 200))
                if len(self.audio_buffer) > 0:
                    max_val = max(np.max(self.audio_buffer), 0.01)
                    for j in range(0, len(self.audio_buffer) - 1, 2):
                        x1 = wx + int((j / len(self.audio_buffer)) * ww)
                        x2 = wx + int(((j + 1) / len(self.audio_buffer)) * ww)
                        y1 = osc_y + osc_h//2 - int((self.audio_buffer[j] / max_val) * (osc_h//2 - 3))
                        y2 = osc_y + osc_h//2 - int((self.audio_buffer[j+1] / max_val) * (osc_h//2 - 3))
                        cv2.line(display, (x1, y1), (x2, y2), (0, 255, 255), 1)
    
    def _draw_cups_header(self, display):
        h, w = display.shape[:2]
        cv2.rectangle(display, (0, 0), (w, 55), (0, 0, 0), -1)
        
        # Preset de sonido activo (prominente)
        preset_colors = {
            "MOOG": (100, 200, 255),    # Naranja
            "8BIT": (100, 255, 100),    # Verde
            "PAD": (255, 150, 100),     # Azul
            "PLUCK": (100, 100, 255),   # Rojo
            "BELL": (255, 200, 100),    # Cyan
            "LIBRE": (255, 100, 255)    # Magenta
        }
        color = preset_colors.get(self.current_preset, (255, 255, 255))
        
        cv2.putText(display, f"SONIDO: {self.current_preset}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(display, "<-/-> Cambiar preset", (10, 48),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        if self.active_cam == "cups":
            self._draw_text_with_bg(display, "[ACTIVA] W/S=Brillo", (w - 200, 30), 0.5, (0, 255, 0))
        else:
            self._draw_text_with_bg(display, "TAB = Activar", (w - 150, 30), 0.5, (100, 100, 100))
    
    def _draw_cups_footer(self, display, tangible_proc):
        h, w = display.shape[:2]
        cv2.rectangle(display, (0, h-30), (w, h), (0, 0, 0), -1)
        
        vals = tangible_proc.cup_values
        cv2.putText(display, f"TONO:{vals[0]:.0%} COLOR:{vals[1]:.0%} FILTRO:{vals[2]:.0%} EFECTO:{vals[3]:.0%}",
                   (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)
        
        cv2.putText(display, "F/G=Congelar | H=Ayuda | V=Debug | Q=Salir",
                   (w - 350, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    def _draw_debug_overlay(self, display, tangible_proc):
        h, w = display.shape[:2]
        
        cv2.rectangle(display, (w - 200, 60), (w - 10, 200), (0, 0, 0), -1)
        cv2.rectangle(display, (w - 200, 60), (w - 10, 200), (0, 255, 255), 1)
        cv2.putText(display, "DEBUG", (w - 190, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        y = 100
        for i in range(4):
            label = ["A", "B", "C", "D"][i]
            detected = tangible_proc.cup_detected[i]
            value = tangible_proc.cup_values[i]
            color = (0, 255, 0) if detected else (0, 0, 255)
            cv2.putText(display, f"{label}: {'DETECTA' if detected else 'NO VE'} ({value:.0%})",
                       (w - 190, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            y += 22
        
        # Estado ADSR/Wave
        adsr_ok = tangible_proc.frozen_adsr is not None and np.max(tangible_proc.frozen_adsr) > 0.05
        wave_ok = tangible_proc.frozen_wave is not None and np.max(tangible_proc.frozen_wave) > 0.05
        cv2.putText(display, f"FORMA: {'OK' if adsr_ok else 'vacia'}", (w - 190, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0) if adsr_ok else (100, 100, 100), 1)
        cv2.putText(display, f"ONDA: {'OK' if wave_ok else 'vacia'}", (w - 190, y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0) if wave_ok else (100, 100, 100), 1)
