---
id: 1451
title: 'P4-14: Normalize MCP filters, annotations, and errors'
status: in-progress
priority: needed
created: 2026-05-08T19:32:19.525089+00:00
updated: 2026-05-11T07:03:37.913097+00:00
tags:
- phase-4
- scope:mcp-kanban
- type:build
- filters
- errors
- annotations
- validation
- deployment-readiness
parent: 1437
depends_on:
- 1450
- 1445
- 1447
blocked: false
block_reason:
claimed_at: 2026-05-11T07:03:37.913097+00:00
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: AgentView/MCP interface behavior for list filters, status-destination validation, annotations, descriptions, and error envelopes.
Out of scope: Cockpit UI, setup seed, agent guidance, and docs.

## Acceptance Criteria
1. list_tasks treats ids=[] as an explicit empty ID request and returns an empty tasks list without falling back to unfiltered board listing.
2. list_tasks with archival_reason and no status argument searches archive storage and returns tasks whose archival_reason matches the requested product archive reason.
3. move_task and end_work destination handling use one shared validation path for status names, archive reason requirements, archive refs, completed-only archival, and predicate failures.
4. MCP tool annotations and descriptions state that move_task is mutating and not idempotent, pick_tasks is read-only after dispatch side effects are removed, and resolve_drs performs DR mutation.
5. MCP errors for KanbanError, Pydantic validation, malformed ID, and stale write cases surface structured code and message fields without raw tracebacks or internal paths.
6. Builder verifies AC-1 through AC-5 using the probe artifacts from #1450 and does not use pytest or vitest as the functional proof.
[[2026-05-11]]


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes within kanban MCP interface normalization |
| Interface clarity | PASS after refinement | AC-3 narrowed to archival-constraint helper; AC-5 paths enumerated; AC-6 demoted to guidance |
| Dependency correctness | PASS | #1450 (probes), #1445 (pick_tasks read-only), #1447 (resolve_drs) — all archived/done |
| Module layering | PASS | Changes in serve/kanban (AgentView) and serve/mcp-kanban (server.py); MCP→kanban direction correct |
| TDD compliance | PASS | Probe suite TestMergedFrom1450 in tests/test_mcp_kanban.py provides RED coverage; package-level suites in serve/mcp-kanban/tests/ also constrain behavior |
| KISS/YAGNI | PASS | Shared helper reduces duplication; no new abstractions |
| Premise challenge | PASS | Normalizing inconsistent error surfaces and duplicated validation is warranted |
| Pattern consistency | PASS | Follows existing KanbanError/code taxonomy; structured {code, message} envelope pattern |
| Security surface | PASS | AC-5 explicitly prevents leaking internal paths; no new external boundaries |
| Single domain | PASS | kanban MCP domain only |

### AC Assessment

| AC Line | Original | Refined | Action |
|---------|----------|---------|--------|
| AC-1 | ids=[] returns empty | Keep as-is (td:0) — MCP layer short-circuits at server.py:212; AgentView would also return empty via set arithmetic | No change |
| AC-2 | archival_reason auto-searches archive | Keep as-is (td:0) — MCP layer resolves status=archived at server.py:215; AgentView post-filters at agent_view.py:210 | No change |
| AC-3 | "one shared validation path" | Narrowed (td:1) — see below | Refined |
| AC-4 | move_task not idempotent, descriptions | Tightened (td:0) — see below | Refined |
| AC-5 | structured errors | Enumerated (td:1) — see below | Refined |
| AC-6 | builder uses probes not pytest | Demoted to builder guidance — not a verifiable code criterion | Moved |

### AC-3 Refinement

move_task and end_work share a single private helper for archival-constraint validation (archival-reason requirement, archival-ref constraints, completed-only archival check, archival-field prohibition on non-archive moves). Both methods call this helper instead of duplicating the validate_archival / ERR_ARCHIVAL_FIELDS_FORBIDDEN logic inline. Status-name validation (different valid sets per outcome) and outcome-specific error codes (ERR_MOVE_TO_INVALID_STATUS vs ERR_INVALID_STATUS) remain in each method. The success-outcome derived-next-status predicate check is end_work-specific and stays there. Explicit-target predicate checks (move_task status, end_work reject/block move_to) may optionally be included in the shared helper.

### AC-4 Refinement — Contract Break

**idempotentHint change:** move_task currently has `idempotentHint=True`, defended by two explicit tests:
- `serve/mcp-kanban/tests/test_tool_annotations.py::TestFromAC_ToolAnnotations::test_move_task_idempotent_hint_true`
- `serve/mcp-kanban/tests/test_tool_annotations.py::TestFromAC_AnnotationContractRestore_1475::test_move_task_idempotent_hint_true_per_original_ac`

