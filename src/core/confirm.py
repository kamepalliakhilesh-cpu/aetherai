"""
core/confirm.py — Unforgeable hardware-level confirmation gate.
Adopted from Mark-LVII architecture.

Guarantees:
  • Destructive actions (reboot, shutdown, partition wipe) park behind a physical UI token.
  • The LLM cannot authorize itself via tool parameters (e.g. confirmed=True).
  • Confirmation token is issued exclusively by the UI (WebView2 banner).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

TIMEOUT_SECONDS = 90.0


@dataclass
class _Pending:
    key: str
    title: str
    detail: str
    run: Callable[[], str]
    at: float
    event: threading.Event = None
    accepted: Optional[bool] = None


_pending: Optional[_Pending] = None
_lock = threading.Lock()

_show_cb: Optional[Callable[[str, str], None]] = None
_hide_cb: Optional[Callable[[], None]] = None
_log_cb: Optional[Callable[[str], None]] = None


def bind(show, hide, log=None) -> None:
    """Binds UI callbacks for confirmation dialogs."""
    global _show_cb, _hide_cb, _log_cb
    _show_cb, _hide_cb, _log_cb = show, hide, log


def _log(msg: str) -> None:
    if _log_cb:
        try:
            _log_cb(msg)
        except Exception:
            pass


def request(key: str, title: str, detail: str, run: Callable[[], str]) -> str:
    """Parks an irreversible action behind the UI confirmation gate."""
    global _pending

    if _show_cb is None:
        return f"Unable to confirm '{title}' as interface is currently unavailable, Sir."

    with _lock:
        _pending = _Pending(key=key, title=title, detail=detail, run=run, at=time.monotonic(), event=threading.Event())

    try:
        _show_cb(title, detail)
    except Exception as e:
        with _lock:
            _pending = None
        return f"Confirmation display error: {e}. Action was aborted."

    _log(f"SYS: Awaiting physical confirmation — {title}")
    return (
        f"[CONFIRMATION_PENDING] Physical confirmation requested on the HUD for: '{title}'. "
        f"Ask the user to click Confirm on the display before proceeding, Sir."
    )


def request_and_wait(key: str, title: str, detail: str, run: Callable[[], str], timeout: float = TIMEOUT_SECONDS) -> tuple[bool, str]:
    """Parks an action behind the UI confirmation gate and waits for user response.
    Returns (accepted, message). Blocks until user responds or timeout."""
    global _pending

    if _show_cb is None:
        return False, f"Unable to confirm '{title}' as interface is currently unavailable, Sir."

    event = threading.Event()
    with _lock:
        pending = _Pending(key=key, title=title, detail=detail, run=run, at=time.monotonic(), event=event)
        _pending = pending

    try:
        _show_cb(title, detail)
    except Exception as e:
        with _lock:
            _pending = None
        return False, f"Confirmation display error: {e}. Action was aborted."

    _log(f"SYS: Awaiting physical confirmation — {title}")
    
    # Wait for user response
    if event.wait(timeout=timeout):
        accepted = pending.accepted if pending else False
        msg = "Confirmed and executed." if accepted else "User cancelled."
    else:
        # Timeout
        with _lock:
            if _pending is pending:
                _pending = None
        if _hide_cb:
            try:
                _hide_cb()
            except Exception:
                pass
        _log(f"SYS: Confirmation timed out — {title}")
        return False, "Confirmation timeout: timed out waiting for user response."

    # Run the action synchronously before returning (so reply reflects actual result)
    if accepted:
        try:
            result = pending.run() or "Executed successfully."
            _log(f"SYS: Confirmed and completed — {title}. {result}")
            msg = result
        except Exception as e:
            _log(f"ERR: {title} execution error — {e}")
            msg = f"Execution failed: {e}"

    return accepted, msg


def resolve(accepted: bool) -> None:
    """Called when the user clicks Confirm or Cancel on the UI."""
    global _pending

    with _lock:
        p = _pending
        _pending = None

    if _hide_cb:
        try:
            _hide_cb()
        except Exception:
            pass

    if p is None:
        return

    if time.monotonic() - p.at > TIMEOUT_SECONDS:
        _log(f"SYS: Confirmation timed out — {p.title}")
        return

    if p.event:
        p.accepted = accepted
        p.event.set()

    if not accepted:
        _log(f"SYS: User cancelled — {p.title}")


def pending_title() -> str:
    with _lock:
        if _pending is None or (time.monotonic() - _pending.at > TIMEOUT_SECONDS):
            return ""
        return _pending.title
