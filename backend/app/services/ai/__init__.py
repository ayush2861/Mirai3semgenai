"""
AI Services Module.
Provides modular LLM integration, prompt templates, citation validation,
numerical fidelity monitoring, and RAG answer generation.
"""

from app.services.ai.base import BaseLLMProvider
from app.services.ai.gemini_provider import gemini_provider, GeminiProvider
from app.services.ai.prompt_builder import prompt_builder, PromptBuilder
from app.services.ai.context_builder import context_builder, ContextBuilder
from app.services.ai.answer_formatter import answer_formatter, AnswerFormatter
from app.services.ai.citation_validator import citation_validator, CitationValidator
from app.services.ai.numerical_guard import numerical_guard, NumericalGuard
from app.services.ai.ai_service import ai_service, AIService

__all__ = [
    "BaseLLMProvider",
    "gemini_provider",
    "GeminiProvider",
    "prompt_builder",
    "PromptBuilder",
    "context_builder",
    "ContextBuilder",
    "answer_formatter",
    "AnswerFormatter",
    "citation_validator",
    "CitationValidator",
    "numerical_guard",
    "NumericalGuard",
    "ai_service",
    "AIService"
]
