"""Tests for domain validation guard edge cases added during hardening."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.contacts.entities import Contact
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.key_facts.entities import KeyFact
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.tenants.entities import Tenant
from src.domain.users.entities import User


def test_tenant_create_empty_name_raises() -> None:
    with pytest.raises(InvalidOperationError, match="name cannot be empty"):
        Tenant.create(name="  ", slug="valid-slug")


def test_tenant_create_invalid_slug_raises() -> None:
    with pytest.raises(InvalidOperationError, match="Invalid slug"):
        Tenant.create(name="Good Name", slug="BAD SLUG!")


def test_tenant_rename_emits_event() -> None:
    t = Tenant.create(name="Old", slug="old-name")
    t.clear_events()
    t.rename("New Name")
    assert len(t.pending_events) == 1
    assert t.name == "New Name"


def test_contact_create_no_identifier_raises() -> None:
    with pytest.raises(InvalidOperationError, match="at least a phone"):
        Contact.create(tenant_id=uuid4())


def test_key_fact_empty_key_raises() -> None:
    with pytest.raises(InvalidOperationError, match="key cannot be empty"):
        KeyFact.create(tenant_id=uuid4(), contact_id=uuid4(), key="", value="val")


def test_key_fact_empty_value_raises() -> None:
    with pytest.raises(InvalidOperationError, match="value cannot be empty"):
        KeyFact.create(tenant_id=uuid4(), contact_id=uuid4(), key="name", value="  ")


def test_key_fact_update_empty_value_raises() -> None:
    kf = KeyFact.create(tenant_id=uuid4(), contact_id=uuid4(), key="name", value="Alice")
    with pytest.raises(InvalidOperationError, match="value cannot be empty"):
        kf.update_value("")


def test_document_mark_ready_wrong_status_raises() -> None:
    doc = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="a.txt",
        mime_type=DocumentMimeType.PLAIN,
        size_bytes=10,
    )
    with pytest.raises(InvalidOperationError, match="Cannot mark ready"):
        doc.mark_ready(chunk_count=1)


def test_document_mark_ready_zero_chunks_raises() -> None:
    doc = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="a.txt",
        mime_type=DocumentMimeType.PLAIN,
        size_bytes=10,
    )
    doc.mark_ingesting()
    with pytest.raises(InvalidOperationError, match="at least one chunk"):
        doc.mark_ready(chunk_count=0)


def test_document_mark_failed_wrong_status_raises() -> None:
    doc = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="a.txt",
        mime_type=DocumentMimeType.PLAIN,
        size_bytes=10,
    )
    with pytest.raises(InvalidOperationError, match="Cannot mark failed"):
        doc.mark_failed(reason="oops")


def test_user_deactivate_already_inactive_raises() -> None:
    u = User.create(email="a@b.com", hashed_password="hash")
    u.deactivate()
    with pytest.raises(InvalidOperationError, match="already deactivated"):
        u.deactivate()


def test_user_activate_already_active_raises() -> None:
    u = User.create(email="a@b.com", hashed_password="hash")
    with pytest.raises(InvalidOperationError, match="already active"):
        u.activate()
