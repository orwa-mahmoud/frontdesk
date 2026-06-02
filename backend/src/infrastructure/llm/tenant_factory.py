"""Per-tenant LLM client factory with in-memory cache + TTL.

Builds and caches LLM clients per tenant_id (one client = one
provider/model/api_key). Cache entries expire after 1 hour. When a tenant
updates its LLM config, the settings route calls `invalidate()` (via
`invalidate_tenant_llm_client` in the gateway) so the next chat rebuilds the
client with the new credentials instead of serving the stale cached one.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from uuid import UUID

import structlog

from src.domain.llm.ports import LLMClientPort
from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.llm.client import LangChainLLMClient

logger = structlog.get_logger()

_CACHE_TTL_SECONDS = 3600
_CACHE_MAX_SIZE = 100


class TenantLLMClientFactory:
    """Cached per-tenant LLM client builder."""

    def __init__(self, ttl: int = _CACHE_TTL_SECONDS, max_size: int = _CACHE_MAX_SIZE) -> None:
        self._cache: OrderedDict[str, tuple[LLMClientPort, float]] = OrderedDict()
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.Lock()

    def get_or_build(self, tenant_id: UUID, config: TenantConfig) -> LLMClientPort:
        key = str(tenant_id)
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None and (time.monotonic() - entry[1]) <= self._ttl:
                self._cache.move_to_end(key)
                return entry[0]

            client = LangChainLLMClient(
                provider=config.llm_provider.value,
                model=config.llm_model,
                api_key=config.llm_api_key,
            )
            self._cache[key] = (client, time.monotonic())
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            logger.debug("tenant_llm_factory.built", tenant_id=key, model=config.llm_model)
            return client

    def invalidate(self, tenant_id: UUID) -> None:
        with self._lock:
            removed = self._cache.pop(str(tenant_id), None)
        if removed:
            logger.info("tenant_llm_factory.invalidated", tenant_id=str(tenant_id))

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
