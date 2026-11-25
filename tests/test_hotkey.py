"""Tests for push-to-talk hotkey (core/hotkey.py)."""
import pytest
from src.core.hotkey import PushToTalk, chord_label, qt_sequence, DEFAULT_CHORD


def test_chord_label_default():
    label = chord_label()
    assert "Ctrl" in label
    assert "Space" in label


def test_chord_label_custom():
    label = chord_label(("alt", "space"))
    assert "Alt" in label
    assert "Space" in label


def test_qt_sequence():
    seq = qt_sequence(("ctrl", "shift", "space"))
    assert seq == "Ctrl+Shift+Space"


def test_push_to_talk_init():
    events = []
    ptt = PushToTalk(on_change=lambda held: events.append(held), chord=("alt", "space"))
    assert ptt.held is False
    assert "Alt" in ptt.label


def test_push_to_talk_set_held():
    events = []
    ptt = PushToTalk(on_change=lambda held: events.append(held), chord=("alt", "space"))
    ptt.set_held(True)
    assert ptt.held is True
    assert events == [True]
    ptt.set_held(True)  # idempotent
    assert events == [True]
    ptt.set_held(False)
    assert ptt.held is False
    assert events == [True, False]


def test_push_to_talk_lifecycle():
    ptt = PushToTalk(on_change=lambda held: None, chord=("alt", "space"))
    scope = ptt.start()
    assert scope in ("global", "window")
    ptt.stop()
    assert ptt.held is False
