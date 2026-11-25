"""
core/undo.py — Shared 10-turn LIFO reversible state stack.
Adopted from Mark-LVII architecture.

Enables safe, instant rollback for reversible operations:
  • Audio volume adjustments
  • Display & brightness settings
  • Moved / renamed files
  • Presets & lighting modes
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

MAX_DEPTH = 10


@dataclass
class _Entry:
    label: str
    undo: Callable[[], str]
    at: float = field(default_factory=time.monotonic)


_stack: list[_Entry] = []
_lock = threading.Lock()


def push_undo(label: str, undo_fn: Callable[[], str]) -> None:
    """Records that `label` was performed and `undo_fn()` reverses it."""
    if not callable(undo_fn):
        return
    try:
        with _lock:
            _stack.append(_Entry(label=str(label)[:120], undo=undo_fn))
            while len(_stack) > MAX_DEPTH:
                _stack.pop(0)
    except Exception as e:
        print(f"[Undo] Registration error: {e}")


def can_undo() -> bool:
    with _lock:
        return bool(_stack)


def peek() -> str:
    """Returns the label of the operation that undo_last() will reverse, or ''."""
    with _lock:
        return _stack[-1].label if _stack else ""


def history() -> list[str]:
    """Returns the history of reversible actions, newest first."""
    with _lock:
        return [e.label for e in reversed(_stack)]


def undo_last() -> str:
    """Reverses the most recent reversible action."""
    with _lock:
        entry = _stack.pop() if _stack else None

    if entry is None:
        return "There are no actions to undo, Sir."

    try:
        detail = entry.undo() or ""
    except Exception as e:
        return f"Could not undo '{entry.label}': {e}"

    return f"Reversed: {entry.label}." + (f" {detail}" if detail else "")


def clear() -> None:
    with _lock:
        _stack.clear()
