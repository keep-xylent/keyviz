import os
import json
import shutil
import sys
from typing import Dict, Any

# Package and configuration paths setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if "site-packages" in BASE_DIR or "dist-packages" in BASE_DIR:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".keyviz")
    os.makedirs(CONFIG_DIR, exist_ok=True)
else:
    # Use parent directory of keyviz/ (which is the root directory of the project)
    CONFIG_DIR = os.path.dirname(BASE_DIR)

CONFIG_FILE_NAME = "config.json"
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "pos": [100, 100],
    "recorded_keys": {},
    "mode": "normal",
    "color": "default",
    "custom_pos": {},
    "no_mouse": False,
    "consent_granted": False
}

def get_config_path() -> str:
    """Returns the absolute path to the main user configuration file."""
    return CONFIG_FILE_PATH

def validate_and_migrate(config_data: Any) -> Dict[str, Any]:
    """Validates the configuration structure and types, migrating settings if needed."""
    if not isinstance(config_data, dict):
        return DEFAULT_CONFIG.copy()

    validated = DEFAULT_CONFIG.copy()

    # Version check and migration if necessary
    version = config_data.get("version", 0)
    
    # Validation rules: Checks types and assigns default on mismatch/absence
    
    # 1. pos: list/tuple of 2 numeric values
    pos = config_data.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        try:
            validated["pos"] = [int(pos[0]), int(pos[1])]
        except (ValueError, TypeError):
            pass

    # 2. recorded_keys: dict mapping string to list of strings
    recorded = config_data.get("recorded_keys")
    if isinstance(recorded, dict):
        cleaned_recorded = {}
        for k, v in recorded.items():
            if isinstance(k, str) and isinstance(v, list):
                cleaned_recorded[str(k)] = [str(item) for item in v]
        validated["recorded_keys"] = cleaned_recorded

    # 3. mode: string in ["normal", "gaming", "custom"]
    mode = config_data.get("mode")
    if isinstance(mode, str) and mode in ["normal", "gaming", "custom"]:
        validated["mode"] = mode

    # 4. color: string
    color = config_data.get("color")
    if isinstance(color, str):
        validated["color"] = color

    # 5. custom_pos: dict mapping string to coordinate list of 2 integers
    custom_pos = config_data.get("custom_pos")
    if isinstance(custom_pos, dict):
        cleaned_custom = {}
        for k, v in custom_pos.items():
            if isinstance(k, str) and isinstance(v, dict):
                # Handle nested key coordinates mapping: mode -> key -> [x, y]
                cleaned_mode_map = {}
                for key_name, coord in v.items():
                    if isinstance(key_name, str) and isinstance(coord, (list, tuple)) and len(coord) == 2:
                        try:
                            cleaned_mode_map[str(key_name)] = [int(coord[0]), int(coord[1])]
                        except (ValueError, TypeError):
                            pass
                cleaned_custom[str(k)] = cleaned_mode_map
            elif isinstance(k, str) and isinstance(v, (list, tuple)) and len(v) == 2:
                # Fallback for old custom_pos structure which was just a single layer (sc_key -> [x, y])
                try:
                    cleaned_custom[str(k)] = [int(v[0]), int(v[1])]
                except (ValueError, TypeError):
                    pass
        validated["custom_pos"] = cleaned_custom

    # 6. no_mouse: boolean
    if "no_mouse" in config_data:
        validated["no_mouse"] = bool(config_data["no_mouse"])

    # 7. consent_granted: boolean
    if "consent_granted" in config_data:
        validated["consent_granted"] = bool(config_data["consent_granted"])

    # Update version to current latest
    validated["version"] = 1
    return validated

def load_config() -> Dict[str, Any]:
    """Loads config.json from disk, migrating or creating it with default values if necessary."""
    if not os.path.exists(CONFIG_FILE_PATH):
        # Check if legacy settings exist
        migration_data = DEFAULT_CONFIG.copy()
        settings_path = os.path.join(CONFIG_DIR, 'settings.json')
        recorded_path = os.path.join(CONFIG_DIR, 'recorded_keys.json')
        
        legacy_found = False
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    migration_data["pos"] = json.load(f).get("pos", [100, 100])
                legacy_found = True
            except Exception:
                pass
        if os.path.exists(recorded_path):
            try:
                with open(recorded_path, 'r', encoding='utf-8') as f:
                    migration_data["recorded_keys"] = json.load(f)
                legacy_found = True
            except Exception:
                pass
        
        # If legacy configs are found or first-time creation, we persist it
        save_config(migration_data)
        return migration_data

    # Load existing config
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        return validate_and_migrate(raw_data)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"[WARNING] Configuration file is corrupted or invalid ({e}). Restoring to default values.")
        # Create a backup of the corrupted file
        try:
            backup_path = CONFIG_FILE_PATH + ".bak"
            shutil.copy2(CONFIG_FILE_PATH, backup_path)
            print(f"[INFO] Backed up corrupted configuration to: {backup_path}")
        except Exception:
            pass
        
        # Save and return default config
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config_data: Dict[str, Any]) -> None:
    """Saves config_data dict to config.json file."""
    try:
        # Validate/clean before saving
        validated = validate_and_migrate(config_data)
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(validated, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save configuration to {CONFIG_FILE_PATH}: {e}")

def update_button_pos(config_data: Dict[str, Any], mode: str, sc_key: str, x: int, y: int) -> Dict[str, Any]:
    """Updates a specific button position in custom_pos mapping and returns updated config data."""
    if "custom_pos" not in config_data or not isinstance(config_data["custom_pos"], dict):
        config_data["custom_pos"] = {}
        
    # Ensure mode dict exists
    if mode not in config_data["custom_pos"] or not isinstance(config_data["custom_pos"][mode], dict):
        config_data["custom_pos"][mode] = {}
        
    config_data["custom_pos"][mode][sc_key] = [x, y]
    return config_data

def load_packaged_json(filename: str) -> Any:
    """Loads a packaged JSON asset file (like layout.json or key.json). Logs user friendly errors and exits on failure."""
    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(file_path):
        print(f"[CRITICAL ERROR] Required asset file '{filename}' was not found at {file_path}.")
        print("Please reinstall KeyViz or check your installation files.")
        sys.exit(1)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[CRITICAL ERROR] Required asset file '{filename}' is corrupted or contains invalid JSON.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to load asset file '{filename}': {e}")
        sys.exit(1)
