# Sound Presets Configuration
# Each preset defines ADSR envelope and waveform characteristics

SOUND_PRESETS = {
    "MOOG": {
        "name": "MOOG Classic",
        "description": "Sonido analógico cálido con filtro resonante",
        "adsr": {
            "attack": 0.05,    # Ataque rápido
            "decay": 0.2,      # Decay moderado
            "sustain": 0.7,    # Sustain alto
            "release": 0.3    # Release moderado
        },
        "waveform": "saw",     # Onda diente de sierra
        "filter_cutoff": 0.6,
        "filter_resonance": 0.4,
        "detune": 0.02
    },
    
    "8BIT": {
        "name": "8-Bit Retro",
        "description": "Sonido de videojuego clásico",
        "adsr": {
            "attack": 0.01,    # Ataque instantáneo
            "decay": 0.1,
            "sustain": 0.5,
            "release": 0.1     # Release corto
        },
        "waveform": "square",   # Onda cuadrada
        "filter_cutoff": 1.0,   # Sin filtro
        "filter_resonance": 0.0,
        "detune": 0.0
    },
    
    "PAD": {
        "name": "Ambient Pad",
        "description": "Pad atmosférico suave",
        "adsr": {
            "attack": 0.8,     # Ataque lento
            "decay": 0.5,
            "sustain": 0.8,
            "release": 1.5     # Release largo
        },
        "waveform": "sine",     # Onda sinusoidal
        "filter_cutoff": 0.4,
        "filter_resonance": 0.2,
        "detune": 0.01
    },
    
    "PLUCK": {
        "name": "Pluck Bass",
        "description": "Bajo punzante tipo slap",
        "adsr": {
            "attack": 0.001,   # Ataque instantáneo
            "decay": 0.3,
            "sustain": 0.0,    # Sin sustain
            "release": 0.2
        },
        "waveform": "triangle",
        "filter_cutoff": 0.8,
        "filter_resonance": 0.3,
        "detune": 0.0
    },
    
    "BELL": {
        "name": "Crystal Bell",
        "description": "Campana metálica brillante",
        "adsr": {
            "attack": 0.001,
            "decay": 0.8,
            "sustain": 0.2,
            "release": 1.0
        },
        "waveform": "sine",
        "filter_cutoff": 1.0,
        "filter_resonance": 0.0,
        "detune": 0.005,
        "fm_amount": 0.3       # Modulación FM para efecto campana
    },
    
    "LIBRE": {
        "name": "LIBRE (Dibujo)",
        "description": "Usa el ADSR y onda dibujados en cámara",
        "adsr": None,          # Se toma del dibujo
        "waveform": None,      # Se toma del dibujo
        "filter_cutoff": 0.8,
        "filter_resonance": 0.3,
        "detune": 0.0
    }
}

PRESET_ORDER = ["MOOG", "8BIT", "PAD", "PLUCK", "BELL", "LIBRE"]

def get_preset(name):
    """Obtiene un preset por nombre."""
    return SOUND_PRESETS.get(name, SOUND_PRESETS["MOOG"])

def get_next_preset(current):
    """Obtiene el siguiente preset en el ciclo."""
    idx = PRESET_ORDER.index(current) if current in PRESET_ORDER else 0
    return PRESET_ORDER[(idx + 1) % len(PRESET_ORDER)]

def get_prev_preset(current):
    """Obtiene el preset anterior en el ciclo."""
    idx = PRESET_ORDER.index(current) if current in PRESET_ORDER else 0
    return PRESET_ORDER[(idx - 1) % len(PRESET_ORDER)]

def get_all_presets():
    """Lista todos los presets disponibles."""
    return PRESET_ORDER
