"""Tests for non-destructive demo harness (scripts/demo_harness.py)."""
import sys
from pathlib import Path
import pytest

# Ensure scripts directory is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import demo_harness


def test_harness_command_lists():
    """Verify safe and destructive lists are defined and well-structured."""
    assert len(demo_harness.SAFE_DEMO_COMMANDS) >= 10
    assert len(demo_harness.DESTRUCTIVE_COMMANDS) >= 5

    safe_texts = {cmd[0].lower() for cmd in demo_harness.SAFE_DEMO_COMMANDS}
    dest_texts = {cmd[0].lower() for cmd in demo_harness.DESTRUCTIVE_COMMANDS}

    # Safe and destructive commands must be disjoint
    assert safe_texts.isdisjoint(dest_texts)


def test_harness_output(capsys):
    """Verify demo_harness runs main without throwing exceptions."""
    demo_harness.main()
    captured = capsys.readouterr()
    assert "AETHER.AI // DEMO HARNESS (NON-DESTRUCTIVE)" in captured.out
    assert "RECOMMENDED DEMO SEQUENCE" in captured.out
    assert "DEMO READY" in captured.out
