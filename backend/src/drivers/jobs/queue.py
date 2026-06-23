"""Job queue helpers — the Arq Redis pool + enqueue, shared by web and worker.

Only the document id (+ tenant + filename) is enqueued; the raw bytes stay on disk,
so the job payload is tiny and constant regardless of file size.
"""

from __future__ import annotations

from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from src.config.settings import get_settings

PROCESS_DOCUMENT = "process_document"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def create_job_pool() -> ArqRedis:
    return await create_pool(redis_settings())


async def enqueue_document_ingestion(pool: ArqRedis, *, tenant_id: UUID, document_id: UUID, filename: str) -> None:
    await pool.enqueue_job(PROCESS_DOCUMENT, str(tenant_id), str(document_id), filename)
