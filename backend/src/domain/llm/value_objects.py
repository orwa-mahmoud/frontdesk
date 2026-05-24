"""LLM value objects — framework-agnostic shapes used across the codebase.

These mirror the OpenAI-style chat schema (role/content + optional tool_calls)
but stay free of any specific provider SDK. Adapters in `infrastructure/llm/`
translate to/from `langchain_core.messages`, Anthropic types, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class LLMMessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, kw_only=True)
class LLMToolCall:
    """A single tool invocation an assistant message asked for."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class LLMMessage:
    role: LLMMessageRole
    content: str
    tool_calls: tuple[LLMToolCall, ...] = field(default_factory=tuple)
    tool_call_id: str | None = None  # set on role=TOOL responses


@dataclass(frozen=True, kw_only=True)
class TokenUsage:
    """Per-call token accounting."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_write_tokens


@dataclass(frozen=True, kw_only=True)
class LLMCallResult:
    """Single LLM call outcome — text reply, tool calls (if any), usage, model name."""

    text: str
    tool_calls: tuple[LLMToolCall, ...] = field(default_factory=tuple)
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
