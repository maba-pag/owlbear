---
id: 737
title: Expose refresh_source as MCP tool in mcp-knowledge
status: archived
priority: medium
created: '2026-04-10T04:24:32.3432406+02:00'
updated: '2026-04-10T05:31:44.138886+00:00'
tags:
- knowledge
- mcp
- v1-port
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
class: standard
---

## Objective

Expose the existing RefreshOrchestrator as an MCP tool so agents can trigger re-ingestion of registered knowledge sources.

## Context

v1 had `refresh_source` as a CLI command and agent tool. v2 has `RefreshOrchestrator` in `serve/knowledge/` but it's not exposed via the mcp-knowledge server. Agents currently cannot trigger source refresh.

## Acceptance Criteria

- [ ] New `refresh_source` MCP tool in mcp-knowledge server
- [ ] Tool accepts source_id or source_name parameter
- [ ] Tool calls existing RefreshOrchestrator.refresh() for the specified source
- [ ] Returns refresh result (refreshed/skipped/failed counts)
- [ ] Existing tests pass; new test verifies MCP tool wiring

[[2026-04-10]] Fri 05:03

## Architecture Review

### Refined Acceptance Criteria

Original AC was directionally correct but underspecified. Refined:

- [ ] Add `refresh_orchestrator: RefreshOrchestrator | None` field to `AppContext` in `server.py`
- [ ] Construct `RefreshOrchestrator(store=source_store, pipeline=pipeline, workspace_root=Path.cwd())` in `app_lifespan` and assign to `AppContext`
- [ ] New `refresh_source` MCP tool registered on `mcp` with `ToolAnnotations(readOnlyHint=False, destructiveHint=False)`
- [ ] Tool accepts `source_id: str` parameter (required); name-based lookup deferred (no `get_by_name` exists on `KnowledgeSourceStore`)
- [ ] Tool resolves source via `source_store.get(source_id)`; raises `ToolError` if source not found
- [ ] Tool handles disabled sources: if `source.enabled is False`, return meaningful error string (do not let `ValueError` propagate)
- [ ] Tool calls `await refresh_orchestrator.refresh(source)` directly (async method — no `asyncio.to_thread`)
- [ ] Returns dict with `source_id`, `refreshed`, `skipped`, `failed` counts from `RefreshResult`
- [ ] Add `refresh_source` to the `__all__` list in `server.py`
- [ ] Existing tests pass; new test verifies MCP tool wiring (mock store returns `KnowledgeSource`, mock pipeline, assert tool returns expected counts)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One tool: expose refresh via MCP |
| Interface clarity | PASS (after refinement) | Specified: source_id param, ToolError on not-found, disabled handling, return shape |
| Dependency correctness | PASS | No `depends_on` needed — `RefreshOrchestrator`, `KnowledgeSourceStore`, `IngestPipeline` all exist |
| Module layering | PASS | mcp-knowledge → owlbear_knowledge is the correct import direction |
| TDD compliance | PASS | AC specifies new test for wiring |
| KISS/YAGNI | PASS (after refinement) | Dropped `source_name` param — no `get_by_name` exists, agents use `list_sources` to discover IDs |
| Premise challenge | PASS | Legitimate gap — agents cannot trigger source refresh; `RefreshOrchestrator` exists unused from MCP |
| Pattern consistency | PASS (after refinement) | Follows existing tool pattern: AppContext field → lifespan init → ctx accessor → error on unavailable. `refresh()` is async so no `asyncio.to_thread` (unlike sync store methods) |
| Security surface | PASS | source_id maps to internal store lookup; no new external input surface |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `source_store.get(source_id)` | Source not found | None (returns `None`) | AC: ToolError | Agent sees clear error |
| `refresh(source)` | Source disabled | `ValueError` | AC: catch and return error string | Agent sees "source disabled" |
| `refresh(source)` | Ingestion errors | Captured in `RefreshResult.errors` | Yes (by design) | Failed count > 0, errors list populated |
| `refresh_orchestrator is None` | Service unavailable | N/A | AC: follows existing pattern | Agent sees "not available" |

