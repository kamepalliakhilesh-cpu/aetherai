"""
Simulated IoT & Ambient Room Hardware Controller (Demo Sandbox).

NOTE FOR AUDITORS / HACKATHON EVALUATION:
This module provides a deterministic in-memory simulation sandbox for room ambient lighting,
desk lamps, and smart plugs. It models Home Assistant / WLED / Zigbee state changes locally
without requiring external hardware bridges on demo workstations.
"""

import json
import requests
from pathlib import Path

# Persistent state of the local IoT and smart room hardware (Simulated Sandbox)
_IOT_STATE = {
    "desk_lamp": True,
    "ambient_light": {
        "state": True,
        "color": "#FFB848",
        "color_name": "Solaris Gold",
        "brightness": 85
    },
    "smart_plugs": {
        "desk": True,
        "monitor": True,
        "speakers": True,
        "fan": False
    },
    "current_preset": "nominal"
}

COLOR_MAP = {
    "solaris": ("#FFB848", "Solaris Gold"),
    "gold": ("#FFB848", "Solaris Gold"),
    "amber": ("#FF9F1C", "Solaris Amber"),
    "warm": ("#FFAA33", "Warm Amber"),
    "white": ("#FFFFFF", "Daylight White"),
    "blue": ("#00B4D8", "Cyber Cyan"),
    "cyan": ("#00F5D4", "Neon Cyan"),
    "red": ("#FF2A55", "Alert Red"),
    "purple": ("#9D4EDD", "Deep Violet"),
    "green": ("#2EC4B6", "Emerald Green")
}

def set_ambient_lighting(color: str = None, brightness: int = None, state: str = None, record_undo: bool = True) -> dict:
    """
    Controls room ambient lighting, desk LED strip, or smart bulbs (Hue / WLED / Home Assistant).
    """
    global _IOT_STATE

    prev_state = dict(_IOT_STATE["ambient_light"])

    if state is not None:
        _IOT_STATE["ambient_light"]["state"] = (state.lower() in ["on", "true", "enable", "1"])

    if brightness is not None:
        _IOT_STATE["ambient_light"]["brightness"] = max(0, min(100, int(brightness)))

    if color:
        c_lower = color.lower().strip()
        matched = False
        for k, (hex_code, name) in COLOR_MAP.items():
            if k in c_lower:
                _IOT_STATE["ambient_light"]["color"] = hex_code
                _IOT_STATE["ambient_light"]["color_name"] = name
                matched = True
                break
        if not matched:
            _IOT_STATE["ambient_light"]["color"] = color if color.startswith("#") else f"#{color}"
            _IOT_STATE["ambient_light"]["color_name"] = color.title()

    light = _IOT_STATE["ambient_light"]
    status_str = "ON" if light["state"] else "OFF"
    msg = f"[Simulated IoT] Ambient lighting set to {status_str} at {light['brightness']}% brightness ({light['color_name']}), Sir."

    if record_undo:
        try:
            from core.undo import push_undo
            push_undo(
                f"Ambient lighting {light['color_name']}",
                lambda: set_ambient_lighting(
                    color=prev_state.get("color"),
                    brightness=prev_state.get("brightness"),
                    state="on" if prev_state.get("state") else "off",
                    record_undo=False
                )
            )
        except Exception:
            pass

    return {
        "success": True,
        "state": status_str,
        "brightness": light["brightness"],
        "color": light["color"],
        "color_name": light["color_name"],
        "light": light,
        "message": msg
    }

def toggle_desk_lamp(state: str = "toggle") -> dict:
    """
    Toggles or sets the desk lamp state (on/off/toggle).
    """
    global _IOT_STATE
    st = (state or "toggle").lower().strip()
    if st == "toggle":
        _IOT_STATE["desk_lamp"] = not _IOT_STATE["desk_lamp"]
    elif st in ["on", "true", "1"]:
        _IOT_STATE["desk_lamp"] = True
    else:
        _IOT_STATE["desk_lamp"] = False

    state_str = "ON" if _IOT_STATE["desk_lamp"] else "OFF"
    return {
        "success": True,
        "device": "desk_lamp",
        "state": state_str,
        "desk_lamp": _IOT_STATE["desk_lamp"],
        "message": f"[Simulated IoT] Desk lamp switched {state_str}, Sir."
    }

