"""Arq worker — durable document ingestion + a reaper for stuck documents.

Run it as its own process (see docker-compose ``worker`` service):

    arq src.drivers.jobs.worker.WorkerSettings

- ``process_document`` runs the ingestion job (retried by Arq on transient errors).
- ``reap_stuck_documents`` runs on startup and every 5 minutes: any document left in
  uploaded/ingesting past the stale window is re-enqueued (its file is still on disk),
  so a crash or a lost job recovers instead of sticking forever.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from uuid import UUID

import structlog
from arq import cron
from arq.connections import RedisSettings

from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.drivers.jobs.ingestion import ingest_document
from src.drivers.jobs.queue import PROCESS_DOCUMENT
from src.infrastructure.persistence.postgres.database import async_session_factory

logger = structlog.get_logger()


async def process_document(ctx: dict[str, Any], tenant_id: str, document_id: str, filename: str) -> None:
    await ingest_document(tenant_id=UUID(tenant_id), document_id=UUID(document_id), filename=filename)


async def reap_stuck_documents(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.ingestion_stale_after_seconds)
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        stuck = await uow.documents.list_stuck(older_than=cutoff)
    for doc in stuck:
        logger.warning("reaper.requeue", document_id=str(doc.id), status=doc.status.value)
        await ctx["redis"].enqueue_job(PROCESS_DOCUMENT, str(doc.tenant_id), str(doc.id), doc.filename)


class WorkerSettings:
    functions: ClassVar[list[Any]] = [process_document]
    cron_jobs: ClassVar[list[Any]] = [cron(reap_stuck_documents, minute=set(range(0, 60, 5)), run_at_startup=True)]
    redis_settings: RedisSettings = RedisSettings.from_dsn(get_settings().redis_url)
    max_tries = 3
    job_timeout = 600
