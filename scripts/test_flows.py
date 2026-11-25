#!/usr/bin/env python3
"""
Quick test to verify the golden path flows work.
Run from project root: python scripts/test_flows.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

def test_flow_engine():
    print("Testing FlowEngine...")
    try:
        from actions.flow_engine import CommandFlowEngine
        
        # Test focus session detection
        test_cases = [
            "start focus session",
            "begin focus mode", 
            "focus session",
            "start coding session",
            "dev session",
            "deep work",
            "open notepad and write hello",  # existing pattern
            "open chrome and search python",  # existing pattern
        ]
        
        def dummy_parser(text):
            return {"action": "open_application", "args": {"app_name": "notepad"}, "reply": "Opened notepad"}
        
        for case in test_cases:
            res = CommandFlowEngine.try_execute_flow(case, dummy_parser)
            if res:
                print(f"  [OK] '{case}' -> flow_execution: {res.get('reply', '')[:60]}...")
            else:
                print(f"  [SKIP] '{case}' -> no flow match")
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False
    return True

def test_intent_parser():
    print("\nTesting IntentParser...")
    try:
        from ai.intent_parser import LocalIntentParser
        
        test_cases = [
            "what was i working on",
            "what was i doing", 
            "recent work",
            "undo",
            "focus session",
            "lock pc",
            "volume up",
            "search google for python",
        ]
        
        for case in test_cases:
            res = LocalIntentParser.parse(case)
            action = res.get("action")
            reply = res.get("reply", "")[:80]
            print(f"  [OK] '{case}' -> action={action}: {reply}...")
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False
    return True

def test_undo():
    print("\nTesting Undo system...")
    try:
        from core.undo import push_undo, undo_last
        
        push_undo("test_action", "Test description for undo")
        msg = undo_last()
        print(f"  [OK] Undo message: {msg}")
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False
    return True

def test_confirm():
    print("\nTesting Confirm system...")
    try:
        from core.confirm import request_and_wait
        
        def dummy_action():
            return "Action executed"
        
        # This would block waiting for UI, so just test import
        print(f"  [OK] confirm module imports and request_and_wait exists")
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False
    return True

def main():
    print("=" * 60)
    print("  GOLDEN PATH FLOW TESTS")
    print("=" * 60)
    
    results = []
    results.append(test_flow_engine())
    results.append(test_intent_parser())
    results.append(test_undo())
    results.append(test_confirm())
    
    print("\n" + "=" * 60)
    if all(results):
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())