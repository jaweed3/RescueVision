from pathlib import Path 
from constant import DEFAULT_CONFIG
import json

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_config():
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                loaded = json.load(f) or {}
            if isinstance(loaded, dict):
                config.update(loaded)
        except json.JSONDecodeError as e:
            logger.warning("config.json is invalid JSON (%s) — using defaults", e)
        except OSError as e:
            logger.warning("Could not read config.json (%s) — using defaults", e)
    return config

