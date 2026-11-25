from .app_actions import open_application, close_application
from .system_actions import (
    set_volume, lock_workstation, sleep_pc, empty_recycle_bin, open_folder, open_file,
    ring_phone, get_phone_battery, send_phone_whatsapp, send_phone_sms,
    toggle_phone_torch, sync_clipboard_to_phone, get_mobile_link_status
)
from .media_actions import control_media
from .web_actions import search_google, search_youtube, open_url, play_first_youtube_result, play_youtube_result
from .vision_actions import capture_screen_image, capture_active_window_image
from .webcam_actions import capture_webcam_frame
from .computer_use import (
    mouse_move, mouse_click, mouse_drag, mouse_scroll,
    keyboard_type, keyboard_hotkey, keyboard_press,
    get_active_window_info, focus_window, list_open_windows,
    find_files, read_document_text, draft_in_notepad, run_system_command,
    find_and_click_element, find_and_type
)
from ..core.telemetry import get_system_telemetry
from ..core.undo import undo_last
from ..core.confirm import resolve as resolve_confirm
from ..environment import (
    get_peripheral_snapshot, switch_display_mode,
    set_ambient_lighting, toggle_desk_lamp, toggle_smart_plug, set_environment_preset,
    run_compiler_diagnostics, hot_patch_file, diagnose_code_error
)

# Lazy singleton for Second Brain memory store
_SECOND_BRAIN_INSTANCE = None
def _get_second_brain():
    global _SECOND_BRAIN_INSTANCE
    if _SECOND_BRAIN_INSTANCE is None:
        from ..memory.second_brain import SecondBrain
        _SECOND_BRAIN_INSTANCE = SecondBrain()
    return _SECOND_BRAIN_INSTANCE


def _gated_terminal_command(args: dict) -> dict:
    """Gate terminal commands behind UI confirmation."""
    from ..core.confirm import request_and_wait
    command = args.get("command", "")
    cwd = args.get("cwd", "")
    timeout = args.get("timeout", 60)
    background = args.get("background", False)
    
    accepted, msg = request_and_wait(
        key="terminal_command",
        title="Terminal Command",
        detail=f"Run: {command[:80]}{'...' if len(command) > 80 else ''}",
        run=lambda: run_system_command(command, cwd or None, timeout, background),
        timeout=30
    )
    if not accepted:
        return {"success": False, "message": msg}
    if isinstance(msg, dict):
        return msg
    return {"success": True, "message": msg}


def _gated_hot_patch(args: dict) -> dict:
    """Gate hot patch operations behind UI confirmation."""
    from ..core.confirm import request_and_wait
    file_path = args.get("file_path", "")
    target = args.get("target_snippet", "")[:60]
    replacement = args.get("replacement_snippet", "")[:60]
    
    accepted, msg = request_and_wait(
        key="hot_patch",
        title="Code Patch",
        detail=f"Patch {file_path}: '{target}' -> '{replacement}'",
        run=lambda: hot_patch_file(
            file_path,
            args.get("target_snippet", ""),
            args.get("replacement_snippet", ""),
            args.get("verify_compile", True)
        ),
        timeout=30
    )
    if not accepted:
        return {"success": False, "message": msg}
    if isinstance(msg, dict):
        return msg
    return {"success": True, "message": msg}


