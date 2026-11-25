# Aether.ai-PC Hackathon Demo Script (3 minutes)
#
# This script walks through the golden path demo for judges.
# Total time: ~3 minutes
#
# ─────────────────────────────────────────────────────────────────────────────
# BEFORE YOU START:
#   1. Close Discord, Spotify, Slack (they'll be closed by the demo anyway)
#   2. Have VS Code closed but ready to open
#   3. Make sure voice is working (say "wake up" to test)
#   4. Have your phone paired with the mobile bridge (or skip phone section)
#   5. Have a backup video ready in data/demo_backup.mp4
# ─────────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# ACT 1: THE PROBLEM (30 seconds)
# ═══════════════════════════════════════════════════════════════════════════════
#
# "Every day, we switch between 10+ apps, lose focus, and waste time.
#  What if your computer could understand what you're trying to do
#  and just... do it?"
#
# Show the 3D Solaris orb pulsing in idle state.
# Click the orb once to show it responds to touch.

# ═══════════════════════════════════════════════════════════════════════════════
# ACT 2: THE GOLDEN PATH - FOCUS SESSION (90 seconds)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Say: "Aether, start focus session"
#
# Expected flow:
#   1. Aether closes Discord, Spotify, Slack (distractions)
#   2. Opens VS Code
#   3. Opens project folder
#   4. Sets volume to ~50%
#   5. Saves preference to memory
#   6. Shows undo option
#
# Narrate: "Watch - it's not just opening apps. It's understanding intent.
#  It closed my distractions, opened my tools, set the right volume,
#  and saved my preference so it learns over time."
#
# Then say: "Aether, what was I working on?"
#
# Expected: Aether recalls from memory - shows recent session, preferences, project context.
# Narrate: "This is the Second Brain - it remembers context across sessions."

# ═══════════════════════════════════════════════════════════════════════════════
# ACT 3: SAFETY & CONTROL (30 seconds)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Say: "Aether, undo"
#
# Expected: Restores previous state (reopens closed apps, restores volume)
# Narrate: "Every action is reversible. One command to undo."
#
# Say: "Aether, lock my PC"
# (or use phone to trigger lock with hardware confirmation)
#
# Expected: PC locks immediately
# Narrate: "And for destructive actions, there's a hardware confirmation gate.
#  The AI can't authorize itself - only you can, via the UI."
#
# If using phone: Show mobile bridge pairing code (QR code in UI),
# trigger "lock" from phone, show the confirmation modal appearing on PC.

# ═══════════════════════════════════════════════════════════════════════════════
# ACT 4: THE ARCHITECTURE (30 seconds)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Point to the architecture (use a slide or draw on whiteboard):
#
#   Voice Input → Local Intent Parser (<2ms, offline)
#                     ↓ (if no match)
#   Memory (SQLite FTS5 BM25) → Second Brain
#                     ↓ (if no match)
#   Gemini / OpenRouter → Action Registry (50+ tools)
#                     ↓
#   Windows: UIA automation, SendInput, display, audio, peripherals
#
# Narrate: "Local-first architecture. 80% of commands handled offline
#  in under 2ms. Cloud AI only when needed. SQLite FTS5 memory that
#  actually works offline. 50+ Windows actions - not just web search."

# ═══════════════════════════════════════════════════════════════════════════════
# ACT 5: CLOSE (30 seconds)
# ═══════════════════════════════════════════════════════════════════════════════
#
# "This is Aether.ai-PC. A local-first, privacy-focused assistant that
#  actually controls your Windows machine. Not a chatbot - an OS.
#
#  Built with: Python, pywebview, Three.js, SQLite FTS5, Windows UIA.
#  Voice: VAD + RMS + barge-in. Memory: Second Brain with fact extraction.
#  Safety: SSRF guard, hardware confirm gate, LIFO undo stack.
#
#  Everything runs locally. Your data stays yours."
#
# Demo backup: If anything fails, play data/demo_backup.mp4 and say:
# "Here's a pre-recorded demo while we fix the live connection."
#
# ═══════════════════════════════════════════════════════════════════════════════