"""Message ORM model — one row per turn (user / assistant / tool) plus
checkpoint and compressed-summary rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.postgres.models import Base


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Tool exchange details — preserves args (PropertyBot lacked this) + result.
    tool_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Tiered compression — older tool turns may be rolled up to a summary.
    is_compressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compressed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # PropertyBot-style structured checkpoint row.
    is_checkpoint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
