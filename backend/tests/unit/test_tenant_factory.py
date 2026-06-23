"""Unit tests for the tenant LLM client factory."""

from __future__ import annotations

from uuid import UUID, uuid4

from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.llm.tenant_factory import TenantLLMClientFactory

_TEST_KEY = "sk-test-12345678"  # fake credential for tests only


def _config(tenant_id: UUID | None = None) -> TenantConfig:
    c = TenantConfig.create_default(tenant_id=tenant_id or uuid4())
    c.llm_api_key = _TEST_KEY
    return c


def test_builds_and_caches() -> None:
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    c1 = factory.get_or_build(tid, cfg)
    c2 = factory.get_or_build(tid, cfg)
    assert c1 is c2


def test_invalidate_forces_rebuild() -> None:
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    c1 = factory.get_or_build(tid, cfg)
    factory.invalidate(tid)
    c2 = factory.get_or_build(tid, cfg)
    # After invalidation the next build is a fresh client, not the cached one —
    # this is what lets an LLM-config change take effect immediately.
    assert c2 is not c1


def test_reranker_client_is_separate_from_answer_client() -> None:
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    answer = factory.get_or_build(tid, cfg)
    rerank = factory.get_or_build_reranker(tid, cfg)
    # Cached under distinct keys → distinct clients, each reused on repeat calls.
    assert rerank is not answer
    assert factory.get_or_build_reranker(tid, cfg) is rerank


def test_invalidate_drops_both_answer_and_reranker() -> None:
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    answer = factory.get_or_build(tid, cfg)
    rerank = factory.get_or_build_reranker(tid, cfg)
    factory.invalidate(tid)
    # A config change must take effect for both clients on the next chat.
    assert factory.get_or_build(tid, cfg) is not answer
    assert factory.get_or_build_reranker(tid, cfg) is not rerank


def test_invalidate_unknown_tenant_is_noop() -> None:
    factory = TenantLLMClientFactory()
    factory.invalidate(uuid4())  # must not raise


def test_ttl_expiry() -> None:
    factory = TenantLLMClientFactory(ttl=0)
    tid = uuid4()
    cfg = _config(tid)
    c1 = factory.get_or_build(tid, cfg)
    c2 = factory.get_or_build(tid, cfg)
    assert c1 is not c2


def test_max_size_evicts() -> None:
    factory = TenantLLMClientFactory(max_size=2)
    configs = [(uuid4(), _config()) for _ in range(3)]
    for tid, cfg in configs:
        factory.get_or_build(tid, cfg)
    assert len(factory._cache) == 2


def test_clear() -> None:
    factory = TenantLLMClientFactory()
    factory.get_or_build(uuid4(), _config())
    factory.clear()
    assert len(factory._cache) == 0
