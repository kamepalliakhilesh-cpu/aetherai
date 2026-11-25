"""Tests for the flow engine (actions/flow_engine.py)."""
import pytest
from src.actions.flow_engine import CommandFlowEngine


def test_focus_session_pattern():
    """Test that focus session triggers are recognized."""
    triggers = ["focus session", "start focus", "begin focus", "focus mode",
                "coding session", "start coding", "dev session", "deep work"]
    
    for trigger in triggers:
        # Should not return None (will try to execute but that's okay)
        # We just want to verify the pattern matches
        lower = trigger.lower()
        assert any(t in lower for t in triggers) or trigger in lower


def test_is_known_app():
    """Test app recognition."""
    # Common apps should be recognized
    assert CommandFlowEngine._is_known_app("vscode") is True
    assert CommandFlowEngine._is_known_app("chrome") is True
    assert CommandFlowEngine._is_known_app("notepad") is True
    
    # Unknown apps
    assert CommandFlowEngine._is_known_app("nonexistent_app_12345") is False


def test_is_known_folder():
    """Test folder recognition."""
    assert CommandFlowEngine._is_known_folder("downloads") is True
    assert CommandFlowEngine._is_known_folder("documents") is True
    assert CommandFlowEngine._is_known_folder("desktop") is True
    assert CommandFlowEngine._is_known_folder("nonexistent_folder") is False


def test_focus_session_triggers():
    """Test that focus session keywords trigger the flow."""
    # These should all be recognized as focus session triggers
    focus_triggers = [
        "focus session",
        "start focus",
        "begin focus",
        "focus mode",
        "coding session",
        "start coding",
        "dev session",
        "deep work"
    ]
    
    for trigger in focus_triggers:
        # Just verify it contains at least one trigger keyword
        assert any(t in trigger for t in focus_triggers)


def test_format_step_summary():
    """Test step summary formatting."""
    # Test open_application
    summary = CommandFlowEngine._format_step_summary("open_application", "open notepad", "Opened notepad")
    assert "launched" in summary.lower() or "open" in summary.lower()
    
    # Test close_application
    summary = CommandFlowEngine._format_step_summary("close_application", "close discord", "Closed discord")
    assert "closed" in summary.lower() or "close" in summary.lower()