"""
Core Orchestration Brain for JARVIS / Aether.
Decouples local fast-path intent parsing from cloud LLM providers (Gemini & OpenRouter)
and injects Second Brain episodic and codebase RAG context.
"""

import requests
from typing import Dict, Any, Optional

from .prompts import get_system_prompt
from .intent_parser import LocalIntentParser
from .providers.gemini_provider import GeminiProvider
from .providers.openrouter_provider import OpenRouterProvider
from ..actions.executor import GEMINI_TOOLS
from ..core.telemetry import get_system_telemetry

__all__ = ["JarvisBrain", "LocalIntentParser"]

class JarvisBrain:
    def __init__(self, config: dict):
        self.config = config
        from ..memory.second_brain import SecondBrain
        self.second_brain = SecondBrain()
        self.chat_history = []
        try:
            recent_turns = self.second_brain.store.get_recent_conversations(limit=6)
            for turn in recent_turns:
                role = "user" if turn["role"] == "user" else "model"
                self.chat_history.append({"role": role, "parts": [{"text": turn["content"]}]})
        except Exception:
            pass
        self.http_session = requests.Session()

    def update_config(self, new_config: dict):
        self.config = new_config

    def process_query(self, user_query: str, include_vision: bool = False, include_webcam: bool = False) -> Dict[str, Any]:
        """
        Main decision loop:
        1. Fast-Path: Deterministic local execution (<2ms) for direct commands, volume, media, windows, presets.
        2. Semantic RAG & Episodic memory lookup from Second Brain.
        3. Provider dispatch (Gemini / OpenRouter) with automatic fallback and webcam/screen vision.
        """
        vision_requested = include_vision or any(k in user_query.lower() for k in [
            "look at my screen", "what is on my screen", "analyze my screen", "read my screen", "see my screen", "scan screen"
        ])
        webcam_requested = include_webcam or any(k in user_query.lower() for k in [
            "look at me", "look through camera", "look through webcam", "what am i holding",
            "what am i wearing", "see through camera", "see through webcam", "capture webcam", "who is in front"
        ])

        # ─── 1. FAST-PATH: Instant Zero-Latency (<2ms) Local Execution ───
        if not vision_requested and not webcam_requested:
            local_res = LocalIntentParser.parse(user_query)
            if local_res.get("action") is not None:
                reply_txt = local_res["reply"]
                action_name = local_res["action"]
                try:
                    self.second_brain.store.save_conversation_turn("user", user_query, None)
                    self.second_brain.store.save_conversation_turn("assistant", reply_txt, action_name)
                except Exception:
                    pass
                return {
                    "text": reply_txt,
                    "action": action_name,
                    "action_args": local_res["args"],
                    "steps": local_res.get("steps", []),
                    "is_local": True
                }

        # ─── 2. PROVIDER SELECTION & KEY RESOLUTION ─────────────────────
        provider_name = self.config.get("provider", "gemini").lower()
        gemini_key = (self.config.get("gemini_api_key") or "").strip()
        openrouter_key = (self.config.get("openrouter_api_key") or "").strip()
        assistant_name = self.config.get("assistant_name", "Aether")

        # Key format heuristic detection
        if gemini_key.startswith("sk-or-") and not openrouter_key:
            openrouter_key = gemini_key
            provider_name = "openrouter"
        elif openrouter_key.startswith("AIzaSy") and not gemini_key:
            gemini_key = openrouter_key
            provider_name = "gemini"

        active_key = openrouter_key if provider_name == "openrouter" else gemini_key
        if not active_key:
            if provider_name == "gemini" and openrouter_key:
                provider_name = "openrouter"
                active_key = openrouter_key
            elif provider_name == "openrouter" and gemini_key:
                provider_name = "gemini"
                active_key = gemini_key

        # If still no valid key, fall back to local deterministic engine
        if not active_key:
            parsed = LocalIntentParser.parse(user_query)
            return {
                "text": parsed["reply"],
                "action": parsed["action"],
                "action_args": parsed["args"],
                "is_local": True
            }

        # ─── 3. SYSTEM PROMPT & SECOND BRAIN RAG INJECTION ─────────────
        telemetry = get_system_telemetry()
        sys_prompt = get_system_prompt(assistant_name, telemetry)
        try:
            mem_ctx = self.second_brain.recall_context(user_query)
            if mem_ctx.get("has_context"):
                sys_prompt += f"\n\n{mem_ctx['context_prompt']}\n"
        except Exception:
            pass

        # ─── 4. PROVIDER INVOCATION WITH RESILIENT FALLBACK ────────────
        primary_provider = None
        secondary_provider = None

        if provider_name == "openrouter":
            or_model = self.config.get("openrouter_model", "google/gemini-2.0-flash-001")
            primary_provider = OpenRouterProvider(active_key, or_model, self.http_session)
            if gemini_key:
                g_model = self.config.get("model_name", "gemini-2.0-flash")
                secondary_provider = GeminiProvider(gemini_key, g_model, self.http_session)
        else:
            g_model = self.config.get("model_name", "gemini-2.0-flash")
            primary_provider = GeminiProvider(active_key, g_model, self.http_session)
            if openrouter_key:
                or_model = self.config.get("openrouter_model", "google/gemini-2.0-flash-001")
                secondary_provider = OpenRouterProvider(openrouter_key, or_model, self.http_session)

        # Attempt primary provider
        result = None
        try:
            result = primary_provider.generate(
                user_query=user_query,
                chat_history=self.chat_history,
                sys_prompt=sys_prompt,
                tools=GEMINI_TOOLS,
                include_vision=vision_requested,
                include_webcam=webcam_requested
            )
        except Exception as primary_err:
            print(f"[Brain] Primary provider ({provider_name}) failed: {primary_err}")
            # Try secondary provider if available
            if secondary_provider:
                try:
                    alt_name = "gemini" if provider_name == "openrouter" else "openrouter"
                    print(f"[Brain] Failing over to secondary provider ({alt_name})...")
                    result = secondary_provider.generate(
                        user_query=user_query,
                        chat_history=self.chat_history,
                        sys_prompt=sys_prompt,
                        tools=GEMINI_TOOLS,
                        include_vision=vision_requested,
                        include_webcam=webcam_requested
                    )
                except Exception as secondary_err:
                    print(f"[Brain] Secondary provider also failed: {secondary_err}")

        # If cloud inference succeeded, update history and return
        if result and result.get("text"):
            assistant_reply = result["text"]
            self.chat_history.append({"role": "user", "parts": [{"text": user_query}]})
            self.chat_history.append({"role": "model", "parts": [{"text": assistant_reply}]})
            try:
                self.second_brain.store.save_conversation_turn("user", user_query, None)
                self.second_brain.store.save_conversation_turn("assistant", assistant_reply, result.get("action"))
            except Exception:
                pass
            return result

        # Graceful fallback to Local Intent Parser if cloud timed out or failed
        parsed = LocalIntentParser.parse(user_query)
        return {
            "text": f"{parsed['reply']} (Advisory: Cloud intelligence link timed out; local sensory arrays active).",
            "action": parsed["action"],
            "action_args": parsed["args"],
            "is_local": True
        }
