"""Conversation checkpoint — summarize history when token budget exceeded.

After each agent response, check if total tokens since the last checkpoint
exceed the threshold. If so, generate a structured JSON summary that
compresses the conversation into current active state. The summary is
saved as a hidden checkpoint message that future history loads see.

Generalized from PropertyBot's checkpoint.py — the JSON schema is
domain-agnostic (documents discussed, open questions, key decisions)
instead of property-specific.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import structlog

from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole

logger = structlog.get_logger()

_CHECKPOINT_TOKEN_THRESHOLD = 3000
_MAX_RECENT_MESSAGES = 30

_SUMMARIZE_SYSTEM_PROMPT = """\
You are a conversation state summarizer for an AI front desk assistant.

Your job is to extract the CURRENT ACTIVE STATE — not a full transcript replay.

## Recency rules
- Latest explicit preference ALWAYS wins over older ones.
- If contradictory statements exist, keep only the latest.

## Output rules
- Respond ONLY with valid JSON — no markdown, no explanation.
- Always include ALL keys. Use null for unknown values, [] for empty lists.
- Max 5 items in documents_discussed.

## JSON format
{
  "summary": "2-4 sentence summary of the CURRENT active conversation state.",
  "current_state": {
    "name": null,
    "language": null,
    "intent": null,
    "topic": null
  },
  "documents_discussed": [
    {"title": "...", "status": "cited|requested|not_found"}
  ],
  "open_questions": [],
  "key_decisions": [],
  "escalated": false
}\
"""


async def maybe_create_checkpoint(
    *,
    thread_id: str,
    tenant_id: UUID,
    channel: ConversationChannel,
    llm: LLMClientPort,
    uow: UnitOfWork,
    request_id: str | None = None,
) -> None:
    """Check token budget and create a checkpoint if threshold exceeded."""
    conv = await uow.conversations.get_by_thread_id(thread_id)
    if not conv:
        return

    total_tokens = await uow.messages.sum_tokens_since_checkpoint(conv.id)
    if total_tokens < _CHECKPOINT_TOKEN_THRESHOLD:
        return

    logger.info("checkpoint.triggered", thread_id=thread_id, tokens=total_tokens)

    messages = await uow.messages.list_since_last_checkpoint(conv.id)
    if not messages:
        return

    conv_text = _build_summarizer_input(messages)

    try:
        response = await llm.chat_with_tools(
            [
                LLMMessage(role=LLMMessageRole.SYSTEM, content=_SUMMARIZE_SYSTEM_PROMPT),
                LLMMessage(role=LLMMessageRole.USER, content=conv_text),
            ],
            max_tokens=1536,
        )
    except Exception:
        logger.warning("checkpoint.summarize_failed", thread_id=thread_id, exc_info=True)
        return

    # The summarizer runs on the tenant's answer model — a real, billable call.
    # Record it even if the reply is empty (it still cost tokens).
    await _record_summarizer_usage(response, tenant_id=tenant_id, request_id=request_id, channel=channel, uow=uow)

    summary_text = response.text.strip()
    if not summary_text:
        return

    display_summary, tool_data = _parse_summary(summary_text)

    save_uc = SaveThreadMessageUseCase(uow=uow)
    await save_uc.execute(
        SaveThreadMessage(
            thread_id=thread_id,
            content=display_summary,
            role=ConversationRole.ASSISTANT,
            tenant_id=tenant_id,
            channel=channel,
            hidden=True,
            is_checkpoint=True,
            tool_args=tool_data,
            request_id=request_id,
        )
    )
    logger.info("checkpoint.created", thread_id=thread_id, tokens_before=total_tokens)


async def _record_summarizer_usage(
    response: LLMCallResult,
    *,
    tenant_id: UUID,
    request_id: str | None,
    channel: ConversationChannel,
    uow: UnitOfWork,
) -> None:
    usage = response.usage
    if usage.input_tokens <= 0 and usage.output_tokens <= 0:
        return
    await RecordTokenUsageUseCase(uow=uow).execute(
        RecordTokenUsage(
            tenant_id=tenant_id,
            provider=response.provider,
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=usage.cache_read_tokens,
            request_id=request_id,
            source="checkpoint",
            channel=channel.value,
        )
    )


def _build_summarizer_input(messages: list[Message]) -> str:
    lines: list[str] = []
    recent = messages[-_MAX_RECENT_MESSAGES:] if len(messages) > _MAX_RECENT_MESSAGES else messages
    if len(messages) > _MAX_RECENT_MESSAGES:
        skipped = len(messages) - _MAX_RECENT_MESSAGES
        lines.append(f"[... {skipped} older messages omitted ...]")
    for m in recent:
        role = m.role if isinstance(m.role, str) else m.role.value
        content = m.content or ""
        if m.is_checkpoint:
            lines.append(f"[Previous checkpoint state]: {content}")
        elif content.strip():
            lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


def _parse_summary(summary_text: str) -> tuple[str, dict[str, Any] | None]:
    cleaned = summary_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        display = parsed.get("summary", summary_text)
        return display, {"checkpoint": parsed}
    except (json.JSONDecodeError, TypeError):
        logger.warning("checkpoint.json_parse_failed", raw_length=len(summary_text))
        return summary_text, None
