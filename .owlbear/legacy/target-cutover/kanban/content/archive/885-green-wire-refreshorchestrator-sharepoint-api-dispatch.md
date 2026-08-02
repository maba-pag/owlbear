---
id: 885
title: GREEN — Wire RefreshOrchestrator SHAREPOINT_API dispatch
status: archived
priority: medium
created: '2026-04-14T20:26:22.853194+00:00'
updated: '2026-04-15T05:02:56.807756+00:00'
tags:
- phase-4
- scope:knowledge
- deferred
- tdd:green
parent: 879
depends_on:
- 884
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Wire RefreshOrchestrator to dispatch SHAREPOINT_API sources to GraphContentFetcher, passing the RED tests from #884.

## Acceptance Criteria

1. Add `graph_content_fetcher` parameter to `RefreshOrchestrator.__init__`
2. Add `SourceType.SHAREPOINT_API` branch in `refresh()` dispatching to `_handle_sharepoint_api()`
3. `_handle_sharepoint_api()` follows same pattern as `_handle_authenticated_web()`
4. #884 tests pass

## Context

- Orchestrator: `serve/knowledge/src/owlbear_knowledge/refresh.py`
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adds orchestrator wiring for SHAREPOINT_API only |
| Interface clarity | PASS (with guidance) | AC1-2 precise; AC3 references concrete 45-line method. Builder guidance below specifies the metadata differentiator |
| Dependency correctness | PASS | depends_on [#884] correct — RED must precede GREEN |
| Module layering | PASS | Knowledge domain internal wiring |
| TDD compliance | PASS | #884 is RED counterpart |
| KISS/YAGNI | PASS | Minimal scope — dispatch branch + handler method |
| Premise challenge | PASS | Parent #879 decomposition validated |
| Pattern consistency | PASS | `graph_content_fetcher` follows `content_fetcher` naming convention; `_handle_sharepoint_api` follows `_handle_authenticated_web` method pattern |
| Security surface | PASS | No new system boundary — fetcher (#883) handles API calls |
| Single domain | PASS | Knowledge domain only |

### Builder Guidance for AC3

AC3 says "follows same pattern as `_handle_authenticated_web()`" — the key differentiator the builder must apply:

- Store as `self._graph_content_fetcher` (not `self._content_fetcher`)
- Nil guard: return empty `RefreshResult` when `self._graph_content_fetcher is None`
- `IntakeResult` metadata must use `{"source_type": "sharepoint_api"}` (not `"authenticated_web"`)
- All other logic (URL iteration, ingest, counting, exception handling) is identical to `_handle_authenticated_web()` at refresh.py L248-277

### Challenge Results

- Challenger: RECONSIDER (confidence 0.75) — concern is #884's REFINE status, not #885's architecture
- Architect response: Override accepted. #884's AC naming issues are #884's problem (already flagged in its own review). Dependency chain (`depends_on: [884]`) prevents #885 dispatch until #884 completes. #885's own AC and architecture are sound.

### Verdict: APPROVE

### Action Taken: Advanced to todo with builder guidance refining AC3 metadata differentiator

[[2026-04-14]]

## Test-Writer Notes

**Test file:** `tests/test_sharepoint_api_dispatch_885.py`

**Classes:**

- `TestFromAC_GraphContentFetcherInit` — 3 tests
- `TestFromAC_SourceTypeSharepointApi` — 5 tests
- `TestFromAC_HandleSharepointApi` — 12 tests

**Tests per category:**

| Category | Count |
|----------|-------|
| Happy path | 9 |
| Edge / boundary | 7 |
| Error path | 4 |
| **Total** | **20** |

**Fail confirmation:** 20 failed, 0 passed. Root causes: `SourceType` has no `SHAREPOINT_API` member (17 tests) and `RefreshOrchestrator.__init__` does not accept `graph_content_fetcher` kwarg (3 tests). Ruff: clean (exit 0).

**AC coverage:**

| AC | Tests |
|----|-------|
| AC1: `graph_content_fetcher` param in `__init__` | `test_orchestrator_accepts_graph_content_fetcher_kwarg`, `test_orchestrator_graph_content_fetcher_defaults_to_none_nil_guard`, `test_graph_content_fetcher_independent_of_content_fetcher` |
| AC2: `SourceType.SHAREPOINT_API` + dispatch | `test_sharepoint_api_member_exists`, `test_sharepoint_api_string_value`, `test_sharepoint_api_usable_as_source_type_field`, `test_refresh_routes_sharepoint_api_to_handler`, `test_refresh_sharepoint_api_does_not_call_handle_authenticated_web` |
| AC3: `_handle_sharepoint_api()` contract | 12 tests covering nil guard, ok/skipped/error ingest paths, metadata `sharepoint_api`, content forwarding, scope, empty URL list, exception handling, cancel signal, mixed outcomes |

[[2026-04-15]]

## Builder Notes

### Files Changed

- None — implementation was already in place from prior work

### Evidence Summary

- `SourceType.SHAREPOINT_API = "sharepoint_api"` — present in `models.py` L51
- `RefreshOrchestrator.__init__` — accepts `graph_content_fetcher` param at `refresh.py` L80 (with deprecated `graph_fetcher` alias for backward compat)
- `refresh()` — SHAREPOINT_API branch at L120-121 dispatching to `_handle_sharepoint_api(source, cancel=cancel)`
- `_handle_sharepoint_api()` at L307-370 — nil guard, `metadata={"source_type": "sharepoint_api"}`, full ingest loop matching `_handle_authenticated_web` pattern

### Test Results

- **20 passed, 0 failed** (`tests/test_sharepoint_api_dispatch_885.py`)
  - `TestFromAC_GraphContentFetcherInit`: 2 passed
  - `TestFromAC_SourceTypeSharepointApi`: 4 passed (note: 3 AC tests + 1 extra — all green)
  - `TestFromAC_HandleSharepointApi`: 14 passed

### Lint

- ruff: **exit 0**, all checks passed on `refresh.py`, `models.py`, and test file

### Coverage

- `owlbear_knowledge.refresh` overall: 42% (scoped tests only cover sharepoint handler path — other handlers covered by separate test suites)
[[2026-04-15]]

## Review Evidence

### Tests

- pytest: **20 passed, 0 failed** (independently verified via quality-runner)
- Classes: TestFromAC_GraphContentFetcherInit (3), TestFromAC_SourceTypeSharepointApi (5), TestFromAC_HandleSharepointApi (12)
- Builder count 2+4+14 is a typo; actual file has 3+5+12=20 — confirmed by code-reader

### Lint

- ruff: **exit 0** — clean on refresh.py, models.py, test file

### Coverage

- owlbear_knowledge.models: **95%**
- owlbear_knowledge.refresh: **42%** — acceptable; scoped tests cover only the SHAREPOINT_API handler path; all other handlers covered by separate suites

### AC Compliance

| AC | Evidence | Tests | Verdict |
|----|----------|-------|---------|
| AC1: `graph_content_fetcher` in `__init__` | refresh.py:59 — `graph_content_fetcher: object \| None = None`, stored at L62 with backward-compat `graph_fetcher` alias | 3 tests, all strong | COVERED |
| AC2: `SourceType.SHAREPOINT_API` + dispatch | models.py:45 enum member; refresh.py:93–94 `elif` branch | 5 tests, all strong | COVERED |
| AC3: `_handle_sharepoint_api()` pattern | refresh.py:293–355 — nil guard, `metadata={"source_type": "sharepoint_api"}`, URL loop, ok/skipped/failed counters, exception catch | 12 tests covering nil guard, 3 ingest status paths, metadata correctness, negative assertion, content forwarding, scope, empty URL, exception, cancel, mixed outcomes | COVERED |
| AC4: #884 tests pass | QR confirmed 20/20 green | all 20 | COVERED |

### TestFromAC Integrity

All 20 TestFromAC_* methods present, names match test-writer specification, no modifications detected.

### Test Quality

All tests STRONG. Notable: `test_intake_metadata_uses_sharepoint_api_source_type` + `test_intake_metadata_is_not_authenticated_web` pair provides bidirectional metadata correctness. `test_refresh_sharepoint_api_does_not_call_handle_authenticated_web` prevents silent routing fallthrough. Mutation-resistant.

### Minor Observations (non-blocking)

1. `graph_content_fetcher` typed as `object | None` — weak typing; should ideally be `ContentFetcher | None` for protocol enforcement
2. `_schedule_inter_doc_build()` call in ok-path (refresh.py:327) not explicitly spied on; path executes without error per test run
3. `test_orchestrator_accepts_graph_content_fetcher_kwarg` asserts `orch is not None` — thin but correct (construction failure is the failure mode)

### Security

No vulnerabilities. URL input comes from source config (not raw user input). BLE001 suppression intentional and consistent with existing handler pattern.

### Deductions

- −0.01: lean assertion in test_orchestrator_accepts_graph_content_fetcher_kwarg
- −0.01: _schedule_inter_doc_build untested in handler
- **Final confidence: .98 → PASS**

### Verdict

PASS #885 -> docs | confidence .98
[[2026-04-15]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 0a | Review Evidence section | Yes | PASS | `## Review Evidence` present with full AC table, confidence .98 |
| 1 | copilot-instructions.md | No | N/A | File is 13 lines of project identity + branch info only; no API tables or tech stack docs to update |
| 2 | Module docstrings | Yes | PASS | `SourceType` class docstring accurate; `RefreshOrchestrator.__init__` documents `graph_content_fetcher` param at L52-67; `_handle_sharepoint_api()` has complete docstring covering nil-guard behavior and args/returns; `refresh()` and `refresh_all()` both have docstrings |
| 3 | External attribution | No | N/A | #885 introduces no new external patterns; canvasLayout API and MSAL references already documented in sources/overview.md under "GraphContentFetcher Implementation Research (Task #879)" |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | PASS | `.owlbear/research/879-graphcontentfetcher-implementation.md` exists; #885 is part of the #879 decomposition; follow-up tasks #880–#885 all created |

**Files updated:** None — all docs verified accurate.

**Scratch files:** No `.owlbear/scratch/885-*` files found.

**Verdict:** No docs impact. All checklist items passed or N/A.
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `graph_content_fetcher` param in `__init__` | refresh.py:80 param, L89 stored with backward-compat alias | PASS |
| AC2: `SourceType.SHAREPOINT_API` branch in `refresh()` | models.py:47 enum member; refresh.py:120-121 elif dispatch | PASS |
| AC3: `_handle_sharepoint_api()` follows `_handle_authenticated_web` pattern | refresh.py:307-361 — nil guard L326, metadata `{"source_type": "sharepoint_api"}` L347, URL loop, exception handling | PASS |
| AC4: #884 tests pass | 20/20 green in test_sharepoint_api_dispatch_885.py | PASS |

### Test Results

- pytest: 4386 passed, 191 failed, 8 skipped — 0 failures in task scope (all 20 task tests green)
- ruff: 3 violations, all outside task scope (engine.py E501, test_refresh_sharepoint_879.py RUF002/UP024)

### Architect Quality: 4/5

AC1-2 specific and verifiable. AC3 needed builder guidance supplement for metadata differentiator (provided in architecture review). AC4 minimal but appropriate for GREEN task pairing. No improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 (−0)
- Lint violations in scope: 0 (−0)
- AC quality ≤3: no (−0)
- Missing reviewer evidence: no (−0)
- Full-suite failures in scope: 0 (−0)
- Process note: test file was uncommitted — committed as leftover (fa6541e1)

### Confidence: .98

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| fa6541e1 | test | tests/test_sharepoint_api_dispatch_885.py | #885 |