### Key Files

- `serve/knowledge/src/owlbear_knowledge/refresh.py` — RefreshOrchestrator, RefreshResult
- `serve/knowledge/src/owlbear_knowledge/source_store.py` — KnowledgeSourceStore.get()
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — AppContext, app_lifespan, tool registrations

### Challenge Results

- Challenger: FALLBACK — challenger agent not available in tool allowlist
- Architect response: proceeded with analysis; high confidence (.92) based on clear codebase evidence

### Verdict: APPROVE (with AC refinement)

### Action Taken: Refined AC to specify exact infrastructure changes (AppContext field, lifespan construction), simplified to source_id-only (KISS), added error case specifications, and noted async pattern. Advanced to todo

[[2026-04-10]] Fri 05:16

## Test-Writer Notes

**Test file:** `tests/test_refresh_source_mcp_tool_737.py`
**Class:** `TestFromAC_RefreshSourceMcpTool`

### Tests per category

| Category | Tests |
|----------|-------|
| Structural/contract | 4 (importable, `__all__`, async, `source_id` param, `AppContext` field) |
| Happy path | 5 (store.get called, orchestrator.refresh called, result has source_id/refreshed/skipped/failed) |
| Error path | 3 (source not found → ToolError, source_store None → ToolError, orchestrator None → error string) |
| Edge/boundary | 2 (disabled source → error string, error string mentions source) |
| **Total** | **14 tests, all FAIL** |

### Verification

All 14 tests fail at collection with `ImportError: cannot import name 'refresh_source' from 'owlbear_mcp_knowledge.server'` — expected RED-phase behavior. `ruff check` passes clean.

### AC coverage

| AC | Tests |
|----|-------|
| refresh_source tool exists | test_refresh_source_is_importable, test_refresh_source_in_all |
| AppContext.refresh_orchestrator field | test_app_context_has_refresh_orchestrator_field |
| ToolAnnotations(readOnlyHint=False, destructiveHint=False) | test_refresh_source_is_async (structural; exact annotation verified by builder) |
| source_id parameter required | test_refresh_source_accepts_source_id_parameter |
| source_store.get(source_id) lookup | test_calls_store_get_with_source_id |
| ToolError if not found | test_raises_tool_error_when_source_not_found |
| Disabled source → error string, no ValueError | test_disabled_source_returns_error_string_not_exception, test_disabled_source_error_string_mentions_source |
| await refresh_orchestrator.refresh(source) | test_calls_refresh_orchestrator_refresh_with_source |
| Returns {source_id, refreshed, skipped, failed} | test_result_contains_source_id/refreshed/skipped/failed_count |
| refresh_orchestrator is None → error string | test_refresh_orchestrator_none_returns_error_string |
| source_store is None → ToolError | test_source_store_none_raises_tool_error |

[[2026-04-10]] Fri 05:37

## Builder Notes

### Files Changed

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — 4 changes:
  1. Added `from owlbear_knowledge.refresh import RefreshOrchestrator` import (sorted into block)
  2. Added `refresh_orchestrator: RefreshOrchestrator | None = None` field to `AppContext`
  3. Constructed `RefreshOrchestrator(store=source_store, pipeline=pipeline, workspace_root=Path.cwd())` in `app_lifespan`, passed into `AppContext`
  4. Added `refresh_source` to `__all__`
  5. Implemented `refresh_source` MCP tool with `ToolAnnotations(readOnlyHint=False, destructiveHint=False)`, `source_id: str` param, `ToolError` on store-None or source-not-found, ValueError → error string for disabled sources, `await orchestrator.refresh(source)` directly, returns `{source_id, refreshed, skipped, failed}` dict

### Test Results

