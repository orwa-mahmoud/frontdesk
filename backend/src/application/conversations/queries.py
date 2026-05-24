"""Conversation queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class LoadThreadHistory:
    thread_id: str
    limit: int | None = None
    include_hidden: bool = True
