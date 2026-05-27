---
id: 1891
title: 'Knowledge: MCP wire get_next_batch to EnrichmentStore.claim_batch'
status: archived
priority: needed
created: 2026-05-27T01:00:59.243665+02:00
updated: 2026-05-27T10:10:32.526755+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - get_next_batch calls 
    EnrichmentStore.claim_batch(EnrichmentParams(batch_size=limit))
  - Each claimed item hydrated via ContentStore.get_chunk(chunk_id), 
    ContentStore.get_document(document_id), and 
    source_store_v2.get_source(source_id); items where get_chunk() returns None 
    are skipped
  - 'Response dict per item preserves all current fields: chunk_id, text, doc_title,
    section_path ("/".join or None), source_name, document_id, source_id, scope, claim_token
    (batch.batch_id), claimed_at (item.started_at ISO)'
  - Old direct SQL claiming code removed (SELECT/UPDATE block and 
    _extract_section_path helper if unused)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Replace direct SQL claiming in `get_next_batch` with EnrichmentStore.claim_batch(EnrichmentParams). Hydrate response with chunk text via ContentStore.get_chunk(). Maintain same response shape (chunk_id, text, doc_title, section_path, source_name, scope, claim_token, claimed_at).

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`

[[2026-05-27T03:14:15+02:00]]
## Research
See `.owlbear/research/mcp-get-next-batch-wiring.md`

**Implementation notes for builder:**
- AppContext already has all stores wired (`enrichment_store`, `content_store`, `source_store_v2`)
- Field mapping table in §3.1 — use dedup caches for document/source lookups
- Handle `get_chunk()` → None (skip item)
- `batch.batch_id` → `claim_token`, `item.started_at.isoformat()` → `claimed_at`
- `\"/\".join(chunk.section_path) or None` for section_path serialization
- `_normalize_batch_limit()` stays; `_extract_section_path()` likely removable

[[2026-05-27T03:14:21+02:00]]
## Research
Key findings: All building blocks exist and are wired in AppContext. Field mapping from old SQL to new store calls is 1:1. Per-item hydration with dedup caches is acceptable (same-process SQLite, max 100 items). One behavioral difference: source `enrich` flag not re-checked at claim time (low risk — items only enter queue when flag was true). No decomposition needed.

Doc: `.owlbear/research/mcp-get-next-batch-wiring.md`
Confidence: .85

