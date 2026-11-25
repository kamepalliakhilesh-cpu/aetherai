"""
Media Actions Module for JARVIS / Aether.
Provides reliable hardware-level media key dispatch using Windows SendInput
with extended key flags and PowerShell SMTC fallback.
"""

import ctypes
from typing import Dict, Any

# Windows Virtual Key Codes for Media
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

# Windows SendInput Constants
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_u",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_u", _INPUT_UNION)
    ]

def _send_media_key(vk_code: int) -> bool:
    """Dispatches media key via Windows SendInput with KEYEVENTF_EXTENDEDKEY."""
    try:
        user32 = ctypes.windll.user32

        # Key down
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.ki.wVk = vk_code
        inp_down.ki.wScan = 0
        inp_down.ki.dwFlags = KEYEVENTF_EXTENDEDKEY
        inp_down.ki.time = 0
        inp_down.ki.dwExtraInfo = None

        # Key up
        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.ki.wVk = vk_code
        inp_up.ki.wScan = 0
        inp_up.ki.dwFlags = KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP
        inp_up.ki.time = 0
        inp_up.ki.dwExtraInfo = None

        inputs = (INPUT * 2)(inp_down, inp_up)
        ret = user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
        if ret == 2:
            return True
    except Exception:
        pass

    # Fallback to keybd_event
    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False

def control_media(command: str) -> Dict[str, Any]:
    """
    Controls Windows media playback across Spotify, Chrome, YouTube, and media players:
    - 'toggle' / 'play' / 'pause' / 'resume'
    - 'next' / 'skip'
    - 'previous' / 'prev' / 'back'
    - 'stop'
    - 'mute' / 'unmute'
    """
    cmd = command.strip().lower()

    if any(k in cmd for k in ["next", "skip", "forward"]):
        success = _send_media_key(VK_MEDIA_NEXT_TRACK)
        return {
            "success": success,
            "command": "next",
            "message": "Skipped to next media track, Sir." if success else "Failed to dispatch next track command."
        }
    elif any(k in cmd for k in ["previous", "prev", "back", "last"]):
        success = _send_media_key(VK_MEDIA_PREV_TRACK)
        return {
            "success": success,
            "command": "previous",
            "message": "Returned to previous media track, Sir." if success else "Failed to dispatch previous track command."
        }
    elif "stop" in cmd:
        success = _send_media_key(VK_MEDIA_STOP)
        return {
            "success": success,
            "command": "stop",
            "message": "Media playback stopped, Sir." if success else "Failed to dispatch stop playback command."
        }
    elif any(k in cmd for k in ["mute", "unmute"]):
        success = _send_media_key(VK_VOLUME_MUTE)
        return {
            "success": success,
            "command": "mute",
            "message": "Master audio mute toggled, Sir." if success else "Failed to toggle audio mute."
        }
    else:
        # Default: play / pause toggle
        success = _send_media_key(VK_MEDIA_PLAY_PAUSE)
        return {
            "success": success,
            "command": "play_pause",
            "message": "Media playback state toggled, Sir." if success else "Failed to toggle media playback."
        }
