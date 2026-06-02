"""Unit tests for the domain error → HTTP response handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError
from src.drivers.api.responses import domain_error_handler, integrity_error_handler


def test_maps_not_found_to_404() -> None:
    exc = EntityNotFoundError("User not found")
    resp = domain_error_handler(MagicMock(), exc)
    assert resp.status_code == 404


def test_maps_auth_error_to_401() -> None:
    exc = AuthenticationError("Bad token")
    resp = domain_error_handler(MagicMock(), exc)
    assert resp.status_code == 401


def test_maps_integrity_error_to_409() -> None:
    # A unique-constraint race (e.g. duplicate email/slug) becomes a clean 409,
    # not an opaque 500.
    request = MagicMock()
    request.url.path = "/api/v1/auth/register"
    exc = IntegrityError("INSERT ...", {}, ValueError("duplicate key"))
    resp = integrity_error_handler(request, exc)
    assert resp.status_code == 409
