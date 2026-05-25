---
id: 1855
title: 'P1-05: MCP tools — create_request, list_requests, show_request'
status: backlog
priority: needed
created: 2026-05-24T20:58:39.096212+02:00
updated: 2026-05-25T13:24:21.801043+02:00
tags:
  - phase-1
  - scope:mcp-kanban
  - mcp
parent: 1850
depends_on:
  - 1854
ac:
  - 'create_request tool: @mcp.tool(ToolAnnotations(destructiveHint=False)), params
    (task_id: str|int, kind, title, summary, agent, options?: list[dict]|None, body?:
    str). parse_task_id validates task_id. _normalize_escaped_newlines on body. asyncio.to_thread
    delegates to engine.create_request. Returns model_dump() + guidance array when
    normalization applied. KanbanError → _map_kanban_error. PydanticValidationError
    → _raise_param_validation.'
  - 'list_requests tool: @mcp.tool(ToolAnnotations(readOnlyHint=True, idempotentHint=True)),
    params (status: str="pending", task_id: str|int|None=None). parse_task_id when
    task_id non-None. asyncio.to_thread delegates to engine.list_requests(status,
    task_id). Returns [r.model_dump(exclude={"body"}) for r in records]. KanbanError
    → _map_kanban_error.'
  - 'show_request tool: @mcp.tool(ToolAnnotations(readOnlyHint=True, idempotentHint=True)),
    params (request_id: str). Validates request_id is UUID4 format before delegation
    — invalid → _raise_param_validation. asyncio.to_thread delegates to engine.get_request(request_id).
    Returns model_dump() (full detail + resolution + body). KanbanError → _map_kanban_error.'
  - "pick_tasks annotation fix: readOnlyHint changed from True to False (sweep_requests
    writes). idempotentHint=True retained. Docstring updated to remove 'Read-only'
    claim."
  - 'Delegation proof contracts: (a) create_request tests must assert engine mock
    called with all forwarded params (task_id, kind, title, summary, agent, options,
    body); normalization test must assert normalized body is the value forwarded.
    (b) list_requests tests must assert engine mock receives explicit non-default
    status when caller passes one.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Three new MCP tools: `create_request`, `list_requests`, `show_request`
