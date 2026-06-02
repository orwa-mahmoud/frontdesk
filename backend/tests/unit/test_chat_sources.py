"""Unit tests for chat source extraction (RAG citations surfaced to the dashboard)."""

from __future__ import annotations

from src.ai.gateway import _extract_sources
from src.ai.types import AgentLoopResult, ToolCallResult


def _result(*tool_calls: ToolCallResult) -> AgentLoopResult:
    return AgentLoopResult(text="ok", tool_calls=list(tool_calls))


def test_no_search_calls_yields_no_sources() -> None:
    result = _result(ToolCallResult(tool_name="escalate_question", arguments={}, result={"ok": True}))
    assert _extract_sources(result) == []


def test_extracts_best_chunk_per_document_sorted_by_score() -> None:
    search = ToolCallResult(
        tool_name="search_documents",
        arguments={"query": "hours"},
        result=[
            {"document_id": "doc-a", "content": "low", "score": 0.2},
            {"document_id": "doc-a", "content": "high", "score": 0.9},
            {"document_id": "doc-b", "content": "mid", "score": 0.5},
        ],
    )
    sources = _extract_sources(_result(search))
    assert [s.document_id for s in sources] == ["doc-a", "doc-b"]
    assert sources[0].snippet == "high"  # best-scoring chunk per document wins
    assert sources[0].score == 0.9


def test_ignores_malformed_rows_and_truncates_snippet() -> None:
    search = ToolCallResult(
        tool_name="search_documents",
        arguments={},
        result=[
            "not-a-dict",
            {"content": "no id", "score": 1.0},
            {"document_id": "doc-c", "content": "x" * 500, "score": 0.4},
        ],
    )
    sources = _extract_sources(_result(search), snippet_len=240)
    assert len(sources) == 1
    assert sources[0].document_id == "doc-c"
    assert len(sources[0].snippet) == 240


def test_non_list_result_is_ignored() -> None:
    search = ToolCallResult(tool_name="search_documents", arguments={}, result="boom")
    assert _extract_sources(_result(search)) == []


def test_respects_limit() -> None:
    rows = [{"document_id": f"doc-{i}", "content": str(i), "score": i / 10} for i in range(10)]
    search = ToolCallResult(tool_name="search_documents", arguments={}, result=rows)
    sources = _extract_sources(_result(search), limit=3)
    assert len(sources) == 3
    assert [s.document_id for s in sources] == ["doc-9", "doc-8", "doc-7"]
