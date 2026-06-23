"""Shared domain utilities."""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Control characters are how untrusted text breaks onto a new line to impersonate
# an instruction. The default strips them all; the keep-newlines variant preserves
# tab / newline / carriage-return (legitimate document formatting) and strips the rest.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")
_CONTROL_KEEP_NEWLINES_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")


def is_valid_slug(value: str) -> bool:
    return bool(_SLUG_RE.match(value)) and len(value) >= 2


def strip_control_chars(text: str, *, keep_newlines: bool = False) -> str:
    """Collapse runs of control characters to a single space.

    Neutralizes untrusted text (key facts, retrieved document content) before it
    reaches the LLM. With ``keep_newlines=True`` tab/newline/carriage-return are
    preserved (real document formatting) and only other control characters go.
    """
    pattern = _CONTROL_KEEP_NEWLINES_RE if keep_newlines else _CONTROL_RE
    return pattern.sub(" ", text)
