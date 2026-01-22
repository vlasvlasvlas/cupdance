import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "../config/settings.json")
BANKS_PATH = os.path.join(os.path.dirname(__file__), "../config/sound_banks.json")

class ConfigManager:
    def __init__(self):
        self.settings = self.load_json(SETTINGS_PATH)
        self.banks = self.load_json(BANKS_PATH)

    def load_json(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading {path}: {e}")
            return {}

    def save_settings(self):
        try:
            with open(SETTINGS_PATH, 'w') as f:
                json.dump(self.settings, f, indent=4)
            print("[Config] Settings saved.")
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")

    def get_camera_config(self, cam_name):
        return self.settings.get("cameras", {}).get(cam_name, {})

    def get_audio_config(self):
        return self.settings.get("audio", {})

    def get_bank(self, bank_id):
        for b in self.banks.get("banks", []):
            if b["id"] == bank_id:
                return b
        return None

# Global instance
cfg = ConfigManager()
