import cv2
import time
import sys
import os
import numpy as np

# Ensure we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cupdance import config
from cupdance.cv.capture import CameraStream
from cupdance.ui.calibration import load_calibration, CalibrationUI, save_calibration
from cupdance.ui.camera_selector import select_cameras
from cupdance.cv.floor import FloorProcessor
from cupdance.cv.cups import CupsProcessor
from cupdance.cv.memory import MemoryEngine
from cupdance.cv.match import MatchEngine
from cupdance.ui.overlay import VisualRenderer
# from cupdance.io.osc_sender import OSCSender # Replaced by Internal Engine
from cupdance.audio.engine import AudioEngine
from cupdance.audio.synths.chip import ChipSynth
from cupdance.audio.synths.moog import MoogSynth
from cupdance.audio.synths.retro import RetroSynth
from cupdance.audio.synths.exotic import ExoticSynth
from cupdance.audio.synths.custom_draw import CustomDrawSynth
from cupdance.cv.tangible import TangibleSynthProcessor
from cupdance.cv.body_pad import BodyPad, BodyKaoss
from cupdance.ui.setup_wizard import SetupWizard
from cupdance.ui.display_manager_v2 import DisplayManagerV2
from cupdance.audio.sound_presets import get_preset, get_next_preset, get_prev_preset, PRESET_ORDER

