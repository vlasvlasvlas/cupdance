# Cupdance
**A Computer Vision Choreographic Interface**

> *Transforming movement into harmony. A dialogue between the dance floor and the table.*

## 📜 Abstract (Concept)
**Cupdance** is an interactive performance instrument that bridges the gap between large-scale body movement and fine-motor tactile control. It consists of two interconnected spaces:
1.  **The Floor (The Stage):** A 2x2m grid where a dancer's positioning and energy are captured by a zenithal camera, translating kinetic expression into spatial data.
2.  **The Table (The Conductor):** A tabletop interface where an operator manipulates four ordinary cups acting as high-precision rotational controllers.

Using real-time Computer Vision (CV), the system synthesizes these two inputs—the chaotic, organic movement of the body and the precise, deliberate rotation of objects—to generate a complex audiovisual soundscape. It is an exploration of memory, presence, and control.

## 🛠 Technical Architecture
Designed for low-latency live performance (SOTA standards).

- **Core:** Python 3.10+, OpenCV (Multi-threaded Architecture).
- **Vision Strategy:**
  - **Floor:** Adaptive Background Subtraction & Motion Energy Analysis (16x16 Grid).
  - **Table:** Homography-rectified object tracking with occlusion handling ("Angle Latch").
- **Output Protocols:**
  - **Audio:** OSC (Open Sound Control) or MIDI to standard DAWs (Ableton Live, Max/MSP, SuperCollider).
  - **Visuals:** Organic, fluid projection overlay running on a separate render thread.
- **Hardware Requirements:**
  - 2x USB Cameras (1080p @ 60fps recommended).
  - Computer with decent CPU (GPU acceleration via OpenCL enabled).
  - Controlled lighting conditions (or IR illumination for robustness).

## 🚀 Usage & Features
- **4-Point Manual Calibration:** Robust setup tool to adapt to any venue or stage size.
- **"Angle Latch" Technology:** Allows the operator to handle cups naturally; values are held even when hands occlude the markers.
- **Memory Engine:** Dance "trails" decay over time, modified by the table's cup positions (The operator "holds" or "erases" the dancer's memory).
- **Match System:** Detects harmonic alignment between cups (AB, ABC, ABCD) to trigger scene changes or climactic moments.

## 📅 Development Roadmap (Residency Plan)
This project is structured to evolve from a technical prototype to a touring performance piece.

### Phase I: The Core (Skeleton)
*Est. Duration: 2 Weeks*
- Implementation of multi-threaded dual-camera capture.
- Robust 4-point calibration UI.
- Basic motion grid extraction and cup angle detection.

### Phase II: The Feel (Instrument)
*Est. Duration: 3 Weeks*
- Refinement of "Angle Latch" and smoothing algorithms to ensure the system feels "musical" and responsive.
- Implementation of the Memory/Decay engine.
- OSC unification for sound tests.

### Phase III: The Aesthetics (Visuals & Polish)
*Est. Duration: 3 Weeks*
- Development of the "Organic Overlay": replacing debug grids with fluid, aesthetic visualizations suitable for projection.
- Integration of "Modes" (Dorian, Phrygian, etc.) and lighting control.

### Phase IV: Performance & Rehearsal
*Est. Duration: Ongoing*
- Full integration with dancer and sound designer.
- Stress testing in variable lighting conditions.
- Final adjustments to mapping curves.

---
*Created for the 2026 Interactive Arts Residency Program.*
