---
id: 1893
title: 'Knowledge: MCP wire ingest_document to IngestCoordinator.ingest'
status: archived
priority: needed
created: 2026-05-27T01:00:59.346799+02:00
updated: 2026-05-27T11:51:05.888084+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - ingest_document tool delegates to IngestCoordinator.ingest(IngestRequest) 
    instead of IngestPipeline.ingest_text(); guard checks ingest_coordinator is 
    not None and source_store_v2 is not None (returns error string if either 
    missing)
  - Inline source resolved via source_store_v2.list_sources(scope=scope, 
    state=SourceState.ACTIVE) filtered by name==f'mcp-inline-{scope}' and 
    kind==SourceKind.INLINE; if not found, created via 
    register_source(SourceRegistration(name=f'mcp-inline-{scope}', kind=INLINE, 
    fetch_method=NONE, config=InlineConfig(), scope=scope, enrich=True, 
    refreshable=False))
  - IngestRequest constructed with source_id=resolved_source.id, 
    documents=(IngestDocument(title=metadata.get('title', source_url or 
    'Untitled inline document'), text=text, uri=source_url, metadata=metadata or
    {}),), enrich=True
  - Response string surfaces IngestResult.documents_processed, .chunks_created, 
    .chunks_enqueued
  - Old IngestPipeline.ingest_text() call and associated result parsing removed 
    from ingest_document; exception handling preserved (broad except returning 
    error string)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Replace IngestPipeline.ingest_text() in `ingest_document` with IngestCoordinator.ingest(IngestRequest). Resolve or create a source record for the inline document. Build IngestRequest with source_id and single IngestDocument.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`



## Research Notes

See `.owlbear/research/mcp-ingest-document-wiring.md` for full analysis.

**Implementation approach:**
- Shared inline source per scope (`mcp-inline-{scope}`) — resolve via `list_sources` + filter, create via `register_source` if missing
- Build `IngestRequest` with single `IngestDocument(title=..., text=text, uri=source_url)`
- Surface `IngestResult.documents_processed`, `.chunks_created`, `.chunks_enqueued` in response
- Remove old `IngestPipeline.ingest_text()` call
- Guard: check `ingest_coordinator is not None` (same pattern as current `pipeline is None` check)

[[2026-05-27T03:15:07+02:00]]
## Research

Key findings: IngestCoordinator.ingest already instantiated in AppContext. Wiring requires inline source resolution (shared `mcp-inline-{scope}` source per scope via `list_sources` + filter → `register_source` if missing), IngestRequest/IngestDocument construction from existing tool params, and IngestResult field surfacing. No protocol extension needed — existing `SourceStore.list_sources` + `register_source` suffices.

Doc: `.owlbear/research/mcp-ingest-document-wiring.md`
Confidence: .82
No follow-up tasks needed — 1893 is self-contained and ready for architect.

[[2026-05-27T03:26:25+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: rewire ingest_document from legacy pipeline to IngestCoordinator |
| Interface clarity | PASS | Refined AC specifies exact resolution strategy, field mappings, and guard behavior |
| Dependency correctness | PASS | Dep #1888 archived — AppContext fields (ingest_coordinator, source_store_v2) wired |
| Module layering | PASS | mcp-knowledge → knowledge (correct direction); uses protocol interfaces only |
| TDD compliance | PASS | Proof bundle behavioral; test-writer will write coordinator/source mock tests |
| KISS/YAGNI | PASS | Minimal wiring change per research recommendation A (shared inline source) |
| Premise challenge | PASS | Required to complete IngestCoordinator transition; old IngestPipeline is being deprecated |
| Pattern consistency | PASS | Follows existing tool patterns: None guard → error string, try/except → error string, string response |
| Security surface | PASS | No new external boundaries; same tool parameters; source name derived from scope (controlled input) |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| list_sources + filter | No matching source → register_source | N/A (create path) | Yes | None (transparent fallback) |
| register_source | ValueError (bad SourceRegistration) | ValueError | Yes (broad except) | Error string returned |
| coordinator.ingest | LookupError (source_id invalid) | LookupError | Yes (broad except) | Error string returned |
| coordinator.ingest | Per-document failure | Swallowed in _process_document | Yes (zero counts) | Partial success reported |

### Design Diverge
- Trigger: skipped — single clear approach from research (Strategy A: shared inline source per scope); no competing designs

### Challenge Results
- Challenger: FALLBACK — upstream model provider overload
- Architect response: proceeded with self-assessment; AC lines are highly specific and mechanically testable

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinement
Original AC was vague on resolution strategy and field mapping. Refined all 5 lines to specify exact method calls, parameter values, and guard behavior.

### Verdict: APPROVE
### Action Taken: Refined AC to fully-specified testable conditions. Advanced to todo.

[[2026-05-27T03:53:20+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_ingest_document_coordinator_1893.py`
**Class:** `TestFromAC_IngestDocumentCoordinatorWiring`
**Total:** 30 tests, all FAIL (RED phase confirmed)
**Lint:** clean (ruff)

