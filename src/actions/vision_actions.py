"""
Vision Actions Module for JARVIS / Aether.
Provides high-DPI aware screen capture, active window targeting,
multi-monitor bounding, and base64 optimization for multimodal LLMs.
"""

import io
import time
import base64
import ctypes
from typing import Dict, Any, Optional, Tuple
from PIL import Image

# Initialize High-DPI awareness on Windows so coordinate grabs are pixel-accurate
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_SCREEN_CACHE = {
    "timestamp": 0.0,
    "data": None
}

def capture_screen_image(monitor_index: int = 1, bbox: Optional[Tuple[int, int, int, int]] = None, use_cache_sec: float = 0.0) -> Dict[str, Any]:
    """
    Captures display buffer and returns PIL image, base64 data, and dimensions.
    Supports multi-tier fallbacks:
    1. PIL ImageGrab (with bbox support)
    2. mss (high-speed DirectX/DXGI capture)
    3. Windows GDI BitBlt
    """
    global _SCREEN_CACHE
    now = time.time()
    if use_cache_sec > 0 and _SCREEN_CACHE["data"] and (now - _SCREEN_CACHE["timestamp"]) < use_cache_sec:
        return _SCREEN_CACHE["data"]

    img = None
    last_err = ""

    # Strategy 1: PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=bbox, all_screens=True if bbox is None else False)
    except Exception as e:
        last_err = f"ImageGrab: {e}"

    # Strategy 2: mss DXGI capture
    if img is None:
        try:
            from mss import MSS
            with MSS() as sct:
                mon = sct.monitors[monitor_index] if monitor_index < len(sct.monitors) else sct.monitors[0]
                sct_img = sct.grab(mon)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                if bbox:
                    img = img.crop(bbox)
        except Exception as e:
            last_err = f"{last_err} | MSS: {e}"

    if img is None:
        return {
            "success": False,
            "error": f"Display capture unavailable (interactive desktop context required): {last_err}",
            "is_session_restricted": True
        }

    try:
        orig_w, orig_h = img.width, img.height

        # Scale down if large (max 1920 width) to preserve bandwidth / tokens
        if img.width > 1920:
            ratio = 1920 / img.width
            new_size = (1920, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85, optimize=True)
        img_bytes = buffered.getvalue()
        b64_str = base64.b64encode(img_bytes).decode("utf-8")

        result = {
            "success": True,
            "image_bytes": img_bytes,
            "base64": b64_str,
            "width": img.width,
            "height": img.height,
            "original_resolution": f"{orig_w}x{orig_h}",
            "format": "JPEG"
        }

        _SCREEN_CACHE["timestamp"] = now
        _SCREEN_CACHE["data"] = result
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to encode screen buffer: {str(e)}"
        }

def capture_active_window_image() -> Dict[str, Any]:
    """
    Captures only the currently active foreground window instead of the entire desktop.
    Ideal for debugging, code review, or focused application analysis.
    """
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return capture_screen_image()

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]

        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top

        if w <= 0 or h <= 0:
            return capture_screen_image()

        return capture_screen_image(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    except Exception:
        return capture_screen_image()
