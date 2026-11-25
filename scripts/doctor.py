#!/usr/bin/env python3
"""
Pre-flight doctor script for Aether.ai-PC demo.
Checks imports, audio, API keys, and UI boot readiness.
Run: python scripts/doctor.py
"""
import sys
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

# Add src to path
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

def check_import(name: str, critical: bool = True) -> bool:
    try:
        __import__(name)
        print(f"  [OK] {name}")
        return True
    except ImportError as e:
        if critical:
            print(f"  [FAIL] {name} (CRITICAL) - {e}")
        else:
            print(f"  [WARN] {name} (optional) - {e}")
        return False

def check_env_var(name: str, critical: bool = False) -> bool:
    val = os.environ.get(name)
    if val:
        print(f"  [OK] {name} = {val[:8]}...")
        return True
    else:
        if critical:
            print(f"  [FAIL] {name} not set (CRITICAL)")
        else:
            print(f"  [WARN] {name} not set (optional)")
        return False

def check_file(path: Path, critical: bool = True) -> bool:
    if path.exists():
        print(f"  [OK] {path.relative_to(PROJECT_ROOT)}")
        return True
    else:
        if critical:
            print(f"  [FAIL] {path.relative_to(PROJECT_ROOT)} missing (CRITICAL)")
        else:
            print(f"  [WARN] {path.relative_to(PROJECT_ROOT)} missing (optional)")
        return False

def main():
    print("=" * 60)
    print("  AETHER.AI  //  PRE-FLIGHT DOCTOR")
    print("=" * 60)

    all_ok = True

    print("\n[1/6] Core Python imports...")
    core_imports = [
        ("json", True), ("os", True), ("sys", True), ("pathlib", True),
        ("asyncio", True), ("threading", True), ("subprocess", True),
        ("sqlite3", True), ("logging", True), ("dataclasses", True),
    ]
    for name, crit in core_imports:
        if not check_import(name, crit):
            all_ok = False

    print("\n[2/6] Third-party imports (core)...")
    third_party_core = [
        ("psutil", True),
        ("requests", True),
        ("websockets", True),
        ("qrcode", True),
        ("cryptography", True),
        ("sounddevice", True),
        ("speech_recognition", True),
        ("numpy", True),
        ("PIL", True),
        ("mss", True),
        ("pyautogui", True),
        ("pygetwindow", True),
        ("pyperclip", True),
        ("pypdf", True),
    ]
    for name, crit in third_party_core:
        if not check_import(name, crit):
            all_ok = False

    print("\n[3/6] Optional third-party imports...")
    optional_imports = [
        ("win32crypt", False),
        ("pywinauto", False),
        ("uiautomation", False),
        ("comtypes", False),
        ("cv2", False),
        ("edge_tts", False),
    ]
    for name, crit in optional_imports:
        check_import(name, crit)

    print("\n[4/6] Project module imports...")
    project_modules = [
        "src.app",
        "src.core.config",
        "src.core.telemetry",
        "src.core.confirm",
        "src.core.policy",
        "src.core.undo",
        "src.core.tasks.desktop",
        "src.core.tasks.engine",
        "src.ai.brain",
        "src.ai.intent_parser",
        "src.ai.providers.gemini_provider",
        "src.ai.providers.openrouter_provider",
        "src.memory.store",
        "src.memory.second_brain",
        "src.actions.executor",
        "src.actions.flow_engine",
        "src.actions.computer_use",
        "src.actions.app_actions",
        "src.actions.system_actions",
        "src.actions.media_actions",
        "src.actions.vision_actions",
        "src.actions.webcam_actions",
        "src.voice.listener",
        "src.network.bridge_server",
        "src.proactive.watcher",
        "src.proactive.briefing",
        "src.environment.iot_controller",
        "src.environment.peripherals",
    ]
    for name in project_modules:
        if not check_import(name, True):
            all_ok = False

    print("\n[5/6] Environment variables...")
    env_ok = True
    if not check_env_var("GEMINI_API_KEY", critical=False):
        env_ok = False
    if not check_env_var("OPENROUTER_API_KEY", critical=False):
        env_ok = False
    if not env_ok:
        print("  -> Set GEMINI_API_KEY and/or OPENROUTER_API_KEY for cloud features")

    print("\n[6/6] Critical files...")
    files_ok = True
    critical_files = [
        PROJECT_ROOT / "config.json",
        PROJECT_ROOT / "ui" / "index.html",
        PROJECT_ROOT / "ui" / "js" / "aether_ui.js",
        PROJECT_ROOT / "ui" / "js" / "singularity.js",
        PROJECT_ROOT / "ui" / "css" / "aether.css",
        PROJECT_ROOT / "run.bat",
    ]
    for f in critical_files:
        if not check_file(f, True):
            files_ok = False
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("  [OK] ALL CRITICAL CHECKS PASSED - Ready for demo")
    else:
        print("  [FAIL] SOME CRITICAL CHECKS FAILED - Fix before demo")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())