# RAG Pipeline

Frontdesk uses a hybrid retrieval-augmented generation pipeline to ground the AI agent's answers in the tenant's uploaded knowledge base. Every stage is tenant-isolated. The pipeline covers two phases: **document ingestion** (write path) and **query-time retrieval** (read path).

> **Source of truth:** The code. If this document disagrees with the code, the code wins -- update the doc in the same change.

---

## Architecture Overview

```text
                         INGESTION (write path)
                         ──────────────────────
  Owner uploads file
        │
        ▼
  Web request (drivers/api/v1/documents/routes.py)
        ├── stream raw bytes to disk  ──  <UPLOAD_STORAGE_DIR>/<tenant>/<doc_id>
        ├── RegisterDocumentUseCase   ──  status = UPLOADED
        └── enqueue document_id        ──  Arq / Redis  (only the id, never the bytes)
        │
        ▼
  Arq worker (drivers/jobs/worker.py → ingestion.py → ProcessDocumentUseCase)
        │   reads the file back from disk by id
        ├── 1. Parse    ──  infrastructure/rag/parser.py
        ├── 2. Chunk    ──  infrastructure/rag/chunker.py
        ├── 3. Embed    ──  infrastructure/rag/embedder.py
        └── 4. Persist  ──  Chunk rows (content + embedding + tsvector)

  Reaper (cron in the worker): re-enqueues any document left UPLOADED/INGESTING
  past INGESTION_STALE_AFTER_SECONDS — the file is still on disk, so a crash recovers.

                         RETRIEVAL (read path)
                         ─────────────────────
  Agent calls search_documents tool
        │
        ▼
  HybridRetriever.hybrid_retrieve()  (infrastructure/rag/retriever.py)
        │
        ├── Stage 1: Vector search   (HNSW cosine, top-50)
        ├── Stage 2: BM25 search     (tsvector + ts_rank, top-50)
        ├── Stage 3: RRF fusion      (k=60)
        └── Return top-k (default 8) RetrievedChunk objects
```

---

## Document Ingestion

Ingestion is **durable**: the heavy work runs on an Arq worker, not in the web request, and survives restarts.

1. **Upload** (`drivers/api/v1/documents/routes.py`): the request streams the raw file straight to disk in fixed-size chunks (constant memory, even for big or many concurrent uploads), records the document via `RegisterDocumentUseCase` (status `UPLOADED`), and enqueues **only the `document_id`** — the bytes stay on disk, so the Redis payload is tiny and constant.
2. **Process** (`drivers/jobs/ingestion.py` → `ProcessDocumentUseCase`): the worker loads the file back from disk by id and runs parse → chunk → embed → persist. The use case orchestrates ports (chunker, embedder) without knowing their implementations. It is idempotent: an already-`READY` document is a no-op, so a retried or re-enqueued job is safe.
3. **Recover** (reaper cron in `drivers/jobs/worker.py`): any document stuck in `UPLOADED`/`INGESTING` past `INGESTION_STALE_AFTER_SECONDS` is re-enqueued — the file is still on disk, so a crash or lost job recovers instead of sticking forever.

Errors during parsing or embedding mark the document FAILED with a reason string (without losing the upload metadata), so the owner can see what happened in the dashboard. Unexpected/transient errors propagate so Arq retries with backoff.

> Storage is behind the `DocumentStoragePort` (`domain/documents/ports.py`); the default adapter is `DiskDocumentStorage` writing to `UPLOAD_STORAGE_DIR`, which **must be a shared volume** between the web and worker containers.

### Step 1: Parse

**File:** `infrastructure/rag/parser.py`

Extracts plain text from the uploaded binary content. Supported formats:

| MIME Type | Library | Notes |
| --------- | ------- | ----- |
| PDF | `pypdf` (`PdfReader`) | Pages joined with `\n\n`; empty pages skipped |
| DOCX | `python-docx` (`Document`) | Paragraphs joined with `\n\n`; lazy import |
| Markdown | built-in | UTF-8 decode with `errors="replace"` |
| Plain text | built-in | UTF-8 decode with `errors="replace"` |

The `DocumentMimeType` enum determines the parser via `match` dispatch. Unsupported types raise `InvalidOperationError` before any parsing begins.