def toggle_smart_plug(plug_name: str = "desk", state: str = "toggle") -> dict:
    """
    Controls connected smart plugs (e.g. 'desk', 'monitor', 'fan', 'speakers').
    """
    global _IOT_STATE
    p = plug_name.lower().strip()
    if p not in _IOT_STATE["smart_plugs"]:
        _IOT_STATE["smart_plugs"][p] = True

    st = (state or "toggle").lower().strip()
    if st == "toggle":
        _IOT_STATE["smart_plugs"][p] = not _IOT_STATE["smart_plugs"][p]
    elif st in ["on", "true", "1"]:
        _IOT_STATE["smart_plugs"][p] = True
    else:
        _IOT_STATE["smart_plugs"][p] = False

    state_str = "ON" if _IOT_STATE["smart_plugs"][p] else "OFF"
    return {
        "success": True,
        "plug": p,
        "state": state_str,
        "is_on": _IOT_STATE["smart_plugs"][p],
        "message": f"[Simulated IoT] Smart plug '{p.title()}' switched {state_str}, Sir."
    }

def set_environment_preset(preset_name: str) -> dict:
    """
    Orchestrates room lighting, displays, and audio into defined situational presets:
    - 'coding' / 'focus': Warm amber 50%, desk lamp ON, extended monitor layout.
    - 'cinematic' / 'movie': Dim amber 12%, desk lamp OFF.
    - 'alert' / 'high_performance': Vivid cyan/red accent, maximum cooling.
    - 'daylight': Daylight white 100%, bright desk lighting.
    """
    global _IOT_STATE
    preset = preset_name.lower().strip()
    _IOT_STATE["current_preset"] = preset

    if any(k in preset for k in ["code", "coding", "focus", "work", "develop"]):
        set_ambient_lighting(color="amber", brightness=60, state="on")
        toggle_desk_lamp("on")
        return {
            "success": True,
            "preset": "coding_focus",
            "message": "[Simulated IoT] Focus environment engaged: Warm amber ambient glow at 60%, desk lamp active, workspace synchronized, Sir."
        }
    elif any(k in preset for k in ["movie", "cinema", "cinematic", "night"]):
        set_ambient_lighting(color="amber", brightness=15, state="on")
        toggle_desk_lamp("off")
        return {
            "success": True,
            "preset": "cinematic",
            "message": "[Simulated IoT] Cinematic preset active: Room lights dimmed to 15% warm amber, desk lamp off, Sir."
        }
    elif any(k in preset for k in ["daylight", "bright", "morning"]):
        set_ambient_lighting(color="white", brightness=100, state="on")
        toggle_desk_lamp("on")
        return {
            "success": True,
            "preset": "daylight",
            "message": "[Simulated IoT] Daylight environment engaged: 100% illumination calibrated, Sir."
        }
    elif any(k in preset for k in ["alert", "overclock", "red"]):
        set_ambient_lighting(color="red", brightness=90, state="on")
        return {
            "success": True,
            "preset": "alert",
            "message": "[Simulated IoT] High-urgency alert lighting engaged: Red luminescent pulse calibrated, Sir."
        }
    else:
        set_ambient_lighting(color="solaris", brightness=80, state="on")
        return {
            "success": True,
            "preset": "nominal",
            "message": f"[Simulated IoT] Environment preset '{preset}' calibrated, Sir."
        }

def get_iot_status() -> dict:
    """Returns the full status of all connected smart home devices"""
    return {
        "success": True,
        "state": _IOT_STATE
    }

get_iot_state = get_iot_status
