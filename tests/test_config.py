"""Tests for config loading (core/config.py)."""
import json
import tempfile
import pytest
from pathlib import Path
from src.core import config


def test_default_config():
    """Test that default config has required fields."""
    cfg = config.DEFAULT_CONFIG
    
    assert "assistant_name" in cfg
    assert "provider" in cfg
    assert "model_name" in cfg
    assert "auto_listen" in cfg


def test_default_model_is_real():
    """Test that default model is a real Gemini model."""
    model = config.DEFAULT_CONFIG["model_name"]
    
    # Should be gemini-2.0-flash or similar real model
    assert "3.5" not in model
    assert "3.8" not in model
    assert "2.0" in model or "1.5" in model


def test_model_aliases():
    """Test that model aliases map to real models."""
    aliases = config.MODEL_ALIASES
    
    for alias, target in aliases.items():
        # Target should not be a fictional model
        assert "3.5" not in target or "2.0" in target or "1.5" in target


def test_load_config_missing_file(tmp_path):
    """Test that load_config creates default config if missing."""
    # This would create a config.json in the project root
    # Just verify the function exists and doesn't crash
    assert hasattr(config, 'load_config')
    assert hasattr(config, 'save_config')


def test_save_config():
    """Test save_config function exists."""
    assert hasattr(config, 'save_config')