### Step 2: Chunk

**File:** `infrastructure/rag/chunker.py` -- `RecursiveTokenChunker`

Splits on the longest available separator so chunks respect natural boundaries:

```text
Separator hierarchy (tried in order):
  "\n\n"  (paragraph)
  "\n"    (line)
  ". "    (sentence)
  "? "    (question)
  "! "    (exclamation)
  "; "    (semicolon)
  ", "    (comma)
  " "     (word)
  ""      (character -- hard split on tokens)
```

| Parameter | Default | Notes |
| --------- | ------- | ----- |
| `chunk_size` | 512 tokens | Target per chunk |
| `overlap_ratio` | 0.15 (15%) | Overlap between consecutive chunks |
| `encoding_name` | `o200k_base` | tiktoken encoding for token counting |

**How it works:**

1. **Recursive split:** If a piece exceeds `chunk_size` tokens, split on the current separator. If the sub-piece still exceeds, recurse with the next separator.
2. **Merge with overlap:** Small pieces are accumulated until the token budget is reached, then flushed. The tail of each flushed chunk (last `overlap` tokens) is prepended to the next chunk for continuity.
3. **Token counting:** All sizing uses `tiktoken.get_encoding("o200k_base").encode()` to count actual tokens, not characters.

**Output:** A list of `TextChunk(index, content)` value objects.

### Step 3: Embed

**File:** `infrastructure/rag/embedder.py` -- `OpenAIEmbedder`

Implements the `EmbeddingPort` domain interface.

| Parameter | Default | Source |
| --------- | ------- | ------ |
| `api_key` | from `TenantConfig.embedding_api_key` (falls back to `llm_api_key`) | Per-tenant |
| `model` | `settings.default_embedding_model` | `text-embedding-3-large` |
| `dimensions` | `settings.default_embedding_dimensions` | 1536 |

**Behavior:**

- Client creation is deferred to the first actual embedding call, so constructing an embedder with an empty API key does not crash the route.
- Empty texts are replaced with `" "` to avoid API errors.
- `embed_documents(texts)` returns a list of float vectors, one per input text.
- `embed_query(text)` wraps `embed_documents` for single-query use at retrieval time.

### Step 4: Persist

Each chunk becomes a `Chunk` entity row:

| Column | Type | Content |
| ------ | ---- | ------- |
| `id` | UUID | Generated by `Chunk.create()` factory |
| `document_id` | UUID FK | Parent document |
| `tenant_id` | UUID FK | Tenant isolation key |
| `chunk_index` | int | Position in the original document |
| `content` | text | The chunk text |
| `embedding` | vector(1536) | pgvector column (HNSW index, cosine ops) |
| `content_tsvector` | tsvector | GIN index for BM25 full-text search |
| `extra_metadata` | JSONB | `{"source_filename": "..."}` + any chunk metadata |

**Indexes on the chunks table:**

- **HNSW** (cosine distance) on `embedding` -- for vector search.
- **GIN** on `content_tsvector` -- for BM25 full-text search.

### Ingestion Lifecycle

```text
Document.upload()     → status = UPLOADED   (web request; file on disk, id enqueued)
doc.mark_ingesting()  → status = INGESTING  (worker picks up the job)
  ├── parse + chunk + embed + persist chunks
  └── doc.mark_ready(chunk_count=N)   → status = READY
      OR
      doc.force_failed(reason="...")   → status = FAILED
```

`mark_ingesting` also accepts re-entry from `INGESTING` (a crashed job leaves the row `INGESTING`; the worker/reaper re-runs it idempotently). Errors during parsing or embedding mark the document FAILED with a reason string; the owner sees the failure in the dashboard and can re-upload.

---

## Query-Time Retrieval

**File:** `infrastructure/rag/retriever.py` -- `HybridRetriever`

Implements the `RetrieverPort` domain interface. Called by the `search_documents` agent tool.

### Stage 1: Vector Search (HNSW Cosine)

```python
SELECT * FROM chunks
WHERE tenant_id = :tid
ORDER BY embedding <=> :query_embedding   -- cosine distance
LIMIT 50
```

Uses the HNSW index for approximate nearest-neighbor search. Returns top-50 candidates.

### Stage 2: BM25 Search (tsvector)

