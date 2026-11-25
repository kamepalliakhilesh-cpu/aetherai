#!/usr/bin/env python3
"""
Demo mode seed + orb state test.
Run from project root: python scripts/demo_prep.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

# Set up paths like the app does
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Also change to src directory for relative imports to work
import os
os.chdir(str(SRC_ROOT))

def seed_demo_memory():
    print("Seeding demo memory...")
    try:
        from memory.second_brain import SecondBrain
        sb = SecondBrain()
        
        # Focus session preferences
        sb.store.save_fact("preferences", "focus_session", "User prefers VS Code + quiet environment for focus sessions. Last used 2024-11-20.")
        sb.store.save_fact("preferences", "coding", "Currently working on Aether.ai-PC: autonomous Windows assistant with local-first architecture.")
        sb.store.save_fact("preferences", "music", "Prefers lo-fi beats while coding. Last playlist: 'Chillhop Essentials'.")
        
        # Project context
        sb.store.save_fact("project", "aether_pc", "Aether.ai-PC: Local-first voice assistant with memory, automation, and mobile bridge. Target: hackathon demo.")
        sb.store.save_fact("project", "aether_pc", "Key features: deterministic intent parser, SQLite FTS5 memory, Windows UIA automation, Three.js 3D UI.")
        
        # Recent work session
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        sb.store.save_fact("session", "focus_2024_11_20", f"Focus session on {yesterday}: Closed Discord, Spotify, Slack. Opened VS Code on Aether.ai-PC. Duration: 2h 15m. Commits: 3. Files modified: 5.")
        
        # Verify
        facts = sb.store.search_facts("focus_session OR coding OR work", limit=10)
        print(f"  [OK] Seeded {len(facts)} demo facts")
        for f in facts[:3]:
            print(f"    - {f.get('category', '')}/{f.get('entity', '')}: {f.get('content', '')[:80]}...")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False

def test_orb_states():
    print("\nTesting orb state constants...")
    states = ['idle', 'listening', 'thinking', 'speaking', 'error']
    print(f"  States: {states}")
    return True

def test_undo():
    print("\nTesting undo stack...")
    try:
        from core.undo import push_undo, undo_last, history
        
        push_undo("test_focus_session", "Focus session started - apps closed, VS Code launched, volume adjusted")
        stack = history()
        print(f"  [OK] Undo stack size: {len(stack)}")
        
        msg = undo_last()
        print(f"  [OK] Undo message: {msg}")
        
        stack = history()
        print(f"  [OK] Undo stack after pop: {len(stack)}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False

def test_confirm():
    print("\nTesting confirm system...")
    try:
        from core.confirm import request_and_wait
        print(f"  [OK] request_and_wait imported")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False

def test_flow_engine():
    print("\nTesting FlowEngine focus session...")
    try:
        # Import the same way app.py does
        from src.actions.flow_engine import CommandFlowEngine
        
        def dummy_parser(text):
            return {"action": "open_application", "args": {"app_name": "notepad"}, "reply": "Opened notepad"}
        
        res = CommandFlowEngine.try_execute_flow("start focus session", dummy_parser)
        if res and res.get("action") == "flow_execution":
            print(f"  [OK] Focus session flow triggered")
            print(f"    Steps: {res.get('steps', [])}")
            return True
        else:
            print(f"  [FAIL] No flow matched")
            return False
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False

def test_intent_parser():
    print("\nTesting IntentParser 'what was I working on'...")
    try:
        # Import the same way app.py does
        from src.ai.intent_parser import LocalIntentParser
        
        res = LocalIntentParser.parse("what was i working on")
        action = res.get("action")
        reply = res.get("reply", "")
        print(f"  [OK] Action: {action}")
        print(f"    Reply: {reply[:100]}...")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("  DEMO PREPARATION & VERIFICATION")
    print("=" * 60)
    
    results = []
    results.append(seed_demo_memory())
    results.append(test_orb_states())
    results.append(test_undo())
    results.append(test_confirm())
    results.append(test_flow_engine())
    results.append(test_intent_parser())
    
    print("\n" + "=" * 60)
    if all(results):
        print("  ALL DEMO PREP PASSED - Ready for live demo!")
    else:
        print("  SOME PREP FAILED - Fix before demo")
    print("=" * 60)
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())