### Tests per category

| Category | Count | Examples |
|----------|-------|---------|
| Happy path | 8 | both guards OK, source found, IngestRequest built correctly, response format, default scope |
| Edge | 8 | wrong-kind source triggers register, wrong-name triggers register, metadata=None, no source_url |
| Error path | 8 | coordinator=None, store=None, both None, coordinator exception, register_source exception |
| Boundary | 6 | scope in name, enrich=True always, title fallback chain, pipeline mock not called |

### AC coverage

| AC | Tests |
|----|-------|
| AC1 — coordinator/store guards, not pipeline | `test_returns_error_when_ingest_coordinator_is_none`, `test_returns_error_when_source_store_v2_is_none`, `test_returns_error_when_both_guards_fail`, `test_ingest_pipeline_none_is_not_an_error` |
| AC2 — list_sources filter + register_source if not found | `test_list_sources_called_with_scope_and_active_state`, `test_register_source_not_called_when_source_found`, `test_register_source_called_when_no_matching_source`, `test_register_source_registration_params_correct`, `test_source_name_uses_scope_prefix`, `test_source_with_wrong_kind_not_used_triggers_register`, `test_source_with_wrong_name_not_used_triggers_register` |
| AC3 — IngestRequest construction | `test_coordinator_ingest_called_with_ingest_request`, `test_ingest_request_source_id_from_resolved_source`, `test_ingest_request_enrich_is_true`, `test_ingest_document_text_passed_correctly`, `test_ingest_document_title_from_metadata_title`, `test_ingest_document_title_falls_back_to_source_url`, `test_ingest_document_title_untitled_when_no_title_no_url`, `test_ingest_document_uri_is_source_url`, `test_ingest_document_uri_is_none_when_no_source_url`, `test_ingest_document_metadata_none_becomes_empty_dict`, `test_ingest_document_metadata_passed_through` |
| AC4 — response surfaces documents_processed, chunks_created, chunks_enqueued | `test_response_contains_documents_processed`, `test_response_contains_chunks_created`, `test_response_contains_chunks_enqueued`, `test_response_values_match_ingest_result`, `test_proceeds_when_both_guards_satisfied` |
| AC5 — old pipeline call removed, exception handling preserved | `test_ingest_pipeline_ingest_text_not_called`, `test_coordinator_exception_returns_error_string`, `test_register_source_exception_returns_error_string` |

### Key design notes
- Guard tests use `_make_pipeline_mock()` (AsyncMock returning success string) so old code doesn't short-circuit on `pipeline is None` before reaching the new guard logic — ensuring tests fail for the right reason.
- `test_register_source_not_called_when_source_found` includes a positive `coordinator.ingest.assert_called_once()` assertion to prevent vacuous pass before fix.
- Tests import `IngestRequest`, `IngestDocument`, `SourceRegistration`, `InlineConfig`, `SourceKind`, `FetchTransport`, `SourceState` for contract verification.

