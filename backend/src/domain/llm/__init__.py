"""LLM domain — provider-agnostic port + value objects.

This package never imports `langchain_*` or `langgraph` — concrete LLM
plumbing lives in `infrastructure/llm/` behind these abstractions.
"""

from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import (
    LLMCallResult,
    LLMMessage,
    LLMMessageRole,
    LLMToolCall,
    TokenUsage,
)

__all__ = [
    "LLMCallResult",
    "LLMClientPort",
    "LLMMessage",
    "LLMMessageRole",
    "LLMToolCall",
    "TokenUsage",
]