```python
SELECT *, ts_rank(content_tsvector, websearch_to_tsquery('english', :query)) AS rank
FROM chunks
WHERE tenant_id = :tid
  AND content_tsvector @@ websearch_to_tsquery('english', :query)
ORDER BY rank DESC
LIMIT 50
```

Uses PostgreSQL's built-in full-text search with `websearch_to_tsquery` (handles natural language queries). Returns top-50 candidates.

### Stage 3: Reciprocal Rank Fusion (RRF)

Combines the two ranked lists with RRF (k=60):

```
score(doc) = sum(1 / (k + rank_in_list)) across all lists where doc appears
```

RRF is robust to scale differences between vector similarity scores and BM25 ranks. The `k` parameter (60) smooths rank importance -- a document at rank 1 in one list and rank 50 in the other still gets a reasonable combined score.

### Output

Returns the top-k (default 8) results as `RetrievedChunk` value objects:

```python
@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    tenant_id: UUID
    content: str
    score: float
    extra_metadata: dict
```

The `search_documents` tool formats these for the LLM as `{"content": ..., "score": ..., "chunk_id": ...}`.

---

## Tenant Isolation

Both vector and BM25 queries include `WHERE tenant_id = :tid`. This is enforced at the infrastructure layer (inside `HybridRetriever`), not left to callers. A tenant can never retrieve another tenant's chunks.

---

## Domain Ports

The RAG pipeline uses three domain ports defined in `domain/rag/ports.py`:

| Port | Interface | Implementation |
| ---- | --------- | -------------- |
| `ChunkerPort` | `chunk(text) -> list[TextChunk]` | `RecursiveTokenChunker` |
| `EmbeddingPort` | `embed_documents(texts) -> list[list[float]]`, `embed_query(text) -> list[float]` | `OpenAIEmbedder` |
| `RetrieverPort` | `hybrid_retrieve(query, tenant_id, top_k) -> list[RetrievedChunk]` | `HybridRetriever` |

Value objects in `domain/rag/value_objects.py`: `TextChunk(index, content)` and `RetrievedChunk(chunk_id, document_id, tenant_id, content, score, extra_metadata)`.

---

## Reranking

The retriever supports an optional `RerankerPort` (Step 4, after RRF fusion). A `PassThroughReranker` (no-op) is used by default. To enable real reranking, implement `RerankerPort` (e.g. Cohere Rerank, cross-encoder) and inject it when constructing the `HybridRetriever`.

---

## Key Source Files

| File | Role |
| ---- | ---- |
| `infrastructure/rag/parser.py` | Document text extraction (PDF, DOCX, Markdown, plain text) |
| `infrastructure/rag/chunker.py` | `RecursiveTokenChunker` -- token-aware recursive splitting |
| `infrastructure/rag/embedder.py` | `OpenAIEmbedder` -- OpenAI embeddings endpoint adapter |
| `infrastructure/rag/retriever.py` | `HybridRetriever` -- vector + BM25 + RRF fusion |
| `application/documents/use_cases/process_document.py` | `ProcessDocumentUseCase` -- orchestrates parse/chunk/embed/persist |
| `application/documents/use_cases/register_document.py` | `RegisterDocumentUseCase` -- records the upload (status UPLOADED) |
| `domain/documents/ports.py` | `DocumentStoragePort` -- durable raw-file storage |
| `infrastructure/storage/disk_document_storage.py` | `DiskDocumentStorage` -- streams files to `UPLOAD_STORAGE_DIR` |
| `drivers/jobs/worker.py` | Arq `WorkerSettings`: `process_document` job + reaper cron |
| `drivers/jobs/ingestion.py` | Worker-side ingestion runner (loads file, runs `ProcessDocumentUseCase`) |
| `drivers/jobs/queue.py` | Arq pool + `enqueue_document_ingestion` (web → worker handoff) |
| `domain/rag/ports.py` | Domain port protocols (`ChunkerPort`, `EmbeddingPort`, `RetrieverPort`) |
| `domain/rag/value_objects.py` | `TextChunk`, `RetrievedChunk` |
| `domain/documents/entities.py` | `Document` (status machine), `Chunk` (create factory) |
| `ai/tools/search_documents.py` | Agent tool definition + runner |
