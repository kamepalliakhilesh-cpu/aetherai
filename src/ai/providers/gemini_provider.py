"""
Google Gemini Native API Provider for JARVIS / Aether.
Implements resilient fallback chains, strict OpenAPI 3.0 tool schemas, multi-turn tool calling, and vision support.
"""

import json
import time
import requests
from typing import Dict, Any, List, Optional
from .base import BaseLLMProvider
from ...actions.vision_actions import capture_screen_image
from ...actions.executor import execute_action

MODEL_FALLBACKS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash-8b",
]

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash", session: Optional[requests.Session] = None):
        self.api_key = (api_key or "").strip().strip("\"'").replace("\r", "").replace("\n", "").strip()
        self.model_name = self._normalize_model(model_name)
        self.session = session or requests.Session()
        self.session.trust_env = False

    def _normalize_model(self, model: str) -> str:
        clean = (model or "").replace("models/", "").replace("google/", "").strip()
        alias_map = {
            "gemini-3.8-flashlite": "gemini-2.0-flash",
            "gemini 3.8 flashlite": "gemini-2.0-flash",
            "gemini 3.8 flash-lite": "gemini-2.0-flash",
            "3.8-flash-lite": "gemini-2.0-flash",
            "gemini-3.5-flashlite": "gemini-2.0-flash",
            "gemini 3.5 flashlite": "gemini-2.0-flash",
            "gemini 3.5 flash-lite": "gemini-2.0-flash",
            "3.5-flash-lite": "gemini-2.0-flash",
            "gemini-2.0-flashlite": "gemini-2.0-flash-lite",
            "gemini 2.0 flash-lite": "gemini-2.0-flash-lite",
        }
        return alias_map.get(clean.lower(), clean) if clean else "gemini-2.0-flash"

    def _send_request(self, payload: dict, models_to_try: list, headers: dict):
        resp = None
        last_error = None
        for target_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=12)
                if resp.status_code == 200:
                    return resp.json(), target_model
                elif resp.status_code == 404:
                    last_error = f"Model '{target_model}' not found (404)"
                    continue
                else:
                    last_error = f"Gemini API status {resp.status_code}: {resp.text}"
                    break
            except Exception as ex:
                try:
                    import urllib.request
                    body_bytes = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url,
                        data=body_bytes,
                        headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key, "User-Agent": "AetherAI/2.0"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=12) as uresp:
                        if uresp.status == 200:
                            raw_json = json.loads(uresp.read().decode("utf-8"))
                            return raw_json, target_model
                except Exception as uex:
                    last_error = f"{ex} (fallback error: {uex})"
                continue

        raise RuntimeError(last_error or "Failed to connect to Gemini API.")

    def generate(
        self,
        user_query: str,
        chat_history: List[Dict[str, Any]],
        sys_prompt: str,
        tools: List[Dict[str, Any]],
        include_vision: bool = False,
        include_webcam: bool = False
    ) -> Dict[str, Any]:
        contents = []
        for msg in chat_history[-4:]:
            contents.append(msg)

        current_parts = [{"text": user_query}]
        if include_webcam:
            from ...actions.webcam_actions import capture_webcam_frame
            cam_data = capture_webcam_frame()
            if cam_data.get("success"):
                current_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": cam_data["base64"]
                    }
                })
        elif include_vision:
            screen_data = capture_screen_image()
            if screen_data.get("success"):
                current_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": screen_data["base64"]
                    }
                })

        contents.append({"role": "user", "parts": current_parts})

        # Sanitize function declarations strictly adhering to Gemini OpenAPI Schema
        function_declarations = []
        for t in tools:
            decl = {
                "name": t["name"],
                "description": t["description"]
            }
            params = t.get("parameters", {})
            props = params.get("properties", {})
            decl["parameters"] = {
                "type": "OBJECT",
                "properties": props
            }
            if props and params.get("required"):
                decl["parameters"]["required"] = params["required"]
            function_declarations.append(decl)

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        models_to_try = [self.model_name]
        for fb in MODEL_FALLBACKS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        # Multi-turn tool execution loop (up to 4 turns)
        max_turns = 4
        all_actions = []
        all_steps = []
        last_action_args = {}
        final_text = ""

        for turn in range(max_turns):
            payload = {
                "system_instruction": {
                    "parts": [{"text": sys_prompt}]
                },
                "contents": contents,
                "tools": [{"function_declarations": function_declarations}],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 384,
                    "topP": 0.95
                }
            }

            data, successful_model = self._send_request(payload, models_to_try, headers)
            candidates = data.get("candidates", [])
            if not candidates:
                break

            candidate = candidates[0]
            content_parts = candidate.get("content", {}).get("parts", [])

            tool_calls_in_turn = []
            text_in_turn = ""

            for part in content_parts:
                if "text" in part:
                    text_in_turn += part["text"] + " "
                elif "functionCall" in part:
                    tool_calls_in_turn.append(part["functionCall"])

            if text_in_turn.strip():
                final_text = text_in_turn.strip()

            if not tool_calls_in_turn:
                # No more tools called; model finished its answer
                break

            # Execute tool calls and create function responses for Gemini
            contents.append({"role": "model", "parts": content_parts})
            fn_responses = []

            for fn_call in tool_calls_in_turn:
                fn_name = fn_call.get("name")
                fn_args = fn_call.get("args", {})
                all_actions.append(fn_name)
                last_action_args = fn_args

                exec_result = execute_action(fn_name, fn_args)
                msg = exec_result.get("message", f"Done with {fn_name}.")
                all_steps.append(f"{fn_name.replace('_', ' ').title()}: {msg}")

                fn_responses.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"name": fn_name, "content": exec_result}
                    }
                })

            contents.append({"role": "function", "parts": fn_responses})
            time.sleep(0.1)

        final_reply = final_text or (all_steps[-1] if all_steps else "Directives executed, Sir.")

        return {
            "text": final_reply,
            "action": all_actions[-1] if all_actions else None,
            "action_args": last_action_args,
            "steps": all_steps,
            "is_local": False
        }
