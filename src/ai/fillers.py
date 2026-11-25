"""
Aether Conversational Fillers & Latency Bridge.
Ported & adapted from J.A.R.V.I.S. (jarvis-main) fillers.ts

Provides immediate spoken acoustic feedback the instant a query or tool starts,
eliminating awkward dead silence while the model plans and executes.
"""

import random
from typing import Optional

# Working lines: spoken immediately when a tool/action or heavy query starts
WORKING_FILLERS = [
    "Working on it, sir.",
    "Compiling.",
    "Retrieving.",
    "Accessing the archive.",
    "Cross-referencing.",
    "Running the query now.",
    "Searching.",
    "Under way.",
]

# Acknowledge lines: spoken when taking a directive
ACKNOWLEDGE_FILLERS = [
    "As you wish, sir.",
    "Very good, sir.",
    "Certainly.",
    "Understood.",
    "Consider it done.",
    "Directly, sir.",
]

# Attention lines: spoken on wake/intercept before command is given
ATTENTION_FILLERS = [
    "Yes, sir?",
    "Sir?",
    "At your service, sir.",
    "Standing by, sir.",
]

# Optical / Vision lines: spoken when screen or camera analysis begins
VISION_FILLERS = [
    "Scanning visual field.",
    "Analyzing optical feed.",
    "Examining display.",
    "Processing visual stream.",
]

def get_working_filler(query: Optional[str] = None) -> str:
    """Returns a context-appropriate filler string to speak immediately"""
    q = (query or "").lower()
    if any(k in q for k in ["look", "see", "screen", "camera", "photo", "watch"]):
        return random.choice(VISION_FILLERS)
    if any(k in q for k in ["search", "find", "who is", "what is", "lookup", "google"]):
        return random.choice(["Searching.", "Running the query now.", "Cross-referencing.", "Accessing archives."])
    if any(k in q for k in ["code", "run", "diagnostic", "syntax", "compile"]):
        return random.choice(["Compiling.", "Cross-referencing.", "Running diagnostics."])
    return random.choice(WORKING_FILLERS)

def get_attention_filler() -> str:
    return random.choice(ATTENTION_FILLERS)
