"""
OpenRouter API Provider for JARVIS / Aether.
Implements OpenAI standard tool definitions, multi-turn tool calling, HTTP SSE compatibility, and multi-model routing.
"""

import json
import time
import requests
from typing import Dict, Any, List, Optional
from .base import BaseLLMProvider
from ...actions.vision_actions import capture_screen_image
from ...actions.executor import execute_action

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "google/gemini-2.0-flash-001", session: Optional[requests.Session] = None):
        self.api_key = api_key.strip()
        self.model_name = self._normalize_model(model_name)
        self.session = session or requests.Session()
        self.session.trust_env = False

    def _normalize_model(self, model: str) -> str:
        alias_map = {
            "gemini-3.8-flashlite": "google/gemini-2.0-flash-001",
            "gemini-3.8-flash-lite": "google/gemini-2.0-flash-001",
            "google/gemini-3.8-flashlite": "google/gemini-2.0-flash-001",
            "3.8-flash-lite": "google/gemini-2.0-flash-001",
            "gemini-3.5-flashlite": "google/gemini-2.0-flash-001",
            "gemini-3.5-flash-lite": "google/gemini-2.0-flash-001",
            "google/gemini-3.5-flashlite": "google/gemini-2.0-flash-001",
            "3.5-flash-lite": "google/gemini-2.0-flash-001",
        }
        return alias_map.get(model.lower(), model) if model else "google/gemini-2.0-flash-001"

    def generate(
        self,
        user_query: str,
        chat_history: List[Dict[str, Any]],
        sys_prompt: str,
        tools: List[Dict[str, Any]],
        include_vision: bool = False,
        include_webcam: bool = False
    ) -> Dict[str, Any]:
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://aether.ai",
            "X-Title": "Aether AI Assistant",
            "Content-Type": "application/json"
        }

        messages = [{"role": "system", "content": sys_prompt}]
        for msg in chat_history[-6:]:
            role = "assistant" if msg.get("role") == "model" else msg.get("role", "user")
            content = ""
            for p in msg.get("parts", []):
                if "text" in p:
                    content += p["text"]
            if content:
                messages.append({"role": role, "content": content})

        if include_webcam:
            from ...actions.webcam_actions import capture_webcam_frame
            cam_data = capture_webcam_frame()
            if cam_data.get("success"):
                user_content = [
                    {"type": "text", "text": user_query},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{cam_data['base64']}"
                        }
                    }
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": user_query})
        elif include_vision:
            screen_data = capture_screen_image()
            if screen_data.get("success"):
                user_content = [
                    {"type": "text", "text": user_query},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screen_data['base64']}"
                        }
                    }
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": user_query})
        else:
            messages.append({"role": "user", "content": user_query})

        # Format function tools for OpenRouter / OpenAI standard schema
        formatted_tools = []
        for t in tools:
            props = {}
            for p_name, p_val in t.get("parameters", {}).get("properties", {}).items():
                props[p_name] = {
                    "type": p_val.get("type", "STRING").lower(),
                    "description": p_val.get("description", "")
                }
            fn_params = {
                "type": "object",
                "properties": props
            }
            req = t.get("parameters", {}).get("required", [])
            if req:
                fn_params["required"] = req

            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": fn_params
                }
            })

        max_turns = 4
        all_actions = []
        all_steps = []
        last_action_args = {}
        final_text = ""

        for turn in range(max_turns):
            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": formatted_tools,
                "tool_choice": "auto",
                "temperature": 0.4,
                "max_tokens": 384
            }

            resp = self.session.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenRouter status {resp.status_code}: {resp.text}")

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content_text = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            if content_text.strip():
                final_text = content_text.strip()

            if not tool_calls:
                break

            # Append the assistant message with tool calls to conversation
            messages.append(message)

            for tc in tool_calls:
                fn = tc.get("function", {})
                fn_name = fn.get("name")
                try:
                    fn_args = json.loads(fn.get("arguments", "{}"))
                except Exception:
                    fn_args = {}

                all_actions.append(fn_name)
                last_action_args = fn_args

                exec_result = execute_action(fn_name, fn_args)
                msg = exec_result.get("message", f"Done with {fn_name}.")
                all_steps.append(f"{fn_name.replace('_', ' ').title()}: {msg}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": fn_name,
                    "content": json.dumps(exec_result)
                })

            time.sleep(0.1)

        final_reply = final_text or (all_steps[-1] if all_steps else "Directives executed, Sir.")

        return {
            "text": final_reply,
            "action": all_actions[-1] if all_actions else None,
            "action_args": last_action_args,
            "steps": all_steps,
            "is_local": False
        }
