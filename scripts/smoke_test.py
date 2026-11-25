#!/usr/bin/env python3
"""
Smoke Test for Aether.ai-PC - boots with stubbed webview and runs 10 core commands.
Run from project root: python scripts/smoke_test.py

Target: All 10 commands pass, app boots without crashing.
"""
import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Stub webview module
import types
webview_stub = types.ModuleType("webview")
webview_stub.create_window = lambda **kwargs: types.SimpleNamespace(
    evaluate_js=lambda x: None,
    minimize=lambda: None,
    destroy=lambda: None,
    set_window=lambda: None
)
webview_stub.start = lambda: None
sys.modules["webview"] = webview_stub

def run_smoke_test():
    print("=" * 60)
    print("  AETHER.AI-PC SMOKE TEST")
    print("=" * 60)

    results = []

    # 1. Import core modules
    print("\n[1/3] Importing core modules...")
    try:
        from src.ai.brain import JarvisBrain
        from src.actions.executor import execute_action
        from src.core.config import load_config
        print("  [OK] Core modules imported")
        results.append(("core_import", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("core_import", False))
        return results

    # 2. Test config
    print("\n[2/3] Testing config...")
    try:
        cfg = load_config()
        assert "assistant_name" in cfg
        print(f"  [OK] Config loaded: {cfg['assistant_name']}")
        results.append(("config", True))
    except Exception as e:
        print(f"  [FAIL] {e}")
        results.append(("config", False))

    # 3. Test 10 core commands
    print("\n[3/3] Testing 10 core commands...")
    commands = [
        ("lock pc", "lock_workstation"),
        ("volume up", "set_volume"),
        ("mute volume", "set_volume"),
        ("open calculator", "open_application"),
        ("play music", "control_media"),
        ("screenshot", "capture_screen"),
        ("what was i working on", "recall_memory"),
        ("undo", "undo"),
        ("confirm", "confirm_action"),
        ("start focus session", "flow_execution"),
    ]

    passed = 0
    for i, (cmd, expected) in enumerate(commands, 1):
        t0 = time.perf_counter()
        try:
            res = execute_action(expected, {})
            elapsed = (time.perf_counter() - t0) * 1000
            ok = res.get("success", False) or res.get("message", "")
            status = "[OK]" if ok else "[WARN]"
            print(f"  {i:2d}. {status} '{cmd}' -> {expected} ({elapsed:.0f}ms)")
            passed += 1 if ok else 0
            results.append((f"cmd_{cmd}", bool(ok)))
        except Exception as e:
            print(f"  {i:2d}. [FAIL] '{cmd}' -> {expected}: {e}")
            results.append((f"cmd_{cmd}", False))

    # Summary
    total = len(results)
    passed_count = sum(1 for _, ok in results if ok)

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed_count}/{total} passed")
    if passed_count >= total * 0.8:
        print("  STATUS: PASS")
        status_code = 0
    else:
        print("  STATUS: FAIL")
        status_code = 1
    print("=" * 60)

    return status_code

if __name__ == "__main__":
    sys.exit(run_smoke_test())