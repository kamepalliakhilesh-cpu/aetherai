"""Pytest configuration for Aether.ai-PC tests."""
import sys
from pathlib import Path

# Add project root to path so we can import src.* modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))