"""LLM domain port.

Use cases and the AI orchestration layer depend on this Protocol — never on
a concrete provider SDK. Adapters in `infrastructure/llm/` translate calls
across providers (OpenAI, Anthropic, Google) behind this surface.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from src.domain.llm.value_objects import LLMCallResult, LLMMessage


class LLMClientPort(Protocol):
    async def chat_with_tools(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMCallResult: ...
