---
id: 1886
title: 'Knowledge: IngestCoordinator.refresh() — implement refresh with fetcher'
status: archived
priority: medium
created: 2026-05-26T06:08:59.608970+02:00
updated: 2026-05-26T11:28:29.609676+02:00
tags:
  - knowledge
  - layer-2
parent: 1877
depends_on:
  - 1884
  - 1885
ac:
  - 'IngestCoordinator.__init__ accepts optional fetcher: SourceFetcher | None (backward-compatible,
    defaults to None)'
  - refresh() with no fetcher returns empty RefreshResult (sources_checked=0, 
    sources_refreshed=0)
  - refresh() lists sources with state=ACTIVE (ConfiguredSourceRecord only), 
    filters by request.source_ids when non-empty, filters by refreshable=True 
    unless request.force=True
  - refresh() calls SourceFetcher.fetch_source per filtered source; maps each 
    FetchedDocument to IngestDocument (title, text, uri, external_id, metadata —
    1:1 field copy)
  - refresh() calls self.ingest(IngestRequest(source_id=source.id, 
    documents=mapped_docs, enrich=source.enrich)) only when fetch returns ≥1 
    document
  - refresh() updates last_refreshed_at via update_source(source.id, 
    SourceUpdate(last_refreshed_at=now)) after each successfully-fetched source 
    (including zero-document results; NOT after errors)
  - Per-source errors (any exception from fetch_source or self.ingest) captured 
    as RefreshError(source_id, str(exc), timestamp) in RefreshResult.errors; 
    batch continues to next source
  - RefreshResult.sources_checked = count of filtered sources attempted; 
    sources_refreshed = count completed without error; ingest_results = tuple of
    IngestResult from successful ingest calls; errors = tuple of per-source 
    RefreshErrors
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Implement the IngestCoordinator.refresh() method using the ContentFetcher protocol and SourceStore refresh watermarks.

## Context

