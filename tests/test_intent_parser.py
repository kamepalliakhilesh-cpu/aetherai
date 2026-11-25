"""Tests for the intent parser (ai/intent_parser.py)."""
import pytest
from src.ai.intent_parser import LocalIntentParser


def test_parse_time():
    """Test time query."""
    res = LocalIntentParser.parse("what time is it")
    
    assert res.get("action") == "time"
    assert "time" in res.get("reply", "").lower()


def test_parse_date():
    """Test date query."""
    res = LocalIntentParser.parse("what is the date")
    
    assert res.get("action") == "date"
    assert "today" in res.get("reply", "").lower() or "date" in res.get("reply", "").lower()


def test_parse_greeting():
    """Test greeting."""
    res = LocalIntentParser.parse("hello")
    
    assert res.get("action") == "salutation"
    assert "online" in res.get("reply", "").lower() or "standing" in res.get("reply", "").lower()


def test_parse_joke():
    """Test joke request."""
    res = LocalIntentParser.parse("tell me a joke")
    
    assert res.get("action") == "joke"
    assert len(res.get("reply", "")) > 10


def test_parse_help():
    """Test help request."""
    res = LocalIntentParser.parse("help")
    
    assert res.get("action") == "help"
    assert "can" in res.get("reply", "").lower() or "assist" in res.get("reply", "").lower()


def test_parse_identity():
    """Test identity question."""
    res = LocalIntentParser.parse("who are you")
    
    assert res.get("action") == "identity"
    assert "aether" in res.get("reply", "").lower()


def test_parse_thanks():
    """Test thanks."""
    res = LocalIntentParser.parse("thank you")
    
    assert res.get("action") == "thanks"
    assert "pleasure" in res.get("reply", "").lower() or "service" in res.get("reply", "").lower()


def test_parse_volume_up():
    """Test volume up (should not crash)."""
    res = LocalIntentParser.parse("volume up")
    
    # Volume actions return set_volume
    assert res.get("action") in ["set_volume", None]
    assert res.get("reply") is not None


def test_parse_volume_down():
    """Test volume down."""
    res = LocalIntentParser.parse("volume down")
    
    assert res.get("action") in ["set_volume", None]


def test_parse_mute():
    """Test mute."""
    res = LocalIntentParser.parse("mute volume")
    
    assert res.get("action") in ["set_volume", None]


def test_parse_lock_pc():
    """Test lock pc (should not crash)."""
    res = LocalIntentParser.parse("lock pc")
    
    assert res.get("action") in ["lock_workstation", None]


def test_parse_sleep_pc():
    """Test sleep pc (should not crash)."""
    res = LocalIntentParser.parse("sleep pc")
    
    assert res.get("action") in ["sleep_pc", None]


def test_parse_undo():
    """Test undo."""
    res = LocalIntentParser.parse("undo")
    
    assert res.get("action") == "undo"
    assert "reversed" in res.get("reply", "").lower() or "no actions" in res.get("reply", "").lower()


def test_parse_confirm():
    """Test confirm."""
    res = LocalIntentParser.parse("confirm")
    
    assert res.get("action") == "confirm_action"


def test_parse_unknown():
    """Test unknown command."""
    res = LocalIntentParser.parse("asdf qwerty zxcv")
    
    # Should return None action with fallback reply
    assert res.get("action") is None
    assert "acknowledged" in res.get("reply", "").lower() or "directive" in res.get("reply", "").lower()