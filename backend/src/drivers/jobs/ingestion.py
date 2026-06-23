"""Document ingestion job — the heavy work, moved off the web request.

A worker reads the raw file from storage (only the document id travels through the
queue) and runs the full parse/chunk/embed pipeline in its own session. Idempotent:
an already-ready document is a no-op, and re-running from any other state is safe.

It never raises for *terminal* problems (missing config/file, parse/embed errors) —
those are recorded as FAILED on the document. It *does* let unexpected errors (e.g.
a transient DB blip) propagate so the queue can retry with backoff.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from src.application.documents.commands import ProcessDocument
from src.application.documents.use_cases.process_document import ProcessDocumentUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentStatus
from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.llm.tenant_factory import TenantLLMClientFactory
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.rag.chunker import RecursiveTokenChunker
from src.infrastructure.rag.contextualizer import LLMContextualizer
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.parser import DocumentParser
from src.infrastructure.storage.disk_document_storage import DiskDocumentStorage

logger = structlog.get_logger()

_EMBEDDING_DIMENSIONS = 1536
_llm_factory = TenantLLMClientFactory()


def document_storage() -> DiskDocumentStorage:
    return DiskDocumentStorage(get_settings().upload_storage_dir)


def _build_embedder(config: TenantConfig) -> OpenAIEmbedder:
    return OpenAIEmbedder(
        api_key=config.embedding_api_key or config.llm_api_key,
        model=config.embedding_model,
        dimensions=_EMBEDDING_DIMENSIONS,
    )


def _build_contextualizer(tenant_id: UUID, config: TenantConfig) -> LLMContextualizer | None:
    """Contextual Retrieval needs the tenant's LLM — skip when none is configured."""
    if not config.llm_api_key:
        return None
    return LLMContextualizer(_llm_factory.get_or_build(tenant_id, config))


async def _fail(uow: UnitOfWork, doc: Document, reason: str) -> None:
    doc.force_failed(reason=reason)
    await uow.documents.save(doc)
    uow.track(doc)
    await uow.commit()


async def ingest_document(*, tenant_id: UUID, document_id: UUID, filename: str) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await uow.set_tenant_scope(tenant_id)
        doc = await uow.documents.get_by_id(document_id)
        if doc is None:
            logger.warning("ingest.document_missing", document_id=str(document_id))
            return
        if doc.status == DocumentStatus.READY:
            logger.info("ingest.already_ready", document_id=str(document_id))  # idempotent no-op
            return

        config = await uow.tenant_configs.get_by_tenant_id(tenant_id)
        if config is None:
            await _fail(uow, doc, "Tenant is not configured for ingestion")
            return
        try:
            content = await document_storage().load(tenant_id=tenant_id, document_id=document_id)
        except FileNotFoundError:
            await _fail(uow, doc, "Uploaded file is no longer available")
            return

        use_case = ProcessDocumentUseCase(
            uow=uow,
            parser=DocumentParser(),
            chunker=RecursiveTokenChunker(),
            embedder=_build_embedder(config),
            contextualizer=_build_contextualizer(tenant_id, config),
        )
        await use_case.execute(
            ProcessDocument(tenant_id=tenant_id, document_id=document_id, filename=filename, content=content)
        )
