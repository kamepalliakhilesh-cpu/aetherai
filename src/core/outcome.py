"""
core/outcome.py — Verifiable 3-State Outcome Observation Contract.
Adopted from Mark-LVII architecture.

Enforces:
  • done: Action was observed to have succeeded (checked, not assumed).
  • unverified: Request dispatched, but state change could not be confirmed.
  • failed: Action did not happen, with human-readable reason.
  • started: Underway on a background worker.
  • ask: Clarification or user choice required.
"""
from __future__ import annotations

import re
from typing import Any

DONE = "done"
UNVERIFIED = "unverified"
FAILED = "failed"
ASK = "ask"
STARTED = "started"


def _render(value: Any) -> str:
    """Renders one fact value, quoted only when necessary."""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).replace('"', "'").replace("\n", " ").strip()
    return f'"{text}"' if (" " in text or not text) else text


def _line(status: str, action: str, facts: dict[str, Any]) -> str:
    parts = [f"status={status}", f"action={action}"]
    parts += [f"{k}={_render(v)}" for k, v in facts.items() if v is not None]
    return " ".join(parts)


def done(action: str, /, **facts: Any) -> str:
    """Action was executed and observed to have succeeded."""
    return _line(DONE, action, facts)


def unverified(action: str, reason: str, /, **facts: Any) -> str:
    """Action was requested, but state could not be confirmed."""
    return _line(UNVERIFIED, action, {**facts, "reason": reason}) + (
        " -- NOT confirmed. Tell the user plainly that you asked and cannot "
        "confirm it worked, and say what they can check. Do NOT say it is done."
    )


def failed(action: str, reason: str, /, **facts: Any) -> str:
    """Action failed with a human-readable cause."""
    return _line(FAILED, action, {**facts, "reason": reason}) + (
        " -- This did NOT happen. Tell the user so in their own language, with "
        "the reason. Do not claim any part of it succeeded."
    )


def started(action: str, /, **facts: Any) -> str:
    """Action is under way in a background worker."""
    return _line(STARTED, action, facts) + (
        " -- UNDER WAY, not finished. Say in one short sentence, in the user's "
        "own language, that it is starting now."
    )


def ask(action: str, question: str, /, **facts: Any) -> str:
    """Execution paused because input or confirmation is needed."""
    return _line(ASK, action, {**facts, "question": question})


def parse(line: str) -> dict[str, Any]:
    """Parses a machine-shaped status line back into a dictionary."""
    clean = re.split(r"\s+--\s+", line, maxsplit=1)[0].strip()
    out: dict[str, Any] = {}
    tokens = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', clean)
    for k, quoted, unquoted in tokens:
        val = quoted if quoted != "" else unquoted
        if val.lower() == "true":
            out[k] = True
        elif val.lower() == "false":
            out[k] = False
        else:
            out[k] = val
    return out
