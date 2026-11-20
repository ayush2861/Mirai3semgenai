from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMProvider(ABC):
    """Abstract interface for LLM text generation providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Generates grounded response text.
        Returns a dict:
        {
            "text": str,
            "model": str,
            "prompt_tokens": Optional[int],
            "candidates_tokens": Optional[int],
            "total_tokens": Optional[int]
        }
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is configured and available."""
        pass
