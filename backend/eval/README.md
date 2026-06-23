# RAG eval harness

A small, runnable evaluation of retrieval quality for the knowledge base. It
grades a golden Q&A set and reports the metrics that actually predict answer
quality — so prompt/retrieval changes can be measured, not guessed.

```bash
uv run python -m eval.run          # from backend/  (or `make eval` from repo root)
uv run python -m eval.run --k 3
uv run python -m eval.run --ci     # exit non-zero if metrics drop below gates
```

**Offline by default** — no database and no API keys required. A lightweight
lexical retriever (IDF-weighted overlap + light stemming) runs over the fixture
corpus in `fixtures/`, graded against `golden_set.json`. This is what makes it
CI-friendly and reproducible on any laptop.

## What it measures

| Metric | Meaning |
|---|---|
| **hit@k** | a relevant document appears in the top-k |
| **recall@k** | fraction of relevant documents retrieved |
| **MRR** | rank of the first relevant document (higher = it ranks it first) |
| **context sufficiency@k** | the retrieved context actually contains the answer facts |
| **escalation precision / recall** | does the system correctly *not* answer when the KB has nothing? |

The escalation metrics matter for this product specifically: answering off-topic
questions confidently is worse than escalating to a human.

## Golden set

`golden_set.json` — each item has the question, the relevant doc id(s), the answer
keywords that must be present in retrieved context, and `should_escalate`
(true ⇒ the answer is deliberately *not* in the KB). Add your own items to grow
coverage; keep them small and specific.

## DB mode — grade the real retriever

`eval.run` scores an offline lexical retriever so it runs anywhere. To measure
the **production** pipeline — pgvector HNSW + Postgres BM25 + RRF + the LLM
reranker — run `eval.db_eval` against a tenant whose documents are already
ingested:

```bash
DATABASE_URL=postgresql+asyncpg://... \
EVAL_EMBEDDING_API_KEY=sk-... EVAL_LLM_API_KEY=sk-... \
EVAL_TENANT_ID=<uuid> \
uv run python -m eval.db_eval        # or: make eval-db (from the repo root)
```

Each mode has its **own** dataset so editing one never breaks the other (offline
runs in the CI gate):

- **Offline** (`eval.run`) → `golden_set.json` — fixture filenames in `fixtures/`.
- **DB** (`eval.db_eval`) → `golden_set.db.json` — set `relevant_doc_ids` to the
  `EVAL_TENANT_ID` tenant's real ingested filenames. Override with
  `EVAL_GOLDEN_PATH=/path/to/your.json`.

Without the keys/tenant DB mode prints how to enable it and exits 0, so it never
breaks a default `make`. This is how you quantify what the reranker and Contextual
Retrieval actually buy you; the same metrics module grades both modes.