- Depends on: SourceStore last_refreshed_at write path, ContentFetcher protocol
- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/ingest.py` (RefreshRequest/RefreshResult)
- Design: list active+refreshable sources, fetch content, call self.ingest(), update watermark
- Gap identified in: `.owlbear/research/1877-ingest-coordinator.md`

[[2026-05-26T10:09:52+02:00]]
## Research Findings

See `.owlbear/research/1886-refresh-implementation.md`

### Implementation Approach

- Add optional `fetcher: SourceFetcher | None = None` to `IngestCoordinator.__init__`
- Replace `NotImplementedError` stub with ~40 LOC refresh loop:
  1. Guard on fetcher presence (return empty if None)
  2. `list_sources(state=ACTIVE)` → filter by source_ids + refreshable (unless force)
  3. Per-source: `fetch_source()` → map `FetchedDocument` → `IngestDocument` → `self.ingest()` → `update_source(last_refreshed_at=now)`
  4. Per-source error isolation → `RefreshError`
- Update existing AC8 test (currently asserts NotImplementedError)

### Tier: T1 (autonomous)

Fills planned gap using existing protocol types. No new capability, no architectural change.

[[2026-05-26T10:10:01+02:00]]
## Research

Key findings: refresh() is a straightforward integration of existing SourceFetcher protocol + SourceUpdate watermark. ~40 LOC addition to ingest_coordinator.py.

Trade-off: constructor extension (optional 5th param) vs method-level injection → constructor wins (protocol signature is fixed).

Doc: `.owlbear/research/1886-refresh-implementation.md`
Tier: T1 autonomous — no follow-up tasks needed, 8 AC written.
Challenge: skipped (trivial protocol integration).

[[2026-05-26T10:25:13+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single method implementation on existing coordinator |
| Interface clarity | PASS | After refinement: all edge cases (empty fetch, enrich propagation, watermark semantics, counter definitions) explicitly specified |
| Dependency correctness | PASS | #1884 (archived), #1885 (archived) — both complete |
| Module layering | PASS | Layer-2 coordinator consuming Layer-1 stores via DI; no upward imports |
| TDD compliance | PASS | Existing AC8 test asserts NotImplementedError; test-writer will replace with behavioral tests |
| KISS/YAGNI | PASS | ~40 LOC addition; optional constructor param; no speculative features; cancel support deferred (not in RefreshRequest) |
| Premise challenge | PASS | Protocol defines refresh(); stub explicitly created for this task; both prerequisites delivered |
| Pattern consistency | PASS | Per-source error isolation mirrors existing per-document pattern in ingest(); DI constructor extension follows existing 4-store pattern |
| Security surface | PASS | Internal coordinator; no new system boundaries; inputs validated by Pydantic BoundaryModels |
| Single domain | PASS | Knowledge domain exclusively |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| refresh → no fetcher injected | No fetch capability | N/A | Returns empty RefreshResult | None (graceful no-op) |
| refresh → fetch_source raises | Transport error | Any Exception | Captured in RefreshError, batch continues | Source skipped; watermark not updated |
| refresh → self.ingest raises | Ingest pipeline failure | Any Exception | Captured in RefreshError, batch continues | Source skipped; watermark not updated |
| refresh → update_source raises | Store write failure | LookupError/ValueError | Captured in RefreshError | Watermark not persisted but ingest completed |
| refresh → list_sources empty | No eligible sources | N/A | Returns RefreshResult(sources_checked=0) | None |

### Design Diverge
- Trigger: skipped — single clear approach from research (constructor DI + sequential per-source loop). No competing approaches.

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Key findings: (1) AC5 empty-fetch gap vs IngestRequest min_length=1 — ACCEPTED, refined; (2) AC5 enrich propagation ambiguity — ACCEPTED, refined to specify source.enrich; (3) AC6 watermark semantics on error — ACCEPTED, refined to specify "NOT after errors"; (4) AC4/AC7 error promotion rules — PARTIALLY ACCEPTED, clarified RefreshError is per-source only; (5) cancel param not surfaced — DECLINED (YAGNI, not in RefreshRequest); (6) integration backstop — DECLINED (this task IS the integration point)
- Architect response: revised — rewrote all 8 AC lines addressing precision gaps. AC5 now specifies enrich source and ≥1 document condition. AC6 specifies "including zero-document results; NOT after errors". AC3 explicitly names ConfiguredSourceRecord. AC8 defines exact counter semantics.

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Rewrote all 8 AC lines to close challenger-identified precision gaps (empty-fetch branch, enrich propagation, watermark error semantics, counter definitions, ConfiguredSourceRecord filter). Set proof_bundle=behavioral. Advanced to todo.

[[2026-05-26T10:35:35+02:00]]
## Test-Writer Notes
- Test file: tests/test_ingest_coordinator_1886.py
- Classes: TestFromAC_RefreshImplementation
- Tests per category: happy 18, edge 12, error 10, boundary 4
- Total: 44 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 — fetcher optional param | test_init_accepts_fetcher_keyword_argument, test_init_accepts_explicit_fetcher_none |
| AC2 — no fetcher → empty RefreshResult | 5 tests (result type, sources_checked=0, sources_refreshed=0, errors empty, explicit None) |
| AC3 — list ACTIVE, filter source_ids, filter refreshable/force | 6 tests |
| AC4 — fetch_source per source; FetchedDocument→IngestDocument 1:1 | 8 tests (title, text, uri, external_id, None external_id, metadata, all docs, source record passed) |
| AC5 — ingest only when ≥1 doc; enrich=source.enrich | 5 tests |
| AC6 — update last_refreshed_at; zero-doc yes; error no | 5 tests |
| AC7 — RefreshError on fetch/ingest error; batch continues; str(exc) | 7 tests |
| AC8 — counter semantics (sources_checked, refreshed, ingest_results, errors) | 6 tests |

Failure evidence:
- AC1 tests: TypeError (fetcher kwarg not accepted)
- AC2 tests: NotImplementedError (refresh stub not yet implemented)
- AC3–AC8 tests (37 tests): TypeError in coordinator fixture (fetcher kwarg rejected by __init__)

[[2026-05-26T10:44:18+02:00]]
## Builder Notes
- Implementation: updated serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py to add optional `fetcher` DI and implement `refresh()` end-to-end per AC1-AC8.
- RED verification (quality-runner, scoped): `tests/test_ingest_coordinator_1886.py` failed as expected before edits (TypeError on `fetcher` kwarg + NotImplementedError stub).
- GREEN verification (quality-runner, scoped): `tests/test_ingest_coordinator_1886.py` -> 44 passed, 0 failed; ruff clean.
- Coverage evidence:
  - Task-scoped only: module coverage 32% (expected, only refresh-focused tests).
  - With durable module tests included: module coverage 100%.
- Regression signal from module-level durable test check:
  - `tests/test_ingest_coordinator_1877.py::TestFromAC_IngestCoordinator::test_refresh_raises_not_implemented_error` fails (`DID NOT RAISE NotImplementedError`) because refresh is now implemented for #1886.
- Lint status: clean.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update stale durable `TestFromAC` expectation for refresh behavior (remove/replace `NotImplementedError` assertion so durable tests align with #1886 contract) | tests/test_ingest_coordinator_1877.py | quality-runner scoped run with task+durable tests: single failure `test_refresh_raises_not_implemented_error` |

[[2026-05-26T10:52:03+02:00]]
## Test-Writer Notes
- Retry: replaced stale `test_refresh_raises_not_implemented_error` with `test_refresh_with_no_fetcher_returns_empty_refresh_result` in tests/test_ingest_coordinator_1877.py
- Old test asserted `NotImplementedError` (temporary AC8 placeholder, blocked on #1884+#1885 — now resolved)
- New test asserts `refresh()` returns `RefreshResult(sources_checked=0, sources_refreshed=0, errors=())` when no fetcher is injected (aligned to #1886 AC2 behavioral contract)
- Added `RefreshResult` import; updated module docstring for AC8
- Verification: test PASSES against current impl (1 passed, 0 failed); ruff clean
- Builder skip: test-only retry, all new tests green

[[2026-05-26T11:02:29+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1886 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task-scoped quality-runner evidence in the task body reports `tests/test_ingest_coordinator_1886.py` -> 44 passed / 0 failed, ruff clean, and coverage at 32% for task-only plus 100% when durable module tests are included. The only recorded regression was the stale durable `NotImplementedError` expectation, and the retry replaced it with a no-fetcher behavioral assertion in `tests/test_ingest_coordinator_1877.py` that passes.
- AC evidence map:
| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:47` adds optional `fetcher: SourceFetcher | None = None` constructor DI | `tests/test_ingest_coordinator_1886.py:193` proves `fetcher=` is accepted and explicit `None` is allowed | PASS |
| AC2 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:179-180` returns empty `RefreshResult()` when no fetcher is configured | `tests/test_ingest_coordinator_1886.py:240`, `:247`, `:254`, `:261` and durable guard `tests/test_ingest_coordinator_1877.py:698` assert empty result counters/errors | PASS |
| AC3 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:182`, `:187` lists ACTIVE sources and applies `source_ids` / `refreshable` / `force` filters | `tests/test_ingest_coordinator_1886.py:284`, `:291`, `:305`, `:319`, `:342`, `:741` verify ACTIVE listing and post-filter counting | PASS |
| AC4 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:196`, `:199-203` fetches each source and maps fetched fields 1:1 into `IngestDocument` | `tests/test_ingest_coordinator_1886.py:359`, `:372`, `:386`, `:400`, `:415`, `:430`, `:453`, `:468` verify source handoff and field mapping | PASS |
| AC5 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:208-214` calls `self.ingest(...)` only for non-empty docs and passes `enrich=source.enrich` | `tests/test_ingest_coordinator_1886.py:487`, `:502`, `:513`, `:523`, `:534` verify call gating, source_id, and enrich propagation | PASS |
| AC6 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:218-223` updates `last_refreshed_at` after successful fetches, including zero-doc results; exceptions skip the watermark | `tests/test_ingest_coordinator_1886.py:545`, `:564`, `:579`, `:592`, `:605` verify timestamp bounds, zero-doc update, and no update after fetch/ingest errors | PASS |
| AC7 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:225-230` captures per-source exceptions as `RefreshError(source_id, str(exc), timestamp)` and continues the batch | `tests/test_ingest_coordinator_1886.py:621`, `:634`, `:648`, `:661`, `:675`, `:699` verify error contents, timestamp, and batch continuation across fetch and ingest failures | PASS |
| AC8 | `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py:223`, `:233-237` returns filtered-source counts, success counts, successful ingest results, and collected errors | `tests/test_ingest_coordinator_1886.py:727`, `:741`, `:755`, `:779`, `:799`, `:812`, `:826` verify counter semantics, zero-doc exclusion from `ingest_results`, and empty-source behavior | PASS |
- Challenger cross-check (required by `behavioral` proof bundle): proceed, confidence 0.81. No blocking defects found in AC coverage or implementation.
- Blocking findings table: none.

