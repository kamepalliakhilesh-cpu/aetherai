"""Tests for conversation retention & memory store compaction (memory/store.py)."""
import os
import tempfile
import pytest
from pathlib import Path
from src.memory.store import MemoryStore
from src.memory.second_brain import SecondBrain


@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_memory.db"
    store = MemoryStore(str(db_file))
    return store


def test_compact_conversations_empty(temp_store):
    res = temp_store.compact_conversations(max_turns=10)
    assert res["success"] is True
    assert res["pruned_turns"] == 0
    assert res["remaining_turns"] == 10


def test_compact_conversations_under_limit(temp_store):
    for i in range(5):
        temp_store.save_conversation_turn("user", f"Message {i}")
    
    res = temp_store.compact_conversations(max_turns=10)
    assert res["success"] is True
    assert res["pruned_turns"] == 0
    
    recent = temp_store.get_recent_conversations(limit=20)
    assert len(recent) == 5


def test_compact_conversations_over_limit(temp_store):
    for i in range(15):
        temp_store.save_conversation_turn("user", f"Turn {i}", session_id="s1")
    
    recent_before = temp_store.get_recent_conversations(limit=20, session_id="s1")
    assert len(recent_before) == 15

    # Compact keeping only 5 most recent turns
    res = temp_store.compact_conversations(max_turns=5, session_id="s1")
    assert res["success"] is True
    assert res["pruned_turns"] == 10
    
    recent_after = temp_store.get_recent_conversations(limit=20, session_id="s1")
    assert len(recent_after) == 5
    # The remaining turns should be the latest ones: Turn 10 to Turn 14
    contents = [r["content"] for r in recent_after]
    assert "Turn 14" in contents
    assert "Turn 0" not in contents


def test_second_brain_compact_command(tmp_path):
    db_file = tmp_path / "sb_test.db"
    sb = SecondBrain(str(db_file))
    
    for i in range(60):
        sb.store.save_conversation_turn("user", f"Prompt {i}")
        
    query_res = sb.answer_memory_query_locally("compact memory")
    assert query_res["action"] == "compact_memory"
    assert "Second Brain compaction complete" in query_res["reply"]
    
    stats = sb.store.get_memory_stats()
    assert stats["conversations"] == 50
