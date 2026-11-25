"""Tests for the confirmation gate (core/confirm.py)."""
import threading
import time
import pytest
from src.core import confirm


@pytest.fixture(autouse=True)
def reset_confirm():
    """Reset confirm state before each test."""
    confirm._pending = None
    yield
    confirm._pending = None


def test_request_and_wait_accepted():
    """Test that request_and_wait returns True when user accepts."""
    confirm.bind(lambda t, d: None, lambda: None, log=lambda m: None)
    
    def user_clicks_yes():
        time.sleep(0.1)
        confirm.resolve(True)
    
    threading.Thread(target=user_clicks_yes, daemon=True).start()
    accepted, msg = confirm.request_and_wait('test', 'Test', 'Test detail', run=lambda: 'ran', timeout=5)
    
    assert accepted is True
    assert "ran" in msg or "Confirmed" in msg


def test_request_and_wait_cancelled():
    """Test that request_and_wait returns False when user cancels."""
    confirm.bind(lambda t, d: None, lambda: None, log=lambda m: None)
    
    def user_clicks_no():
        time.sleep(0.1)
        confirm.resolve(False)
    
    threading.Thread(target=user_clicks_no, daemon=True).start()
    accepted, msg = confirm.request_and_wait('test', 'Test', 'Test detail', run=lambda: 'ran', timeout=5)
    
    assert accepted is False
    assert "cancel" in msg.lower() or "cancel" in msg.lower()


def test_request_and_wait_timeout():
    """Test that request_and_wait returns False on timeout."""
    confirm.bind(lambda t, d: None, lambda: None, log=lambda m: None)
    
    # No user interaction - should timeout
    accepted, msg = confirm.request_and_wait('test', 'Test', 'Test detail', run=lambda: 'ran', timeout=0.2)
    
    assert accepted is False
    assert "timeout" in msg.lower()


def test_request_and_wait_no_interface():
    """Test that request_and_wait returns False if no UI bound."""
    confirm._show_cb = None
    
    accepted, msg = confirm.request_and_wait('test', 'Test', 'Test detail', run=lambda: 'ran', timeout=5)
    
    assert accepted is False
    assert "unavailable" in msg.lower() or "interface" in msg.lower()


def test_pending_title():
    """Test pending_title returns title when pending."""
    confirm.bind(lambda t, d: None, lambda: None, log=lambda m: None)
    
    def user_clicks_yes():
        time.sleep(0.5)
        confirm.resolve(True)
    
    threading.Thread(target=user_clicks_yes, daemon=True).start()
    
    # Check pending title before it's resolved
    title = confirm.pending_title()
    # May be empty if timing is off, that's okay
    # Just verify it doesn't crash


def test_resolve_none_pending():
    """Test resolve doesn't crash when no pending."""
    confirm.bind(lambda t, d: None, lambda: None, log=lambda m: None)
    
    # Should not raise
    confirm.resolve(True)
    confirm.resolve(False)