# Registry of callable tools
ACTION_REGISTRY = {
    # System & App Controls
    "open_application": lambda args: open_application(args.get("app_name", "")),
    "close_application": lambda args: close_application(args.get("process_name", "")),
    "set_volume": lambda args: set_volume(args.get("action", "up"), args.get("steps", 5)),
    "lock_workstation": lambda args: lock_workstation(),
    "sleep_pc": lambda args: sleep_pc(),
    "empty_recycle_bin": lambda args: empty_recycle_bin(),
    "open_folder": lambda args: open_folder(args.get("folder_name", "")),
    "open_file": lambda args: open_file(args.get("file_path", "")),
    "control_media": lambda args: control_media(args.get("command", "toggle")),
    "capture_active_window": lambda args: capture_active_window_image(),
    "capture_webcam": lambda args: capture_webcam_frame(),
    "search_google": lambda args: search_google(args.get("query", "")),
    "search_youtube": lambda args: search_youtube(args.get("query", "")),
    "play_first_youtube_result": lambda args: play_first_youtube_result(),
    "play_youtube_result": lambda args: play_youtube_result(args.get("index", 1)),
    "open_url": lambda args: open_url(args.get("url", "")),
    "get_telemetry": lambda args: get_system_telemetry(),

    # Pillar 2: Autonomous OS Action (True "Computer Use")
    "mouse_move": lambda args: mouse_move(args.get("x", 0), args.get("y", 0), args.get("smooth", True)),
    "mouse_click": lambda args: mouse_click(args.get("x"), args.get("y"), args.get("button", "left"), args.get("clicks", 1)),
    "mouse_drag": lambda args: mouse_drag(args.get("start_x", 0), args.get("start_y", 0), args.get("end_x", 0), args.get("end_y", 0)),
    "mouse_scroll": lambda args: mouse_scroll(args.get("clicks", 3), args.get("direction", "down")),
    "keyboard_type": lambda args: keyboard_type(args.get("text", ""), args.get("press_enter", False), args.get("use_clipboard", False)),
    "keyboard_hotkey": lambda args: keyboard_hotkey(args.get("keys", "")),
    "keyboard_press": lambda args: keyboard_press(args.get("key", "enter")),
    "get_active_window": lambda args: get_active_window_info(),
    "focus_window": lambda args: focus_window(args.get("title", "")),
    "list_open_windows": lambda args: {"success": True, "windows": list_open_windows()},
    "find_files": lambda args: {"success": True, "files": find_files(args.get("query", ""), None, args.get("extensions"), args.get("days_back"), args.get("limit", 10))},
    "read_document": lambda args: read_document_text(args.get("file_path", "")),
    "draft_in_notepad": lambda args: draft_in_notepad(args.get("content", ""), args.get("filename")),
    "run_terminal_command": lambda args: _gated_terminal_command(args),
    "find_and_click_element": lambda args: find_and_click_element(args.get("name_or_label", "")),
    "find_and_type": lambda args: find_and_type(args.get("name_or_label", ""), args.get("text", "")),
    "undo": lambda args: {"success": True, "message": undo_last()},
    "confirm_action": lambda args: {"success": True, "message": "Confirmation resolved." if resolve_confirm(args.get("accepted", True)) else "No confirmation was pending."},
    "hot_patch_file": lambda args: _gated_hot_patch(args),

    # Pillar 3: Infinite Episodic & Project Memory (The Second Brain)
    "save_memory_fact": lambda args: {"success": True, "fact_id": _get_second_brain().store.save_fact(args.get("category", "general"), args.get("entity", "system"), args.get("content", ""))},
    "recall_memory": lambda args: {"success": True, "facts": _get_second_brain().store.search_facts(args.get("query", ""), args.get("limit", 5))},
    "search_codebase": lambda args: {"success": True, "code_chunks": _get_second_brain().store.search_codebase(args.get("query", ""), args.get("project_name"), args.get("limit", 5))},
    "index_codebase": lambda args: _get_second_brain().store.index_directory(args.get("path", "."), args.get("project_name")),
    "get_memory_stats": lambda args: {"success": True, "stats": _get_second_brain().store.get_memory_stats()},

    # Pillar 5: Multi-System & Environment Orchestration
    "get_peripherals": lambda args: get_peripheral_snapshot(),
    "switch_display": lambda args: switch_display_mode(args.get("mode", "extend")),
    "set_ambient_lighting": lambda args: set_ambient_lighting(args.get("color"), args.get("brightness"), args.get("state")),
    "toggle_desk_lamp": lambda args: toggle_desk_lamp(args.get("state")),
    "toggle_smart_plug": lambda args: toggle_smart_plug(args.get("device", "desk"), args.get("state")),
    "set_environment_preset": lambda args: set_environment_preset(args.get("preset", "coding_focus")),
    "diagnose_compiler_error": lambda args: run_compiler_diagnostics(args.get("target", ""), args.get("cwd")),
    "diagnose_code_traceback": lambda args: diagnose_code_error(args.get("error_log", ""), args.get("code_context")),

    # Aether Mobile Companion Tele-Link
    "ring_phone": lambda args: ring_phone(),
    "get_phone_battery": lambda args: get_phone_battery(),
    "send_phone_whatsapp": lambda args: send_phone_whatsapp(args.get("contact", ""), args.get("message", "")),
    "send_phone_sms": lambda args: send_phone_sms(args.get("contact", ""), args.get("message", "")),
    "toggle_phone_torch": lambda args: toggle_phone_torch(args.get("enabled", True)),
    "sync_clipboard_to_phone": lambda args: sync_clipboard_to_phone(),
    "get_mobile_link_status": lambda args: get_mobile_link_status(),
}

