---
id: 1320
title: 'P0-04: Qdrant filesystem persistence + source identity fix'
status: in-progress
priority: critical
created: 2026-05-04T05:48:37.771717+00:00
updated: 2026-05-04T12:38:48.468695+00:00
tags:
- phase-0
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1319
blocked: false
block_reason:
claimed_at: 2026-05-04T12:38:48.468695+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.3)

## Acceptance Criteria

- [ ] Qdrant uses filesystem persistence — vectors survive server restart (O6)
- [ ] SQLite DB on disk — data survives server restart (O6)
- [ ] Both Qdrant and SQLite storage paths are gitignored
- [ ] ingest_document registers/resolves source record before storing chunks
- [ ] Source record: name, URL/path, fetch_method (http/browser/local), enrich flag (true/false), timestamps
- [ ] Source identity resolved by URL (web) or file path (local)
- [ ] All #1319 tests pass green

## Scope

- **In scope:** Qdrant config, SQLite persistence, source record table/model, ingest_document source registration
- **Out of scope:** Enrichment schema (Layer 1), browser detection flow (Layer 1)
[[2026-05-04]]
## Research
- Research doc: .owlbear/research/1320-qdrant-persistence-source-identity-impl.md
- Sources: 10 studied, 6 high-relevance (1.0)
- Recommendation: 4-change wiring task (~20 LOC across server.py + .gitignore) (confidence: 0.92)
- Follow-up tasks created: none — this IS the implementation task
- Decision requests: none

## Key Findings

All library code already works — 34/34 #1319 tests pass GREEN. Gaps are MCP server wiring only:

1. `QdrantVectorStore()` in lifespan defaults to `:memory:` — needs `location=".owlbear/knowledge/vectors"`
2. `IngestPipeline()` missing `source_store=source_store` kwarg (created but not passed)
3. MCP `ingest_document` tool lacks `source_url`/`source_id` params (pipeline supports them)
4. `.gitignore` missing Qdrant directory entry

## Challenge Results
Challenge: proceed — confidence 0.92. Trivial wiring, no design ambiguity.
[[2026-05-04]]

## Architecture Review

### Verdict: APPROVE (after AC refinement)

### AC Refinements Applied

| Original AC | Issue | Refined |
|------------|-------|---------|
| "Source identity resolved by URL (web) or file path (local)" | `ingest_text` has no `source_path` param; `resolve_by_path` exists in source_store but is not callable from the ingest pipeline. Library change required — out of scope for P0 wiring. | Narrowed to URL-only: "Source identity resolved by URL (web sources)" |
| (implicit) MCP tool adds `source_id` param | Raw `source_id` bypasses register/resolve contract. Internal callers (refresh, bookmark) can use library directly. MCP surface should enforce the contract. | MCP tool exposes `source_url` only; no raw `source_id` passthrough |

**Deferred:** Local-file path resolution requires adding `source_path` parameter to `IngestPipeline.ingest_text` + MCP tool surface — separate Layer 1 task.

### Refined AC (with test-depth)

- [ ] Qdrant uses filesystem persistence — vectors survive server restart (td:1)
- [ ] SQLite DB on disk — data survives server restart (td:0)
- [ ] Both Qdrant and SQLite storage paths are gitignored (td:0)
- [ ] ingest_document registers/resolves source record before storing chunks via `source_url` param (td:1)
- [ ] Source record model: name, URL/path, fetch_method, enrich flag, timestamps (td:0)
- [ ] Source identity resolved by URL (web sources); local-file path deferred to Layer 1 (td:1)
- [ ] All #1319 tests pass green (td:0)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes relate to persistence wiring at MCP server layer |
| Interface clarity | PASS (after refine) | AC6 narrowed to match deliverable surface; source_id removed from MCP tool |
| Dependency correctness | PASS | #1319 archived (done); test file exists with 34 tests |
| Module layering | PASS | MCP server (mcp-knowledge) → library (knowledge); no upward imports |
| TDD compliance | PASS | #1319 provides library-level tests; test-writer will add MCP integration tests |
| KISS/YAGNI | PASS | ~20 LOC wiring, no new abstractions |
| Premise challenge | PASS | Library implementations exist; only server wiring is missing |
| Pattern consistency | PASS | Follows existing env-var config pattern (OWLBEAR_QDRANT_PATH alongside OWLBEAR_KB_PATH) |
| Security surface | PASS | source_url is stored as metadata only, not fetched; ContentInjectionGuard already covers content |
| Single domain | PASS | Knowledge domain only |

### Challenger Results

Confidence: 0.43 (reconsider signal). Concerns evaluated:
1. **Local-file path gap** — VALID. Fixed by narrowing AC6 to URL-only for P0.
2. **Source contract mismatch (AUTHENTICATED_WEB hardcode)** — ACKNOWLEDGED but out of scope. Refresh compatibility is Layer 1. P0 auto-creates minimal web-source records.
3. **Proof gap (no MCP integration tests)** — Expected. Test-writer produces these at `todo` stage.
4. **source_id bypass** — VALID. Removed from MCP tool surface.

### Notes for Builder

- Move `source_store = KnowledgeSourceStore(conn)` BEFORE `IngestPipeline()` creation
- Pass `source_store=source_store` to `IngestPipeline()`
- Add `source_url: str | None = None` param to MCP `ingest_document` tool
- Forward as `source_url=source_url` to `pipeline.ingest_text()`
- Do NOT expose raw `source_id` on MCP surface
- Qdrant path: `os.environ.get("OWLBEAR_QDRANT_PATH", ".owlbear/knowledge/vectors")`
- Add `.owlbear/knowledge/vectors/` to both `.gitignore` and `seed/.gitignore`
[[2026-05-04]]
Architecture review complete. AC refined: (1) AC6 narrowed to URL-only source resolution (local-file path requires library changes deferred to Layer 1), (2) MCP tool exposes source_url only — no raw source_id bypass. Challenger confidence 0.43 (reconsider) — all concerns addressed via AC refinement. 10 criteria PASS. Advancing to todo.
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_persistence_source_wiring_1320.py
- Classes: TestFromAC_QdrantFilesystemPersistence, TestFromAC_IngestDocumentSourceUrl, TestFromAC_SourceStoreWiring, TestFromAC_SourceResolutionByUrl
- Tests per category: happy 9, edge 0, error 0, boundary 0
- Total: 9 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | AC Text | Tests |
|---|---|---|
| AC1 (td:1) | Qdrant uses filesystem persistence | `test_qdrant_vector_store_uses_filesystem_path_by_default`, `test_qdrant_path_uses_env_var_when_set` |
| AC4 (td:1) | ingest_document registers/resolves source via source_url | `test_ingest_document_signature_has_source_url_param`, `test_ingest_document_source_url_defaults_to_none`, `test_ingest_document_forwards_source_url_to_pipeline`, `test_ingest_document_source_url_none_by_default`, `test_ingest_pipeline_receives_source_store_kwarg` |
| AC6 (td:1) | Source identity resolved by URL | `test_ingest_document_with_source_url_triggers_source_resolution`, `test_ingest_document_without_source_url_passes_none` |

### Failure root causes
1. `QdrantVectorStore()` called without `location=` arg (defaults to `:memory:`)
2. `ingest_document` missing `source_url` parameter
3. `IngestPipeline` constructed without `source_store=` kwarg in `app_lifespan`