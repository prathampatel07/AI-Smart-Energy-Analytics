import json
from pathlib import Path

def get_settings_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "settings.json"

def load_settings() -> dict:
    path = get_settings_path()
    default_settings = {
        "tariff_rate": 0.15,
        "forecast_horizon": 48,
        "currency": "INR",
        "theme": "dark",
        "org_name": "Acme Energy Corp",
        "timezone": "UTC",
        "default_building": ""
    }
    
    if not path.exists():
        return default_settings
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = default_settings.copy()
            merged.update(data)
            return merged
    except Exception:
        return default_settings

def save_settings(settings: dict) -> None:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
