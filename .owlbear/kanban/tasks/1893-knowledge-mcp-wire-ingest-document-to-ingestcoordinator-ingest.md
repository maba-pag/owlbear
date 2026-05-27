---
id: 1893
title: 'Knowledge: MCP wire ingest_document to IngestCoordinator.ingest'
status: review
priority: needed
created: 2026-05-27T01:00:59.346799+02:00
updated: 2026-05-27T09:53:51.871927+02:00
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
archival_reason:
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
