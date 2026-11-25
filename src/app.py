import os
import sys
import json
import threading
import time
import traceback
from pathlib import Path

# ─── Path Setup ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import webview

from src.core.compat import check_environment_health
from src.core.config import load_config, save_config
from src.core.telemetry import get_system_telemetry
from src.ai.brain import JarvisBrain
from src.actions.executor import execute_action
from src.actions.vision_actions import capture_screen_image
from src.actions.app_actions import refresh_installed_apps
from src.voice.listener import VoiceListener
from src.proactive.watcher import ProactiveSentinel
from src.proactive.briefing import generate_situational_briefing
from src.core.api_validator import validate_current_config, validate_gemini_key, validate_openrouter_key


class JarvisApi:
    def __init__(self, brain: JarvisBrain, config: dict):
        self.brain = brain
        self.config = config
        self._window = None
        self.listener = None
        self.ptt = None

    def set_window(self, window):
        self._window = window

    def set_listener(self, listener: VoiceListener):
        self.listener = listener

    def set_ptt(self, ptt):
        self.ptt = ptt

    # ── Exposed to JS via pywebview.api ──

    def get_telemetry(self) -> dict:
        try:
            return get_system_telemetry()
        except Exception as e:
            return {"error": str(e)}

    def send_message(self, text: str, include_vision: bool = False, include_webcam: bool = False) -> dict:
        if not text or not text.strip():
            return {"text": "Empty input received.", "action": None}
        try:
            # Instant conversational latency filler (Ported from J.A.R.V.I.S.)
            try:
                from src.ai.fillers import get_working_filler
                filler = get_working_filler(text)
                if self._window:
                    safe_filler = json.dumps(filler)
                    self._window.evaluate_js(f"if (window.aetherApp && window.aetherApp.onFiller) {{ window.aetherApp.onFiller({safe_filler}); }}")
            except Exception as fe:
                print(f"[App] Filler notification notice: {fe}")

            result = self.brain.process_query(text.strip(), include_vision=include_vision, include_webcam=include_webcam)
            # Ensure we always return a dict with 'text' and 'action' keys
            if not isinstance(result, dict):
                return {"text": str(result), "action": None}
            if "text" not in result:
                result["text"] = result.get("reply", result.get("message", "Done."))
            if "action" not in result:
                result["action"] = None
            return result
        except Exception as e:
            traceback.print_exc()
            return {"text": f"Error processing request: {e}", "action": None}

    def scan_screen(self, query: str = "Analyze this screen and summarize the active context.") -> dict:
        try:
            return self.brain.process_query(query, include_vision=True)
        except Exception as e:
            return {"text": f"Vision error: {e}", "action": None}

    def scan_webcam(self, query: str = "Analyze what is visible through the camera.") -> dict:
        try:
            return self.brain.process_query(query, include_webcam=True)
        except Exception as e:
            return {"text": f"Webcam optical error: {e}", "action": None}

    def trigger_quick_action(self, action_name: str, args: dict = None) -> dict:
        try:
            result = execute_action(action_name, args or {})
            return result if isinstance(result, dict) else {"success": True, "message": str(result)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def trigger_briefing(self) -> dict:
        """Generates proactive situational briefing"""
        try:
            name = self.config.get("assistant_name", "Aether")
            return generate_situational_briefing(name)
        except Exception as e:
            return {"text": f"Unable to compile situational briefing: {e}"}

    def get_config(self) -> dict:
        return self.config

    def get_memory_overview(self) -> dict:
        """Pillar 3: Returns Second Brain statistics and active facts"""
        try:
            sb = self.brain.second_brain
            stats = sb.store.get_memory_stats()
            facts = sb.store.get_all_facts(limit=25)
            return {"success": True, "stats": stats, "facts": facts}
        except Exception as e:
            return {"success": False, "error": str(e), "stats": {}, "facts": []}

    def compact_memory(self, max_turns: int = 50) -> dict:
        """Pillar 3: Prunes old conversations and compacts the SQLite database."""
        try:
            sb = self.brain.second_brain
            res = sb.compact_conversations(max_turns=max_turns)
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Pillar 5: Multi-System & Environment Orchestration ──
    def get_environment_snapshot(self) -> dict:
        try:
            from src.environment.peripherals import get_peripheral_snapshot
            from src.environment.iot_controller import get_iot_state
            peripherals = get_peripheral_snapshot()
            iot = get_iot_state()
            return {
                "success": True,
                "peripherals": peripherals,
                "iot": iot.get("state", {})
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_environment_preset(self, preset: str) -> dict:
        try:
            from src.environment.iot_controller import set_environment_preset
            return set_environment_preset(preset)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_ambient_lighting(self, color: str = None, brightness: int = None, state: str = None) -> dict:
        try:
            from src.environment.iot_controller import set_ambient_lighting
            return set_ambient_lighting(color, brightness, state)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_desk_lamp(self, state: str = None) -> dict:
        try:
            from src.environment.iot_controller import toggle_desk_lamp
            return toggle_desk_lamp(state)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def switch_display_mode(self, mode: str) -> dict:
        try:
            from src.environment.peripherals import switch_display_mode
            return switch_display_mode(mode)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_code_diagnostics(self, target: str) -> dict:
        try:
            from src.environment.pair_programmer import run_compiler_diagnostics
            return run_compiler_diagnostics(target)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def index_codebase(self, path: str = None) -> dict:
        """Pillar 3: Indexes code directory into Second Brain vector database"""
        try:
            target_path = path or str(PROJECT_ROOT)
            return self.brain.second_brain.store.index_directory(target_path, project_name="piko-pc")
        except Exception as e:
            return {"success": False, "message": f"Indexing error: {e}"}

    def check_api_status(self) -> dict:
        """Checks the active API key and returns live verification status"""
        try:
            return validate_current_config(self.config)
        except Exception as e:
            return {"status": "error", "valid": False, "message": str(e)}

    def test_key(self, provider: str, key: str, model: str = None) -> dict:
        """Tests an API key on-demand from the UI settings panel"""
        try:
            prov = (provider or "gemini").lower()
            if prov == "openrouter":
                return validate_openrouter_key(key, model or "google/gemini-2.0-flash-001")
            else:
                return validate_gemini_key(key, model or "gemini-2.0-flash")
        except Exception as e:
            return {"status": "error", "valid": False, "message": str(e)}

    def save_settings(self, new_cfg: dict) -> dict:
        try:
            self.config.update(new_cfg)
            save_config(self.config)
            self.brain.update_config(self.config)
            return {"success": True, "config": self.config}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def set_speaking_state(self, is_speaking: bool):
        """Called by UI when TTS speech starts or ends"""
        if self.listener:
            self.listener.set_speaking(is_speaking)

    def toggle_voice_listen(self) -> bool:
        """Toggles python mic listening state"""
        if self.listener:
            return self.listener.toggle()
        return False

    def set_voice_listen(self, enabled: bool) -> bool:
        """Idempotently sets python mic listening state"""
        if self.listener:
            return self.listener.set_enabled(enabled)
        return False

    def undo_last_action(self) -> dict:
        """Rolls back the most recent reversible action from the 10-turn LIFO stack"""
        try:
            from core.undo import undo_last, can_undo, peek
            msg = undo_last()
            return {"success": True, "message": msg, "can_undo": can_undo(), "next_peek": peek()}
        except Exception as e:
            return {"success": False, "message": f"Undo error: {e}"}

    def confirm_action(self, accepted: bool) -> dict:
        """Resolves a pending physical UI confirmation request"""
        try:
            from core.confirm import resolve as confirm_resolve, pending_title
            title = pending_title()
            confirm_resolve(accepted)
            return {"success": True, "accepted": accepted, "title": title}
        except Exception as e:
            return {"success": False, "message": f"Confirmation error: {e}"}

    def get_pending_confirmation(self) -> dict:
        try:
            from core.confirm import pending_title
            t = pending_title()
            return {"has_pending": bool(t), "title": t}
        except Exception as e:
            return {"has_pending": False, "error": str(e)}

    def run_deep_research(self, query: str) -> dict:
        """Launches autonomous research task (currently disabled for demo stability)"""
        return {"success": False, "message": "Deep research is disabled in demo mode. Use 'focus session' for a working demo."}

    def get_bridge_info(self) -> dict:
        """Returns pairing code, local IP, port, and connected mobile status"""
        try:
            from src.network.bridge_server import get_bridge_server
            return get_bridge_server().get_connection_info()
        except Exception as e:
            return {"error": str(e)}

    def rotate_pairing_code(self) -> dict:
        """Rotates the pairing code and returns fresh bridge info and QR code"""
        try:
            from src.network.bridge_server import get_bridge_server
            return get_bridge_server().rotate_pairing_code()
        except Exception as e:
            return {"error": str(e)}

    def send_phone_command(self, action: str, params: dict = None) -> dict:
        try:
            from src.network.bridge_server import get_bridge_server
            ok = get_bridge_server().send_phone_command(action, params)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_mobile_action(self, action: str, params: dict) -> dict:
        """Executes a command dispatched from the mobile phone onto this PC"""
        try:
            if action in ["lock", "pc_lock"]:
                from src.actions.system_actions import lock_workstation
                return lock_workstation()
            elif action in ["mute", "pc_mute"]:
                from src.actions.system_actions import set_volume
                return set_volume("mute")
            elif action in ["unmute", "pc_unmute"]:
                from src.actions.system_actions import set_volume
                return set_volume("up", 1)
            elif action in ["volume", "pc_set_volume"]:
                from src.actions.system_actions import set_volume
                act = params.get("action", "up")
                steps = params.get("steps", 5)
                return set_volume(act, steps)
            elif action in ["screenshot", "pc_screenshot"]:
                from src.actions.vision_actions import capture_screen_image
                res = capture_screen_image()
                if not res.get("success"):
                    return {"success": False, "message": res.get("error", "Screenshot capture failed")}
                return {"success": True, "message": "Screenshot captured", "image_b64": res.get("base64", "")}
            elif action in ["launch_app", "pc_launch_app"]:
                from src.actions.app_actions import open_application
                app_name = params.get("app") or params.get("app_name") or ""
                return open_application(app_name)
            elif action in ["type_text", "pc_type_text"]:
                from src.actions.computer_use import keyboard_type
                text = params.get("text", "")
                return keyboard_type(text)
            elif action in ["get_status", "get_battery", "get_telemetry", "status", "telemetry"]:
                from src.core.telemetry import get_system_telemetry
                return {"success": True, "message": "Telemetry updated", "data": get_system_telemetry()}
            elif action in ["media_play_pause", "media_toggle", "media_play", "media_pause"]:
                from src.actions.media_actions import control_media
                return control_media("toggle")
            elif action in ["media_next", "next_track"]:
                from src.actions.media_actions import control_media
                return control_media("next")
            elif action in ["media_prev", "previous_track", "prev_track"]:
                from src.actions.media_actions import control_media
                return control_media("prev")
            elif action in ["control_media"]:
                from src.actions.media_actions import control_media
                cmd = params.get("command", "toggle")
                return control_media(cmd)
            elif action in ["volume_up", "pc_volume_up"]:
                from src.actions.system_actions import set_volume
                return set_volume("up", params.get("steps", 5))
            elif action in ["volume_down", "pc_volume_down"]:
                from src.actions.system_actions import set_volume
                return set_volume("down", params.get("steps", 5))
            elif action in ["voice_command", "pc_voice_command"]:
                query = params.get("query") or params.get("text") or ""
                if query:
                    res = self.brain.process_query(query)
                    return {"success": True, "reply": res.get("reply", res.get("text", "Done")), "action": res.get("action")}
                return {"success": False, "message": "Empty query"}
            else:
                return execute_action(action, params)
        except Exception as e:
            return {"success": False, "message": f"Execution error: {e}"}

    def set_orb_state(self, state: str) -> dict:
        """Set the 3D orb visual state from backend (idle, listening, thinking, speaking, error)"""
        if not self._window:
            return {"success": False, "message": "No window available"}
        try:
            safe_state = json.dumps(state)
            self._window.evaluate_js(f"if (window.aetherApp) {{ window.aetherApp.setAssistantState({safe_state}); }}")
            return {"success": True, "state": state}
        except Exception as e:
            return {"success": False, "message": f"Orb state error: {e}"}

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def close_window(self):
        if self.ptt:
            try:
                self.ptt.stop()
            except Exception:
                pass
        if self.listener:
            self.listener.stop()
        try:
            from src.network.bridge_server import get_bridge_server
            get_bridge_server().stop()
        except Exception:
            pass
        if self._window:
            self._window.destroy()


def telemetry_stream_worker(window, api: JarvisApi):
    """Pushes live telemetry to the UI every 2 seconds"""
    while True:
        try:
            time.sleep(2)
            if window:
                telem = get_system_telemetry()
                js = f"if (window.onTelemetryUpdate) {{ window.onTelemetryUpdate({json.dumps(telem)}); }}"
                window.evaluate_js(js)
        except Exception:
            pass


def main():
    print("=" * 60)
    print("  AETHER.AI  //  SOLARIS CORE  //  BOOTING...")
    print("=" * 60)

    # Check for exposed secret files
    import os
    secret_files = []
    if os.path.exists(".env"):
        secret_files.append(".env")
    if os.path.exists("config.json"):
        try:
            import json
            with open("config.json") as f:
                cfg_check = json.load(f)
                if cfg_check.get("gemini_api_key") or cfg_check.get("openrouter_api_key"):
                    secret_files.append("config.json (contains API keys)")
        except Exception:
            pass
    if secret_files:
        print(f"[Boot] WARNING: Potential secrets found in: {', '.join(secret_files)}")
        print(f"[Boot] Consider removing these files before sharing the project.")

    health = check_environment_health()
    print(f"[Boot] Runtime: Python {health['python_version']} // Platform: {health['status']}")

    cfg = load_config()
    print(f"[Boot] Config loaded. Assistant: {cfg.get('assistant_name', 'Aether')}")
    print(f"[Boot] Gemini API Key: {'SET' if cfg.get('gemini_api_key', '').strip() else 'NOT SET (offline mode)'}")
    print(f"[Boot] Auto-listen: {cfg.get('auto_listen', True)}")

    brain = JarvisBrain(cfg)
    api = JarvisApi(brain, cfg)

    # Demo mode: seed memory with sample facts for offline demo
    if not cfg.get("gemini_api_key") and not cfg.get("openrouter_api_key"):
        print("[Boot] Demo mode: seeding Second Brain with sample facts...")
        try:
            from memory.second_brain import SecondBrain
            sb = SecondBrain()
            sb.store.save_fact("preferences", "focus_session", "User prefers VS Code + quiet environment for focus sessions. Last used 2024-11-20.")
            sb.store.save_fact("preferences", "coding", "Currently working on Aether.ai-PC: autonomous Windows assistant with local-first architecture.")
            sb.store.save_fact("preferences", "music", "Prefers lo-fi beats while coding. Last playlist: 'Chillhop Essentials'.")
            sb.store.save_fact("project", "aether_pc", "Aether.ai-PC: Local-first voice assistant with memory, automation, and mobile bridge. Target: hackathon demo.")
            sb.store.save_fact("project", "architecture", "Key features: deterministic intent parser, SQLite FTS5 BM25 memory, Windows automation, Three.js 3D UI.")
            print("[Boot] Demo memory seeded successfully.")
        except Exception as e:
            print(f"[Boot] Demo memory seed warning: {e}")

    # Pre-index installed Windows apps in background
    print("[Boot] Indexing installed applications...")
    threading.Thread(target=refresh_installed_apps, daemon=True).start()

    ui_path = PROJECT_ROOT / "ui" / "index.html"
    if not ui_path.exists():
        print(f"[FATAL] UI file not found at: {ui_path}")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"[Boot] Loading UI: {ui_path}")

    window = webview.create_window(
        title=f"{cfg.get('assistant_name', 'Aether')} // Solaris Core",
        url=str(ui_path.resolve()),
        js_api=api,
        width=1000,
        height=680,
        resizable=True,
        frameless=True,
        easy_drag=False,
        on_top=False,
        background_color='#030305'
    )
    api.set_window(window)

    # Wire Hardware UI Confirmation Gate
    try:
        from core.confirm import bind as confirm_bind
        def _show_confirmation(title: str, detail: str):
            if window:
                try:
                    safe_title = json.dumps(title)
                    safe_detail = json.dumps(detail)
                    window.evaluate_js(f"if (window.aetherApp && window.aetherApp.showConfirmation) {{ window.aetherApp.showConfirmation({safe_title}, {safe_detail}); }} else {{ console.warn('Confirmation needed:', {safe_title}); }}")
                except Exception as e:
                    print(f"[Confirm] JS dispatch error: {e}")
        def _hide_confirmation():
            if window:
                try:
                    window.evaluate_js("if (window.aetherApp && window.aetherApp.hideConfirmation) { window.aetherApp.hideConfirmation(); }")
                except Exception:
                    pass
        confirm_bind(_show_confirmation, _hide_confirmation, log=lambda m: print(f"[Confirm] {m}"))
    except Exception as e:
        print(f"[Boot] Confirm gate binding warning: {e}")

    # Wire Push-to-Talk / Wake Hotkey
    try:
        from core.hotkey import PushToTalk
        raw_chord = cfg.get("hotkey", "alt+space")
        chord_parts = tuple(k.strip().lower() for k in raw_chord.split("+") if k.strip())
        def _on_hotkey(held: bool):
            if held and window:
                try:
                    window.restore()
                    window.show()
                    window.evaluate_js("if (window.aetherApp && window.aetherApp.triggerClapWake) { window.aetherApp.triggerClapWake(); }")
                except Exception as he:
                    print(f"[Hotkey] Trigger error: {he}")
        ptt = PushToTalk(on_change=_on_hotkey, chord=chord_parts)
        ptt_scope = ptt.start()
        api.set_ptt(ptt)
        print(f"[Boot] ✓ Push-to-talk hotkey ({raw_chord}) active [scope: {ptt_scope}]")
    except Exception as e:
        print(f"[Boot] Push-to-talk hotkey warning: {e}")

    # Wire VoiceListener callbacks to WebView2 window
    def on_speech_detected(text: str):
        if window:
            try:
                safe_text = json.dumps(text)
                window.evaluate_js(f"if (window.aetherApp) {{ window.aetherApp.handleQuery({safe_text}); }}")
            except Exception as e:
                print(f"[App] JS dispatch error: {e}")

    def on_rms_update(rms: float):
        if window:
            try:
                window.evaluate_js(f"if (window.setAudioRms) {{ window.setAudioRms({rms:.3f}); }}")
            except Exception:
                pass

    def on_state_change(state: str):
        if window:
            try:
                safe_state = json.dumps(state)
                window.evaluate_js(f"if (window.aetherApp) {{ window.aetherApp.setAssistantState({safe_state}); }}")
            except Exception:
                pass

    def on_barge_in():
        if window:
            try:
                window.evaluate_js("if (window.aetherApp) { window.aetherApp.triggerBargeIn(); }")
            except Exception:
                pass

    listener = VoiceListener(
        on_speech_detected=on_speech_detected,
        on_rms_update=on_rms_update,
        on_state_change=on_state_change,
        on_barge_in=on_barge_in,
        language=cfg.get("stt_language")
    )
    api.set_listener(listener)

    # Wire Proactive Sentinel for zero-click anticipatory intelligence
    def on_proactive_alert(alert_data: dict):
        if window:
            try:
                safe_data = json.dumps(alert_data)
                window.evaluate_js(f"if (window.aetherApp) {{ window.aetherApp.handleProactiveEvent({safe_data}); }}")
            except Exception as e:
                print(f"[App] Proactive alert dispatch error: {e}")

    sentinel = ProactiveSentinel(on_proactive_alert=on_proactive_alert)

    def on_loaded():
        print("[Boot] ✓ WebView loaded. Starting background services...")
        # Start telemetry loop
        threading.Thread(target=telemetry_stream_worker, args=(window, api), daemon=True).start()
        # Start microphone listener loop
        if cfg.get("auto_listen", True):
            print("[Boot] ✓ Starting voice intercept loop...")
            listener.start()
        # Start proactive sentinel loop
        print("[Boot] ✓ Starting proactive sentinel...")
        sentinel.start()

        # Start Aether Mobile Bridge server for companion pairing
        try:
            from src.network.bridge_server import get_bridge_server
            bridge = get_bridge_server()
            bridge.action_executor = lambda action, params: api.execute_mobile_action(action, params)

            def on_bridge_telemetry(telem):
                if window:
                    try:
                        safe_telem = json.dumps(telem)
                        window.evaluate_js(f"if (window.aetherApp && window.aetherApp.onMobileTelemetry) {{ window.aetherApp.onMobileTelemetry({safe_telem}); }}")
                    except Exception:
                        pass

            def on_bridge_notification(notif):
                if window:
                    try:
                        safe_notif = json.dumps(notif)
                        window.evaluate_js(f"if (window.aetherApp && window.aetherApp.onMobileNotification) {{ window.aetherApp.onMobileNotification({safe_notif}); }}")
                    except Exception:
                        pass

            def on_bridge_status(status):
                if window:
                    try:
                        safe_status = json.dumps(status)
                        window.evaluate_js(f"if (window.aetherApp && window.aetherApp.onMobileStatus) {{ window.aetherApp.onMobileStatus({safe_status}); }}")
                    except Exception:
                        pass

            bridge.on_telemetry_callback = on_bridge_telemetry
            bridge.on_notification_callback = on_bridge_notification
            bridge.on_status_change_callback = on_bridge_status
            bridge.start()
            print(f"[Boot] ✓ Aether Mobile Bridge active on ws://{bridge.local_ip}:{bridge.port} (Pairing Code: {bridge.pairing_code})")
        except Exception as be:
            print(f"[Boot] Bridge initialization notice: {be}")

        print("[Boot] ════════════════════════════════════════")
        print("[Boot]   AETHER.AI ONLINE — ALL SYSTEMS GO")
        print("[Boot] ════════════════════════════════════════")

        # Initial situational greeting after UI settles
        def startup_greeting():
            time.sleep(2.0)
            if window and cfg.get("startup_briefing", True):
                try:
                    name = cfg.get("assistant_name", "Aether")
                    brief = generate_situational_briefing(name)
                    alert_payload = {
                        "text": brief["text"],
                        "type": "briefing",
                        "priority": "normal",
                        "speak": True
                    }
                    safe_brief = json.dumps(alert_payload)
                    window.evaluate_js(f"if (window.aetherApp) {{ window.aetherApp.handleProactiveEvent({safe_brief}); }}")
                except Exception as ex:
                    print(f"[Boot] Startup briefing error: {ex}")

        threading.Thread(target=startup_greeting, daemon=True).start()

    window.events.loaded += on_loaded

    # debug=True enables DevTools (F12) for troubleshooting
    webview.start(debug=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
