"""Domain exception -> HTTP response mapping.

Registered on the FastAPI app so use cases can raise `DomainError` (and its
subclasses) without ever knowing about HTTP. Each subclass declares its
`http_status` so the mapping is open for extension without touching this file.
"""

from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from src.domain.shared.exceptions import DomainError
from src.drivers.api.i18n import resolve_locale, translate

logger = structlog.get_logger()


def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    locale = resolve_locale(request.headers.get("accept-language"))
    message = str(exc) or "An error occurred"
    code = exc.code or ("error.generic" if not str(exc) else None)
    detail = translate(code, locale, default=message)
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": detail},
    )


def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map a DB constraint violation to a clean 409.

    Use cases pre-check uniqueness (email, slug, …), but two concurrent requests
    can both pass that check and race to insert — the loser hits the unique index.
    Without this, that surfaces as an opaque 500; here it becomes a 409 Conflict.
    """
    assert isinstance(exc, IntegrityError)
    logger.warning("integrity_error", path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=409,
        content={"detail": "The request conflicts with existing data. Please try again."},
    )
