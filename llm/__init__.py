"""LLM package for Hisaab — BYOK investigative assistant.

Supports Google Gemini and OpenAI-compatible providers (OpenAI, Groq, Together, etc.).
API keys are never stored — they are passed per-request.
"""

from __future__ import annotations

from llm.investigator import InvestigationResult, investigate
from llm.providers import PROVIDER_DEFAULTS, generate

__all__ = [
    "PROVIDER_DEFAULTS",
    "InvestigationResult",
    "generate",
    "investigate",
]
