---
id: 1872
title: 'Knowledge: ContentStore — search & purge'
status: todo
priority: needed
created: 2026-05-25T19:03:11.262484+02:00
updated: 2026-05-26T05:53:02.345723+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1871
ac:
  - search(ContentSearchQuery) returns ContentSearchResult tuples ordered by 
    descending score; scores clamped to [0.0, 1.0]; result count ≤ query.top_k; 
    scores below query.min_score excluded; scopes and source_ids filters applied
    (D53)
  - search() raises ValueError when query.text is empty
  - purge_source(source_id) removes all documents, chunks, and Qdrant vectors 
    for that source; returns ContentPurgeResult with document_ids, chunk_ids, 
    vector_ids ID tuples
  - stats() returns ContentStats with documents (row count), chunks (row count),
    vectors (chunks whose parent document has vectors_synced=1)
  - Purge is idempotent — purging unknown source_id returns ContentPurgeResult 
    with empty tuples, no error
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement hybrid search (vector + keyword) and source-scoped content purge. Completes the ContentStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/content.py`
- Design decisions: D53 (scope = Content filter only, graph is global), CP9 (embedding encapsulation)
- Depends on: ContentStore ingest (task #1871) for tables and core infrastructure
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/content.py` (extends same module)

## Implementation Notes

- Hybrid search: Qdrant vector similarity + SQLite keyword match (FTS5 or LIKE)
- Scores normalised to 0.0-1.0 regardless of underlying similarity metric
- Scope filters Content only — scope is not part of entity identity (D53)
- purge_source removes all documents and chunks for a source; also removes Qdrant vectors
- Purge is idempotent — purging unknown source returns ContentPurgeResult with zero counts

[[2026-05-26T05:12:58+02:00]]


## Research Findings

See `.owlbear/research/content-store-search-purge.md`

**Key decisions:**
- Vector-primary search: use `embed_hybrid` → `search_similar` (mirrors retrieval.py pattern)
- No FTS5 — BgeM3 sparse vectors already provide lexical matching via Qdrant internal RRF
- `source_ids` filtering: over-fetch from Qdrant, post-filter via SQLite PK lookup
- Purge: sequential cascade (find chunks → delete vectors → delete chunks → delete docs)
- Stats: simple COUNT queries against content_* tables

**AC/Protocol note:** AC4 text mentions `total_tokens` but `ContentStats` model has `documents, chunks, vectors`. Implement against model fields.

**Implementation pattern for search:**
1. `embed_hybrid` with fallback to `embed` (check `hasattr(self._embedding_provider, "embed_hybrid")`)
2. `search_similar(embedding, top_k=overfetch, embedding_type="document", scopes=list(query.scopes))`
3. Join results with `content_chunks` for source_id post-filter
4. Apply min_score, cap at top_k
5. Build ContentSearchResult with full ContentChunk objects

[[2026-05-26T05:13:09+02:00]]
## Research

Completed research for ContentStore search & purge implementation.

**Key findings:**
- Vector-primary hybrid approach — BgeM3 sparse vectors already provide BM25-equivalent lexical matching internally via Qdrant RRF. No separate FTS5/LIKE path needed (YAGNI).
- Score normalization is free — Qdrant cosine similarity is inherently [0, 1].
- `source_ids` filter requires SQLite post-filtering (not in Qdrant payload); use over-fetch + PK join.
- Purge is a straightforward cascade: find → delete vectors → delete SQL rows. Idempotent by empty-set property.
- AC/model discrepancy flagged: AC4 says `total_tokens` but ContentStats model has `vectors` field.

**Trade-off matrix:** See `.owlbear/research/content-store-search-purge.md` §3.1
**Confidence:** 0.85
**Follow-ups:** None needed — task is self-contained; implementation proceeds at backlog.

[[2026-05-26T05:53:02+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Implements remaining 3 ContentStore protocol methods (search, purge_source, stats) — all same module |
| Interface clarity | PASS (after refine) | AC refined: fixed field names (ContentStats), aligned purge result with tuple model, added ValueError contract, explicit score clamping |
| Dependency correctness | PASS | Only dep #1871 is archived (completed) |
| Module layering | PASS | Content has zero deps on other knowledge modules; uses injected EmbeddingProvider + VectorStore |
| TDD compliance | PASS | behavioral bundle — test-writer will process at todo |
| KISS/YAGNI | PASS | Vector-primary via Qdrant internal RRF; no FTS5, no separate keyword path |
| Premise challenge | PASS | Required protocol methods (currently NotImplementedError stubs) |
| Pattern consistency | PASS | Mirrors retrieval.py embed_hybrid → search_similar pattern |
| Security surface | PASS | No new system boundaries; all inputs are internal protocol models |
| Single domain | PASS | Entirely knowledge/content domain |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| search — empty text | Invalid input | ValueError | Yes (protocol contract) | Caller gets clear error |
| search — Qdrant unavailable | Infrastructure failure | Propagates | No (CP9 — impl detail) | Search fails; caller handles |
| purge — Qdrant delete fails mid-cascade | Partial purge | Propagates | Acceptable — SQL rows remain for re-purge | Stale vectors (recoverable) |
| stats — vectors_synced=0 docs | Stale count | N/A | Yes — counted accurately via join | Minor staleness acceptable per protocol |

### Design Diverge
- Skipped: single clear approach (vector-primary via Qdrant RRF). Research already eliminated alternatives (FTS5, LIKE boost). No split criteria.

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Issues raised: AC field-name mismatch (AC4), purge result wording (AC3), score normalization not guaranteed [0,1] without clamp, stats().vectors observability, missing ValueError contract
- Architect response: accepted all findings. Refined all 5 AC lines to address: (1) explicit score clamping, (2) ValueError contract added as AC2, (3) purge returns ID tuples not counts, (4) vectors = chunks with synced parent, (5) idempotency via empty tuples. Verified _cosine_similarity can produce negatives — clamp required.

### Proof-Bundle Validation
- Planner assignment: (none — null)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (5 lines) to match protocol model precisely, added ValueError contract, set proof_bundle=behavioral, advanced to todo.