[[2026-05-27T03:26:05+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: replace SQL claiming with store calls |
| Interface clarity | PASS | AC refined to name all 3 stores, all 10 response fields, and None-handling |
| Dependency correctness | PASS | Dep #1888 archived; AppContext has enrichment_store, content_store, source_store_v2 |
| Module layering | PASS | mcp-knowledge → knowledge (correct direction) |
| TDD compliance | PASS | Proof bundle behavioral; test-writer will cover |
| KISS/YAGNI | PASS | Direct replacement with dedup caches; no new abstractions |
| Premise challenge | PASS | Old SQL must go; store layer exists and is wired |
| Pattern consistency | PASS | Same AppContext→store delegation pattern as lifespan wiring |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| claim_batch() | Empty queue | Returns EnrichmentBatch(items=()) | Yes (returns []) | None — normal |
| get_chunk(chunk_id) | Chunk deleted after claim | Returns None | Yes (AC2: skip item) | Partial batch — acceptable |
| get_document(doc_id) | Document missing | Returns None | Should handle (default to \"\") | Degraded metadata |
| get_source(source_id) | Source missing | Returns None | Should handle (default to \"\") | Degraded metadata |

### Design Diverge
- Trigger: skipped — single valid approach prescribed by research; no competing designs

### Challenge Results
- Challenger: FALLBACK — subagent returned no response
- Architect response: proceeded with single-pass evaluation; straightforward 1:1 field mapping with full codebase verification

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinements Applied
- AC2: expanded from \"ContentStore.get_chunk()\" to name all 3 stores and None-skip behavior
- AC3: expanded from 4 named fields to complete 10-field response shape with derivation notes
- AC4: clarified scope of removal (SQL block + helper)

### Verdict: APPROVE
### Action Taken: Refined AC for completeness (all stores, all fields, None-handling), confirmed field mapping against ContentChunk/EnrichmentBatch models. Advanced to todo.

[[2026-05-27T03:55:15+02:00]]
## Test-Writer Notes
- Test file: `tests/test_get_next_batch_1891.py`
- Class: `TestFromAC_ClaimBatchDelegation`, `TestFromAC_PerItemHydration`, `TestFromAC_ResponseFieldMapping`, `TestFromAC_OldSqlRemoved`
- Tests per category: happy/delegation 4, hydration/edge 6, field-mapping 11, regression 2
- Total: 23 tests — all FAIL (verified by quality-runner)
- Lint: ruff clean

| AC | Tests | Status |
|----|-------|--------|
| AC1 — claim_batch(EnrichmentParams(batch_size=limit)) | test_claim_batch_called_with_batch_size_from_limit, test_claim_batch_called_with_default_limit_10, test_claim_batch_limit_clamped_to_100, test_empty_batch_returns_empty_list | 4 FAIL |
| AC2 — hydration via get_chunk/get_document/get_source; None skips | test_get_chunk_called_with_item_chunk_id, test_get_document_called_with_chunk_document_id, test_get_source_called_with_item_source_id, test_chunk_none_item_skipped, test_two_items_same_doc_get_document_called_once, test_two_items_same_source_get_source_called_once | 6 FAIL |
| AC3 — all 10 response fields from new store calls | 11 field-value tests (claim_token, claimed_at, chunk_id, text, doc_title, section_path×2, source_name, document_id, source_id, scope) | 11 FAIL |
| AC4 — old conn.execute/commit removed | test_conn_execute_not_called, test_conn_commit_not_called | 2 FAIL |

[[2026-05-27T04:13:56+02:00]]
## Builder Notes
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Implementation: Replaced direct SQL claim/select/update path in `get_next_batch` with `enrichment_store.claim_batch(EnrichmentParams(batch_size=limit))`; hydrated each claimed item via `content_store.get_chunk`, `content_store.get_document`, and `source_store_v2.get_source`; skipped items when `get_chunk()` returned `None`; preserved response keys and mapped `claim_token` from `batch.batch_id` and `claimed_at` from `item.started_at.isoformat()`.
- Cleanup: Removed old SQL-claim branch usage and removed `_extract_section_path` dependency from this code path.

- RED verification (quality-runner, scoped): tests/test_get_next_batch_1891.py -> 23 failed / 0 passed (expected before implementation).
- GREEN verification (quality-runner, scoped): tests/test_get_next_batch_1891.py -> 23 passed / 0 failed.
- Lint (quality-runner): clean=true for serve/mcp-knowledge/src/ and tests/test_get_next_batch_1891.py.
- Coverage (quality-runner, scoped): module `owlbear_mcp_knowledge.server` reported 32% (overall 34%) for this scoped run.
- Durable module-level test check: no canonical durable `test_get_next_batch.py` file found (skip).

- Commit: 227adf97b5ed0ff305242d4180b675fdde96392e
- Evidence summary: All AC-targeted task tests pass and old SQL conn usage assertions pass (`conn.execute`/`conn.commit` not called).

[[2026-05-27T04:37:56+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | The unused `_extract_section_path` helper still exists, so the cleanup clause is not satisfied even though `get_next_batch` no longer performs direct SQL claiming. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:96` still defines `_extract_section_path`; workspace search found no remaining call sites. `tests/test_get_next_batch_1891.py:493` and `tests/test_get_next_batch_1891.py:503` only prove `conn.execute`/`conn.commit` are not called. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Remove the unused `_extract_section_path` helper so AC4 is actually satisfied, then refresh the builder evidence for that cleanup. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | AC4; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py:96`; `tests/test_get_next_batch_1891.py:493`; `tests/test_get_next_batch_1891.py:503` |

## Observations
- AC1-AC3 map cleanly to `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:149-203` and the task-local tests that cover delegation, per-item hydration, field mapping, and no direct SQL calls.
- Builder evidence was otherwise sufficient for a behavioral bundle: task-local tests passed, lint was clean, and the challenger did not find another blocking concern.
- The current AC4 task tests prove SQL-path removal but do not independently prove the helper-cleanup clause.

[[2026-05-27T04:48:32+02:00]]
## Builder Notes
- Implementation: removed unused helper `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py::_extract_section_path` and dropped now-unused `json` import.
- Files changed: serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py
- Approach: Surgical AC4 cleanup only; no behavior/path changes in `get_next_batch`.

- Tests (quality-runner, scoped): `tests/test_get_next_batch_1891.py` -> 23 passed, 0 failed.
- Lint (quality-runner): clean=true for `serve/mcp-knowledge/src/` and `tests/test_get_next_batch_1891.py`.
- Coverage (quality-runner scoped run): overall 33%; module highlights include `owlbear_mcp_knowledge/_helpers.py` 19%, `owlbear_mcp_knowledge/server.py` 28%.
- Evidence summary: reviewer-blocking AC4 item resolved; `_extract_section_path` no longer exists and task-local behavioral tests remain green.

- Commit: fd439121 (chore: remove unused section-path helper (#1891, builder))

[[2026-05-27T05:09:41+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1891 -> docs | AC mapped to code and evidence sufficient.
- AC1: `get_next_batch` delegates batch claims through `EnrichmentStore.claim_batch(EnrichmentParams(batch_size=limit))` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:149` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:157`; task tests assert explicit parameter forwarding, defaulting, clamping, and empty-batch behavior at `tests/test_get_next_batch_1891.py:183`, `tests/test_get_next_batch_1891.py:195`, `tests/test_get_next_batch_1891.py:207`, and `tests/test_get_next_batch_1891.py:220`.
- AC2: each claimed item is hydrated via `content_store.get_chunk`, `content_store.get_document`, and `source_store_v2.get_source` with missing chunks skipped at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:164`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:172`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:177`; task tests cover store-call routing, skip-on-missing-chunk, and document/source dedup caches at `tests/test_get_next_batch_1891.py:235`, `tests/test_get_next_batch_1891.py:247`, `tests/test_get_next_batch_1891.py:257`, `tests/test_get_next_batch_1891.py:272`, and `tests/test_get_next_batch_1891.py:286`.
- AC3: response field mapping is assembled from store data at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:182`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:184`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:185`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:191`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:201`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:202`; task tests assert `claim_token`, `claimed_at`, `chunk_id`, `text`, `doc_title`, both `section_path` branches, `source_name`, `document_id`, `source_id`, and `scope` at `tests/test_get_next_batch_1891.py:346`, `tests/test_get_next_batch_1891.py:358`, `tests/test_get_next_batch_1891.py:370`, `tests/test_get_next_batch_1891.py:382`, `tests/test_get_next_batch_1891.py:394`, `tests/test_get_next_batch_1891.py:407`, `tests/test_get_next_batch_1891.py:421`, `tests/test_get_next_batch_1891.py:435`, `tests/test_get_next_batch_1891.py:447`, `tests/test_get_next_batch_1891.py:459`, and `tests/test_get_next_batch_1891.py:471`.
- AC4: `get_next_batch` no longer uses the old direct SQL claim path; task tests prove `conn.execute` and `conn.commit` are not invoked at `tests/test_get_next_batch_1891.py:493` and `tests/test_get_next_batch_1891.py:503`, and source-tree search under `serve/` now finds no `_extract_section_path` usage after the builder retry.
- Builder evidence sufficiency: current builder note reports quality-runner green on `tests/test_get_next_batch_1891.py` (23 passed, 0 failed) and lint clean for `serve/mcp-knowledge/src/` plus the task test at `.owlbear/kanban/tasks/1891-knowledge-mcp-wire-get-next-batch-to-enrichmentstore-claim-batch.md:156` and `.owlbear/kanban/tasks/1891-knowledge-mcp-wire-get-next-batch-to-enrichmentstore-claim-batch.md:157`.

## Observations
- Challenger review raised a potential `started_at=None` proof gap, but the concrete `EnrichmentStore.claim_batch` implementation sets `started_at` when claiming and returns rows with that value populated at `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:218`, `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:241`, `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:520`, and `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py:529`; for this wiring task, the fallback branch in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:185` is therefore not a blocking AC mismatch.
- Research documents one low-risk semantic drift versus the retired SQL path: claim-time source `enrich` filtering is no longer re-checked at batch claim time (`.owlbear/research/mcp-get-next-batch-wiring.md:71`). Architecture approved that drift for this task, so it is tracked but not blocking.
- The scoped coverage numbers in builder notes are low at module level because the file is large, but the task-local suite is strong for the touched slice: it uses value-specific assertions that would fail against the retired SQL implementation rather than generic truthy checks.

[[2026-05-27T09:44:18+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | PASS — no drift | `serve/mcp-knowledge/README.md` read in full; `get_next_batch` entry ("Atomically claim a batch of chunks ready for enrichment") remains accurate; external interface and response shape unchanged; no mention of `_extract_section_path` or SQL claiming in public docs |
| External Attribution | N/A | No external sources used; builder implemented direct store-delegation refactor using existing codebase primitives |
| Research Doc | PASS | `.owlbear/research/mcp-get-next-batch-wiring.md` exists and linked from task body at lines 39 and 53 |
| Deletion Detection | PASS | `_extract_section_path` removed; grep over `**/*.md` confirms zero public-facing docs reference this helper; no orphaned references |

### Files Updated
None — no documentation drift detected.

### Scratch Cleanup
No `.owlbear/scratch/1891-*` files found.

[[2026-05-27T10:10:32+02:00]]
## Audit

### Regression Detection
Domain-scoped regression (`serve/mcp-knowledge/tests/` + `tests/test_get_next_batch_1891.py`): 23 passed, 0 failed. Lint (`ruff check serve/mcp-knowledge/src/ tests/test_get_next_batch_1891.py`): All checks passed. Full-suite quality-runner timed out but domain-scoped run is clean and covers the touched package.

### Intent Verification
Changed files: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (main wiring), `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_helpers.py` (dead code removal). Both within `serve/mcp-knowledge/` domain — correct scope for "wire get_next_batch to EnrichmentStore.claim_batch". No extraneous files touched.

### Architect Quality
Score: **5/5** — AC lines were highly specific (named all 3 stores, all 10 response fields with derivation, None-skip behavior, explicit cleanup scope). Architecture review included failure mode map and field mapping verification. AC refinements improved testability. No builder improvisation needed beyond prescribed approach.

### Commit Integrity
- `227adf97` — feat: wire get_next_batch via enrichment store (#1891, builder)
- `fd439121` — chore: remove unused section-path helper (#1891, builder)
- Both commits present in git history for touched files with correct format and attribution.

### Reviewer Evidence
Detailed PASS verdict with AC-to-code mapping for all 4 AC lines. First review caught AC4 gap (unused helper), builder resolved, second review confirmed PASS.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
