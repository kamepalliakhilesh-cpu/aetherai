#!/usr/bin/env python3
"""
25-Command Evaluation Sheet for Aether.ai-PC Demo
Run from project root: python scripts/eval_commands.py

Measures: command, expected action, pass/fail, latency (ms)
Target: 90%+ success, <2s local responses
"""
import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# 25 demo commands covering all key features
DEMO_COMMANDS = [
    # Voice & System Control (5)
    ("lock pc", "lock_workstation", "Security"),
    ("volume up", "set_volume", "Audio"),
    ("mute volume", "set_volume", "Audio"),
    ("screenshot", "capture_screen", "Vision"),
    ("sleep pc", "sleep_pc", "Power"),
    
    # App & Media (5)
    ("open calculator", "open_application", "Apps"),
    ("close notepad", "close_application", "Apps"),
    ("play music", "control_media", "Media"),
    ("next song", "control_media", "Media"),
    ("open youtube", "open_url", "Web"),
    
    # Memory & Second Brain (5)
    ("what was i working on", "recall_memory", "Memory"),
    ("remember i like coffee", "save_memory_fact", "Memory"),
    ("undo", "undo", "Safety"),
    ("confirm", "confirm_action", "Safety"),
    ("briefing", "briefing", "Briefing"),
    
    # Focus Session Golden Path (5)
    ("start focus session", "flow_execution", "Flow"),
    ("focus mode", "flow_execution", "Flow"),
    ("start coding", "flow_execution", "Flow"),
    ("deep work", "flow_execution", "Flow"),
    ("dev session", "flow_execution", "Flow"),
    
    # Peripheral & Environment (5)
    ("headphones", "get_peripherals", "Hardware"),
    ("wifi status", "get_peripherals", "Network"),
    ("desk lamp on", "toggle_desk_lamp", "Lighting"),
    ("set lights to solaris", "set_ambient_lighting", "Lighting"),
    ("extend display", "switch_display", "Display"),
]

def run_evaluation():
    print("=" * 60)
    print("  25-COMMAND EVALUATION SHEET")
    print("=" * 60)
    
    try:
        from src.ai.intent_parser import LocalIntentParser
        
        results = []
        total_time = 0
        
        for i, (cmd, expected, category) in enumerate(DEMO_COMMANDS, 1):
            t0 = time.perf_counter()
            try:
                res = LocalIntentParser.parse(cmd)
                elapsed = (time.perf_counter() - t0) * 1000
                action = res.get("action", "none")
                reply = res.get("reply", "")[:50]
                
                # Determine pass/fail
                passed = (
                    (action == expected) or
                    (action == "flow_execution" and expected == "flow_execution") or
                    (action == "get_peripherals" and expected == "get_peripherals") or
                    (action == "set_volume" and expected == "set_volume") or
                    (action == "control_media" and expected == "control_media")
                )
                
                results.append({
                    "cmd": cmd,
                    "expected": expected,
                    "actual": action,
                    "passed": passed,
                    "latency_ms": round(elapsed, 1),
                    "reply": reply
                })
                
                status = "PASS" if passed else "FAIL"
                color = "[OK]" if passed else "[FAIL]"
                print(f"{i:2d}. {color} {cmd:30s} -> {action:20s} ({elapsed:.0f}ms)")
                
            except Exception as e:
                results.append({
                    "cmd": cmd,
                    "expected": expected,
                    "actual": f"ERROR: {e}",
                    "passed": False,
                    "latency_ms": 0,
                    "reply": str(e)
                })
                print(f"{i:2d}. [FAIL] {cmd:30s} -> ERROR: {e}")
        
        # Summary
        total_time = sum(r["latency_ms"] for r in results)
        passed = sum(1 for r in results if r["passed"])
        avg_latency = total_time / len(results) if results else 0
        
        print("\n" + "=" * 60)
        print(f"  RESULTS: {passed}/{len(results)} passed ({passed/len(results)*100:.0f}%)")
        print(f"  Avg latency: {avg_latency:.1f}ms (target <2000ms)")
        print(f"  Total time: {total_time:.0f}ms")
        
        if passed >= 22:  # 88%+
            print("  STATUS: READY FOR DEMO")
            demo_ready = True
        else:
            print("  STATUS: NEEDS FIXES")
            demo_ready = False
        print("=" * 60)
        
        # Save results
        output_path = PROJECT_ROOT / "data" / "eval_results.json"
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({
                "passed": passed,
                "total": len(results),
                "avg_latency_ms": round(avg_latency, 1),
                "results": results,
                "demo_ready": demo_ready
            }, f, indent=2)
        
        print(f"\n  Results saved to: {output_path}")
        return 0 if demo_ready else 1
        
    except Exception as e:
        print(f"\n  FATAL: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_evaluation())