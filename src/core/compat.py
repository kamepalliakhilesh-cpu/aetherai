"""
Runtime Compatibility & Platform Verification Layer for JARVIS / Aether.
Ensures seamless operation across Python 3.11, 3.12, 3.13, and 3.14 on Windows 11.
Provides shim loading for removed standard modules (audioop, aifc, chunk).
"""

import sys
import os
import platform
from typing import Dict, Any, List

# ─── Python 3.13 / 3.14 Audio Shims ──────────────────────────────────────────
# Python 3.13+ removed the built-in 'audioop' module.
# speech_recognition and wav parsers require audioop; we map audioop-lts if missing.
try:
    import audioop  # noqa: F401
except ImportError:
    try:
        import audioop_lts as audioop  # type: ignore
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

def check_environment_health() -> Dict[str, Any]:
    """
    Runs diagnostic audit across Python runtime, C-extensions, audio devices,
    and desktop automation libraries.
    """
    py_ver = sys.version_info
    ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    is_win = platform.system() == "Windows"
    warnings: List[str] = []
    checks: Dict[str, bool] = {}

    # Check 1: Operating System
    checks["windows_os"] = is_win
    if not is_win:
        warnings.append("Operating system is not Windows. Desktop automation features may be restricted.")

    # Check 2: Audio Engine (sounddevice & PortAudio DLL)
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        checks["sounddevice_active"] = len(devices) > 0
    except Exception as e:
        checks["sounddevice_active"] = False
        warnings.append(f"sounddevice/PortAudio warning: {e}")

    # Check 3: Audioop module availability
    try:
        import audioop  # noqa: F401
        checks["audioop_available"] = True
    except Exception:
        checks["audioop_available"] = False
        warnings.append("audioop not found. Install 'audioop-lts' on Python 3.13/3.14.")

    # Check 4: Computer Use & Input Emulation
    try:
        import pyautogui  # noqa: F401
        import pygetwindow  # noqa: F401
        checks["input_emulation_available"] = True
    except Exception as e:
        checks["input_emulation_available"] = False
        warnings.append(f"Input emulation library warning: {e}")

    # Check 5: Display Vision & PIL
    try:
        from PIL import Image, ImageGrab  # noqa: F401
        checks["vision_available"] = True
    except Exception as e:
        checks["vision_available"] = False
        warnings.append(f"PIL/ImageGrab warning: {e}")

    # Check 6: PDF Text Parsing
    try:
        import pypdf  # noqa: F401
        checks["pdf_parsing_available"] = True
    except Exception as e:
        checks["pdf_parsing_available"] = False
        warnings.append(f"pypdf warning: {e}")

    # Check 7: SQLite FTS5 Vector Engine
    try:
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE fts_test USING fts5(content);")
        conn.close()
        checks["sqlite_fts5_available"] = True
    except Exception as e:
        checks["sqlite_fts5_available"] = False
        warnings.append(f"SQLite FTS5 warning: {e}")

    all_passed = len(warnings) == 0 and all(checks.values())
    return {
        "success": all_passed,
        "python_version": ver_str,
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "checks": checks,
        "warnings": warnings,
        "status": "NOMINAL" if all_passed else "COMPATIBLE_WITH_ADVISORIES"
    }
