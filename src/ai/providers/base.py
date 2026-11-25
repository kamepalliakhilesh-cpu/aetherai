"""
Base LLM Provider Interface for JARVIS / Aether.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        user_query: str,
        chat_history: List[Dict[str, Any]],
        sys_prompt: str,
        tools: List[Dict[str, Any]],
        include_vision: bool = False
    ) -> Dict[str, Any]:
        """
        Executes an inference request against the provider.
        Returns a dict with:
        - text: str
        - action: Optional[str]
        - action_args: Dict[str, Any]
        """
        pass