def execute_action(action_name: str, args: dict) -> dict:
    handler = ACTION_REGISTRY.get(action_name)
    if handler:
        try:
            return handler(args or {})
        except Exception as e:
            return {"success": False, "message": f"Execution error in {action_name}: {str(e)}"}
    return {"success": False, "message": f"Action '{action_name}' is not recognized."}

# Tool declarations for Gemini and OpenRouter (Strict OpenAPI 3.0 schema)
GEMINI_TOOLS = [
    {
        "name": "open_application",
        "description": "Opens or launches an installed Windows application or software, such as Chrome, VS Code, Discord, Spotify, Notepad, Calculator, Android Studio, Terminal, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "The name of the application to open (e.g. 'chrome', 'vscode', 'android studio', 'spotify', 'calculator')."}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "close_application",
        "description": "Closes or terminates a running Windows program or process.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "process_name": {"type": "STRING", "description": "The name of the process/application to close (e.g. 'chrome', 'spotify', 'notepad')."}
            },
            "required": ["process_name"]
        }
    },
    {
        "name": "set_volume",
        "description": "Adjusts Windows master sound volume: up, down, or mute/unmute.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'up', 'down', or 'mute'"},
                "steps": {"type": "INTEGER", "description": "How many increments (default 5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "control_media",
        "description": "Controls audio/media playback on Windows (Spotify, YouTube, video/audio players).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "'play', 'pause', 'toggle', 'next', 'previous', 'stop'"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "get_telemetry",
        "description": "Retrieves real-time Windows laptop diagnostic telemetry: CPU %, RAM %, Battery %, Storage, Uptime.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "capture_webcam",
        "description": "Captures a single optical frame from the user's laptop webcam. Use when the user asks to look at them, examine what they are holding, describe their surroundings, or read a physical item in front of the camera.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "search_google",
        "description": "Performs a web search on Google in the default browser.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search term or query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_youtube",
        "description": "Searches YouTube for videos or music.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Video or song title to search for on YouTube"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_first_youtube_result",
        "description": "Selects, clicks, and plays the first video result on YouTube in the active browser.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "open_url",
        "description": "Opens a specific website URL in the browser.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "The URL to open, e.g. 'https://github.com'"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "open_folder",
        "description": "Opens a Windows Explorer folder such as Downloads, Documents, Desktop, Pictures, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "folder_name": {"type": "STRING", "description": "Folder name or path, e.g. 'Downloads', 'Documents'"}
            },
            "required": ["folder_name"]
        }
    },
    {
        "name": "lock_workstation",
        "description": "Locks the Windows PC workstation / screen immediately.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "sleep_pc",
        "description": "Puts the Windows laptop into sleep/suspend mode.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "empty_recycle_bin",
        "description": "Empties the Windows Recycle Bin to free up disk space.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    # ─── Pillar 2: Computer Use Tools ──────────────────────────────────────────
    {
        "name": "mouse_move",
        "description": "Moves the Windows mouse cursor to target screen coordinates (x, y).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "x": {"type": "INTEGER", "description": "Target X pixel coordinate"},
                "y": {"type": "INTEGER", "description": "Target Y pixel coordinate"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "mouse_click",
        "description": "Clicks at the specified screen coordinates or current cursor location (left, right, or double-click).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "x": {"type": "INTEGER", "description": "Optional X coordinate to click at"},
                "y": {"type": "INTEGER", "description": "Optional Y coordinate to click at"},
                "button": {"type": "STRING", "description": "'left', 'right', or 'middle' (default 'left')"},
                "clicks": {"type": "INTEGER", "description": "1 for single click, 2 for double click"}
            }
        }
    },
    {
        "name": "mouse_drag",
        "description": "Drags mouse cursor from (start_x, start_y) to (end_x, end_y).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "start_x": {"type": "INTEGER", "description": "Start X"},
                "start_y": {"type": "INTEGER", "description": "Start Y"},
                "end_x": {"type": "INTEGER", "description": "End X"},
                "end_y": {"type": "INTEGER", "description": "End Y"}
            },
            "required": ["start_x", "start_y", "end_x", "end_y"]
        }
    },
    {
        "name": "mouse_scroll",
        "description": "Scrolls the mouse wheel up or down by a given number of increments.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "clicks": {"type": "INTEGER", "description": "Number of scroll notches (default 3)"},
                "direction": {"type": "STRING", "description": "'up' or 'down' (default 'down')"}
            }
        }
    },
    {
        "name": "keyboard_type",
        "description": "Types text into the active focused window or text box on Windows.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "The exact text string to type"},
                "press_enter": {"type": "BOOLEAN", "description": "Whether to press Enter after typing"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "keyboard_hotkey",
        "description": "Presses a keyboard shortcut combo on Windows (e.g. 'ctrl+c', 'ctrl+v', 'win+r', 'alt+tab', 'ctrl+s', 'enter', 'esc').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "keys": {"type": "STRING", "description": "Shortcut key combination, e.g. 'ctrl+c', 'ctrl+v', 'win+d', 'alt+f4'"}
            },
            "required": ["keys"]
        }
    },
    {
        "name": "keyboard_press",
        "description": "Presses an individual keyboard key such as 'enter', 'escape', 'tab', 'backspace', 'space', 'up', 'down'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Key name (e.g. 'enter', 'tab', 'esc', 'space', 'backspace')"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "focus_window",
        "description": "Brings a running application window to the foreground by matching its window title.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Application or window title keyword (e.g. 'Chrome', 'Visual Studio', 'Android Studio', 'Notepad')"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "find_files",
        "description": "Locates files across Downloads, Documents, and Desktop matching keywords and recency (e.g. 'neural networks', 'research paper', 'APK').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Keywords or search term"},
                "days_back": {"type": "INTEGER", "description": "Optional filter for files modified within the last N days (e.g. 1 for yesterday)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_document",
        "description": "Extracts full text content from a local file (PDF, TXT, MD, Python, JSON, code, or logs).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Absolute or relative path to the file"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "draft_in_notepad",
        "description": "Creates a text summary file on Desktop and immediately launches Notepad focused with the drafted text.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "content": {"type": "STRING", "description": "Text or summary content to draft"},
                "filename": {"type": "STRING", "description": "Optional filename (e.g. 'Research_Summary.txt')"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "run_terminal_command",
        "description": "Executes a terminal/PowerShell command (e.g. 'git pull', 'gradlew assembleDebug', 'npm test', 'python script.py') and returns terminal output.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "Shell command to run"},
                "cwd": {"type": "STRING", "description": "Optional working directory"}
            },
            "required": ["command"]
        }
    },
    # ─── Pillar 3: Infinite Episodic & Project Memory Tools ────────────────────
    {
        "name": "save_memory_fact",
        "description": "Saves a permanent fact, preference, person, or project detail into the user's Second Brain memory database.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING", "description": "Category e.g. 'preference', 'team', 'project', 'system'"},
                "entity": {"type": "STRING", "description": "Entity key e.g. 'coding_style', 'rahul', 'auth_module'"},
                "content": {"type": "STRING", "description": "The exact fact statement to remember"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "recall_memory",
        "description": "Searches the Second Brain episodic memory database for stored facts, preferences, and teammates.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Semantic query or entity to look up in memory"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_codebase",
        "description": "Performs full-text semantic search (RAG) across the user's indexed project files, functions, and endpoints.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Code search term or question, e.g. 'auth endpoint', 'database connection'"},
                "project_name": {"type": "STRING", "description": "Optional project identifier"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "index_codebase",
        "description": "Recursively indexes a project directory into the Second Brain vector database for future semantic RAG recall.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Absolute or relative path of the directory to index"},
                "project_name": {"type": "STRING", "description": "Optional project name"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "get_memory_stats",
        "description": "Retrieves real-time statistics of the Second Brain (total facts, indexed files, code blocks, conversation count).",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "get_peripherals",
        "description": "Scans active laptop peripherals, multi-monitor display topology, audio output endpoints (headphones vs speakers), paired Bluetooth devices, and Wi-Fi network telemetry.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "switch_display",
        "description": "Switches multi-monitor display configuration on Windows: 'extend', 'clone' / 'duplicate', 'internal' (PC screen only), or 'external' (second screen only).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mode": {"type": "STRING", "description": "'extend', 'clone', 'internal', or 'external'"}
            },
            "required": ["mode"]
        }
    },
    {
        "name": "set_ambient_lighting",
        "description": "Controls smart room ambient lighting, desk LED strips, and smart bulbs. Adjusts color (e.g. 'solaris', 'gold', 'blue', 'cyan', 'warm amber', 'red', 'white'), brightness (0-100), or state ('on'/'off').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "color": {"type": "STRING", "description": "Color name or hex code"},
                "brightness": {"type": "INTEGER", "description": "Brightness 0 to 100"},
                "state": {"type": "STRING", "description": "'on' or 'off'"}
            }
        }
    },
    {
        "name": "toggle_desk_lamp",
        "description": "Toggles or sets the desk task lamp on or off.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "state": {"type": "STRING", "description": "'on', 'off', or 'toggle'"}
            }
        }
    },
    {
        "name": "toggle_smart_plug",
        "description": "Toggles or sets IoT smart plugs for desk hardware, speakers, monitors, or fans.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "device": {"type": "STRING", "description": "'desk', 'monitor', 'speakers', 'fan'"},
                "state": {"type": "STRING", "description": "'on' or 'off'"}
            },
            "required": ["device"]
        }
    },
    {
        "name": "set_environment_preset",
        "description": "Applies a synchronized multi-system environment preset: 'coding_focus' (dual screens, focus lighting, desk lamp), 'cinematic' (dim ambient, single display), 'daylight' (100% white, full lighting), 'alert' (red pulse), or 'nominal'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "preset": {"type": "STRING", "description": "'coding_focus', 'cinematic', 'daylight', 'alert', 'nominal'"}
            },
            "required": ["preset"]
        }
    },
    {
        "name": "diagnose_compiler_error",
        "description": "Acts as a pair programmer: runs compiler checks, syntax analysis, and unit tests on a file or command, isolating tracebacks and line numbers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "Python file name or build/test command (e.g. 'main.py', 'pytest', 'py test.py')"},
                "cwd": {"type": "STRING", "description": "Optional working directory"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "diagnose_code_traceback",
        "description": "Analyzes a raw compiler error or Python stack trace and provides root-cause diagnosis and suggested repair instructions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "error_log": {"type": "STRING", "description": "Raw traceback or compiler error message"},
                "code_context": {"type": "STRING", "description": "Optional source code lines around the error"}
            },
            "required": ["error_log"]
        }
    },
    {
        "name": "hot_patch_file",
        "description": "Hot-patches a source code file with atomic safety: creates a backup (.bak), applies the replacement, validates syntax, and automatically rolls back if syntax errors occur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {"type": "STRING", "description": "Path to the file to patch"},
                "target_snippet": {"type": "STRING", "description": "The exact existing code snippet to replace"},
                "replacement_snippet": {"type": "STRING", "description": "The new replacement code"},
                "verify_compile": {"type": "BOOLEAN", "description": "Whether to verify syntax and rollback on failure (default true)"}
            },
            "required": ["file_path", "target_snippet", "replacement_snippet"]
        }
    },
    {
        "name": "undo",
        "description": "Reverses the most recent reversible action (volume change, lighting preset, etc.) from the 10-turn LIFO stack.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "find_and_click_element",
        "description": "Finds a button, link, tab, or interactive UI control on screen using Windows UI Automation accessibility tree and clicks its exact center.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name_or_label": {"type": "STRING", "description": "The visible text label or accessibility name of the button/control to click"}
            },
            "required": ["name_or_label"]
        }
    },
    {
        "name": "find_and_type",
        "description": "Finds an input field or text box by label/name, activates it, and types text into it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name_or_label": {"type": "STRING", "description": "The label or placeholder of the input field"},
                "text": {"type": "STRING", "description": "The text string to type into the field"}
            },
            "required": ["name_or_label", "text"]
        }
    }
]
