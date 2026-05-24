"""Provider-agnostic token counter using tiktoken.

For Anthropic / Google models where tiktoken isn't a perfect estimator, the
o200k_base encoding is close enough for budgeting and cost forecasting.
Treat output as an approximation; the authoritative usage numbers come
from the provider's `usage_metadata` on each call.
"""

from __future__ import annotations

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=4)
def _get_encoding(name: str) -> tiktoken.Encoding:
    return tiktoken.get_encoding(name)


def count_tokens(text: str, encoding_name: str = "o200k_base") -> int:
    if not text:
        return 0
    return len(_get_encoding(encoding_name).encode(text))
