import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "assistant_name": "Aether",
    "provider": "gemini",
    "gemini_api_key": "",
    "openrouter_api_key": "",
    "model_name": "gemini-2.0-flash",
    "openrouter_model": "google/gemini-2.0-flash-001",
    "voice_name": "Microsoft David Desktop",
    "speech_rate": 1.0,
    "speech_pitch": 1.0,
    "auto_listen": True,
    "startup_briefing": True,
    "hotkey": "alt+space",
    "sound_effects": True
}

MODEL_ALIASES = {
    "gemini-3.5-flashlite": "gemini-2.0-flash",
    "gemini 3.5 flashlite": "gemini-2.0-flash",
    "gemini 3.5 flash-lite": "gemini-2.0-flash",
    "3.5-flash-lite": "gemini-2.0-flash",
    "google/gemini-3.5-flashlite": "google/gemini-2.0-flash-001",
    "gemini-2.0-flashlite": "gemini-2.0-flash",
}

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # merge any missing defaults
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v

            # Normalize model aliases
            raw_model = cfg.get("model_name", "gemini-3.5-flash-lite")
            if raw_model in MODEL_ALIASES:
                cfg["model_name"] = MODEL_ALIASES[raw_model]

            raw_or_model = cfg.get("openrouter_model", "google/gemini-3.5-flash-lite")
            if raw_or_model in MODEL_ALIASES:
                cfg["openrouter_model"] = MODEL_ALIASES[raw_or_model]

            # Environment variable overrides
            if not cfg.get("gemini_api_key"):
                env_gemini = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if env_gemini:
                    cfg["gemini_api_key"] = env_gemini

            if not cfg.get("openrouter_api_key"):
                env_or = os.environ.get("OPENROUTER_API_KEY")
                if env_or:
                    cfg["openrouter_api_key"] = env_or

            return cfg
    except Exception as e:
        print(f"[Config] Error loading config, using defaults: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> bool:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception as e:
        print(f"[Config] Error saving config: {e}")
        return False
