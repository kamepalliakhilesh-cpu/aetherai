#!/usr/bin/env python3
"""
Non-Destructive Demo Harness for Aether.ai-PC
Shows what commands would do WITHOUT actually executing them.
Safe for live demos - no side effects.

Run from project root: python scripts/demo_harness.py
"""
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Demo commands that are safe to show
SAFE_DEMO_COMMANDS = [
    ("what was i working on", "recall_memory", "Memory", "Queries Second Brain for recent work sessions"),
    ("remember i like coffee", "save_memory_fact", "Memory", "Saves a preference to long-term memory"),
    ("undo", "undo", "Safety", "Reverses the last reversible action"),
    ("confirm", "confirm_action", "Safety", "Resolves a pending confirmation"),
    ("briefing", "briefing", "Briefing", "Generates situational briefing"),
    ("headphones", "get_peripherals", "Hardware", "Checks audio output routing"),
    ("wifi status", "get_peripherals", "Network", "Checks Wi-Fi connection"),
    ("desk lamp on", "toggle_desk_lamp", "Lighting", "Controls desk lamp (simulated IoT)"),
    ("set lights to solaris", "set_ambient_lighting", "Lighting", "Sets ambient lighting color (simulated)"),
    ("extend display", "switch_display", "Display", "Switches display mode"),
    ("tell me a joke", "joke", "Personality", "A little humor"),
    ("what time is it", "time", "Utility", "Current time"),
    ("who are you", "identity", "Identity", "Assistant introduction"),
]

# Commands that are DESTRUCTIVE and should NEVER be run during demo
DESTRUCTIVE_COMMANDS = [
    ("lock pc", "lock_workstation", "Would lock the screen"),
    ("sleep pc", "sleep_pc", "Would put PC to sleep"),
    ("empty recycle bin", "empty_recycle_bin", "Would permanently delete files"),
    ("volume up", "set_volume", "Changes system volume"),
    ("mute volume", "set_volume", "Mutes audio"),
]

def print_header():
    print("=" * 70)
    print("  AETHER.AI // DEMO HARNESS (NON-DESTRUCTIVE)")
    print("=" * 70)
    print()
    print("  This harness shows what commands WOULD do without executing them.")
    print("  Use this during live demos to show capabilities safely.")
    print()

def print_safe_commands():
    print("-" * 70)
    print("  SAFE COMMANDS (can be demonstrated)")
    print("-" * 70)
    print()
    
    for i, (cmd, action, category, desc) in enumerate(SAFE_DEMO_COMMANDS, 1):
        print(f"  {i:2d}. [{category:10s}] \"{cmd}\"")
        print(f"      -> {action}: {desc}")
        print()

def print_destructive_commands():
    print("-" * 70)
    print("  DESTRUCTIVE COMMANDS (DO NOT RUN DURING DEMO)")
    print("-" * 70)
    print()
    
    for i, (cmd, action, warning) in enumerate(DESTRUCTIVE_COMMANDS, 1):
        print(f"  {i:2d}. \"{cmd}\"")
        print(f"      -> {action}: {warning}")
        print()
    
    print("  WARNING: These commands have real side effects and should be avoided.")
    print("  Use voice/text input instead of direct execution for these.")
    print()

def print_demo_sequence():
    print("-" * 70)
    print("  RECOMMENDED DEMO SEQUENCE (90 seconds)")
    print("-" * 70)
    print()
    print("  1. [0:00-0:15] Voice: \"Aether, what was I working on?\"")
    print("     -> Shows memory recall working offline")
    print()
    print("  2. [0:15-0:30] Voice: \"Aether, remember I prefer dark mode\"")
    print("     -> Shows fact extraction and storage")
    print()
    print("  3. [0:30-0:45] Click 'Focus Session' chip or say \"start focus\"")
    print("     -> Shows multi-app orchestration (DISPLAY ONLY - apps may not exist)")
    print()
    print("  4. [0:45-1:00] Say \"undo\"")
    print("     -> Shows undo capability (volume only if focus session ran)")
    print()
    print("  5. [1:00-1:30] Show 3D orb reacting to voice")
    print("     -> Visual centerpiece")
    print()
    print("  6. [1:30-2:00] Explain architecture (local-first, FTS5 memory, safety)")
    print()
    print("  7. [2:00-3:00] Q&A or show mobile bridge setup screen")
    print()

def main():
    print_header()
    print_safe_commands()
    print_destructive_commands()
    print_demo_sequence()
    
    print("=" * 70)
    print("  DEMO READY")
    print("=" * 70)
    print()
    print("  Remember:")
    print("  - Use voice for commands you want to actually execute")
    print("  - Use this harness to SHOW capabilities without side effects")
    print("  - Never run scripts/eval_commands.py during a live demo")
    print()

if __name__ == "__main__":
    main()