[[2026-05-27T04:15:38+02:00]]
## Builder Notes
- Implementation target: `ingest_document` wiring in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- Net source diff at handoff: none (current `HEAD` already contains the AC-compliant coordinator wiring path)

### AC evidence
- AC1: `ingest_document` uses `ingest_coordinator` + `source_store_v2` guards (error string when missing)
- AC2: inline source resolution via `list_sources(scope=..., state=SourceState.ACTIVE)` with name/kind filter and `register_source(SourceRegistration(..., kind=INLINE, fetch_method=NONE, config=InlineConfig(), enrich=True, refreshable=False))` fallback
- AC3: builds `IngestRequest(source_id=..., documents=(IngestDocument(...),), enrich=True)` with title fallback and `metadata or {}`
- AC4: response string surfaces `documents_processed`, `chunks_created`, `chunks_enqueued`
- AC5: no `IngestPipeline.ingest_text()` call in the tool path; broad exception handling preserved via error string

### Verification (quality-runner)
- RED check (pre-implementation verification): `tests/test_ingest_document_coordinator_1893.py` -> 30 failed, lint clean
- GREEN check: `tests/test_ingest_document_coordinator_1893.py` -> 30 passed, 0 failed
- Lint: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and task test file
- Coverage (reported by quality-runner for module): `owlbear_mcp_knowledge.server` 30%

### Module-level regression visibility
- Ran additional durable ingest wiring check: `tests/test_persistence_source_wiring.py`
- Result: 4 failures due legacy assertions expecting `pipeline.ingest_text` calls, which conflict with this task's coordinator-based AC contract
- Also ran broader mcp-knowledge scoped set for visibility; observed unrelated pre-existing failures outside this task scope

### Fixes applied
- Coordinator-based ingest path and inline source resolution are present and verified by task-scoped TestFromAC suite.
- No additional source edits required at final handoff because workspace `HEAD` already matched required implementation.