- **16 passed** (all `TestFromAC_RefreshSourceMcpTool` tests) — 0 failed
- ruff: **clean** (1 auto-fixed import sort, 0 remaining)

### Coverage

- `server.py` line coverage: 45% (pre-existing module — lifespan/DB/other tools are integration-only paths). All new `refresh_source` code paths are exercised by the 16 tests.

### Evidence

- All AC items confirmed green:
  - AC1 ✅ importable
  - AC2 ✅ AppContext.refresh_orchestrator field
  - AC3a ✅ async def
  - AC3b ✅ in **all**
  - AC4 ✅ source_id param
  - AC5 ✅ store.get called
  - AC6 ✅ ToolError on not found
  - AC7a/b ✅ disabled → error string with source_id
  - AC8 ✅ await orchestrator.refresh(source)
  - AC9a-d ✅ result dict keys
  - AC10 ✅ None orchestrator → error string
  - AC11 ✅ None store → ToolError

[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: 16 passed, 0 failed (independent run via quality-runner)

### Lint: clean (ruff exit 0)

### Coverage: owlbear_mcp_knowledge.server: 41% (pre-existing module; all new `refresh_source` code paths confirmed covered — lifespan/DB paths are integration-only by design, consistent with prior tasks on same module)

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| refresh_source importable | test_refresh_source_is_importable | YES — ImportError | COVERED |
| refresh_source in **all** | test_refresh_source_in_all | YES — AssertionError if missing | COVERED |
| AppContext.refresh_orchestrator field | test_app_context_has_refresh_orchestrator_field | YES — AssertionError | COVERED |
| ToolAnnotations(readOnlyHint=False, destructiveHint=False) | test_refresh_source_is_async (structural; tests async-ness only) | NO — wrong annotation values would pass | LAX |
| source_id: str parameter | test_refresh_source_accepts_source_id_parameter | YES — signature check | COVERED |
| source_store.get(source_id) called | test_calls_store_get_with_source_id | YES — assert_called_once_with | COVERED |
| ToolError if source not found | test_raises_tool_error_when_source_not_found | YES — pytest.raises(ToolError) | COVERED |
| Disabled source → error string, no ValueError | test_disabled_source_returns_error_string_not_exception | YES — isinstance(result, str) | COVERED |
| Disabled error mentions source_id | test_disabled_source_error_string_mentions_source | YES — substring check | COVERED |
| await orchestrator.refresh(source) | test_calls_refresh_orchestrator_refresh_with_source | YES — assert_called_once_with(source) | COVERED |
| Returns {source_id, refreshed, skipped, failed} | test_result_contains_source_id/refreshed/skipped/failed | YES — value equality | COVERED |
| orchestrator None → error string | test_refresh_orchestrator_none_returns_error_string | YES — isinstance(result, str) | COVERED |
| source_store None → ToolError | test_source_store_none_raises_tool_error | YES — pytest.raises(ToolError) | COVERED |

LAX (informational, no auto-FAIL applied): `test_refresh_source_is_async` verifies the function is a coroutine but does not verify the specific annotation values. No compensating `TestBuilderDiscovered_*` test for annotations. However: (a) code reading confirms `ToolAnnotations(readOnlyHint=False, destructiveHint=False)` at server.py L551, (b) annotations are informational MCP hints — not behavior-affecting, and (c) test-writer explicitly documented this decision. Applying -.03 deduction rather than auto-FAIL given the implementation is verified correct. No MISSING coverage.

Test count discrepancy: test-writer noted 14 tests; file contains 16. The 2 extra tests (AC10, AC11) are listed in the AC coverage table with correct test names — the category tally was miscounted, not the coverage. Non-issue.

#### Security Review

- `source_id` used only as a DB lookup key via `store.get()` — no raw SQL, no injection surface
- No subprocess, eval, exec, pickle, path traversal
- No hardcoded secrets, no credential/PII leakage in error messages (`f"Source '{source_id}' not found"` — safe)
- No new external I/O surfaces (source_id maps to internal store)
- **No issues**

#### Test Integrity

Builder modified only `server.py`. No changes to `test_refresh_source_mcp_tool_737.py`.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 16 TestFromAC_RefreshSourceMcpTool methods | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Dict value equality checks, assert_called_once_with(source), isinstance(result, str) — no lazy `not None` asserts |
| Negative/error-path coverage | STRONG | 5 of 16 tests cover error paths (not-found, disabled, None store, None orchestrator, disabled-mentions-source) |
| Mutation reasoning | STRONG | Changing store.get() call → test_calls_store_get_with_source_id fails; removing ToolError → pytest.raises fails; wrong return keys → value equality fails |
| Test independence | STRONG | All use fresh MagicMock/AsyncMock per test, no shared mutable state |
| Descriptive names | STRONG | All names self-document AC line and failure condition |

#### Data Safety

- No LLM output persisted without sanitization
- No shared mutable state; refresh is source-scoped
- No race conditions (single async await chain)
- `source_id` input is bounded to valid DB lookup
- **No issues**

#### Implementation-Aware Test Gap Analysis

Code paths in `refresh_source` (server.py L551–577):

- store is None → ToolError: ✅ covered (test 16)
- store.get() → None → ToolError: ✅ covered (test 7)
- orchestrator is None → error string: ✅ covered (test 15)
- `except ValueError as exc` → error string: ✅ covered (tests 8, 9)
- `await orchestrator.refresh(source)` → dict: ✅ covered (tests 10–14)

AppContext lifespan construction is integration-only — consistent with all other tools in same module. No untested significant paths.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Retries | 0 |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

1. **LAX annotation test**: `test_refresh_source_is_async` does not verify `ToolAnnotations(readOnlyHint=False, destructiveHint=False)`. Annotations confirmed correct by code reading (server.py L551). Low practical risk — MCP annotations are hints, not behavior enforcement. Test-writer explicitly documented the decision. -.03 deduction.
2. **Coverage 41%**: Pre-existing pattern for server.py in this module. Lifespan/DB/other tools are integration-only paths unchanged by this task. New refresh_source paths fully covered. -.02 deduction.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add refresh_orchestrator to AppContext | server.py L82: `refresh_orchestrator: RefreshOrchestrator | None = None` | test_app_context_has_refresh_orchestrator_field | PASS |
| Construct RefreshOrchestrator in app_lifespan | server.py L228-231: `RefreshOrchestrator(store=source_store, pipeline=pipeline, workspace_root=Path.cwd())` | integration-only path, pattern-consistent | PASS |
| ToolAnnotations(readOnlyHint=False, destructiveHint=False) | server.py L551: `@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))` | test_refresh_source_is_async (LAX) | PASS |
| source_id: str parameter | server.py L552: `async def refresh_source(ctx: Context, source_id: str)` | test_refresh_source_accepts_source_id_parameter | PASS |
| source_store.get(source_id) lookup | server.py L560: `source = store.get(source_id)` | test_calls_store_get_with_source_id | PASS |
| ToolError if not found | server.py L561-562: `if source is None: raise ToolError(msg)` | test_raises_tool_error_when_source_not_found | PASS |
| Disabled source → error string, no ValueError | server.py L565-567: `except ValueError as exc: return f"error: {exc}"` | test_disabled_source_returns_error_string_not_exception/mentions_source | PASS |
| await orchestrator.refresh(source) directly | server.py L565: `result = await orchestrator.refresh(source)` | test_calls_refresh_orchestrator_refresh_with_source | PASS |
| Returns {source_id, refreshed, skipped, failed} | server.py L568-572: return dict with 4 keys | test_result_contains_source_id/refreshed/skipped/failed | PASS |
| refresh_source in **all** | server.py L258: confirmed in **all** list | test_refresh_source_in_all | PASS |
| orchestrator None → error string | server.py L563-564: `if orchestrator is None: return "error: refresh orchestrator not available"` | test_refresh_orchestrator_none_returns_error_string | PASS |
| source_store None → ToolError | server.py L556-558: `if store is None: raise ToolError(msg)` | test_source_store_none_raises_tool_error | PASS |

### Confidence: .94

### Verdict: PASS

[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `copilot-instructions.md` is 13 lines — only Project Identity and Repository Branches. No MCP tool registry or capability table to update. |
| 2 | Module docstrings | Yes | Verified | `server.py` `refresh_source` has accurate docstring (lines ~551–558): documents return dict, error string cases, and ToolError conditions. `AppContext` class docstring present. No updates needed. |
| 3 | External attribution | No | N/A | v1-port task; no external repos or articles used. |
| 4 | CLI changes | No | N/A | MCP tool addition only; no CLI commands added or modified. |
| 5 | Research doc | No | N/A | No dedicated `.owlbear/research/737-*` file; architecture review was inline in task body. |

### Files Updated

None.

### Scratch Files

None found for task 737.

### Verdict

PASS — no documentation updates required. All AC verified by reviewer; docstrings accurate; no external attribution needed.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| refresh_source tool exists | server.py L493: `async def refresh_source` | PASS |
| AppContext.refresh_orchestrator field | server.py L97: `refresh_orchestrator: RefreshOrchestrator \| None = None` | PASS |
| ToolAnnotations(readOnlyHint=False, destructiveHint=False) | server.py L493: `@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))` | PASS |
| source_id: str parameter | server.py L494: `source_id: str` | PASS |
| source_store.get(source_id) lookup | server.py L503: `source = store.get(source_id)`, test_calls_store_get_with_source_id | PASS |
| ToolError if not found | server.py L504-506, test_raises_tool_error_when_source_not_found | PASS |
| Disabled source returns error string | server.py L514-515: `except ValueError as exc`, test_disabled_source_returns_error_string_not_exception | PASS |
| await orchestrator.refresh(source) | server.py L513, test_calls_refresh_orchestrator_refresh_with_source | PASS |
| Returns {source_id, refreshed, skipped, failed} | server.py L516-520, test_result_contains_source_id/refreshed/skipped/failed | PASS |
| refresh_source in **all** | server.py confirmed in **all** list, test_refresh_source_in_all | PASS |
| orchestrator None returns error string | server.py L510-511, test_refresh_orchestrator_none_returns_error_string | PASS |
| source_store None raises ToolError | server.py L500-502, test_source_store_none_raises_tool_error | PASS |

### Test Results

- pytest (task-specific): 16 passed, 0 failed
- pytest (full suite): 3113 passed, 278 failed, 2 errors — all failures in unrelated test files (RED-phase for other tasks: orchestrator_loop, planner_gates_selector, analysis, lint_feedback_547, mcp_kanban_move_task_588, etc.). Zero regressions from #737.
- ruff: clean (exit 0)

### Architect Quality: 5/5

AC was refined from 5 generic items to 11 specific, testable criteria. Included failure mode map, key files, KISS challenge (dropped source_name), exact infrastructure pattern (AppContext field, lifespan init, ctx accessor). Edge cases specified: disabled source, None orchestrator, None store. Exemplary upstream work.

### Process Note

Upstream agents did not commit deliverables. server.py contains mixed changes from tasks #737, #738, #739 — cannot isolate a clean per-task commit. Noted as process gap; does not affect functional correctness.

### Deduction Breakdown

- Starting: 1.00
- No AC lines without evidence: 0
- No lint violations: 0
- AC quality > 3: 0
- Reviewer evidence present and thorough: 0
- No full-suite failures in task scope: 0
- Total deductions: 0

### Confidence: .98

(Minor process gap: uncommitted deliverables with mixed multi-task changes in server.py. Functional quality is impeccable.)

### Action: archive
