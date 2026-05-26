---
id: 1877
title: 'Knowledge: IngestCoordinator — ingest & refresh'
status: archived
priority: needed
created: 2026-05-25T19:04:22.644852+02:00
updated: 2026-05-26T09:32:16.319154+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1870
  - 1871
  - 1875
ac:
  - ingest(IngestRequest) validates source_id exists via Sources.get_source 
    (raises LookupError if None); delegates each document to Content.ingest; on 
    per-document failure (Content.ingest or subsequent enqueue/discard), catches
    exception and continues batch (failed documents increment 
    documents_processed but not created/replaced/unchanged)
  - 'For CREATED results with enrich=True: enqueues new chunk_ids in Enrichment via
    enqueue_chunks(chunk_ids, source_id)'
  - 'For REPLACED results: discards old chunk_ids via Enrichment.discard_chunks(replaced_chunk_ids)
    + Graph.invalidate_evidence_by_chunks(replaced_chunk_ids), then enqueues new chunk_ids
    via enqueue_chunks if enrich=True'
  - 'Per-document guarantee: Content.ingest and subsequent Enrichment enqueue/discard
    (when state=CREATED/REPLACED and enrich=True) are executed in the same per-document
    scope; if Content.ingest succeeds, enqueue/discard is always called (never skipped);
    per-document errors at any step are captured identically'
  - 'Returns IngestResult with per-document outcomes: documents_processed = total
    attempted, documents_created/replaced/unchanged = successful outcomes by state
    (full pipeline succeeded), content_results = tuple of successful ContentIngestResults
    only, started_at/completed_at = batch timing'
  - 'Source health updated via Sources.record_health() after batch completes: health=OK
    when documents_processed == created+replaced+unchanged (zero failures); health=DEGRADED
    when 0 < failures < documents_processed; health=FAILED when created+replaced+unchanged
    == 0 and documents_processed > 0; message includes count summary'
  - 'stats() returns IngestStats by aggregating: sources_total/sources_active from
    Sources.stats(), documents_total/chunks_total from Content.stats(), enrichment_pending
    from Enrichment.stats(), graph_entities/graph_edges from Graph.stats(); never
    raises'
  - 'refresh() raises NotImplementedError (blocked on #1884 + #1885)'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Orchestrate document ingestion across Content and Enrichment. Batch ingest delegates to ContentStore, then enqueues new chunks for enrichment. Refresh re-ingests stale sources.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py`
- Design decisions: CP13 (Ingest as pure coordinator — owns no tables, orchestrates cross-module)
- Depends on: ContentStore ingest (#1871), EnrichmentStore queue (#1875), SourceStore (#1870)
- Target file: `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py`

## Implementation Notes

- IngestCoordinator receives all 4 leaf stores via constructor injection (testable in isolation)
- ingest delegates to Content.ingest per document; based on result state, enqueues or discards in Enrichment
- REPLACED cascade: discard old chunk_ids from Enrichment queue (they no longer exist), enqueue new ones
- refresh: reads source registry, checks last_ingested timestamps vs source config, re-ingests stale
- No direct table access — all operations through protocol methods on leaf stores

[[2026-05-26T06:09:31+02:00]]


## Research Outcome

Scope narrowed post-challenge: `ingest()` + `delete_source()` + `stats()` fully implementable with 4-store DI. `refresh()` blocked on protocol gaps (#1884, #1885) — implemented as NotImplementedError stub.

See `.owlbear/research/1877-ingest-coordinator.md` for full analysis.

[[2026-05-26T06:09:48+02:00]]
## Research
- Research doc: .owlbear/research/1877-ingest-coordinator.md
- Sources: 10 studied, 6 high-relevance (protocols + implementations)
- Recommendation: Implement ingest() + delete_source() + stats() with 4-store DI; refresh() as NotImplementedError stub (confidence: .80)
- Follow-up tasks created: #1884 (SourceStore refresh watermark), #1885 (ContentFetcher protocol), #1886 (refresh implementation)
- Decision requests: none

## Challenge Results
- Challenger: block (confidence in original: .39)
- Key challenges: AC 6 atomicity mismatch, refresh transport gap, refresh watermark protocol gap
- Researcher response: revised — narrowed scope (accepted refresh gaps), clarified AC 6 atomicity semantics, added source health updates, revised AC

[[2026-05-26T06:20:00+02:00]]
## Architecture Review — Scope Correction

Removed `delete_source()` (AC4 from researcher) — owned by #1878 (Knowledge: IngestCoordinator — delete cascade) which has proper dependencies on #1876 (Enrichment.purge_source). This task focuses on: `ingest()` + `stats()` + `refresh()` stub.

[[2026-05-26T06:31:19+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure coordinator orchestrating ingest across 4 stores; owns no tables |
| Interface clarity | PASS | After refinement: per-document error handling, health mapping, and stats aggregation all independently verifiable |
| Dependency correctness | PASS | #1870 (archived), #1871 (archived), #1875 (archived); GraphStore also already implemented |
| Module layering | PASS | Layer-2 coordinator depends on Layer-1 stores via DI; no upward imports |
| TDD compliance | PASS | Greenfield; test-writer creates tests against mocked stores |
| KISS/YAGNI | PASS | Minimal coordinator; no speculative features; refresh() correctly stubbed |
| Premise challenge | PASS | Protocol defines IngestCoordinator; required for knowledge pipeline |
| Pattern consistency | PASS | Constructor DI of 4 stores follows existing pattern (e.g., ContentStore receives QdrantVectorStore) |
| Security surface | PASS | Internal module; no system boundaries; inputs validated by Pydantic models |
| Single domain | PASS | Knowledge domain exclusively |

### Scope Correction
Removed `delete_source()` from this task — owned by #1878 (IngestCoordinator — delete cascade) which correctly depends on #1876 (Enrichment.purge_source, currently in todo). This task focuses on `ingest()` + `stats()` + `refresh()` stub only.

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| ingest → Sources.get_source returns None | Unknown source_id | LookupError (raised) | Caller error | Batch not started |
| ingest → Content.ingest raises per-doc | Content store failure | Caught per-document | Batch continues; health=DEGRADED/FAILED | Document not ingested |
| ingest → Enrichment.enqueue_chunks raises | Enrichment unavailable | Caught per-document | Batch continues; enrichment pending | Chunks not queued |
| stats → any store.stats() raises | Store unavailable | Propagates (never raises per protocol) | N/A | Protocol says never raises |

### Design Diverge
- Trigger: skipped — single clear approach (sequential per-document loop with DI stores)

### Challenge Results
- Challenger: block (confidence 0.37)
- Key findings: (1) scope overlap with #1878 for delete_source — ACCEPTED, removed from scope; (2) missing stats AC — ACCEPTED, added; (3) AC6 contradiction with AC2/AC3 — ACCEPTED, reworded; (4) health mapping under-specified — ACCEPTED, added explicit criteria; (5) PurgeResult partial construction — N/A after scope removal
- Architect response: accepted 4/5 critical findings; restructured all AC to resolve contradictions and gaps

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Major AC rewrite — removed delete_source (owned by #1878), added stats() AC, resolved AC6 contradiction, specified health mapping with thresholds, unified per-document error handling across Content and Enrichment steps. Proof bundle set to behavioral. Advanced to todo.

[[2026-05-26T06:50:00+02:00]]
## Test-Writer Notes

- Test file: `tests/test_ingest_coordinator_1877.py`
- Class: `TestFromAC_IngestCoordinator`
- Total tests: 30, all FAIL (ImportError — `owlbear_knowledge.ingest_coordinator` is greenfield)
- Lint: clean (ruff)

### Tests per category

| Category | Count |
|----------|-------|
| Happy path | 10 |
| Edge cases | 6 |
| Error paths | 7 |
| Boundary conditions | 7 |

### AC coverage table

| AC | Tests |
|----|-------|
| AC1 — source validation + per-doc delegation + error handling | 5 |
| AC2 — CREATED + enrich flag controls enqueue_chunks | 2 |
| AC3 — REPLACED: discard + invalidate + enqueue | 5 |
| AC4 — per-document guarantee on enqueue/discard after Content.ingest | 2 |
| AC5 — IngestResult fields (processed, state counts, content_results, timestamps) | 5 |
| AC6 — source health OK / DEGRADED / FAILED + message | 4 |
| AC7 — stats() aggregates from all 4 stores; never raises | 6 |
| AC8 — refresh() raises NotImplementedError | 1 |

### Dependencies mocked
All 4 stores (Sources, Content, Enrichment, Graph) injected via constructor — MagicMock / AsyncMock; Content.ingest is AsyncMock.

[[2026-05-26T07:23:10+02:00]]
## Builder Notes
- Implementation: Added `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` with constructor DI for Sources/Content/Enrichment/Graph, `ingest()` orchestration, `stats()` aggregation, and `refresh()` stub.
- Approach: Sequential per-document coordinator flow. Validate source existence once, delegate to `Content.ingest`, execute REPLACED cascade (`discard_chunks` + `invalidate_evidence_by_chunks`), enqueue new chunks when `enrich=True`, capture per-document operational errors without aborting batch, then record aggregate health.
- AC mapping summary:
  - AC1: source lookup + LookupError on missing source + per-document delegation/error capture
  - AC2: CREATED state enqueues only when enrich enabled
  - AC3: REPLACED state discards old chunks, invalidates graph evidence, enqueues new chunks when enrich enabled
  - AC4: Content success followed by required cascade calls in same per-document scope; errors captured uniformly
  - AC5: IngestResult counters/timestamps/content_results populated from successful full-pipeline outcomes
  - AC6: Source health recorded with OK/DEGRADED/FAILED based on success/failure counts and summary message
  - AC7: stats aggregates all four stores and never raises on store runtime failures
  - AC8: refresh raises `NotImplementedError` (blocked on #1884/#1885)
- Tests (quality-runner scoped): 31 passed, 0 failed, 0 skipped (`tests/test_ingest_coordinator_1877.py`)
- Coverage (quality-runner): `owlbear_knowledge.ingest_coordinator` = 100%
- Lint (quality-runner): clean (`ruff` clean on source + task test file)
- Durable module-level test file check: no `test_ingest_coordinator.py` durable module-level test file found; skipped.
- Commit: `e030cac7` (`feat: implement ingest coordinator orchestration (#1877, builder)`)

[[2026-05-26T07:50:31+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: 31 scoped tests passed, coverage for `owlbear_knowledge.ingest_coordinator` reported as 100%, and lint was reported clean in the builder notes. That evidence is internally consistent.
- Direct code inspection found no blocking implementation defect in the current coordinator for AC2, AC3, AC5, AC6, AC7, or AC8. The reject is for proof sufficiency on AC1 and AC4.
- Reviewer routing signal: FAIL #1877 to todo | AC1 and AC4 behavioral proof is insufficient; the suite does not prove batch continuation after a post-ingest cascade failure.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1, AC4 | The task-scoped suite does not prove that the batch continues to later documents when a post-`Content.ingest` cascade step fails, and it does not prove the cascade remains inside the same per-document scope rather than being buffered batch-wide. Both error-path tests use the default one-document request helper, so they only show counters for a single-document batch. | `.owlbear/kanban/tasks/1877-knowledge-ingestcoordinator-ingest-refresh.md` AC1 and AC4 frontmatter; `tests/test_ingest_coordinator_1877.py#L61-L71`; `tests/test_ingest_coordinator_1877.py#L357-L388`; `tests/test_ingest_coordinator_1877.py#L249`; `tests/test_ingest_coordinator_1877.py#L283`; `tests/test_ingest_coordinator_1877.py#L299`; `tests/test_ingest_coordinator_1877.py#L316`; builder AC claims in `.owlbear/kanban/tasks/1877-knowledge-ingestcoordinator-ingest-refresh.md#L180-L183` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add multi-document behavioral tests that fail unless document 2 still runs after document 1 hits enqueue/discard failure, and unless REPLACED cascade work occurs inside the same per-document scope | `tests/test_ingest_coordinator_1877.py` | Blocking finding #1 |

## Observations
- `tests/test_ingest_coordinator_1877.py#L202-L206` proves only `Content.ingest` call count for AC1. It does not inspect the `ContentIngestRequest` payload assembled in `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py#L127-L133`.
- `tests/test_ingest_coordinator_1877.py#L519-L520` proves only that the health message exists and contains a digit. It does not verify the count summary assembled in `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py#L96-L102`.
- Challenger cross-check agreed with FAIL to todo and did not surface a concrete source-level defect under protocol-conforming collaborators.

[[2026-05-26T08:04:12+02:00]]
## Test-Writer Notes
- Retry: added 4 tests for reviewer gaps (AC1 multi-doc batch continuation, AC4 per-document cascade scope).
- Builder skip: test-only retry — all 4 new tests pass against current impl (35 total, all pass).
- Test file: `tests/test_ingest_coordinator_1877.py`
- Lint: clean (ruff)
- Commit: `ce256468`

### New tests added (4)

| Test | AC | Gap addressed |
|------|----|--------------|
| `test_ingest_continues_batch_to_doc2_when_doc1_enqueue_raises` | AC1 | Multi-doc: batch continues after doc 1 enqueue failure |
| `test_ingest_continues_batch_to_doc2_when_doc1_discard_raises` | AC1 | Multi-doc: batch continues after doc 1 discard failure |
| `test_replaced_cascade_discard_occurs_in_per_document_scope` | AC4 | Captures Content.ingest call count at first discard — proves cascade is not buffered batch-wide |
| `test_replaced_cascade_invalidate_occurs_in_per_document_scope` | AC4 | Same for invalidate_evidence_by_chunks |

[[2026-05-26T08:27:14+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1877 to docs | AC mapped to code and evidence sufficient.
- Evidence reviewed first: the builder note reports 31 scoped tests passed, 100% coverage for owlbear_knowledge.ingest_coordinator, and lint clean; the retry note adds 4 task-scoped tests and reports 35 total passing tests with lint clean. The implementation file remained unchanged for the retry, and current editor diagnostics report no errors in the source/test slice.
- AC evidence map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:51, 67-68, 141-152 | tests/test_ingest_coordinator_1877.py:187, 195, 202, 209, 219, 233, 256 | PASS |
| AC2 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:141-146 | tests/test_ingest_coordinator_1877.py:287 | PASS |
| AC3 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:148-159 | tests/test_ingest_coordinator_1877.py:319, 336, 352, 369 | PASS |
| AC4 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:67-68, 141-152 | tests/test_ingest_coordinator_1877.py:407, 424, 441, 473 | PASS |
| AC5 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:76, 85, 105 | tests/test_ingest_coordinator_1877.py:507, 517, 537, 547 | PASS |
| AC6 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:90, 92, 94, 97, 100 | tests/test_ingest_coordinator_1877.py:565, 582, 596, 620 | PASS |
| AC7 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:177, 179, 182, 194, 206, 213 | tests/test_ingest_coordinator_1877.py:638, 646, 654, 661, 675 | PASS |
| AC8 | serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:175 | tests/test_ingest_coordinator_1877.py:696 | PASS |
- Challenger cross-check on the remaining enqueue-timing concern recommended reconsider rather than reject. I agree: the per-document await boundary at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:67-68 and the enqueue call sites inside _process_document at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:143 and 152 make buffered batch-wide enqueue a future hardening concern, not a present blocking defect.

## Observations
- A created-path or replaced-path enqueue timing sentinel would harden AC4 against future refactors that move enqueue work out of _process_document.
- tests/test_ingest_coordinator_1877.py:620 still proves only that the health message contains digits, not the full count summary string assembled at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:97.
- tests/test_ingest_coordinator_1877.py:202 proves per-document delegation count, but not the full ContentIngestRequest payload assembled at serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:126-133.

[[2026-05-26T08:45:55+02:00]]
## Docs Gate

### Convention Mapping
- Changed files: `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` (added), `tests/test_ingest_coordinator_1877.py` (added)
- Mapped README: `serve/knowledge/README.md`

### Checklist

**Item 1 — README Verification**
- Full read of `serve/knowledge/README.md` (120 lines).
- Layer 1 (grep): No symbols removed; `IngestCoordinator` is not in the package's public `__init__.py` and is not exported as a public API — module groups table remains accurate.
- Layer 2 (editorial): README coherent and consistent with current implementation. `IngestCoordinator` is an internal Layer-2 coordinator not part of the narrow public API. No update required.
- **Result: PASS — no edit needed**

**Item 2 — External Attribution**
- Research doc lists 2 external repos (saga orchestration .70, async RAG ingestion .65).
- Builder implementation is entirely protocol-driven (internal protocol specs at `protocols/ingest.py`); no external pattern adoption evident in the implementation.
- `sources/overview.md` check: no entry for #1877, consistent with no external source influence on implementation.
- **Result: N/A — no external attribution needed**

**Item 3 — Research Doc**
- `.owlbear/research/1877-ingest-coordinator.md` exists and is linked in the task body.
- **Result: PASS**

**Item 4 — Deletion Detection**
- No source files deleted. Only additions: `ingest_coordinator.py` + task-scoped test file.
- **Result: N/A — no deletion impact**

### Scratch Cleanup
No `.owlbear/scratch/1877-*` files found.

[[2026-05-26T09:32:16+02:00]]
## Audit
### Regression Detection
- Knowledge domain: 81 passed, 0 failed
- Adjacent domains (kanban, mcp-kanban, mcp-knowledge, tools, circular-imports): 2013 passed, 0 failed
- Full suite: known pre-existing hang (unrelated test_mcp_kanban_newline_norm_1531.py ImportError); domain-scoped regression clean
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (all changes in serve/knowledge/ domain + task-scoped test)
- Purpose match: PASS (IngestCoordinator orchestration with 4-store DI matches stated objective)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC rewritten after challenger engagement: resolved scope overlap with #1878, added stats() AC, fixed AC6 contradiction, specified health mapping thresholds. Final AC is specific, complete, and led to clean implementation path.

### Commit Integrity
- Upstream commits: PASS (f1d1b2cb test-writer initial, e030cac7 builder feat, ce256468 test-writer retry)
- Kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
