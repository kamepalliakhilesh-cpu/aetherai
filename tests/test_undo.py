"""Tests for the undo stack (core/undo.py)."""
import pytest
from src.core import undo


@pytest.fixture(autouse=True)
def reset_undo():
    """Clear undo stack before each test."""
    undo.clear()
    yield
    undo.clear()


def test_push_undo_with_callable():
    """Test that push_undo works with a callable."""
    undo.push_undo("test_action", lambda: "undone")
    
    assert undo.can_undo() is True
    assert undo.peek() == "test_action"


def test_push_undo_with_string_silently_ignored():
    """Test that push_undo silently ignores non-callable (regression test for bug)."""
    undo.push_undo("focus_session_started", "Focus session started - apps closed")
    
    # Should NOT be added to stack (this was the bug)
    assert undo.can_undo() is False


def test_undo_last():
    """Test undo_last reverses the most recent action."""
    undo.push_undo("action1", lambda: "undid 1")
    undo.push_undo("action2", lambda: "undid 2")
    
    result = undo.undo_last()
    
    assert "action2" in result
    assert "undid 2" in result
    assert undo.peek() == "action1"


def test_undo_empty():
    """Test undo_last on empty stack."""
    result = undo.undo_last()
    
    assert "no actions" in result.lower() or "nothing" in result.lower()


def test_undo_history():
    """Test history returns entries in LIFO order."""
    undo.push_undo("a", lambda: "x")
    undo.push_undo("b", lambda: "y")
    undo.push_undo("c", lambda: "z")
    
    hist = undo.history()
    
    assert hist == ["c", "b", "a"]


def test_max_depth():
    """Test that stack respects MAX_DEPTH."""
    for i in range(15):
        undo.push_undo(f"action{i}", lambda: "x")
    
    # Should only keep MAX_DEPTH (10) entries
    assert undo.can_undo() is True
    # The oldest entries should be dropped
    hist = undo.history()
    assert len(hist) <= 10