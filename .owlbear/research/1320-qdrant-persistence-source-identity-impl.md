# Qdrant Filesystem Persistence + Source Identity Fix

> **Owning task:** #1320 — P0-04: Qdrant filesystem persistence + source identity fix
> **Date:** 2026-05-04 **Status:** Complete

## 1. Context and Question

Task #1320 implements O6 (persistence) and source identity wiring from the knowledge activation brief. The #1319 tests (34 tests) already pass GREEN — meaning the library-level implementation is complete. **The remaining work is MCP server wiring only.**

**Core question:** What exactly must change to satisfy each AC at the MCP integration layer?

## 2. Sources Studied

| Source | Location | Relevance | What |
|--------|----------|-----------|------|
| MCP server lifespan | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:244-340` | 1.0 | `QdrantVectorStore()` called without path; `IngestPipeline()` missing `source_store` |
| MCP ingest_document tool | `server.py:401-420` | 1.0 | No `source_url`/`source_id` params forwarded |
| QdrantVectorStore | `serve/knowledge/src/owlbear_knowledge/qdrant.py:30-51` | 1.0 | `location=path` → `QdrantClient(path=...)` for filesystem |
| IngestPipeline | `serve/knowledge/src/owlbear_knowledge/ingest.py:76-150` | 1.0 | Already accepts `source_store`, `source_id`, `source_url` |
| KnowledgeSourceStore | `serve/knowledge/src/owlbear_knowledge/source_store.py` | 1.0 | `resolve_by_url()`, `resolve_by_path()` — fully implemented |
| KnowledgeSource model | `serve/knowledge/src/owlbear_knowledge/models.py` | 1.0 | `fetch_method`, `enrich` — already first-class fields |
| Schema v10 | `serve/knowledge/src/owlbear_knowledge/schema.py` | 1.0 | `fetch_method`, `enrich` columns present |
| .gitignore | `.gitignore:112` | 1.0 | `.owlbear/knowledge/*.db` — no Qdrant dir coverage |
| #1319 tests | `tests/test_qdrant_source_identity_1319.py` | 1.0 | All 34 pass GREEN (library implementation complete) |
| Qdrant local docs | qdrant.tech/documentation | 0.9 | `QdrantClient(path=...)` persists without server |

## 3. Analysis

### 3.1 Gap Assessment

| AC | Description | Library Status | MCP Gap |
|----|-------------|---------------|---------|
| AC1 | Qdrant filesystem persistence | `QdrantVectorStore(location=path)` works | `QdrantVectorStore()` in lifespan uses `:memory:` default |
| AC2 | SQLite on disk | `init_db(path)` works, default `.owlbear/knowledge/local.db` | Already done — no gap |
| AC3 | Gitignored storage paths | SQLite: `.owlbear/knowledge/*.db` ✓ | Qdrant dir not ignored |
| AC4 | ingest_document registers source | `ingest_text(source_url=...)` resolves/creates source | MCP tool doesn't accept/forward params; pipeline missing `source_store` |
| AC5 | Source record fields | Model has all fields | No gap |
| AC6 | Source identity by URL/path | `resolve_by_url()` / `resolve_by_path()` work | Not reachable via MCP due to AC4 gap |
| AC7 | #1319 tests pass | All 34 GREEN | No gap |

### 3.2 Implementation Plan

**Change 1 — Qdrant persistence path** (server.py lifespan, ~3 lines):

```python
qdrant_path = os.environ.get("OWLBEAR_QDRANT_PATH", ".owlbear/knowledge/vectors")
vs = QdrantVectorStore(location=qdrant_path)
```

**Change 2 — Wire source_store to pipeline** (server.py lifespan, reorder + 1 arg):

```python
source_store = KnowledgeSourceStore(conn)  # move before pipeline
pipeline = IngestPipeline(
    doc_store,
    extractor,
    chunker,
    content_guard=content_guard,
    source_store=source_store,
)
```

**Change 3 — Forward source params in MCP tool** (server.py ingest_document, +2 params):

```python
async def ingest_document(
    ctx: Context,
    text: str,
    metadata: dict[str, Any] | None = None,
    scope: str = "global",
    source_url: str | None = None,
    source_id: str | None = None,
) -> str:
    ...
    result = await pipeline.ingest_text(
        text,
        metadata=metadata,
        scope=scope,
        source_url=source_url,
        source_id=source_id,
    )
```

**Change 4 — Gitignore Qdrant directory** (.gitignore, 1 line):

```
.owlbear/knowledge/vectors/
```

### 3.3 Trade-off: Qdrant Path Location

| Option | Path | Pros | Cons |
|--------|------|------|------|
| A (recommended) | `.owlbear/knowledge/vectors/` | Collocated with SQLite, single data dir | Need new gitignore entry |
| B | `store/knowledge/vectors/` | Matches `store/` convention | `store/` already has `*.db` ignore, but not subdirs |
| C | `~/.owlbear/knowledge/vectors/` | Global state, survives workspace moves | Unexpected for devs; harder to wipe clean |

**Recommendation: Option A** — `.owlbear/knowledge/vectors/` collocates with `.owlbear/knowledge/local.db`. Both are gitignored. Single env var `OWLBEAR_QDRANT_PATH` overrides.

### 3.4 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Qdrant local mode lock files on crash | Low | portalocker handles; restart cleans |
| Disk space (Qdrant grows with embeddings) | Low | <10K chunks initially; 1024-dim × 10K = ~40MB |
| Concurrent access (single-process lock) | None | MCP server is single-process by design |
| Breaking change to `ingest_document` tool | None | New params are optional with `None` defaults |

## 4. Recommendation

**Confidence: 0.92** — This is a 4-change wiring task, not a design challenge:

1. Pass filesystem path to `QdrantVectorStore()` in server lifespan
2. Move `source_store` creation before pipeline; pass it as constructor arg
3. Add `source_url`/`source_id` params to MCP `ingest_document` tool
4. Add Qdrant directory to `.gitignore`

All library code already works (34/34 tests GREEN). The implementation is ~20 lines of changes across 2 files.

Challenge: proceed — confidence in original: 0.92. No challenger needed for trivial wiring.

## 5. Follow-up Tasks

None required — this IS the implementation task. The research confirms it's ready for architect review (backlog).
