"""Regression tests for verified UI/UX, safety gate, and model fallback fixes."""
from pathlib import Path
from unittest.mock import patch

from src.actions import executor
from src.core import api_validator
from src.core.config import DEFAULT_CONFIG
from src.environment import iot_controller


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_confirm_modal_present_in_ui():
    """Verify confirmModal and JS handlers match backend confirm.bind calls."""
    html = (PROJECT_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    js = (PROJECT_ROOT / "ui" / "js" / "aether_ui.js").read_text(encoding="utf-8")

    for elem_id in ("confirmModal", "confirmTitle", "confirmDetail", "confirmAcceptBtn", "confirmCancelBtn"):
        assert f'id="{elem_id}"' in html, f"Missing {elem_id} in ui/index.html"

    assert "showConfirmation(" in js
    assert "hideConfirmation(" in js
    assert "confirm_action" in js


def test_no_stale_fictional_model_defaults():
    """Verify production defaults use valid model identifiers instead of 3.8-flash-lite."""
    assert "3.8" not in DEFAULT_CONFIG["model_name"]
    assert "3.5" not in DEFAULT_CONFIG["model_name"]
    assert api_validator.validate_gemini_key("")["model"] == "gemini-2.0-flash"
    assert api_validator.validate_openrouter_key("")["model"] == "google/gemini-2.0-flash-001"
    assert api_validator.MODEL_ALIASES.get("gemini-3.8-flashlite") == "gemini-2.0-flash"


def test_gated_terminal_command_preserves_dict_output():
    """Verify _gated_terminal_command propagates output and success from run_system_command."""
    sample_res = {"success": True, "output": "ok-output", "message": "Command completed"}
    with patch("src.core.confirm.request_and_wait", return_value=(True, sample_res)):
        out = executor._gated_terminal_command({"command": "dir"})
    assert out == sample_res


def test_hot_patch_file_uses_gated_handler():
    """Verify hot_patch_file in ACTION_REGISTRY routes through _gated_hot_patch."""
    with patch("src.actions.executor._gated_hot_patch", return_value={"success": False, "message": "gated"}) as mock_gate:
        res = executor.execute_action("hot_patch_file", {"file_path": "x.py", "target_snippet": "a", "replacement_snippet": "b"})
    mock_gate.assert_called_once()
    assert res["message"] == "gated"


def test_iot_presets_consistently_labeled_simulated():
    """Verify all IoT preset outputs clearly declare [Simulated IoT]."""
    for preset in ("coding_focus", "cinematic", "daylight", "alert", "nominal"):
        res = iot_controller.set_environment_preset(preset)
        assert res["success"] is True
        assert "[Simulated IoT]" in res["message"]
