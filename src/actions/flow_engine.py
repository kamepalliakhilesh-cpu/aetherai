"""
Command Flow & Multi-Step Execution Engine for Aether / Piko.
Decomposes compound directives, sequential commands, and idiomatic workflows
into ordered executions with detailed progress tracking.
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .executor import execute_action
from .app_actions import COMMON_SHORTCUTS, _INSTALLED_APPS_CACHE, open_application
from .system_actions import open_folder, open_file

class CommandFlowEngine:
    """
    Orchestrates compound multi-step command sequences:
    1. Idiomatic compound patterns (App + Type, App + Search, Multi-App, Find + Open)
    2. Sequential chaining via conjunctions ('and then', 'then', ', then', 'after that', ';', 'and')
    """

    @classmethod
    def try_execute_flow(cls, user_text: str, single_parser_func) -> Optional[Dict[str, Any]]:
        """
        Attempts to detect and execute a multi-step flow or compound command.
        Returns None if user_text is a single simple directive or open-ended reasoning.
        """
        raw = user_text.strip()
        lower = raw.lower()
        # Clean trailing punctuation
        lower = re.sub(r"[?!.,]+$", "", lower).strip()

        # ─── Pattern 0: Focus Session (Golden Path Demo)
        focus_res = cls._try_focus_session(lower, raw)
        if focus_res:
            return focus_res

        # ─── Pattern 1: App + Write / Type / Draft ────────────────────────────
        # e.g. "open notepad and write hello world", "launch notepad then type meeting notes"
        app_type_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:open|launch|start)\s+([a-zA-Z0-9_\-\s]+?)\s+(?:and\s+then|,?\s*then|and\s+also|and)?\s*(?:write|type|draft|enter)\s+(.+)$",
            lower
        )
        if app_type_match:
            raw_target = app_type_match.group(1).strip()
            app_target = re.sub(r"\b(then|and then|and)\b", "", raw_target).strip()
            content_to_type = raw[app_type_match.start(2):app_type_match.end(2)].strip()
            # Clean outer quotes if present
            content_to_type = content_to_type.strip("\"'")

            if cls._is_known_app(app_target):
                open_res = open_application(app_target)
                time.sleep(0.4) # Allow window to render and receive focus
                type_res = execute_action("keyboard_type", {"text": content_to_type, "press_enter": True})

                steps = [
                    f"Launched {app_target.title()}",
                    f"Typed: '{content_to_type}'"
                ]
                return {
                    "action": "flow_execution",
                    "args": {"app": app_target, "typed": content_to_type},
                    "steps": steps,
                    "reply": f"Opened {app_target.title()} and entered text, Sir.",
                    "is_local": True
                }

        # ─── Pattern 2: Browser/App + Search ──────────────────────────────────
        # e.g. "open chrome and search for quantum computing", "open youtube and search interstellar"
        app_search_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:open|launch|start|go to)\s+(chrome|edge|brave|firefox|browser|google|youtube)\s+(?:and\s+)?(?:search(?:\s+for|\s+on|\s+in)?|look up|google|find)\s+(.+)$",
            lower
        )
        if app_search_match:
            browser_target = app_search_match.group(1).strip()
            query_text = raw[app_search_match.start(2):app_search_match.end(2)].strip()
            query_text = re.sub(r"^(?:for|on google|in google|on youtube)\s+", "", query_text, flags=re.IGNORECASE).strip()

            if browser_target == "youtube":
                s_res = execute_action("search_youtube", {"query": query_text})
                steps = [
                    "Opened YouTube",
                    f"Searched & playing: '{query_text}'"
                ]
                return {
                    "action": "flow_execution",
                    "args": {"target": "youtube", "query": query_text},
                    "steps": steps,
                    "reply": f"Opened YouTube and searched for '{query_text}', Sir.",
                    "is_local": True
                }
            else:
                s_res = execute_action("search_google", {"query": query_text})
                steps = [
                    f"Opened {browser_target.title()}",
                    f"Searched Google for: '{query_text}'"
                ]
                return {
                    "action": "flow_execution",
                    "args": {"target": browser_target, "query": query_text},
                    "steps": steps,
                    "reply": f"Searching Google for '{query_text}', Sir.",
                    "is_local": True
                }

        # ─── Pattern 3: Multi-App Launch ──────────────────────────────────────
        # e.g. "open calculator and notepad", "launch chrome and spotify", "open downloads and documents"
        multi_app_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:open|launch|start)\s+([a-zA-Z0-9_\-\s,]+?\s+and\s+[a-zA-Z0-9_\-\s]+)$",
            lower
        )
        if multi_app_match:
            remainder = multi_app_match.group(1).strip()
            # Split by comma or 'and'
            parts = [p.strip() for p in re.split(r",|\band\b", remainder) if p.strip()]
            if len(parts) >= 2:
                # Check if all parts are recognized apps or folders
                apps_or_folders = []
                for p in parts:
                    clean_p = p.replace("the", "").replace("my", "").strip()
                    if cls._is_known_app(clean_p) or cls._is_known_folder(clean_p):
                        apps_or_folders.append(clean_p)

                if len(apps_or_folders) == len(parts):
                    steps = []
                    for item in apps_or_folders:
                        if cls._is_known_folder(item):
                            f_res = open_folder(item)
                            steps.append(f"Opened folder: {item.title()}")
                        else:
                            a_res = open_application(item)
                            steps.append(f"Launched {item.title()}")
                        time.sleep(0.15)

                    names_str = " and ".join([i.title() for i in apps_or_folders])
                    return {
                        "action": "flow_execution",
                        "args": {"targets": apps_or_folders},
                        "steps": steps,
                        "reply": f"Launched {names_str}, Sir.",
                        "is_local": True
                    }

        # ─── Pattern 4: Find File + Open It ───────────────────────────────────
        # e.g. "find file notes and open it", "locate report.pdf and open"
        find_open_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:find|locate|search\s+for)\s+(?:file|document|pdf)?\s*([a-zA-Z0-9_\-\.\s]+?)\s+and\s+(?:open|launch|view)\s*(?:it|the\s+file)?$",
            lower
        )
        if find_open_match:
            target_query = find_open_match.group(1).strip()
            f_res = execute_action("find_files", {"query": target_query, "limit": 3})
            files = f_res.get("files", [])
            if files:
                first_file = files[0]
                open_res = open_file(first_file["path"])
                steps = [
                    f"Located file: {first_file['name']}",
                    f"Opened in default viewer: {first_file['name']}"
                ]
                return {
                    "action": "flow_execution",
                    "args": {"query": target_query, "file": first_file["path"]},
                    "steps": steps,
                    "reply": f"Located and opened '{first_file['name']}', Sir.",
                    "is_local": True
                }
            else:
                return {
                    "action": "find_files",
                    "args": {"query": target_query},
                    "steps": [f"Searched storage for: {target_query}"],
                    "reply": f"No files found matching '{target_query}', Sir.",
                    "is_local": True
                }

        # ─── Pattern 5: Explicit Sequential Conjunctions ──────────────────────
        # e.g. "mute volume and then lock pc", "turn up volume, then play music"
        seq_delimiters = [
            r"\s+and\s+then\s+",
            r",\s+then\s+",
            r"\s+then\s+",
            r"\s+after\s+that\s+",
            r"\s+and\s+also\s+",
            r";\s*"
        ]
        for delim in seq_delimiters:
            if re.search(delim, lower):
                raw_segments = re.split(delim, raw, flags=re.IGNORECASE)
                segments = [s.strip() for s in raw_segments if s.strip()]
                if len(segments) >= 2:
                    flow_res = cls._execute_subcommand_sequence(segments, single_parser_func)
                    if flow_res:
                        return flow_res

        # ─── Pattern 6: Compound Conjunction ' and ' ──────────────────────────
        # e.g. "mute and lock pc", "turn up volume and play music", "take screenshot and open downloads"
        if " and " in lower:
            # Avoid splitting open-ended conversational questions
            if not any(lower.startswith(w) for w in ["what", "who", "why", "where", "how", "when", "is", "can you explain"]):
                segments = [s.strip() for s in raw.split(" and ") if s.strip()]
                if len(segments) == 2:
                    flow_res = cls._execute_subcommand_sequence(segments, single_parser_func)
                    if flow_res:
                        return flow_res

        return None

    # Pattern 7: Focus Session (Demo Golden Path)
    @classmethod
    def _try_focus_session(cls, lower: str, raw: str):
        focus_triggers = [
            "focus session", "start focus", "begin focus", "focus mode",
            "coding session", "start coding", "dev session", "deep work"
        ]
        if not any(t in lower for t in focus_triggers):
            return None

        # Default distracting apps to close
        distract_apps = ["discord", "spotify", "slack", "teams", "steam", "epic games", "battle.net"]
        # Default productive apps to open
        productive_apps = ["vscode", "visual studio code", "code"]

        steps = []
        closed_apps = []  # Track apps that were actually closed
        opened_apps = []  # Track apps that were actually opened

        # 1. Close distracting apps (only if running)
        for app in distract_apps:
            if cls._is_known_app(app):
                close_res = execute_action("close_application", {"process_name": app})
                if close_res.get("success"):
                    steps.append("Closed " + app.title())
                    closed_apps.append(app)
                time.sleep(0.1)

        # 2. Open productive apps
        for app in productive_apps:
            if cls._is_known_app(app):
                open_res = execute_action("open_application", {"app_name": app})
                if open_res.get("success"):
                    steps.append("Launched " + app.title())
                    opened_apps.append(app)
                time.sleep(0.2)

        # 3. Open project folder
        folder_opened = False
        try:
            folder_res = execute_action("open_folder", {"folder_name": "documents"})
            if folder_res.get("success"):
                steps.append("Opened Documents folder")
                folder_opened = True
        except Exception:
            pass

        # 4. Set volume to moderate level
        vol_res = execute_action("set_volume", {"action": "up", "steps": 25})
        if vol_res.get("success"):
            steps.append("Set volume to ~50%")

        # 5. Save preference to memory
        try:
            from ..memory.second_brain import SecondBrain
            sb = SecondBrain()
            sb.store.save_fact("preferences", "focus_session", "User prefers VS Code + quiet environment for focus sessions")
            steps.append("Saved focus preference to memory")
        except Exception:
            pass

        # 6. Add real undo: reopen closed apps, close opened apps
        if closed_apps or opened_apps:
            try:
                from ..core.undo import push_undo
                def _undo_focus():
                    undone = []
                    # Reopen apps that were closed
                    for app in closed_apps:
                        execute_action("open_application", {"app_name": app})
                        undone.append(f"Reopened {app}")
                    # Close apps that were opened
                    for app in opened_apps:
                        execute_action("close_application", {"process_name": app})
                        undone.append(f"Closed {app}")
                    return "; ".join(undone) if undone else "Nothing to revert"
                push_undo("Focus session", _undo_focus)
                steps.append("Undo available: say 'undo' to restore apps")
            except Exception:
                pass
        elif not steps:
            # No actions actually took place
            steps.append("No apps to close or open")

        # Build honest reply
        if not steps or (not closed_apps and not opened_apps):
            reply = "Focus session: no distracting apps found to close, no productive apps launched. Say 'undo' does nothing."
        else:
            parts = []
            if closed_apps:
                parts.append(f"closed {len(closed_apps)} app(s)")
            if opened_apps:
                parts.append(f"launched {len(opened_apps)} app(s)")
            if folder_opened:
                parts.append("opened Documents")
            reply = "Focus session: " + ", ".join(parts) + ". Say 'undo' to revert."

        return {
            "action": "flow_execution",
            "args": {"flow": "focus_session"},
            "steps": steps,
            "reply": reply,
            "is_local": True
        }

    @classmethod
    def _execute_subcommand_sequence(cls, segments: List[str], single_parser_func) -> Optional[Dict[str, Any]]:
        """
        Evaluates a list of subcommand strings. If at least 2 produce valid actions,
        executes them in strict sequence and returns an aggregated flow result.
        """
        parsed_actions = []
        for seg in segments:
            res = single_parser_func(seg)
            if res and res.get("action") is not None:
                parsed_actions.append((seg, res))

        # Only proceed if every segment is a recognized actionable command
        if len(parsed_actions) >= 2 and len(parsed_actions) == len(segments):
            steps = []
            executed_names = []

            for seg_text, p_res in parsed_actions:
                act = p_res.get("action")
                args = p_res.get("args", {})

                # If the action wasn't executed inside single_parser, execute it now
                ex_res = execute_action(act, args)
                time.sleep(0.1)

                msg = p_res.get("reply") or ex_res.get("message") or f"Executed {act}."
                clean_step = cls._format_step_summary(act, seg_text, msg)
                steps.append(clean_step)
                executed_names.append(act)

            reply = f"Completed {len(steps)} sequential directives, Sir."
            return {
                "action": "flow_execution",
                "args": {"sub_actions": executed_names},
                "steps": steps,
                "reply": reply,
                "is_local": True
            }

        return None

    @staticmethod
    def _is_known_app(name: str) -> bool:
        clean = name.lower().strip()
        if clean in COMMON_SHORTCUTS:
            return True
        if clean in _INSTALLED_APPS_CACHE:
            return True
        for k in COMMON_SHORTCUTS.keys():
            if clean in k or k in clean:
                return True
        return False

    @staticmethod
    def _is_known_folder(name: str) -> bool:
        clean = name.lower().strip()
        return any(f in clean for f in ["download", "document", "desktop", "picture", "photo", "music", "video"])

    @staticmethod
    def _format_step_summary(action: str, segment: str, reply: str) -> str:
        """Formats a concise human-readable step label for the UI checklist"""
        if action == "open_application":
            return f"Launched {segment.replace('open', '').replace('launch', '').strip().title()}"
        elif action == "close_application":
            return f"Closed {segment.replace('close', '').replace('kill', '').strip().title()}"
        elif action == "set_volume":
            return "Adjusted audio volume"
        elif action == "lock_workstation":
            return "Locked workstation"
        elif action == "control_media":
            return "Toggled media playback"
        elif action == "capture_screen":
            return "Captured display buffer"
        elif action == "empty_recycle_bin":
            return "Purged Recycle Bin"
        elif action == "open_folder":
            return f"Opened {segment.replace('open', '').strip().title()} folder"
        elif action == "keyboard_hotkey":
            return "Dispatched desktop shortcut"
        return reply.split(",")[0].strip()
