"""Cheap, dependency-free token estimate for conversation messages.

Used only to drive the checkpoint-compaction trigger (sum of message tokens
since the last checkpoint vs a threshold) — NOT for billing. Billing uses the
provider-reported usage recorded via RecordTokenUsageUseCase. A rough estimate
is the right tool here: it must be consistent and roughly proportional to text
size, not exact, and it must not add an encoder dependency or per-message
latency to every save.

The ~4-chars-per-token ratio is the well-worn rule of thumb for English prose;
it over-counts a little for other scripts, which only makes compaction fire
slightly sooner — the safe direction.
"""

from __future__ import annotations

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Approximate token count for a piece of message text (0 for blank text)."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // _CHARS_PER_TOKEN)
