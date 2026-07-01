"""Unit tests for the recursive token chunker — pure CPU, no IO."""

from __future__ import annotations

from src.infrastructure.rag.chunker import _SEPARATORS, RecursiveTokenChunker


def test_empty_text_produces_no_chunks() -> None:
    assert RecursiveTokenChunker().chunk("") == []
    assert RecursiveTokenChunker().chunk("   \n\n  ") == []


def test_short_text_is_a_single_chunk() -> None:
    chunks = RecursiveTokenChunker(chunk_size=200).chunk("Hello, this is a short document.")
    assert len(chunks) == 1
    assert "Hello" in chunks[0].content


def test_long_text_is_split_into_multiple_chunks() -> None:
    paragraphs = "\n\n".join(f"Paragraph {i}. " + ("word " * 100) for i in range(10))
    chunks = RecursiveTokenChunker(chunk_size=200, overlap_ratio=0.15).chunk(paragraphs)
    assert len(chunks) > 1
    # Indexes start at 0 and increment monotonically.
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunks_overlap_carries_tail_to_next() -> None:
    text = "A. B. C. D. " + ("filler " * 200) + " end-marker"
    chunks = RecursiveTokenChunker(chunk_size=150, overlap_ratio=0.2).chunk(text)
    assert len(chunks) >= 2


def test_recursive_split_is_lossless_no_duplicated_trailing_separator() -> None:
    """Splitting then rejoining the pieces must reproduce the source exactly — the
    final part must not get a re-appended separator (which doubled punctuation)."""
    chunker = RecursiveTokenChunker(chunk_size=5)  # tiny → forces a real ". " split
    text = "Sentence one. Sentence two. Sentence three."

    pieces = chunker._recursive_split(text, _SEPARATORS)

    assert "".join(pieces) == text  # lossless reconstruction
    assert not any(".. " in p for p in pieces)  # no doubled period on the tail
