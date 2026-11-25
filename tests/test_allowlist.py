"""Tests for the command allowlist (actions/computer_use.py)."""
import pytest
from src.actions.computer_use import _is_command_allowed, ALLOWED_COMMANDS


def test_allowed_simple_command():
    """Test simple allowed commands."""
    assert _is_command_allowed("git status") is True
    assert _is_command_allowed("python script.py") is True
    assert _is_command_allowed("npm install") is True
    assert _is_command_allowed("dir") is True
    assert _is_command_allowed("ls") is True


def test_blocked_dangerous_commands():
    """Test that dangerous commands are blocked."""
    assert _is_command_allowed("powershell -Command Get-Process") is False
    assert _is_command_allowed("cmd /c dir") is False
    assert _is_command_allowed("rm -rf /") is False
    assert _is_command_allowed("del /f /q C:\\temp") is False


def test_blocked_dangerous_args():
    """Test that dangerous arguments are blocked."""
    assert _is_command_allowed("git -Command foo") is False
    assert _is_command_allowed("python /c script.py") is False
    assert _is_command_allowed("python -rf script.py") is False


def test_blocked_shell_metacharacters():
    """Test that shell metacharacters are blocked."""
    assert _is_command_allowed("git status > output.txt") is False
    assert _is_command_allowed("git status | grep foo") is False
    assert _is_command_allowed("git status && echo done") is False


def test_empty_command():
    """Test empty command."""
    assert _is_command_allowed("") is False
    assert _is_command_allowed("   ") is False
    assert _is_command_allowed(None) is False


def test_path_handling():
    """Test that paths are handled correctly."""
    # Windows paths
    assert _is_command_allowed("C:\\Python\\python.exe script.py") is True
    assert _is_command_allowed("./python script.py") is True
    
    # Unix-style paths
    assert _is_command_allowed("/usr/bin/python script.py") is True


def test_case_insensitivity():
    """Test case insensitivity."""
    assert _is_command_allowed("GIT status") is True
    assert _is_command_allowed("Git Status") is True
    assert _is_command_allowed("PYTHON script.py") is True


def test_unknown_command():
    """Test unknown command."""
    assert _is_command_allowed("unknowncmd arg") is False
    assert _is_command_allowed("xyz") is False


def test_allowed_commands_set():
    """Test that ALLOWED_COMMANDS doesn't contain dangerous commands."""
    dangerous = {"powershell", "cmd", "rm", "del", "rmdir", "format", "shutdown", "restart"}
    intersection = ALLOWED_COMMANDS & dangerous
    assert len(intersection) == 0, f"Dangerous commands found in allowlist: {intersection}"