def main():
    print("--- CUPDANCE SOTA INSTRUMENT v2.0 ---")
    
    # 1. Load existing Calibration
    calib_data = load_calibration()
    H_floor = calib_data.get("floor_homography")
    H_cups = calib_data.get("cups_homography")
    floor_cam_id = calib_data.get("floor_cam_id", 0)
    cups_cam_id = calib_data.get("cups_cam_id", -1)
    
    # 2. Startup Dialog - Ask if want to recalibrate
    def show_startup_dialog():
        """Shows a startup dialog asking if user wants to recalibrate."""
        dialog = np.zeros((300, 500, 3), dtype=np.uint8)
        
        cv2.putText(dialog, "CUPDANCE", (150, 50), cv2.FONT_HERSHEY_TRIPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(dialog, "Configuracion de inicio:", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        if H_floor is not None:
            cv2.putText(dialog, "[ENTER] Usar configuracion guardada", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            cv2.putText(dialog, f"        (Cam Piso: {floor_cam_id}, Cam Tazas: {cups_cam_id})", (50, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        else:
            cv2.putText(dialog, "(No hay configuracion guardada)", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 100, 100), 1)
        
        cv2.putText(dialog, "[R] Recalibrar camaras y zonas", (50, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)
        cv2.putText(dialog, "[ESC] Cancelar y salir", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        cv2.imshow("Inicio", dialog)
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == 13:  # ENTER
                cv2.destroyWindow("Inicio")
                return "use_existing" if H_floor is not None else "recalibrate"
            if key == ord('r'):
                cv2.destroyWindow("Inicio")
                return "recalibrate"
            if key == 27:  # ESC
                cv2.destroyWindow("Inicio")
                return "cancel"
    
    startup_choice = show_startup_dialog()
    
    if startup_choice == "cancel":
        print("[Main] Cancelled. Exiting.")
        return
    
    if startup_choice == "recalibrate" or H_floor is None:
        print("[Main] Running Setup Wizard...")
        wizard = SetupWizard()
        wizard_result = wizard.run()
        if wizard_result is None:
            print("[Main] Setup cancelled. Exiting.")
            return
        
        calib_data = load_calibration()  # Reload
        H_floor = calib_data.get("floor_homography")
        H_cups = calib_data.get("cups_homography")
        cups_points = calib_data.get("cups_points")
        floor_cam_id = calib_data.get("floor_cam_id", 0)
        cups_cam_id = calib_data.get("cups_cam_id", -1)
    
    # Get calibrated points for processing
    cups_points = calib_data.get("cups_points")
    floor_points = calib_data.get("floor_points")
    
    if H_floor is not None:
        H_floor = np.array(H_floor)
        print(f"[Main] H_floor loaded: {H_floor.shape}")
    else:
        print("[Main] WARNING: H_floor is None!")
        
    if H_cups is not None:
        H_cups = np.array(H_cups)
        print(f"[Main] H_cups loaded: {H_cups.shape}")
    
    # Start Floor Cam
    print(f"[Main] Starting Floor Camera (ID: {floor_cam_id})...")
    cam_floor = CameraStream(src=floor_cam_id, name="Floor", 
                             width=config.CAM_WIDTH, height=config.CAM_HEIGHT, fps=config.CAM_FPS)
    cam_floor.start()
    
    # Start Cups Cam (Optional)
    cam_cups = None
    if cups_cam_id >= 0:  # Start even without H_cups - we want to see the raw feed
        print(f"[Main] Starting Cups Camera (ID: {cups_cam_id})...")
        try:
            cam_cups = CameraStream(src=cups_cam_id, name="Cups", 
                                    width=config.CAM_WIDTH, height=config.CAM_HEIGHT, fps=config.CAM_FPS)
            cam_cups.start()
        except Exception as e:
            print(f"[Main] Failed to open Cups camera: {e}")

    time.sleep(1.0) # Warmup

    # 3. Init Processors
    floor_proc = FloorProcessor(size=(config.WARP_FLOOR_SIZE, config.WARP_FLOOR_SIZE))
    cups_proc = CupsProcessor(size=(config.WARP_CUPS_SIZE, config.WARP_CUPS_SIZE))
    memory_eng = MemoryEngine()
    match_eng = MatchEngine(match_eps=config.SNAP_EPS, hold_ms=400, cooldown_ms=3000)
    renderer = VisualRenderer(width=1000, height=1000)
    tangible_proc = TangibleSynthProcessor(frame_size=(config.CAM_WIDTH, config.CAM_HEIGHT))
    
    # Configure tangible processor with calibrated zone
    if cups_points:
        tangible_proc.set_zone(cups_points)
        print(f"[Main] Tangible processor configured with cups_points")
    else:
        print(f"[Main] WARNING: No cups_points - tangible zones will not be positioned correctly")
    
    # --- BODY PAD (Octapad for body) ---
    body_pad = BodyPad(grid_size=config.WARP_FLOOR_SIZE, mode="2x4")  # 8 pads like Octapad
    body_kaoss = BodyKaoss(grid_size=config.WARP_FLOOR_SIZE)  # XY effects surface
    body_pad_mode = "pad"  # "pad" or "kaoss" - toggle with 'M' key
    
    # --- DISPLAY MANAGER ---
    display_mgr = DisplayManagerV2()
    display_mgr.position_windows()  # Posicionar ventanas lado a lado
    
    # --- INTERNAL AUDIO ENGINE ---
    audio_sys = AudioEngine()
    
    # Load default synths (Bank 1: Mixed)
    s1 = ChipSynth() # Cups A/B
    s2 = MoogSynth() # Cup C
    s3 = ExoticSynth() # Cup D
    s4 = CustomDrawSynth() # Tangible Drawn Synth (replaces RetroSynth)
    
    audio_sys.set_synth(0, s1)
    audio_sys.set_synth(1, s2)
    audio_sys.set_synth(2, s3)
    audio_sys.set_synth(3, s4)
    
    audio_sys.start() # START AUDIO
    
    # --- Camera Controls State ---
    # [Brightness, Contrast] for Floor (0) and Cups (1)
    # Default: Brightness=0 (beta), Contrast=1.0 (alpha)
    cam_controls = {
        "floor": {"br": 0, "co": 1.0},
        "cups":  {"br": 0, "co": 1.0}
    }
    active_cam_control = "floor" # Which one we are editing
    
    # Tangible synthesis freeze state
    freeze_adsr = False
    freeze_wave = False
    
    # Sound preset
    current_preset = "MOOG"  # Preset inicial

    print("\n" + "="*60)
    print("   CUPDANCE LISTO - CONTROLES:")
    print("="*60)
    print("  TAB     = Cambiar camara activa (PISO/TAZAS)")
    print("  W / S   = Subir/Bajar BRILLO de camara activa")
    print("  A / D   = Subir/Bajar CONTRASTE de camara activa")
    print("  <- / -> = Cambiar PRESET de sonido (MOOG, 8BIT, PAD...)")
    print("  ESPACIO = Modo PERFORMANCE (oculta toda la UI)")
    print("  V       = Modo DEBUG (ver que detecta)")
    print("  M       = Cambiar modo PISO (Zonas/Libre)")
    print("  P       = Cambiar pads (8 o 16)")
    print("  F / G   = Congelar curva ADSR / Wave")
    print("  0       = MUTE todo el sonido")
    print("  R       = Recalibrar camaras")
    print("  Q       = Salir")
    print("="*60 + "\n")
    
    prev_time = time.time()

    try:
        while True:
            # --- Read Frames ---
            frame_floor = cam_floor.read()
            frame_cups = cam_cups.read() if cam_cups else None
            
            if frame_floor is None:
                continue

            # --- Apply Camera Adjustments ---
            # Floor
            ctrl_f = cam_controls["floor"]
            frame_floor = cv2.convertScaleAbs(frame_floor, alpha=ctrl_f["co"], beta=ctrl_f["br"])
            
            # Cups
            if frame_cups is not None:
                ctrl_c = cam_controls["cups"]
                frame_cups = cv2.convertScaleAbs(frame_cups, alpha=ctrl_c["co"], beta=ctrl_c["br"])

            # --- Warp & Process Floor ---
            if H_floor is not None:
                floor_warp = cv2.warpPerspective(frame_floor, H_floor, (config.WARP_FLOOR_SIZE, config.WARP_FLOOR_SIZE))
                
                # Process floor detection
                grid, features, debug_floor = floor_proc.process(floor_warp)
                
                # --- BODY PAD / KAOSS Processing ---
                body_pad_events = []
                if body_pad_mode == "pad":
                    body_pad_events = body_pad.process(debug_floor)
                    
                    # Handle pad events (triggers notes)
                    for event in body_pad_events:
                        if event["type"] == "trigger":
                            pad_idx = event["pad"]
                            note = event["note"]
                            velocity = event["velocity"]
                            print(f"[BodyPad] PAD {pad_idx+1} TRIGGER: {note} vel={velocity:.2f}")
                            
                            # Map to synths based on pad
                            # Pads 1-4: Synth 0 (ChipSynth) - different pitches
                            # Pads 5-8: Synth 1 (MoogSynth) - different pitches
                            synth_idx = 0 if pad_idx < 4 else 1
                            pitch = (note - 36) / 60.0  # Normalize MIDI to 0-1
                            audio_sys.set_param(synth_idx, "pitch", pitch)
                            audio_sys.set_param(synth_idx, "velocity", velocity)
                            
                            # XY modulation within pad
                            px, py = event["position"]
                            audio_sys.set_param(synth_idx, "timbre", px)
                            audio_sys.set_param(synth_idx, "filter", py)
                            
                        elif event["type"] == "release":
                            pad_idx = event["pad"]
                            print(f"[BodyPad] PAD {pad_idx+1} RELEASE")
                else:
                    # Kaoss mode - XY effects
                    body_kaoss.process(debug_floor)
                    fx = body_kaoss.get_fx_params()
                    
                    # Apply XY to all synths
                    for si in range(4):
                        audio_sys.set_param(si, "filter", fx["filter_cutoff"])
                        audio_sys.set_param(si, "timbre", fx["filter_resonance"])
                
                # --- Warp & Process Cups --- (Moved up to feed memory)
                current_cup_values = [0.0]*4
                cup_velocities = [0.0]*4
                if cam_cups and frame_cups is not None and H_cups is not None:
                     cups_warp = cv2.warpPerspective(frame_cups, H_cups, (config.WARP_CUPS_SIZE, config.WARP_CUPS_SIZE))
                     current_cup_values, debug_rois, cup_velocities = cups_proc.process(cups_warp)
                     # Note: Debug view now handled by DisplayManager in "2. TAZAS"
                
                # --- Tangible Synthesis Processing ---
                # Process on RAW cups frame (not warped) - overlays drawn at calibrated positions
                tangible_cup_values = [0.0] * 4
                if frame_cups is not None:
                    tangible_cup_values, adsr_params, wavetable, _ = tangible_proc.process(
                        frame_cups, freeze_adsr=freeze_adsr, freeze_wave=freeze_wave
                    )
                    
                    # Use tangible values if no H_cups (alternative detection)
                    if H_cups is None:
                        current_cup_values = tangible_cup_values
                    
                    # Update CustomDrawSynth (channel 3)
                    if adsr_params:
                        s4.set_adsr(adsr_params)
                    if wavetable is not None:
                        s4.set_wavetable(wavetable)
                    # Note: Display handled by DisplayManager in "2. TAZAS"
                
                # --- Memory Engine ---
                mem_grid = memory_eng.update(grid, current_cup_values)
                
                # --- Match Engine ---
                active_matches = match_eng.check(current_cup_values)
                
                # --- AUDIO MAPPING (Direct) ---
                # Cup A -> Synth 1 Pitch
                # Cup B -> Synth 1 Filter/Timbre
                # Cup C -> Synth 2 Pitch
                # Cup D -> Synth 3 Metal
                
                audio_sys.set_param(0, "pitch", current_cup_values[0])
                audio_sys.set_param(0, "timbre", current_cup_values[1])
                
                audio_sys.set_param(1, "pitch", current_cup_values[2])
                audio_sys.set_param(1, "filter", 0.2 + (current_cup_values[2]*0.8))
                
                audio_sys.set_param(2, "metal", current_cup_values[3])
                audio_sys.set_param(2, "pitch", 0.3 + (features.get('q4_density', 0)*0.5)) # Motion controls pitch of metal?
                
                # Floor Density -> Synth 4 (Background Pad) Vol / Release
                overall_motion = (features.get('q1_density',0) + features.get('q2_density',0)) / 2.0
                audio_sys.set_param(3, "pitch", 0.2) # Low drone
                # Synth 4 is now CustomDraw - pitch controlled by Cup D
                audio_sys.set_param(3, "pitch", current_cup_values[3])

                # --- OSC Output (Optional/Disabled for standalone) ---
                # osc_sender.send_frame(current_cup_values, features, active_matches)

                # --- Visual Renderer ---
                # Generate aesthetic frame (for projection)
                art_frame = renderer.render(grid, mem_grid, current_cup_values, active_matches)

                # === 2 VENTANAS PRINCIPALES ===
                
                # Actualizar estado de controles de cámara
                display_mgr.update_controls(
                    active_cam_control,
                    cam_controls["floor"]["br"], cam_controls["floor"]["co"],
                    cam_controls["cups"]["br"], cam_controls["cups"]["co"]
                )
                display_mgr.set_floor_mode(body_pad_mode)
                
                # Actualizar buffer de audio para visualización (osciloscopio)
                display_mgr.update_audio_buffer(audio_sys.get_viz_buffer())
                display_mgr.set_mute_state(audio_sys.global_mute)
                
                # 1. PISO - Video completo + grid superpuesto
                floor_display = display_mgr.render_floor(
                    frame_floor, floor_points, body_pad, body_kaoss
                )
                cv2.imshow(display_mgr.FLOOR_WIN, floor_display)
                
                # DEBUG: Mostrar lo que detecta el FloorProcessor
                if display_mgr.show_debug and debug_floor is not None:
                    debug_vis = cv2.resize(debug_floor, (400, 400))
                    if len(debug_vis.shape) == 2:
                        debug_vis = cv2.cvtColor(debug_vis, cv2.COLOR_GRAY2BGR)
                    cv2.putText(debug_vis, f"DETECCION Thresh:{floor_proc.threshold} (V=cerrar)", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.imshow("DEBUG: Que detecta", debug_vis)
                else:
                    try:
                        cv2.destroyWindow("DEBUG: Que detecta")
                    except:
                        pass
                
                # 2. TAZAS - Video completo + perillas y zonas de dibujo
                if frame_cups is not None:
                    cups_display = display_mgr.render_cups(
                        frame_cups, cups_points, tangible_proc
                    )
                    cv2.imshow(display_mgr.CUPS_WIN, cups_display)
                    
            else:
                cv2.imshow("Floor Raw (Sin Calibrar)", cv2.resize(frame_floor, (640, 360)))
                current_cup_values = [0.0] * 4  # Default values when no calibration

            # --- Status Print ---
            print(f"\rCups: {[f'{v:.2f}' for v in current_cup_values]} | Q1 Decay: {memory_eng.decays[0]:.2f}", end="")

            # --- FPS ---
            curr_time = time.time()
            # print(f"FPS: {1/(curr_time - prev_time + 1e-6):.1f}")
            prev_time = curr_time

            # --- Input ---
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord('c'):
                print("\n[Main] Entering Calibration Mode...")
                cv2.destroyAllWindows() # Clear screen
                
                # Calib Floor
                calib_ui_floor = CalibrationUI("Floor Calib", (config.WARP_FLOOR_SIZE, config.WARP_FLOOR_SIZE))
                Hf, ptsf = calib_ui_floor.run(cam_floor)
                
                # Calib Cups (if available)
                Hc, ptsc = None, None
                if cam_cups:
                     calib_ui_cups = CalibrationUI("Cups Calib", (config.WARP_CUPS_SIZE, config.WARP_CUPS_SIZE))
                     Hc, ptsc = calib_ui_cups.run(cam_cups)
                
                # Save if successful
                if Hf is not None:
                    data = {"floor_homography": Hf, "floor_points": ptsf}
                    if Hc is not None:
                        data["cups_homography"] = Hc
                        data["cups_points"] = ptsc
                    save_calibration(data)
                    H_floor = Hf
                    H_cups = Hc
                    print("[Main] Calibration Updated and Saved.")
                else:
                    print("[Main] Calibration Aborted.")
            
            # === CONTROLES DE CÁMARA ===
            # TAB = Cambiar entre cámaras
            if key == 9:  # TAB
                active_cam_control = "cups" if active_cam_control == "floor" else "floor"
                print(f"\n>>> CÁMARA ACTIVA: {active_cam_control.upper()} <<<")
            
            # 1/2 también cambian cámara
            if key == ord('1'):
                active_cam_control = "floor"
                print(f"\n>>> CÁMARA ACTIVA: PISO <<<")
            if key == ord('2'):
                active_cam_control = "cups"
                print(f"\n>>> CÁMARA ACTIVA: TAZAS <<<")
            
            # Brillo/Contraste
            step_br = 10
            step_co = 0.1
            target = cam_controls[active_cam_control]
            
            # W/S = Brillo arriba/abajo
            if key == ord('w'):
                target["br"] += step_br
                print(f"[{active_cam_control}] Brillo: {target['br']}")
            if key == ord('s'):
                target["br"] -= step_br
                print(f"[{active_cam_control}] Brillo: {target['br']}")
            
            # A/D = Contraste
            if key == ord('a'):
                target["co"] = max(0.1, target["co"] - step_co)
                print(f"[{active_cam_control}] Contraste: {target['co']:.1f}")
            if key == ord('d'):
                target["co"] += step_co
                print(f"[{active_cam_control}] Contraste: {target['co']:.1f}")
            
            # === MODO DEBUG ===
            if key == ord('v'):
                display_mgr.show_debug = not getattr(display_mgr, 'show_debug', False)
                print(f"[Debug] {'ACTIVADO' if display_mgr.show_debug else 'DESACTIVADO'}")
            
            # === MODO PERFORMANCE (oculta toda la UI) ===
            if key == 32:  # ESPACIO
                perf = display_mgr.toggle_performance_mode()
                print(f"[Performance] {'ACTIVADO - UI oculta' if perf else 'DESACTIVADO - UI visible'}")
            
            # === AYUDA ===
            if key == ord('h'):
                help_on = display_mgr.toggle_help()
                print(f"[Ayuda] {'VISIBLE' if help_on else 'OCULTA'}")
            
            # === MUTE GLOBAL ===
            if key == ord('0'):
                audio_sys.toggle_global_mute()
            
            # === FREEZE ADSR/WAVE ===
            if key == ord('f'):
                freeze_adsr = not freeze_adsr
                print(f"[Tangible] ADSR Congelado: {'SI' if freeze_adsr else 'NO'}")
            if key == ord('g'):
                freeze_wave = not freeze_wave
                print(f"[Tangible] Wave Congelado: {'SI' if freeze_wave else 'NO'}")
            
            # === PRESETS DE SONIDO (flechas izquierda/derecha) ===
            if key == 81 or key == 2:  # Flecha izquierda
                current_preset = get_prev_preset(current_preset)
                preset_info = get_preset(current_preset)
                display_mgr.current_preset = current_preset
                print(f"[Preset] {preset_info['name']}: {preset_info['description']}")
            if key == 83 or key == 3:  # Flecha derecha
                current_preset = get_next_preset(current_preset)
                preset_info = get_preset(current_preset)
                display_mgr.current_preset = current_preset
                print(f"[Preset] {preset_info['name']}: {preset_info['description']}")
            
            # --- Mixer Mute Controls (teclas 5-8) ---
            if key == ord('5'):
                audio_sys.toggle_mute(0)
            if key == ord('6'):
                audio_sys.toggle_mute(1)
            if key == ord('7'):
                audio_sys.toggle_mute(2)
            if key == ord('8'):
                audio_sys.toggle_mute(3)
            
            # --- Body Pad Controls ---
            if key == ord('m'):
                # Toggle between Pad and Kaoss mode
                body_pad_mode = "kaoss" if body_pad_mode == "pad" else "pad"
                print(f"[BodyPad] Mode: {body_pad_mode.upper()}")
            
            # Threshold para detección figura-fondo (+/- y I para invertir)
            if key == ord('+') or key == ord('='):
                floor_proc.set_threshold(floor_proc.threshold + 10)
                print(f"[Floor] Threshold: {floor_proc.threshold}")
            if key == ord('-') or key == ord('_'):
                floor_proc.set_threshold(floor_proc.threshold - 10)
                print(f"[Floor] Threshold: {floor_proc.threshold}")
            if key == ord('i'):
                inv = floor_proc.toggle_invert()
                print(f"[Floor] Invertir: {'SI (claro sobre oscuro)' if inv else 'NO (oscuro sobre claro)'}")
            
            if key == ord('e'):
                # Cycle through scales
                scales = ["pentatonic", "major", "minor", "chromatic", "drums"]
                current_scale = getattr(body_pad, '_current_scale', 0)
                current_scale = (current_scale + 1) % len(scales)
                body_pad._current_scale = current_scale
                body_pad.set_scale(root=48, scale_type=scales[current_scale])
                print(f"[BodyPad] Scale: {scales[current_scale].upper()}")
            
            if key == ord('p'):
                # Toggle pad layout 2x4 vs 4x4
                new_mode = "4x4" if body_pad.mode == "2x4" else "2x4"
                body_pad = BodyPad(grid_size=config.WARP_FLOOR_SIZE, mode=new_mode)
                print(f"[BodyPad] Layout: {new_mode} ({body_pad.num_pads} pads)")
            
            # --- Zone Recalibration (R key) ---
            if key == ord('r'):
                print("[Main] Re-running Setup Wizard...")
                cv2.destroyAllWindows()
                wizard = SetupWizard()
                wizard_result = wizard.run()
                if wizard_result:
                    # Reload calibration
                    calib_data = load_calibration()
                    H_floor = np.array(calib_data.get("floor_homography")) if calib_data.get("floor_homography") else None
                    H_cups = np.array(calib_data.get("cups_homography")) if calib_data.get("cups_homography") else None
                    cups_points = calib_data.get("cups_points")
                    
                    # Update tangible processor with new zone
                    if cups_points:
                        tangible_proc.set_zone(cups_points)
                        print("[Main] Tangible zones updated!")
                    
                    print("[Main] Calibration updated!")


    except KeyboardInterrupt:
        pass
    finally:
        print("\n--- SHUTTING DOWN ---")
        cam_floor.stop()
        if cam_cups: cam_cups.stop()
        audio_sys.stop() # STOP AUDIO
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