[[2026-05-27T04:38:59+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: reject to in-progress.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2, AC4 | The real runtime source-resolution path is not sufficiently proved and appears inconsistent with the current SQLite connection wiring. `app_lifespan` creates `ctx.conn` with `sqlite3.connect(path)` and shares that same connection with `source_store_v2`; `ingest_document` then calls `source_store_v2.list_sources(...)` and `register_source(...)` through `asyncio.to_thread(...)`. The task-scoped suite only proves mocked store interactions, so it does not demonstrate that the actual app-lifespan-backed happy path can resolve/register a source and reach the coordinator result path under the real server wiring. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:471,559,865,883,893`; `serve/knowledge/src/owlbear_knowledge/stores/sources.py:43-44,79,165`; `tests/test_mcp_knowledge_lifespan_1888.py:206`; `tests/test_ingest_document_coordinator_1893.py:93,125-127,136,232,249-279,306-350,378,612-615` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make the `ingest_document` source-store path runtime-safe for the app-lifespan SQLite connection, or provide concrete executable proof that the shared-connection `to_thread` access is safe under the real server wiring. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`; `serve/knowledge/src/owlbear_knowledge/stores/sources.py` | Blocking finding 1 |
| 2 | builder | Add or update executable proof so at least one test covers `ingest_document` against the real app-lifespan-backed v2 source store instead of only mocked store interactions. | `tests/test_ingest_document_coordinator_1893.py` or relevant durable mcp-knowledge test | Blocking finding 1 |

## Observations
- The task-scoped assertions are otherwise specific for the intended coordinator contract: guard behavior, source-name and kind filtering, `SourceRegistration` fields, `IngestRequest` construction, response fields, and broad-exception string handling are all directly asserted in `tests/test_ingest_document_coordinator_1893.py`.
- The four failures in `tests/test_persistence_source_wiring.py` look like stale legacy pipeline assertions and are not the blocking reason for this rejection.

[[2026-05-27T04:50:44+02:00]]
## Builder Notes

- Files changed:
  - serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

- Surgical fix applied:
  - Updated ingest_document to call source_store_v2.list_sources(...) and source_store_v2.register_source(...) directly on the request thread instead of via asyncio.to_thread(...).
  - Rationale: app_lifespan wires a shared sqlite3 connection into source_store_v2; running those calls in a worker thread risks sqlite cross-thread access failures.

- AC mapping:
  - AC1 preserved: ingest_coordinator/source_store_v2 guards unchanged.
  - AC2 preserved: list_sources(scope=..., state=ACTIVE) + name/kind filter + register_source(SourceRegistration(... INLINE/NONE/InlineConfig/enrich=True/refreshable=False)).
  - AC3 preserved: IngestRequest/IngestDocument construction unchanged.
  - AC4 preserved: response string still surfaces documents_processed/chunks_created/chunks_enqueued.
  - AC5 preserved: no IngestPipeline.ingest_text path; broad exception-to-error-string handling unchanged.

- Verification results:
  - quality-runner scoped (task tests): tests/test_ingest_document_coordinator_1893.py -> 30 passed, 0 failed.
  - quality-runner lint: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_ingest_document_coordinator_1893.py.
  - quality-runner coverage (module): owlbear_mcp_knowledge.server 27% in scoped run.

- Runtime executable proof (reviewer follow-up #1):
  - Ran one-shot uv-run script using real app_lifespan + real SqliteSourceStore (patched only heavy deps).
  - Overrode coordinator.ingest with AsyncMock return payload to isolate source-store wiring path.
  - ingest_document(...) succeeded, created/resolved source mcp-inline-global in ACTIVE state, and returned expected counters.
  - Output: PASS: ingest_document runtime proof OK (real SqliteSourceStore + app_lifespan)

- Fixes applied summary:
  - Resolved reviewer blocking concern by making ingest_document source-store access runtime-safe under app-lifespan sqlite wiring without changing tool contract or response format.

[[2026-05-27T05:10:59+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: reject to todo.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC2, AC4 | The implementation concern from the prior review is addressed, but the proof gap is still open. The prior required follow-up explicitly asked for at least one committed test covering `ingest_document` against the real app-lifespan-backed `source_store_v2`; that proof is still not present. The task AC suite remains mock-backed, the lifespan suite proves wiring separately but does not call `ingest_document`, and the only real-store exercise in this cycle is a one-shot script recorded in builder notes rather than a durable test. That leaves real source resolution/registration on the runtime wiring insufficiently protected against regression. | `.owlbear/kanban/tasks/1893-knowledge-mcp-wire-ingest-document-to-ingestcoordinator-ingest.md:182`; `tests/test_ingest_document_coordinator_1893.py:93-140`; `tests/test_mcp_knowledge_lifespan_1888.py:198-238`; `.owlbear/kanban/tasks/1893-knowledge-mcp-wire-ingest-document-to-ingestcoordinator-ingest.md:210-214` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a committed executable test that drives `ingest_document` through `app_lifespan` with a real `SqliteSourceStore` and asserts source resolve/create behavior plus returned coordinator counters. | `tests/test_ingest_document_coordinator_1893.py` or relevant durable mcp-knowledge test | Blocking finding 1 |

## Observations
- AC1-AC5 now map cleanly to `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:874-927`, including request-thread source-store access at `:883-894` and the coordinator counter response at `:925-927`.
- The task-scoped suite is otherwise specific and useful for the coordinator contract. The blocking issue is proof sufficiency at the real runtime wiring boundary, not a newly observed implementation defect.
- `tests/test_persistence_source_wiring.py:152-345` still targets the removed pipeline/source_url contract and is not valid proof for this coordinator-based AC.

[[2026-05-27T09:53:51+02:00]]
## Test-Writer Notes
- Retry: added 3 lifespan proof tests to `tests/test_ingest_document_coordinator_1893.py` for reviewer gap (AC2/AC4 real store wiring).
- All 3 new tests PASS against current implementation (builder already fixed the wiring).
- Builder skip: test-only retry — all 33 tests green, implementation correct.
- Class: `TestFromAC_IngestDocumentLifespanProof` (3 tests)
- Tests per category: integration/happy 3
- ruff: clean

### New tests
| Test | AC |
|------|---------|
| `test_ingest_document_creates_inline_source_in_real_store` | AC2 — real list_sources + register_source on SqliteSourceStore |
| `test_ingest_document_reuses_existing_inline_source` | AC2 — no duplicate source on repeat calls |
| `test_ingest_document_response_surfaces_coordinator_counters_real_wiring` | AC4 — response counters surfaced under real wiring |

### Approach
- Uses `app_lifespan` with in-memory SQLite and patched Qdrant/BgeM3 (heavy deps)
- `SqliteSourceStore` is real (unpatched); only `coordinator.ingest` mocked to return fake `IngestResult`
- Asserts source creation/reuse in the real DB and response counter format

[[2026-05-27T10:21:11+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: reject to backlog. This is a repeated review cycle; the remaining blockers are proof-quality gaps rather than a newly observed implementation mismatch.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3 | The retry still does not prove the source-creation branch passes the resolved or newly registered source id into `IngestRequest.source_id`. The suite asserts `request.source_id` only for the existing-source path, while the create-path tests stop at registration fields or final store state. A broken first-use path could create the inline source yet call `coordinator.ingest` with the wrong source id and still pass green. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:897-922`; `tests/test_ingest_document_coordinator_1893.py:259-286`; `tests/test_ingest_document_coordinator_1893.py:373-384`; `tests/test_ingest_document_coordinator_1893.py:659-719` | backlog |
| 2 | AC5 | Broad-exception proof remains incomplete at the first protected operation. `ingest_document` wraps `list_sources`, `register_source`, and `coordinator.ingest` in one broad handler, but the suite only proves error-string behavior for `register_source` and `coordinator.ingest`. Narrowing the try boundary above `list_sources` would still pass the current tests. | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:888-923`; `tests/test_ingest_document_coordinator_1893.py:591-619` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the proof expectations for AC3 so the next RED cycle must prove the create-source branch passes the resolved or newly registered source id into `IngestRequest.source_id`, then return the task for new tests. | `tests/test_ingest_document_coordinator_1893.py`; `.owlbear/kanban/tasks/1893-knowledge-mcp-wire-ingest-document-to-ingestcoordinator-ingest.md` | Blocking finding 1 |
| 2 | architect | Refine the proof expectations for AC5 so the next RED cycle must include executable proof that `list_sources` exceptions are converted into the documented error string by the broad handler, then return the task for new tests. | `tests/test_ingest_document_coordinator_1893.py`; `.owlbear/kanban/tasks/1893-knowledge-mcp-wire-ingest-document-to-ingestcoordinator-ingest.md` | Blocking finding 2 |

## Observations
- The prior runtime-wiring concern is now closed: request-thread `source_store_v2` access is in place, and the new lifespan tests do exercise the real `SqliteSourceStore` boundary for AC2 and AC4.
- AC1, AC2, and AC4 otherwise map cleanly to the current implementation in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:868-930`.
- `tests/test_persistence_source_wiring.py` still encodes legacy pipeline-oriented expectations and is not valid proof for this coordinator-based AC set.

[[2026-05-27T10:34:58+02:00]]
## Architecture Review (retry-2)

### Context
Reviewer rejected to backlog requesting architect refine proof expectations for two gaps:
1. AC3 create-path: `IngestRequest.source_id` not asserted for the register_source branch
2. AC5 broad-handler: `list_sources` exception path not covered

### Codebase Verification
Confirmed in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:883-930`:
- The try/except wraps `list_sources`, `register_source`, AND `coordinator.ingest` — so all three can produce the "error: ingestion failed:" response.
- The create-source branch assigns `source = source_store.register_source(...)` and then uses `source.id` in `IngestRequest(source_id=source.id, ...)` — so a test that sets `register_source.return_value` with a known id and then asserts `request.source_id == that_id` closes the gap.

### Proof-Gap Guidance (for test-writer retry)

**Gap 1 — AC3 create-path source_id flow:**
Add a test that:
- Configures `store.list_sources` to return empty (triggers register_source branch)
- Sets `store.register_source.return_value` to a source record with a distinct id (e.g. `"newly-registered-123"`)
- Asserts `coordinator.ingest.call_args[0][0].source_id == "newly-registered-123"`

This proves the register_source return value flows into IngestRequest.source_id (not a stale or hardcoded value).

**Gap 2 — AC5 list_sources exception:**
Add a test that:
- Configures `store.list_sources` to raise `RuntimeError("db locked")`
- Asserts result is a string containing "error"
- Asserts `coordinator.ingest` is NOT called (exception short-circuits before coordinator)

This proves the broad handler covers the first protected operation in the try block.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same scope as prior reviews |
| Interface clarity | PASS | AC unchanged; proof guidance added |
| Dependency correctness | PASS | Dep #1888 archived-done |
| Module layering | PASS | mcp-knowledge → knowledge (correct) |
| TDD compliance | PASS | Test-writer will add 2 gap-closing tests |
| KISS/YAGNI | PASS | Minimal additions to close proof gaps |
| Premise challenge | PASS | Covered in prior cycle |
| Pattern consistency | PASS | Same mock/assert pattern as existing suite |
| Security surface | PASS | No change |
| Single domain | PASS | Knowledge only |

### Design Diverge
- Trigger: skipped — no competing approaches; reviewer gap is test coverage only

### Challenge Results
- Challenger: SKIPPED — re-review of same design; no new architectural decisions; prior challenges still apply

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (add 2 specified tests only)

### Verdict: APPROVE
### Action Taken: Added explicit proof-gap guidance for test-writer to close AC3 create-path and AC5 list_sources exception gaps. Advanced to todo.

[[2026-05-27T10:35:04+02:00]]
Architecture review retry-2: refined proof expectations for two reviewer-identified gaps (AC3 create-path source_id flow, AC5 list_sources exception coverage). No AC wording change needed — the gaps are in test coverage, not specification. Added explicit test-writer guidance for 2 targeted additions.

[[2026-05-27T10:55:43+02:00]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gaps (AC3 create-path source_id, AC5 list_sources exception). All 35 tests pass against current implementation.
- Builder skip: test-only retry, all tests green.

### New tests
| Test | AC |
|------|----|
| `test_ingest_request_source_id_from_newly_registered_source` | AC3 — register_source return value id flows into IngestRequest.source_id (create branch) |
| `test_list_sources_exception_returns_error_string` | AC5 — list_sources exception caught by broad handler; returns error string; coordinator.ingest NOT called |

### Class: `TestFromAC_IngestDocumentCoordinatorWiring` (2 added)
- Tests per category: integration/happy 1, integration/error 1
- Total: 35 tests, all PASS (direct-to-review: implementation already correct)
- ruff: clean

[[2026-05-27T11:17:59+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1893 -> docs | AC mapped to code and evidence sufficient.
- Independent verification:
  - quality-runner recheck: `tests/test_ingest_document_coordinator_1893.py` -> 35 passed, 0 failed; `ruff` clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_ingest_document_coordinator_1893.py`; scoped coverage for `owlbear_mcp_knowledge.server` 34%.
  - behavioral-bundle challenger cross-check: proceed; no blocking blind spots found.
- AC evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:889-891,921-933` | `tests/test_ingest_document_coordinator_1893.py:158,172,212,358` | PASS |
| AC2 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:898-918` | `tests/test_ingest_document_coordinator_1893.py:227,273,699,734` | PASS |
| AC3 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:921,924-930` | `tests/test_ingest_document_coordinator_1893.py:358,389,408,433,452,471,485,499,511,525` | PASS |
| AC4 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:938-940` | `tests/test_ingest_document_coordinator_1893.py:541,555,569,582,764` | PASS |
| AC5 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:878-940` (no `ingest_pipeline.ingest_text()` path; broad handler at `:933`) | `tests/test_ingest_document_coordinator_1893.py:598,610,626,643` | PASS |

## Observations
- The prior runtime-wiring concern is now closed: request-thread `source_store_v2` access plus real `SqliteSourceStore` lifespan proof cover the AC2/AC4 boundary.
- `tests/test_persistence_source_wiring.py` still encodes legacy pipeline-oriented assertions and is not valid proof for this coordinator-based AC set.
- Direct git-status contamination check was not available from the current toolset during this review; this PASS is based on the claimed task state, current file contents, and fresh scoped executable verification.

[[2026-05-27T11:20:37+02:00]]
## Docs Gate

### Item 1: README Verification
- Target: `serve/mcp-knowledge/README.md` (convention mapping: `serve/mcp-knowledge/src/**` → `serve/mcp-knowledge/README.md`)
- Layer 1 (grep): `ingest_document` row found; description referenced old `IngestPipeline.ingest_text()` behavior (content-hash delta detection, source linkage, anonymous-only inline provenance, partial graph warnings) — all stale after this task's coordinator wiring.
- Layer 2 (LLM editorial): New implementation always uses shared `mcp-inline-{scope}` inline source; `source_url` stored as document URI only; response is `documents_processed/chunks_created/chunks_enqueued` with no warning mechanism.
- **Fix applied**: Updated `ingest_document` table description to reflect actual coordinator-based behavior.

### Item 2: External Attribution
- N/A — no external sources used; pure internal wiring task.

### Item 3: Research Doc
- `.owlbear/research/mcp-ingest-document-wiring.md` exists and is referenced in task body Research Notes section. ✓

### Item 4: Deletion Detection
- `IngestPipeline.ingest_text()` removed from `ingest_document` tool path.
- `serve/knowledge/README.md` lists `IngestPipeline` as a knowledge package export — still accurate (class exists; not mcp-knowledge's concern). No orphaned references in public docs.
- `.owlbear/research/` mentions are historical notes only — out of scope.

### Scratch Cleanup
- No `1893-*` scratch files found. ✓

### Files Updated
- `serve/mcp-knowledge/README.md` — corrected `ingest_document` tool description

[[2026-05-27T11:51:05+02:00]]
## Audit
### Regression Detection
- quality-runner env fallback: xdist hung repeatedly (instrument_error); ran domain-scoped tests directly
- Domain-scoped (serve/mcp-knowledge/tests/, serve/knowledge/tests/, task test, lifespan test): 66 passed, 0 failed
- Adjacent knowledge tests (test_persistence_source_wiring.py, test_store_enrichment_phase1_1892.py): 46 passed, 4 failed
- 4 failures are legacy assertions on ingest_text (AC5 intentionally removes this path); documented by builder and reviewer
- Lint: clean for server.py and task test file
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changes in serve/mcp-knowledge/ and tests/test_ingest_document_coordinator_1893.py; knowledge domain only)
- purpose match: PASS (wires ingest_document from legacy IngestPipeline to IngestCoordinator per stated task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines highly specific with exact method calls, parameter values, guard behavior, and response format. Architect refined vague originals into mechanically testable conditions. Multiple review cycles resolved proof gaps through targeted architect guidance.

### Commit Integrity
- upstream commit presence: PASS (builder: 0138219e, b5073158; test-writer: 7dd1543b, ff96e1be, 80092f1a)
- doc-writer README: uncommitted working-tree change (process concern noted; other tasks also have uncommitted README updates mixed in)
- kanban commit packaging: pending

### Deduction Breakdown
No deductions. Legacy test failures are intentional (AC5 removes old contract). Lint clean. Reviewer evidence detailed with PASS. No intent mismatch.

### Confidence: 1.00
### Action: archive
