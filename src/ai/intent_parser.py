"""
Local Deterministic Intent Parser for JARVIS / Aether (Pillars 1 to 5).
Provides instant (< 2ms) offline execution for direct OS actions, briefings,
telemetry, media, windows, peripherals, environment presets, and memory lookups.
"""

import re
import datetime
import random
from typing import Dict, Any, Optional

from ..actions.executor import execute_action
from ..actions.vision_actions import capture_screen_image
from ..core.telemetry import get_system_telemetry

class LocalIntentParser:
    """Supercharged offline deterministic engine when no cloud LLM API key is configured or for zero-latency execution"""

    JOKES = [
        "Why do programmers prefer dark mode? Because light attracts bugs, Sir.",
        "There are 10 types of people in the world: those who understand binary, and those who don't.",
        "Why was the computer cold? Because it left its Windows open, Sir.",
        "An SQL statement walks into a bar, approaches two tables, and asks: 'May I join you?'",
        "A programmer's wife tells him: 'Go to the store and get a loaf of bread. If they have eggs, get a dozen.' He returned with 12 loaves of bread.",
        "Hardware: The part of a computer you can kick. Software: The part you can only curse at, Sir."
    ]

    @staticmethod
    def parse(user_text: str) -> Dict[str, Any]:
        """
        Main entrypoint:
        1. Checks for multi-step command sequences & compound flows (App+Type, App+Search, Multi-App, Conjunctions)
        2. Falls back to single deterministic parsing
        """
        from ..actions.flow_engine import CommandFlowEngine
        flow_res = CommandFlowEngine.try_execute_flow(user_text, LocalIntentParser.parse_single)
        if flow_res:
            return flow_res
        return LocalIntentParser.parse_single(user_text)

    @staticmethod
    def parse_single(user_text: str) -> Dict[str, Any]:
        text = user_text.strip().lower()
        # Clean trailing punctuation
        text = re.sub(r"[?!.,]+$", "", text).strip()

        # ─── 00. Pillar 3: Episodic Memory & Second Brain ─────────────
        from ..memory.second_brain import SecondBrain
        _sb = SecondBrain()

        # A. Check if user is recording a fact: "remember that..." or "save to memory..."
        fact_extracted = _sb.extract_fact_from_text(user_text)
        if fact_extracted.get("success"):
            return {
                "action": "save_memory_fact",
                "args": {"content": fact_extracted.get("content")},
                "reply": fact_extracted.get("reply")
            }

        # B. Check if user asks an episodic memory or codebase query
        mem_ans = _sb.answer_memory_query_locally(user_text)
        if mem_ans.get("action") is not None:
            return {
                "action": mem_ans.get("action"),
                "args": {"query": user_text},
                "reply": mem_ans.get("reply")
            }

        # C. Quick "what was I working on" - recent activity from memory
        if any(k in text for k in [
            "what was i working on", "what was i doing", "what did i do",
            "recent work", "my recent", "last task", "previous work"
        ]):
            # Query second brain for recent facts/tasks
            facts = _sb.store.search_facts("focus_session OR coding OR work OR task OR project", limit=5)
            if facts:
                summary = []
                for f in facts[:3]:
                    c = f.get('content', '')[:120]
                    if c:
                        summary.append("- " + c)
                reply = "Recent activity from memory:\n" + "\n".join(summary) + "\nSay 'focus session' to resume, Sir."
            else:
                reply = "No recent work sessions recorded, Sir. Say 'focus session' to start one."
            return {
                "action": "recall_memory",
                "args": {"query": "recent work"},
                "reply": reply
            }

        # ─── 000. Pillar 4: Fluid Barge-In, Halting & Immediate Pivots ─
        # 1. Immediate Halting / Silence
        if text in ["stop", "halt", "quiet", "be quiet", "shut up", "silence", "hush", "never mind", "cancel", "that's enough", "thats enough", "pause speech"]:
            return {"action": "silence", "args": {}, "reply": "Silence engaged, Sir."}

        # 2. Acknowledgement
        if text in ["got it", "okay got it", "understood", "all right", "alright", "okay", "ok"]:
            return {"action": "acknowledge", "args": {}, "reply": "Acknowledged, Sir."}

        # 3. Fluid Pivot: e.g. "got it, skip to battery", "skip to battery", "pivot to cpu", "jump to weather"
        pivot_match = re.search(r"^(?:(?:got it|okay|alright)[,.]?\s+)?(?:skip to|pivot to|jump to|go to|check)\s+(.+)", text)
        if pivot_match:
            target_topic = pivot_match.group(1).strip()
            if any(w in target_topic for w in ["battery", "power", "charge"]):
                telem = get_system_telemetry()
                return {
                    "action": "get_telemetry",
                    "args": {"topic": "battery"},
                    "reply": f"Pivoting to battery: currently at {telem['battery_percent']}%, {telem['battery_time']}, Sir."
                }
            elif any(w in target_topic for w in ["cpu", "processor", "load"]):
                telem = get_system_telemetry()
                return {
                    "action": "get_telemetry",
                    "args": {"topic": "cpu"},
                    "reply": f"CPU load is currently at {telem['cpu_percent']}%, Sir."
                }
            elif any(w in target_topic for w in ["ram", "memory"]):
                telem = get_system_telemetry()
                return {
                    "action": "get_telemetry",
                    "args": {"topic": "ram"},
                    "reply": f"RAM utilization is at {telem['ram_percent']}% ({telem['ram_used_gb']} GB used), Sir."
                }
            elif any(w in target_topic for w in ["weather", "forecast", "temperature"]):
                from ..proactive.briefing import get_live_weather
                w = get_live_weather()
                return {
                    "action": "weather",
                    "args": {},
                    "reply": f"Local weather: {w or 'clear'}, Sir."
                }

        # ─── Safety & LIFO Undo Gate ──────────────────────────────────
        if text in ["undo", "undo that", "revert", "revert that", "take that back", "undo last action"]:
            u_res = execute_action("undo", {})
            return {
                "action": "undo",
                "args": {},
                "reply": u_res.get("message", "Undo completed, Sir.")
            }

        # ─── Physical Confirmation Gate ───────────────────────────────
        if text in ["confirm", "confirm that", "yes confirm", "proceed", "yes proceed", "yes do it"]:
            try:
                from core.confirm import resolve as resolve_confirm, pending_title
                p = pending_title()
                if p:
                    resolve_confirm(True)
                    return {"action": "confirm_action", "args": {"accepted": True}, "reply": f"Confirmed and executing '{p}', Sir."}
                else:
                    return {"action": "confirm_action", "args": {"accepted": False}, "reply": "No pending confirmation to accept, Sir."}
            except Exception:
                return {"action": "confirm_action", "args": {"accepted": False}, "reply": "Confirmation system unavailable, Sir."}

        if text in ["cancel that", "don't do that", "abort that", "cancel action", "deny"]:
            try:
                from core.confirm import resolve as resolve_confirm, pending_title
                p = pending_title()
                if p:
                    resolve_confirm(False)
                    return {"action": "confirm_action", "args": {"accepted": False}, "reply": f"Cancelled pending action '{p}', Sir."}
                else:
                    return {"action": "confirm_action", "args": {"accepted": False}, "reply": "No pending confirmation to cancel, Sir."}
            except Exception:
                return {"action": "confirm_action", "args": {"accepted": False}, "reply": "Confirmation system unavailable, Sir."}

        # ─── UI Automation Element Clicking ───────────────────────────
        uia_click = re.search(r"^click\s+(?:on\s+)?(?:the\s+)?(?:button\s+|link\s+|tab\s+)?['\"]?([^0-9][a-zA-Z0-9_\s\.\-]{1,30})['\"]?$", text)
        if uia_click and not any(k in text for k in ["video", "result", "at ", "coordinates"]):
            target_label = uia_click.group(1).strip()
            if target_label not in ["it", "this", "that", "here"]:
                c_res = execute_action("find_and_click_element", {"name_or_label": target_label})
                if c_res.get("success"):
                    return {"action": "find_and_click_element", "args": {"name_or_label": target_label}, "reply": c_res.get("message", f"Clicked '{target_label}', Sir.")}

        # ─── 0. Autonomous Multi-Step Workflows (Pillar 2) ─────────────
        from ..actions.workflow_engine import AutonomousWorkflowEngine
        if AutonomousWorkflowEngine.is_multi_step_workflow(user_text):
            wf_res = AutonomousWorkflowEngine.execute_workflow(user_text)
            if wf_res.get("success"):
                return {
                    "action": wf_res.get("action", "autonomous_workflow"),
                    "args": {"query": user_text},
                    "reply": wf_res.get("reply"),
                    "steps": wf_res.get("steps", [])
                }

        # ─── 0B. Direct Computer Use Emulation (Pillar 2) ─────────────
        # Click at coordinates: e.g. "click at 500, 300"
        coord_match = re.search(r"(?:click at|click on|move to)\s+(\d+)[,\s]+(\d+)", text)
        if coord_match:
            cx, cy = int(coord_match.group(1)), int(coord_match.group(2))
            execute_action("mouse_click", {"x": cx, "y": cy})
            return {"action": "mouse_click", "args": {"x": cx, "y": cy}, "reply": f"Target coordinates ({cx}, {cy}) clicked, Sir."}

        if text in ["double click", "double-click"]:
            execute_action("mouse_click", {"clicks": 2})
            return {"action": "mouse_click", "args": {"clicks": 2}, "reply": "Double-click executed, Sir."}

        if text in ["right click", "right-click", "context menu"]:
            execute_action("mouse_click", {"button": "right"})
            return {"action": "mouse_click", "args": {"button": "right"}, "reply": "Right-click context menu opened, Sir."}

        if text in ["scroll down", "scroll-down", "page down"]:
            execute_action("mouse_scroll", {"clicks": 4, "direction": "down"})
            return {"action": "mouse_scroll", "args": {"direction": "down"}, "reply": "Scrolled down, Sir."}

        if text in ["scroll up", "scroll-up", "page up"]:
            execute_action("mouse_scroll", {"clicks": 4, "direction": "up"})
            return {"action": "mouse_scroll", "args": {"direction": "up"}, "reply": "Scrolled up, Sir."}

        # Typing with Enter: e.g. "type hello world and press enter"
        type_enter_match = re.search(r"^type\s+['\"]?(.+?)['\"]?\s+and\s+press\s+enter$", text)
        if type_enter_match:
            to_type = type_enter_match.group(1).strip()
            execute_action("keyboard_type", {"text": to_type, "press_enter": True})
            return {"action": "keyboard_type", "args": {"text": to_type}, "reply": f"Typed '{to_type}' and submitted Enter, Sir."}

        # Plain typing: e.g. "type this is an automated message"
        type_match = re.search(r"^type\s+['\"]?(.+?)['\"]?$", text)
        if type_match:
            to_type = type_match.group(1).strip()
            execute_action("keyboard_type", {"text": to_type, "press_enter": False})
            return {"action": "keyboard_type", "args": {"text": to_type}, "reply": f"Typed text into active window, Sir."}

        # Hotkeys & Key presses: e.g. "press enter", "press ctrl+c", "press win+d", "show desktop"
        if text in ["show desktop", "minimize all", "hide all windows"]:
            execute_action("keyboard_hotkey", {"keys": "win+d"})
            return {"action": "keyboard_hotkey", "args": {"keys": "win+d"}, "reply": "Displaying desktop, Sir."}

        if text.startswith("press ") or text.startswith("hit "):
            raw_key = re.sub(r"^(?:press|hit)\s+", "", text).strip()
            if "+" in raw_key:
                execute_action("keyboard_hotkey", {"keys": raw_key})
                return {"action": "keyboard_hotkey", "args": {"keys": raw_key}, "reply": f"Shortcut '{raw_key}' dispatched, Sir."}
            else:
                execute_action("keyboard_press", {"key": raw_key})
                return {"action": "keyboard_press", "args": {"key": raw_key}, "reply": f"Key '{raw_key}' pressed, Sir."}

        # File search query: e.g. "find file neural network", "find pdf invoice"
        find_match = re.search(r"(?:find|search)\s+(?:files?|documents?|pdfs?)\s+(?:for\s+)?(.+)", text)
        if find_match:
            fq = find_match.group(1).strip()
            f_res = execute_action("find_files", {"query": fq, "limit": 4})
            files_list = f_res.get("files", [])
            if files_list:
                names = ", ".join([f["name"] for f in files_list[:3]])
                return {"action": "find_files", "args": {"query": fq}, "reply": f"Located matching files: {names}, Sir."}
            return {"action": "find_files", "args": {"query": fq}, "reply": f"No files found matching '{fq}', Sir."}

        # Draft in notepad: e.g. "draft in notepad todo list for today"
        draft_match = re.search(r"(?:draft|write)\s+in\s+notepad\s+(.+)", text)
        if draft_match:
            content_to_draft = draft_match.group(1).strip()
            d_res = execute_action("draft_in_notepad", {"content": content_to_draft})
            return {"action": "draft_in_notepad", "args": {"content": content_to_draft}, "reply": d_res.get("message", "Draft opened in Notepad, Sir.")}

        # Run terminal command: e.g. "run command git status", "run terminal dir"
        cmd_match = re.search(r"(?:run|execute)\s+(?:command|terminal)\s+(.+)", text)
        if cmd_match:
            cmd = cmd_match.group(1).strip()
            c_res = execute_action("run_terminal_command", {"command": cmd})
            out = c_res.get("output", "")[:200]
            return {"action": "run_terminal_command", "args": {"command": cmd}, "reply": f"Command executed:\n{out}"}

        # ─── 0C. Pillar 5: Multi-System & Environment Orchestration ────
        # 1. Multi-Monitor Presentation Switching
        if any(k in text for k in ["extend display", "extend screen", "second monitor", "dual monitor", "dual screen"]):
            execute_action("switch_display", {"mode": "extend"})
            return {"action": "switch_display", "args": {"mode": "extend"}, "reply": "Display array extended to second monitor, Sir."}

        if any(k in text for k in ["duplicate display", "duplicate screen", "clone display", "clone screen", "mirror screen"]):
            execute_action("switch_display", {"mode": "clone"})
            return {"action": "switch_display", "args": {"mode": "clone"}, "reply": "Display duplicated across all monitors, Sir."}

        if any(k in text for k in ["laptop screen only", "pc screen only", "internal display only", "single screen", "single monitor"]):
            execute_action("switch_display", {"mode": "internal"})
            return {"action": "switch_display", "args": {"mode": "internal"}, "reply": "External displays detached. Operating on primary laptop display, Sir."}

        if any(k in text for k in ["second screen only", "external display only", "external monitor only", "projector only"]):
            execute_action("switch_display", {"mode": "external"})
            return {"action": "switch_display", "args": {"mode": "external"}, "reply": "Switched to secondary display output, Sir."}

        # 2. Audio Routing & Headphone Detection
        if any(k in text for k in ["headphone", "headphones", "earphones", "audio output", "audio routing", "speakers or headphones"]):
            p_res = execute_action("get_peripherals", {})
            audio = p_res.get("audio", {})
            dev_name = audio.get("device_name", "Built-in Speakers")
            kind = audio.get("endpoint_type", "speakers").title()
            is_hp = audio.get("is_headphones", False)
            status_txt = "Headphones connected and active" if is_hp else "Routing to built-in laptop speakers"
            return {
                "action": "get_peripherals",
                "args": {"focus": "audio"},
                "reply": f"{status_txt}: {dev_name} ({kind}), Sir."
            }

        # 3. Wi-Fi & Network Telemetry
        if any(k in text for k in ["wifi status", "wifi network", "what wifi am i on", "network status", "wifi signal", "wifi info"]):
            p_res = execute_action("get_peripherals", {})
            net = p_res.get("network", {})
            if net.get("is_connected"):
                return {
                    "action": "get_peripherals",
                    "args": {"focus": "network"},
                    "reply": f"Connected to Wi-Fi '{net.get('ssid')}' on {net.get('band')} ({net.get('signal_percent')}% signal, {net.get('phy_rate_mbps')} Mbps PHY), Sir."
                }
            return {"action": "get_peripherals", "args": {"focus": "network"}, "reply": "Wi-Fi link is currently disconnected, Sir."}

        # 4. General Peripheral Status
        if any(k in text for k in ["peripherals", "check peripherals", "peripheral status", "connected devices", "what devices are connected", "show peripherals", "hardware status"]):
            p_res = execute_action("get_peripherals", {})
            return {
                "action": "get_peripherals",
                "args": {},
                "reply": f"Peripheral telemetry: {p_res.get('summary', 'Sensory arrays nominal')}, Sir."
            }

        # 5. Desk Lamp & Ambient Lighting
        if any(k in text for k in ["turn on desk lamp", "desk lamp on", "lamp on"]):
            execute_action("toggle_desk_lamp", {"state": "on"})
            return {"action": "toggle_desk_lamp", "args": {"state": "on"}, "reply": "Desk task lamp illuminated, Sir."}

        if any(k in text for k in ["turn off desk lamp", "desk lamp off", "lamp off"]):
            execute_action("toggle_desk_lamp", {"state": "off"})
            return {"action": "toggle_desk_lamp", "args": {"state": "off"}, "reply": "Desk task lamp powered down, Sir."}

        if any(k in text for k in ["toggle desk lamp", "toggle lamp", "desk lamp"]):
            res = execute_action("toggle_desk_lamp", {})
            st = "on" if res.get("desk_lamp") else "off"
            return {"action": "toggle_desk_lamp", "args": {}, "reply": f"Desk lamp toggled {st}, Sir."}

        # Ambient lighting brightness / dimming
        bright_match = re.search(r"(?:set lights to|dim lights to|lights brightness|brightness to)\s+(\d+)(?:%|\s*percent)?", text)
        if bright_match:
            b_val = int(bright_match.group(1))
            execute_action("set_ambient_lighting", {"brightness": b_val})
            return {"action": "set_ambient_lighting", "args": {"brightness": b_val}, "reply": f"Ambient room lighting adjusted to {b_val}%, Sir."}

        # Ambient lighting color
        light_color_match = re.search(r"(?:set lights to|change lights to|lights color|ambient light)\s+(solaris|gold|amber|warm|blue|cyan|red|purple|green|white)", text)
        if light_color_match:
            c_val = light_color_match.group(1)
            res = execute_action("set_ambient_lighting", {"color": c_val})
            # Safely extract color name
            light_info = res.get("light", {}) if isinstance(res, dict) else {}
            c_name = light_info.get("color_name", c_val) if isinstance(light_info, dict) else c_val
            return {"action": "set_ambient_lighting", "args": {"color": c_val}, "reply": f"Ambient illumination shifted to {c_name}, Sir."}

        if any(k in text for k in ["turn on ambient light", "turn on lights", "lights on", "ambient light on"]):
            execute_action("set_ambient_lighting", {"state": "on"})
            return {"action": "set_ambient_lighting", "args": {"state": "on"}, "reply": "Ambient environmental lighting engaged, Sir."}

        if any(k in text for k in ["turn off ambient light", "turn off lights", "lights off", "ambient light off"]):
            execute_action("set_ambient_lighting", {"state": "off"})
            return {"action": "set_ambient_lighting", "args": {"state": "off"}, "reply": "Ambient environmental lighting extinguished, Sir."}

        # 6. Synchronized Multi-System Environment Presets
        if any(k in text for k in ["coding mode", "focus mode", "coding preset", "preset coding", "focus preset", "dev mode"]):
            res = execute_action("set_environment_preset", {"preset": "coding_focus"})
            return {"action": "set_environment_preset", "args": {"preset": "coding_focus"}, "reply": res.get("message", "Coding Focus preset activated, Sir.")}

        if any(k in text for k in ["cinematic mode", "cinema mode", "movie mode", "cinema preset", "movie preset"]):
            res = execute_action("set_environment_preset", {"preset": "cinematic"})
            return {"action": "set_environment_preset", "args": {"preset": "cinematic"}, "reply": res.get("message", "Cinematic Environment preset activated, Sir.")}

        if any(k in text for k in ["daylight mode", "daylight preset"]):
            res = execute_action("set_environment_preset", {"preset": "daylight"})
            return {"action": "set_environment_preset", "args": {"preset": "daylight"}, "reply": res.get("message", "Daylight preset applied, Sir.")}

        if any(k in text for k in ["alert mode", "red alert"]):
            res = execute_action("set_environment_preset", {"preset": "alert"})
            return {"action": "set_environment_preset", "args": {"preset": "alert"}, "reply": res.get("message", "Condition Red engaged, Sir.")}

        if any(k in text for k in ["nominal mode", "reset environment", "nominal preset", "reset lighting"]):
            res = execute_action("set_environment_preset", {"preset": "nominal"})
            return {"action": "set_environment_preset", "args": {"preset": "nominal"}, "reply": res.get("message", "Environment reset to nominal telemetry, Sir.")}

        # 7. Pair Programmer: Compiler Diagnostics & Code Repairs
        diag_match = re.search(r"(?:run diagnostics|diagnose compiler|diagnose error|check syntax|compile|diagnose)\s+(?:on\s+)?([A-Za-z0-9_\-\.\/\\]+)", text)
        if diag_match:
            target_file = diag_match.group(1).strip()
            d_res = execute_action("diagnose_compiler_error", {"target": target_file})
            return {
                "action": "diagnose_compiler_error",
                "args": {"target": target_file},
                "reply": d_res.get("summary", "Diagnostics run completed.")
            }

        # ─── 0D. Aether Mobile Companion Tele-Link ───────────────────
        # 1. Ring / Find Phone
        if any(p in text for p in ["ring my phone", "find my phone", "where is my phone", "ring phone", "locate my phone", "make my phone ring"]):
            from ..actions.system_actions import ring_phone
            res = ring_phone()
            return {
                "action": "ring_phone",
                "args": {},
                "reply": res.get("message", "Triggering alarm on mobile device, Sir.")
            }

        # 2. Phone Battery
        if any(p in text for p in ["phone battery", "mobile battery", "how much battery on my phone", "check phone battery", "phone charge"]):
            from ..actions.system_actions import get_phone_battery
            res = get_phone_battery()
            return {
                "action": "get_phone_battery",
                "args": {},
                "reply": res.get("message", "Checking mobile battery, Sir.")
            }

        # 3. Mobile Link Status
        if any(p in text for p in ["mobile status", "phone status", "phone link status", "mobile link", "is my phone connected"]):
            from ..actions.system_actions import get_mobile_link_status
            res = get_mobile_link_status()
            return {
                "action": "get_mobile_link_status",
                "args": {},
                "reply": res.get("message", "Checking mobile link status, Sir.")
            }

        # 4. Copy to Phone
        if any(p in text for p in ["copy to phone", "sync to phone", "send clipboard to phone", "push to phone"]):
            from ..actions.system_actions import sync_clipboard_to_phone
            res = sync_clipboard_to_phone()
            return {
                "action": "sync_clipboard_to_phone",
                "args": {},
                "reply": res.get("message", "Clipboard synced to mobile device, Sir.")
            }

        # 5. Mobile Torch / Flashlight
        if any(p in text for p in ["turn on phone flashlight", "turn on phone torch", "phone flashlight on", "phone torch on"]):
            from ..actions.system_actions import toggle_phone_torch
            res = toggle_phone_torch(True)
            return {
                "action": "toggle_phone_torch",
                "args": {"enabled": True},
                "reply": res.get("message", "Mobile flashlight enabled, Sir.")
            }
        elif any(p in text for p in ["turn off phone flashlight", "turn off phone torch", "phone flashlight off", "phone torch off"]):
            from ..actions.system_actions import toggle_phone_torch
            res = toggle_phone_torch(False)
            return {
                "action": "toggle_phone_torch",
                "args": {"enabled": False},
                "reply": res.get("message", "Mobile flashlight disabled, Sir.")
            }

        # 6. Send WhatsApp via Phone
        wa_match = re.search(r"send\s+(?:a\s+)?whatsapp(?:\s+message)?\s+to\s+([a-zA-Z0-9_\-\s]+?)\s+(?:saying|that|:)\s+(.+)", text)
        if wa_match:
            contact = wa_match.group(1).strip()
            msg = wa_match.group(2).strip()
            from ..actions.system_actions import send_phone_whatsapp
            res = send_phone_whatsapp(contact, msg)
            return {
                "action": "send_phone_whatsapp",
                "args": {"contact": contact, "message": msg},
                "reply": res.get("message", f"Dispatched WhatsApp to {contact}, Sir.")
            }

        # ─── 0. Situational Briefings & Weather ──────────────────────
        if any(k in text for k in [
            "briefing", "status briefing", "daily briefing", "morning briefing",
            "give me a briefing", "sitrep", "system report", "full report", "morning report", "brief me"
        ]):
            from ..proactive.briefing import generate_situational_briefing
            brief = generate_situational_briefing()
            return {
                "action": "briefing",
                "args": {},
                "reply": brief["text"]
            }

        loc_weather_match = re.search(r"^(?:what(?:'s|\s+is)\s+the\s+weather|how\s+is\s+the\s+weather|weather\s+report|temperature)\s+(?:in|for|at)\s+([a-zA-Z\s]+)$", text)
        if loc_weather_match:
            city = loc_weather_match.group(1).strip()
            execute_action("search_google", {"query": f"weather in {city}"})
            return {"action": "search_google", "args": {"query": f"weather in {city}"}, "reply": f"Fetching weather forecast for {city.title()}, Sir."}

        if re.search(r"^(?:what(?:'s|\s+is)\s+the\s+weather(?:\s+like)?|how\s+is\s+the\s+weather|weather\s+report|temperature\s+today|weather)$", text):
            from ..proactive.briefing import get_live_weather
            w = get_live_weather()
            if w:
                return {"action": "weather", "args": {}, "reply": f"Current local conditions are {w}, Sir."}
            else:
                execute_action("search_google", {"query": "current weather"})
                return {"action": "search_google", "args": {"query": "current weather"}, "reply": "Displaying current weather forecast, Sir."}

        # ─── 1. Diagnostics, Battery & Telemetry ──────────────────────
        if any(k in text for k in [
            "battery", "cpu", "diagnostics", "telemetry",
            "system status", "system health", "system specs", "laptop specs", "hardware specs",
            "ram usage", "cpu usage", "system load"
        ]) or re.search(r"\b(?:ram|laptop battery|system memory)\b", text):
            telem = get_system_telemetry()
            return {
                "action": "get_telemetry",
                "args": {},
                "reply": f"Diagnostics online: CPU at {telem['cpu_percent']}%, RAM at {telem['ram_percent']}%, Battery at {telem['battery_percent']}% ({telem['battery_time']}). All sub-systems nominal, Sir."
            }

        # ─── 2. Time and Date ─────────────────────────────────────────
        if re.search(r"^(?:what(?:'s|\s+is)\s+the\s+time|what\s+time\s+is\s+it|tell\s+me\s+the\s+time|current\s+time|the\s+time|time\s+now)(?:\s+(?:right\s+now|now|please))?$", text):
            now_str = datetime.datetime.now().strftime("%I:%M %p")
            return {"action": "time", "args": {}, "reply": f"The current time is {now_str}, Sir."}

        if re.search(r"^(?:what(?:'s|\s+is)\s+(?:today(?:'s)?|the)\s+date|today(?:'s)?\s+date|what\s+is\s+today|what\s+day\s+is\s+it|current\s+date)(?:\s+(?:today|now|please))?$", text):
            date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return {"action": "date", "args": {}, "reply": f"Today is {date_str}, Sir."}

        # ─── 3. Screen Vision / Screenshot ────────────────────────────
        if any(k in text for k in ["scan screen", "take screenshot", "screenshot", "screen scan", "look at screen", "capture screen", "read screen", "see my screen"]):
            res = capture_screen_image()
            return {
                "action": "capture_screen",
                "args": {},
                "reply": "Optical display buffer captured, Sir." if res.get("success") else "Display capture buffer unavailable in this session."
            }

        # ─── 4. Workstation Security & Power ──────────────────────────
        if re.search(r"^(?:please\s+)?(?:lock|secure)\s+(?:the\s+|my\s+)?(?:pc|screen|computer|workstation|laptop)$", text) or text in ["lock screen", "lock pc", "lock computer", "lock workstation", "lock"]:
            execute_action("lock_workstation", {})
            return {"action": "lock_workstation", "args": {}, "reply": "Securing workstation. Screen locked, Sir."}

        if any(k in text for k in ["sleep pc", "sleep laptop", "put computer to sleep", "go to sleep"]):
            execute_action("sleep_pc", {})
            return {"action": "sleep_pc", "args": {}, "reply": "Entering suspend mode, Sir."}

        if any(k in text for k in ["empty recycle bin", "clean recycle bin", "empty trash", "purge bin", "clean bin", "clear bin"]):
            execute_action("empty_recycle_bin", {})
            return {"action": "empty_recycle_bin", "args": {}, "reply": "Recycle Bin purged, Sir."}

        # ─── 5. Volume & Audio Control ────────────────────────────────
        if any(k == text or text.startswith(k + " ") or text.endswith(" " + k) for k in ["mute", "unmute", "silence", "toggle mute", "mute volume", "mute audio", "mute sound"]):
            execute_action("set_volume", {"action": "mute"})
            return {"action": "set_volume", "args": {"action": "mute"}, "reply": "Audio state toggled, Sir."}

        vol_pct_match = re.search(r"^(?:set\s+)?volume\s+(?:to\s+)?(\d+)(?:%|\s*percent)?$", text)
        if vol_pct_match:
            pct = int(vol_pct_match.group(1))
            steps = max(1, min(50, int(pct / 2)))
            execute_action("set_volume", {"action": "up", "steps": steps})
            return {"action": "set_volume", "args": {"action": "set", "percent": pct}, "reply": f"Master volume set to {pct}%, Sir."}

        if any(k in text for k in ["volume up", "turn up volume", "turn volume up", "vol up", "increase volume", "raise volume", "raise the volume", "turn it up", "boost volume", "louder"]):
            execute_action("set_volume", {"action": "up", "steps": 6})
            return {"action": "set_volume", "args": {"action": "up"}, "reply": "Raising master volume, Sir."}

        if any(k in text for k in ["volume down", "turn down volume", "turn volume down", "vol down", "decrease volume", "lower volume", "lower the volume", "turn it down", "reduce volume", "quieter"]):
            execute_action("set_volume", {"action": "down", "steps": 6})
            return {"action": "set_volume", "args": {"action": "down"}, "reply": "Lowering master volume, Sir."}

        # ─── 6. Media Playback Controls ───────────────────────────────
        if text in ["pause", "resume", "play", "stop", "pause music", "stop music", "resume music", "play music", "play some music", "toggle music", "play songs", "pause songs"]:
            execute_action("control_media", {"command": "toggle"})
            return {"action": "control_media", "args": {"command": "toggle"}, "reply": "Media playback toggled, Sir."}

        if any(k in text for k in ["next song", "next track", "skip", "skip song", "next"]):
            execute_action("control_media", {"command": "next"})
            return {"action": "control_media", "args": {"command": "next"}, "reply": "Skipping to next track, Sir."}

        if any(k in text for k in ["previous song", "prev track", "last song", "back song", "previous track"]):
            execute_action("control_media", {"command": "previous"})
            return {"action": "control_media", "args": {"command": "previous"}, "reply": "Returning to previous track, Sir."}

        # ─── 7A. Play Nth YouTube Video / Search Result ─────────────
        ord_match = re.search(r"^(?:play|click|open|select)\s+(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|video\s+[1-5]|[1-5])\s*(?:video|result|one)?$", text)
        if ord_match or any(k in text for k in [
            "play the first video", "play first video", "play first result", "play the first result",
            "play the first one", "click the first video", "click first video", "click the first result",
            "click first result", "open the first video", "open first video", "open the first result",
            "play 1st video", "click 1st video", "play video 1", "click on the video", "click the video"
        ]):
            idx = 1
            if ord_match:
                raw_ord = ord_match.group(1).replace("video", "").strip()
                ord_map = {
                    "first": 1, "1st": 1, "1": 1,
                    "second": 2, "2nd": 2, "2": 2,
                    "third": 3, "3rd": 3, "3": 3,
                    "fourth": 4, "4th": 4, "4": 4,
                    "fifth": 5, "5th": 5, "5": 5
                }
                idx = ord_map.get(raw_ord, 1)

            res = execute_action("play_youtube_result", {"index": idx})
            return {
                "action": "play_youtube_result",
                "args": {"index": idx},
                "reply": res.get("message", f"Playing video result #{idx}, Sir.")
            }

        # ─── 7B. YouTube Search & Direct Video Auto-Play ───────────────
        yt_match = re.search(r"(?:search youtube for|play on youtube|search on youtube for|watch on youtube|youtube)\s+(.+)", text)
        if yt_match:
            q = yt_match.group(1).replace("on youtube", "").replace("youtube", "").strip()
            if q:
                res = execute_action("search_youtube", {"query": q})
                return {"action": "search_youtube", "args": {"query": q}, "reply": res.get("message", f"Playing '{q}' on YouTube, Sir.")}

        # "play <specific title>" (e.g. "play interstellar theme", "play faded")
        play_specific = re.search(r"^play\s+(.+)", text)
        if play_specific:
            target = play_specific.group(1).strip()
            # Clean trailing 'on youtube'
            target = re.sub(r"\s+on\s+youtube$", "", target).strip()
            # Guard against media control keywords and ordinals
            non_song_tokens = [
                "music", "song", "songs", "something", "audio", "it", "video", 
                "the video", "first video", "the first video", "second video", "the second video",
                "next", "previous", "pause"
            ]
            if target not in non_song_tokens and not re.match(r"^(?:the\s+)?(?:first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s*(?:video|result)?$", target):
                res = execute_action("search_youtube", {"query": target})
                return {"action": "search_youtube", "args": {"query": target}, "reply": res.get("message", f"Playing '{target}' on YouTube, Sir.")}

        # ─── 8. Google / Web Searches ─────────────────────────────────
        google_match = re.search(r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:search\s+(?:google|the\s+web|on\s+google)?\s*(?:for)?|google\s+for|google)\s+(.+?)(?:\s+for\s+me|\s+please)?$", text)
        if google_match:
            q = google_match.group(1).strip()
            q = re.sub(r"^(for|on google|in google)\s+", "", q).strip()
            if q and not re.match(r"^(?:is|was|has|will|can)\s+", q):
                execute_action("search_google", {"query": q})
                return {"action": "search_google", "args": {"query": q}, "reply": f"Searching Google for '{q}', Sir."}

        # ─── 9. Open Popular Websites directly ────────────────────────
        known_sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "reddit": "https://reddit.com",
            "twitter": "https://x.com",
            "x.com": "https://x.com",
            "netflix": "https://netflix.com",
            "chatgpt": "https://chatgpt.com",
            "gemini": "https://gemini.google.com",
            "spotify web": "https://open.spotify.com",
            "amazon": "https://amazon.com",
            "gmail": "https://mail.google.com",
            "linkedin": "https://linkedin.com",
            "instagram": "https://instagram.com"
        }
        for site_key, site_url in known_sites.items():
            if re.search(r"^(?:can\s+you\s+|please\s+)?(?:open|go\s+to|launch|visit)\s+" + re.escape(site_key) + r"\b", text) or text == site_key:
                execute_action("open_url", {"url": site_url})
                return {"action": "open_url", "args": {"url": site_url}, "reply": f"Opening {site_key.title()}, Sir."}

        # ─── 10. Close / Kill Applications ────────────────────────────
        close_match = re.search(r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:close|kill|terminate|exit|shut\s+down)\s+(.+?)(?:\s+for\s+me|\s+please)?$", text)
        if close_match:
            target = close_match.group(1).strip()
            target = re.sub(r"^(the|an|a|my)\s+", "", target).strip()
            if target and target not in ["this", "it", "down", "the door", "door", "window", "my eyes", "eyes", "working", "talking"]:
                res = execute_action("close_application", {"process_name": target})
                return {"action": "close_application", "args": {"process_name": target}, "reply": res.get("message", f"Closed {target}.")}

        # ─── 11. Open Applications & Folders ──────────────────────────
        open_match = re.search(r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:open|launch|start|run|switch\s+to)\s+(.+?)(?:\s+for\s+me|\s+please)?$", text)
        if open_match:
            target = open_match.group(1).strip()
            target = re.sub(r"^(the|an|a|my)\s+", "", target).strip()

            non_app_starters = ["up", "with", "about", "a ", "an ", "to ", "in ", "from ", "working", "thinking", "talking", "learning", "doing"]
            is_conversational = any(target == s or target.startswith(s + " ") for s in non_app_starters)

            if target and not is_conversational:
                # Check for folders
                if any(f in target for f in ["download", "document", "desktop", "picture", "photo", "music", "video"]):
                    f_res = execute_action("open_folder", {"folder_name": target})
                    if f_res.get("success"):
                        return {"action": "open_folder", "args": {"folder_name": target}, "reply": f_res.get("message")}

                res = execute_action("open_application", {"app_name": target})
                if res.get("success"):
                    return {"action": "open_application", "args": {"app_name": target}, "reply": res.get("message")}
                else:
                    f_res = execute_action("open_folder", {"folder_name": target})
                    if f_res.get("success"):
                        return {"action": "open_folder", "args": {"folder_name": target}, "reply": f_res.get("message")}
                    return {"action": "open_application", "args": {"app_name": target}, "reply": f"Searching for application '{target}', Sir."}

        # ─── 12. Jokes, Personality & Q&A ─────────────────────────────
        if text in ["tell me a joke", "tell a joke", "make me laugh", "joke"] or re.search(r"^(?:tell\s+(?:me\s+)?a\s+joke|make\s+me\s+laugh)$", text):
            joke = random.choice(LocalIntentParser.JOKES)
            return {"action": "joke", "args": {}, "reply": joke}

        if any(k in text for k in ["who are you", "what is your name", "what are you", "who made you"]):
            return {
                "action": "identity",
                "args": {},
                "reply": "I am Aether, your cybernetic assistant and intelligent operating system, running natively on your laptop, Sir."
            }

        if text in ["help", "commands", "show commands", "capabilities", "what can you do"] or re.search(r"^(?:what\s+can\s+you\s+do|show\s+(?:me\s+)?commands)$", text):
            return {
                "action": "help",
                "args": {},
                "reply": "I can launch any Windows app, adjust volume, control media, lock your PC, check battery & CPU telemetry, search Google and YouTube, capture your display, and converse via voice, Sir."
            }

        if text in ["how are you", "how are you doing", "what's up", "whats up"] or re.search(r"^how\s+(?:are\s+you|are\s+you\s+doing)$", text):
            return {
                "action": "greeting",
                "args": {},
                "reply": "All sensory arrays and background threads are operating at peak efficiency, Sir. How may I assist you?"
            }

        if any(k in text for k in ["thank you", "thanks", "good job", "well done", "awesome"]):
            return {
                "action": "thanks",
                "args": {},
                "reply": "Always a pleasure to be of service, Sir."
            }

        if (text in ["hello", "hi", "hey", "aether", "jarvis", "piko", "wake up", "online", "are you there"]
            or (re.search(r"^(?:hello|hi|hey|aether|jarvis|piko)(?:\s+(?:aether|jarvis|piko|there))?$", text))):
            return {"action": "salutation", "args": {}, "reply": "Online and standing by, Sir. What are your directives?"}

        # ─── 13. Standalone Single Word App (Exact Match only) ─────────
        from ..actions.app_actions import COMMON_SHORTCUTS, _INSTALLED_APPS_CACHE
        words = text.split()
        if len(words) <= 2:
            clean_word = text.strip()
            if clean_word in COMMON_SHORTCUTS or clean_word in _INSTALLED_APPS_CACHE:
                res = execute_action("open_application", {"app_name": clean_word})
                if res.get("success"):
                    return {"action": "open_application", "args": {"app_name": clean_word}, "reply": res.get("message")}

        # ─── Default Fallback ─────────────────────────────────────────
        return {
            "action": None,
            "args": {},
            "reply": f"Directive acknowledged: '{user_text}'. (To enable open-ended reasoning, add your Gemini API Key in Settings)."
        }