- Parameter validation and forwarding to engine
- Error mapping (KanbanError → ToolError, PydanticValidationError → ToolError)
- UUID4 format validation for request_id at MCP layer (security: prevent path traversal)
- `pick_tasks` annotation correction: `readOnlyHint=False` (delegated from #1854 architecture review — sweep_requests is now wired into pick_tasks)
- No `resolve_request` MCP tool (resolution is human-only via Cockpit)

**Out of scope:**
- Engine implementation (done in P1-01 through P1-04)
- Old `create_dr` tool (retained until P2-05 removal)
- Cockpit API

## Test scope
`serve/mcp-kanban/tests/`"

[[2026-05-25T10:14:56+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three related MCP tools (create/list/show request) + one annotation fix (pick_tasks readOnlyHint delegated from #1854) — single MCP server domain |
| Interface clarity | PASS | After refinement: params, return shapes, error paths, ToolAnnotations all specified. Normalization guidance parity with create_dr included. |
| Dependency correctness | PASS | #1854 archived/completed; engine create_request/get_request/list_requests all exist |
| Module layering | PASS | MCP server (serve/mcp-kanban) calls engine (serve/kanban) — downward dependency only |
| TDD compliance | PASS | Test scope: serve/mcp-kanban/tests/ (established test infrastructure exists) |
| KISS/YAGNI | PASS | Thin forwarding layer; no new abstractions or models needed |
| Premise challenge | PASS | Brief-driven; MCP exposure is explicit requirement in parent epic |
| Pattern consistency | PASS | Follows existing create_dr, list_tasks, show_task patterns exactly: asyncio.to_thread, _map_kanban_error, _raise_param_validation, parse_task_id, _normalize_escaped_newlines |
| Security surface | PASS | UUID4 format validation at MCP layer prevents path traversal to engine's validate_path_containment |
| Single domain | PASS | mcp-kanban only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| create_request: invalid task_id | Bad format | parse_task_id → ToolError | Yes | ERR_INVALID_ID |
| create_request: task not found | Missing task | NotFoundError → _map_kanban_error | Yes | ERR_NOT_FOUND |
| create_request: invalid kind/options | Model validation | PydanticValidationError → _raise_param_validation | Yes | ERR_PARAM_VALIDATION |
| list_requests: invalid status | Engine rejects | ValidationError(KanbanError) → _map_kanban_error | Yes | mapped code |
| show_request: invalid UUID | Pre-delegation check | _raise_param_validation | Yes | ERR_PARAM_VALIDATION |
| show_request: request not found | File missing | NotFoundError → _map_kanban_error | Yes | ERR_NOT_FOUND |

### Design Diverge
- Trigger: skipped — single clear approach (forward to engine via asyncio.to_thread, same as all existing tools)

### Challenge Results
- Challenger: reconsider (confidence 0.39)
- Findings: (1) PydanticValidationError not caught — accepted, AC1 now requires it; (2) show_request path traversal risk — accepted, AC3 now requires UUID4 format validation; (3) AC4 scope concern — rebutted: explicitly delegated from #1854 arch review, same file/domain; (4) list_requests shape implicit — accepted, AC2 now enumerates all fields; (5) normalization guidance parity — accepted, AC1 now includes guidance array requirement.
- Architect response: Accepted 1,2,4,5; rebutted 3. Refined AC from 3 to 4 lines with full error handling spec.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 3 vague lines to 4 precise lines with error mapping, ToolAnnotations, return shapes, UUID4 validation, and pick_tasks annotation fix. Scope section updated to include PydanticValidationError mapping and security validation. Advanced to todo.

[[2026-05-25T10:26:09+02:00]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_request_tools_1855.py
- Classes: TestFromAC_CreateRequestTool, TestFromAC_ListRequestsTool, TestFromAC_ShowRequestTool, TestFromAC_PickTasksAnnotationFix
- Tests per category: happy 8, edge 5, error 10, boundary 8
- Total: 31 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 create_request tool | 12 tests — registration, annotations, signature, success, normalization, error mapping, boundary |
| AC2 list_requests tool | 8 tests — registration, annotations, body exclusion, default status, forwarding, empty result, error mapping, null task_id |
| AC3 show_request tool | 8 tests — registration, annotations, success with full body+resolution, delegation, UUID format validation, UUID version validation, not-found, path-traversal boundary |
| AC4 pick_tasks annotation fix | 3 tests — readOnlyHint=False, idempotentHint=True retained (regression guard), docstring |

[[2026-05-25T10:40:57+02:00]]
## Builder Notes
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Commit: 417245fd (feat: add request MCP tools and pick_tasks hint fix (#1855, builder))

Implementation summary:
- Added MCP tool `create_request` with `ToolAnnotations(destructiveHint=False)`, `parse_task_id` validation, newline normalization for `body`, `asyncio.to_thread` delegation to `engine.create_request`, `KanbanError -> _map_kanban_error`, `PydanticValidationError -> _raise_param_validation`, and `guidance` output when normalization occurs.
- Added MCP tool `list_requests` with `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`, optional `task_id` parsing, `asyncio.to_thread` delegation to `engine.list_requests`, and response shape `[record.model_dump(exclude={"body"}) for record in records]`.
- Added MCP tool `show_request` with `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`, UUID4 format/version validation at MCP layer before delegation, `asyncio.to_thread` delegation to `engine.get_request`, and full `model_dump()` response.
- Fixed `pick_tasks` annotation to `readOnlyHint=False` while retaining `idempotentHint=True`.
- Updated `pick_tasks` docstring to remove the "Read-only" claim.

Verification evidence:
- RED verification via quality-runner (pre-change): 0 passed / 31 failed in `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` (all `TestFromAC_*` expectations failing as intended before GREEN).
- GREEN verification via quality-runner:
  - `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 31 passed, 0 failed.
  - Lint on touched paths (`server.py`, task test file): clean (ruff exit 0).
  - Coverage report (scoped run): module `owlbear_mcp_kanban.server` = 38%.
- Durable module regression baseline (quality-runner):
  - `serve/mcp-kanban/tests/test_mcp_server.py`: 3 passed, 0 failed.
  - Lint clean.

Net test result count executed in verification: 34 passed, 0 failed.

[[2026-05-25T10:59:28+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC4 | Adjacent durable proof is still red on the old pick_tasks contract. The implementation matches AC4, but the existing durable suite still expects `readOnlyHint=True`, so the proof packet is insufficient and the task cannot pass review. | AC4 in task frontmatter; implementation `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:749`; stale durable test `tests/test_mcp_kanban.py:1585`; independent verification via quality-runner on `tests/test_mcp_kanban.py` reported 120 passed, 1 failed: `test_pick_tasks_read_only_hint_is_true` with `assert False is True ... readOnlyHint` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update the adjacent durable pick_tasks annotation expectation to match AC4 (`readOnlyHint=False`, keep `idempotentHint=True`) and rerun the durable suite used as proof for this module slice. | `tests/test_mcp_kanban.py` | Failing test at `tests/test_mcp_kanban.py:1585` and quality-runner report: 120 passed, 1 failed |
| 2 | test-writer | Align the AC4 proof note with the actual proof surface so the review packet names the durable idempotent guard correctly. | `.owlbear/kanban/tasks/1855-p1-05-mcp-tools-create-request-list-requests-show-request.md`, `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`, `tests/test_mcp_kanban.py` | Task note line 118 claims 3 pick_tasks tests, but the task-scoped file only contains readOnly/docstring checks while the idempotent guard lives at `tests/test_mcp_kanban.py:1590` |

## Observations
- AC1-AC3 map cleanly to the implementation in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459`, `:494`, and `:514`, and the task-scoped tests provide adequate local proof for those lines.
- The builder's scoped task test and lint evidence was otherwise clean; the rejection is driven by the missed adjacent durable proof, not by a source-level defect in `server.py`.

[[2026-05-25T11:03:18+02:00]]
## Test-Writer Notes
- Retry: updated 1 stale durable test in `tests/test_mcp_kanban.py` (line 1585).
  - `test_pick_tasks_read_only_hint_is_true` → `test_pick_tasks_read_only_hint_is_false` with assertion `readOnlyHint is False` to match AC4 and current implementation.
- Builder skip: test-only retry, all tests green.

**Quality-runner evidence (post-fix):**
- `tests/test_mcp_kanban.py`: 121 passed, 0 failed (was 120 passed, 1 failed before fix)
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 31 passed, 0 failed
- Total: 152 passed, 0 failed
- Lint: clean (ruff exit 0)

**AC4 proof surface (corrected):**
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py::TestFromAC_PickTasksAnnotationFix::test_pick_tasks_read_only_hint_is_false` — readOnlyHint=False assertion
- `tests/test_mcp_kanban.py::test_pick_tasks_idempotent_hint_is_true` — idempotentHint=True regression guard (durable, line 1590)

[[2026-05-25T11:33:09+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | Task-scoped proof does not verify full `create_request` adapter forwarding. The named forwarding test sends non-default `title`, `summary`, `agent`, and `body`, but only asserts parsed `task_id`, so regressions in forwarded `title`, `summary`, `agent`, `options`, or `body` would still pass. | Test inputs at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:233`, `:234`, `:236`; only delegated-argument assertion at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:242`; implementation forwards full payload at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:474-482` | backlog |
| 2 | AC1 | Normalization proof does not verify that the normalized body is the value delegated to the engine. The task test only checks non-empty `guidance`, so an adapter regression that appends guidance but forwards raw escaped text would still false-green. | Normalization in implementation at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:472` and delegated `body=normalized_body` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:482`; task test only asserts guidance at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:249`, `:267`, `:271` | backlog |
| 3 | AC2 | Explicit non-default `status` forwarding is under-asserted. The test invokes `status="resolved"` but only verifies parsed `task_id`, so an adapter that always forwarded `"pending"` would still pass the current suite. | Call with non-default status at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:500`; assertions only on `task_id` at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:503`, `:506`; implementation forwards `status` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:503-506` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the proof contract for AC1 so task-local tests must assert full `create_request` delegation, including forwarded `title`, `summary`, `agent`, `options`, and normalized `body`, then return the task to `todo` for test coverage repair. | `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` | Weak forwarding proof at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:233-242` and normalization proof gap at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:249-271` |
| 2 | architect | Re-scope the proof contract for AC2 so task-local tests must assert explicit non-default `status` forwarding to `engine.list_requests`, then return the task to `todo` for test coverage repair. | `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` | Weak explicit-status proof at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:500-506` |

## Observations
- The source implementation still maps cleanly to AC1-AC4. I found no implementation defect in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` for this task slice.
- The prior AC4 blocker is resolved: `tests/test_mcp_kanban.py:1585-1593` now matches the current `pick_tasks` contract. The remaining blocker is proof quality in AC1/AC2, not stale AC4 coverage.
- This is a second review cycle on the same task. Per review routing rules, remaining blocking findings route to `backlog` rather than `todo`.

[[2026-05-25T11:35:10+02:00]]
## Architecture Review (Re-scope — Proof Contract Repair)

### Context
Second reviewer cycle rejected AC1/AC2 for weak delegation proof: task-scoped tests assert only `task_id` but not forwarded `title`, `summary`, `agent`, `options`, `body` (AC1) or explicit non-default `status` (AC2). Implementation confirmed correct — this is proof quality only.

### Action Taken
Added AC5 (Delegation proof contracts) specifying:
- (a) `create_request` tests must assert engine mock called with all forwarded params; normalization test must assert the normalized body is the forwarded value.
- (b) `list_requests` tests must assert engine mock receives explicit non-default status.

AC1-AC4 unchanged. No implementation defect — test-writer will strengthen existing task-scoped assertions.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (proof repair cycle)

### Verdict: APPROVE (re-scope)
Advanced to todo for test-writer proof repair.

[[2026-05-25T11:46:21+02:00]]
## Test-Writer Notes
- Retry (AC5 proof repair): added 5 new delegation proof tests to `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` in class `TestFromAC_DelegationContracts`.
- Builder skip: test-only retry — all new tests pass against current implementation.

**New tests (AC5):**
| Test | AC | Assertion |
|------|----|-----------|
| `test_create_request_engine_receives_all_positional_params` | AC5(a) | task_id, kind, title, summary, agent all forwarded |
| `test_create_request_engine_receives_options_kwarg` | AC5(a) | options forwarded unchanged |
| `test_create_request_normalization_forwards_normalized_body_not_raw` | AC5(a) | normalized body forwarded (not raw escaped string) |
| `test_list_requests_explicit_resolved_status_forwarded_to_engine` | AC5(b) | status='resolved' forwarded as 'resolved' |
| `test_list_requests_explicit_all_status_forwarded_to_engine` | AC5(b) | status='all' forwarded as 'all' |

**Quality-runner evidence (post-fix):**
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 36 passed, 0 failed (was 31)
- Lint: clean (ruff exit 0)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC5(a) create_request delegation | 3 new tests — full positional params, options kwarg, normalized body forwarded |
| AC5(b) list_requests status forwarding | 2 new tests — resolved and all status values forwarded to engine |

[[2026-05-25T12:20:49+02:00]]
## Orchestrator Note
Reviewer consistently finds AC1-AC3 success-path tests under-assert the returned model_dump shape. Tests only check subset of fields; a truncated adapter would false-green. Architect should add AC requiring full response-shape assertion for all three tools.