Strictly, move_task is NOT idempotent: repeated calls update `updated` timestamp and create activity events. The AC requirement to set `idempotentHint=False` is correct. **Builder must update both test classes** in `test_tool_annotations.py` to assert `False` and update their docstrings to reflect the revised contract.

**Descriptions:** Update tool docstrings for move_task (state: mutating, non-idempotent), pick_tasks (state: read-only, idempotent), and resolve_drs (state: mutates DR files on disk).

### AC-5 Refinement — Enumerated Raw ToolError Paths

Seven raw-string ToolError paths need structured `{code, message}` JSON envelopes:

1. `_show_validated` FileNotFoundError → `ToolError(msg)` — server.py:270
2. `create_dr` request_type guard → `ToolError(msg)` — server.py:327
3. `move_task` missing status → `ToolError(msg)` — server.py:381
4. `start_work` ValueError/FileNotFoundError → `ToolError(str(exc))` — server.py:479-480
5. `end_work` ValueError/FileNotFoundError → `ToolError(str(exc))` — server.py:516-517
6. `list_tasks` PydanticValidationError → `ToolError(str(exc))` — server.py:231
7. `pick_tasks` PydanticValidationError → `ToolError(str(exc))` — server.py:559

Use consistent codes: ERR_NOT_FOUND for FileNotFoundError, ERR_PARAM_VALIDATION for Pydantic and parameter guards, ERR_INVALID_ID for malformed IDs (already done). No raw tracebacks or internal file paths in any error response.

### Builder Guidance

- Probe suite `tests/test_mcp_kanban.py::TestMergedFrom1450` provides primary verification; builder may extend the probe class with additional assertions for AC-4 (idempotentHint=False) and AC-5 (Pydantic envelope) but does not create new test files.
- The probe test `test_move_task_idempotent_hint_is_false` only checks `isinstance(bool)` — the builder should add an explicit `assert ann.idempotentHint is False` assertion to the probe class.
- Test-writer: SKIP not applicable — td:1 lines present; test-writer processes normally using td annotations.

### Challenge Result

Challenger confidence: 0.41, recommendation: block. Concerns addressed:
1. AC-1/AC-2 scope — MCP-layer normalization is sufficient; AgentView also returns empty for ids=[] via set arithmetic. Kept as verification guards.
2. AC-4 contract conflict — acknowledged; builder must update test_tool_annotations.py explicitly. Justified by strict idempotency semantics.
3. AC-3 shared-helper scope — narrowed to archival constraints; outcome-specific codes/validation remain separate.
4. AC-5 enumerated paths — all 7 raw ToolError sites listed with target codes.
5. AC-6 demotion — moved to builder guidance with proof reference preserved.
Override: PROCEED. All concerns resolved through AC refinement; no architectural blocker remains.
[[2026-05-11]]
Architecture review complete. AC refined: AC-3 narrowed to archival-constraint shared helper (status-name validation stays per-method); AC-4 idempotentHint contract break acknowledged with explicit test update requirement; AC-5 enumerated 7 raw ToolError paths; AC-6 demoted to builder guidance. Challenger override at 0.41 — all concerns resolved through refinement. td:0 for AC-1/2/4, td:1 for AC-3/5.
[[2026-05-11]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1451.py
- Classes: TestFromAC_SharedArchivalHelper, TestFromAC_StructuredErrors
- AC coverage:
  - AC-1 (td:0): skipped — already tested in TestMergedFrom1450
  - AC-2 (td:0): skipped — already tested in TestMergedFrom1450
  - AC-3 (td:1): 3 tests — existence of _validate_archival_constraints, invocation by move_task, invocation by end_work
  - AC-4 (td:0): skipped — builder must update existing test_tool_annotations.py assertions
  - AC-5 (td:1): 18 tests — 2 per enumerated path (envelope + specific code): _show_validated FileNotFoundError (ERR_NOT_FOUND), create_dr request_type guard (ERR_PARAM_VALIDATION), move_task missing status (ERR_PARAM_VALIDATION), start_work ValueError (ERR_PARAM_VALIDATION), start_work FileNotFoundError (ERR_NOT_FOUND), end_work ValueError (ERR_PARAM_VALIDATION), end_work FileNotFoundError (ERR_NOT_FOUND), list_tasks PydanticValidationError (ERR_PARAM_VALIDATION), pick_tasks PydanticValidationError (ERR_PARAM_VALIDATION)
- Tests per category: happy 0, edge 0, error 21, boundary 0
- Total: 21 tests, all FAIL (RED confirmed)
- ruff: clean