## Observations
- The post-retry evidence packet does not record a full combined rerun of task-local plus durable tests after replacing the stale durable expectation. I treated this as non-blocking because the `behavioral` bundle requires scoped tests + lint + coverage, those were already provided, and the retry changed one durable expectation that was then verified directly.
- `FetchResult.errors` in `serve/knowledge/src/owlbear_knowledge/protocols/fetcher.py` is outside the current AC surface and is not interpreted by `refresh()`. If future requirements want partial fetch failures to affect watermarking or `sources_refreshed`, that contract should be made explicit in a follow-up AC rather than inferred here.

[[2026-05-26T11:06:00+02:00]]
## Docs Gate

**Verdict: PASS — docs gate passed**

### Item 1: README Verification
- Convention mapping: `serve/knowledge/src/**` → `serve/knowledge/README.md`
- Changed file `ingest_coordinator.py` is an **internal module** — not exported from `__init__.py` or documented in the README. No task-caused README drift.
- Layer 1 (grep): No removed symbols, flags, or commands in the README.
- Layer 2 (LLM editorial): README coherent; no contradictions with current behavior.
- Pre-existing issues discovered and marked:
  - `TextChunker` listed in module groups table "Ingestion" row but not in `__init__.__all__` → **TODO: stale** marker added [#1886]
  - `RefreshOrchestrator`, `RefreshResult` in `__init__.__all__` but absent from module groups table → **TODO: missing** marker added [#1886]

### Item 2: External Attribution
N/A — no external sources used; implementation fills planned protocol gap using existing types.

### Item 3: Research Doc
PASS — `.owlbear/research/1886-refresh-implementation.md` exists and is linked from task body.

### Item 4: Deletion Detection
N/A — no source files deleted; no orphaned references.

### Files Updated
- `serve/knowledge/README.md` — added 2 TODO markers for pre-existing stale/missing entries

### Scratch Cleanup
No `1886-*` scratch files present.

[[2026-05-26T11:28:29+02:00]]
## Audit

### Regression Detection
quality-runner env fallback (ImportError in unrelated test_mcp_kanban_newline_norm_1531.py + timeout). Direct run: `serve/knowledge/tests/ + tests/test_ingest_coordinator_1886.py + tests/test_ingest_coordinator_1877.py + tests/test_enrichment_store_1876.py` → 125 passed, 0 failed. Lint on `ingest_coordinator.py`: clean.

### Intent Verification
Changed file: `serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py` (knowledge domain, layer-2 coordinator). Implementation adds optional fetcher DI and refresh() method — matches task purpose exactly. No extraneous scope.

### Architect Quality
Score: 5/5. AC1-AC8 are precise with exact field names, counter semantics, error isolation behavior, enrich propagation rules, and watermark conditions. Challenger engaged (confidence 0.62 → reconsider); architect rewrote all 8 AC lines addressing precision gaps. Exemplary architect work.

### Commit Integrity
**Process concern:** Builder implementation is UNCOMMITTED — `ingest_coordinator.py` modified in working tree only. No `feat:` commit exists for #1886. Research doc `.owlbear/research/1886-refresh-implementation.md` is untracked. Test-writer commits (6a3ade14, 77d048e7) are properly committed. Doc-writer README update also uncommitted.

Per verification workflow: noting as process concern; auditor does not silently commit other agents' source code. The implementation is present, tests pass, reviewer verified — but manual commit intervention is needed to persist the deliverable in version control.

### Deduction Breakdown
| Criterion | Deduction |
|---|---|
| Evidence integrity (uncommitted builder deliverable) | -.05 |
| **Total** | **-.05** |

### Confidence: 0.95
### Action: ARCHIVE (at threshold; process concern noted above requires manual commit)
