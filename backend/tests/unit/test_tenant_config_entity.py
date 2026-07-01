"""Unit tests for TenantConfig entity methods."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.shared.exceptions import InvalidOperationError
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenant_config.value_objects import LLMProvider


def test_update_embedding() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_embedding(provider="openai", model="text-embedding-3-small")
    assert c.embedding_provider == "openai"
    assert c.embedding_model == "text-embedding-3-small"


def test_update_embedding_rejects_unsupported_model() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    original = c.embedding_model
    with pytest.raises(InvalidOperationError, match="Unsupported embedding model"):
        c.update_embedding(model="voyage-3")
    assert c.embedding_model == original  # unchanged on rejection


def test_update_embedding_rejects_unsupported_provider() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    with pytest.raises(InvalidOperationError, match="Unsupported embedding provider"):
        c.update_embedding(provider="voyage")


def test_update_embedding_api_key_only_keeps_model() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    original_model = c.embedding_model
    c.update_embedding(api_key="sk-new")
    assert c.embedding_api_key == "sk-new"
    assert c.embedding_model == original_model


def test_update_telegram() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_telegram(bot_token="123:ABC", webhook_secret="secret")
    assert c.telegram_bot_token == "123:ABC"
    assert c.telegram_webhook_secret == "secret"


def test_mask_key_edge_cases() -> None:
    assert TenantConfig.mask_key("12345678") == "****5678"
    assert TenantConfig.mask_key("1234567") == "****"
    assert TenantConfig.mask_key("a") == "****"


def test_llm_provider_values() -> None:
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"
    assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
    assert LLMProvider.GOOGLE.value == "google"


def test_update_llm_partial() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    old_model = c.llm_model
    c.update_llm(api_key="new-key")
    assert c.llm_api_key == "new-key"
    assert c.llm_model == old_model  # unchanged


def test_rerank_model_defaults_and_updates() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    assert c.rerank_model == "gpt-5.4-mini"  # default rerank model
    c.update_llm(rerank_model="gpt-4.1-nano")
    assert c.rerank_model == "gpt-4.1-nano"
    assert c.llm_model == "gpt-4o-mini"  # answer model independent of rerank model
