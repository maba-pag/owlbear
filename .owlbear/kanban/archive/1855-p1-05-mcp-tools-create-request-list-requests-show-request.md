---
id: 1855
title: 'P1-05: MCP tools — create_request, list_requests, show_request'
status: archived
priority: needed
created: 2026-05-24T20:58:39.096212+02:00
updated: 2026-05-26T00:32:01.163857+02:00
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
  - 'Response-shape proof (value equality): create_request success test must assert
    returned dict equals fake_record.model_dump() merged with {"guidance": []} — full
    value equality, not key presence only. Normalization-path success test must assert
    returned dict equals fake_record.model_dump() merged with {"guidance": [non-empty
    list]} — full value equality.'
  - 'Response-shape proof (value equality): list_requests success test must assert
    each returned item equals fake_record.model_dump(exclude={"body"}) — full value
    equality, not key presence only. show_request success test must assert returned
    dict equals fake_record.model_dump() — full value equality.'
  - 'Surface-contract snapshot update: EXPECTED_TOOLS in serve/mcp-kanban/tests/test_mcp_surface_contract.py
    must include create_request, list_requests, show_request (total 12 tools). test_live_registry_contains_exactly_nine_tools
    must be renamed to reflect 12-tool count.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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

[[2026-05-25T19:09:32+02:00]]
## Architecture Review (Re-scope — Response-Shape Proof Repair)

### Context
Third reviewer cycle: orchestrator flagged AC1-AC3 success-path tests under-assert the returned model_dump shape. Tests check subset of fields; a truncated adapter would false-green. Implementation confirmed correct — proof quality only.

### Action Taken
Added AC6+AC7 (Response-shape proof contracts) specifying:
- (a) create_request success test must assert all RequestRecord.model_dump() keys plus guidance key.
- (b) list_requests success test must assert all model_dump(exclude={body}) keys and body absent.
- (c) show_request success test must assert all RequestRecord.model_dump() keys.

AC1-AC5 unchanged. No implementation defect — test-writer will add response-shape assertions to existing task-scoped tests.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (proof repair cycle)

### Verdict: APPROVE (re-scope)
Advanced to todo for test-writer response-shape proof repair.

[[2026-05-25T19:46:58+02:00]]
## Test-Writer Notes
- Retry (AC6+AC7 response-shape proof repair): added 3 new tests to `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` in class `TestFromAC_ResponseShapeContracts`.
- Builder skip: test-only retry — all new tests pass against current implementation.

**New tests (AC6+AC7):**
| Test | AC | Assertion |
|------|----|-----------| 
| `test_create_request_success_returns_all_record_keys_plus_guidance` | AC6 | All 10 RequestRecord.model_dump() keys + guidance key present |
| `test_list_requests_success_each_record_has_all_expected_keys_body_absent` | AC7 | All 9 model_dump(exclude={body}) keys present; body absent |
| `test_show_request_success_returns_all_record_keys` | AC7 | All 10 RequestRecord.model_dump() keys present |

**Quality-runner evidence (post-fix):**
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 39 passed, 0 failed (was 36)
- Lint: clean (ruff exit 0)

**AC coverage (complete):**
| AC | Tests |
|----|-------|
| AC6 create_request full response shape | 1 new test — all 10 record keys + guidance |
| AC7 list_requests response shape | 1 new test — 9 keys (body excluded), body absent |
| AC7 show_request response shape | 1 new test — all 10 record keys |

[[2026-05-25T20:23:52+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1855 -> backlog | create_request/list_requests/show_request proof still allows false-green payload regressions.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1, AC6 | `create_request` success proof is still incomplete. The normalization-path tests verify guidance and delegated body forwarding, but they do not prove that the returned payload on the normalized branch is still the full `RequestRecord.model_dump()` plus guidance. The non-normalized success tests also only spot-check a subset of values and key presence, so incorrect returned `title`, `summary`, `agent`, `options`, `resolution`, or `body` values would still false-green. | Source returns model_dump + guidance at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:472-489`; tests only check guidance on normalized path at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:249-271`, forwarded normalized body at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:882-911`, subset values at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:211-214`, and key presence on a non-normalized call at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:991-1020` | backlog |
| 2 | AC2, AC7 | `list_requests` proof still checks body omission and expected keys, but it does not prove that each returned dict equals `record.model_dump(exclude={"body"})`. A handler that preserved keys while returning wrong `title`, `summary`, `agent`, `created_at`, `options`, or `resolution` values would still pass. | Source returns `record.model_dump(exclude={"body"})` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:504-510`; current assertions are key/body checks only at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:459-466` and `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:1034-1051` | backlog |
| 3 | AC3, AC7 | `show_request` proof still does not prove full payload fidelity to `RequestRecord.model_dump()`. Current tests check body equality plus some key presence, but wrong `title`, `summary`, `agent`, `created_at`, `options`, or nested `resolution` values would still false-green. | Source returns `record.model_dump()` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:520-525`; current assertions are partial-value and key checks at `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:637-642` and `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:1058-1075` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the `create_request` proof contract so one success test asserts full returned payload equality to the mocked `RequestRecord.model_dump()` and one normalization-path success test asserts that the normalized branch still returns the full payload plus guidance, then route back to `todo` for test repair. | `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` | Finding 1; AC1/AC6 evidence above |
| 2 | architect | Re-scope the `list_requests` proof contract so the success test compares each returned item to `fake_record.model_dump(exclude={"body"})`, not only key presence/body absence, then route back to `todo` for test repair. | `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` | Finding 2; AC2/AC7 evidence above |
| 3 | architect | Re-scope the `show_request` proof contract so the success test compares the full returned dict to `fake_record.model_dump()`, including nested `resolution` values, then route back to `todo` for test repair. | `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py` | Finding 3; AC3/AC7 evidence above |

## Observations
- I found no source-level defect in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` for AC1-AC4. The rejection is about proof quality, not implementation correctness.
- The repaired AC4 surface now aligns across task-scoped and durable tests: `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:775-792` and `tests/test_mcp_kanban.py:1585-1592` both match `pick_tasks` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:749-757`.
- Because this task has already been through repeated review/proof-repair cycles, the remaining blocker routes to `backlog` per reviewer routing rules.

[[2026-05-25T20:35:08+02:00]]
## Architecture Review (Re-scope — Value Equality Proof Repair)

### Context
Fourth reviewer cycle: AC6/AC7 response-shape tests check key presence only, not value equality. A handler returning correct keys with wrong values would false-green. Implementation confirmed correct across all cycles — this is proof quality only.

### Action Taken
Replaced AC6 and AC7 wording to require **full value equality** assertions:
- AC6: `create_request` success test must assert `result == fake_record.model_dump() | {"guidance": []}`. Normalization-path test must assert full payload equality with non-empty guidance.
- AC7: `list_requests` success test must assert each item `== fake_record.model_dump(exclude={"body"})`. `show_request` success test must assert `result == fake_record.model_dump()`.

AC1-AC5 unchanged. No implementation defect — test-writer will strengthen existing response-shape assertions from key-presence to value-equality.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (proof repair cycle)

### Verdict: APPROVE (re-scope)
Advanced to todo for test-writer value-equality proof repair.

[[2026-05-25T20:57:06+02:00]]
## Test-Writer Notes
- Retry (AC6+AC7 value-equality proof repair): added 4 new tests in class `TestFromAC_ValueEqualityContracts` to `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`.
- Builder skip: test-only retry — all new tests pass against current implementation.

**New tests (AC6+AC7 value equality):**
| Test | AC | Assertion |
|------|----|-----------| 
| `test_create_request_success_full_value_equality_non_normalized` | AC6 | result == fake_record.model_dump() | {"guidance": []} (exact equality) |
| `test_create_request_normalization_path_full_value_equality` | AC6 | all 10 record fields == model_dump() exactly + guidance is non-empty list |
| `test_list_requests_success_full_value_equality` | AC7 | result[0] == fake_record.model_dump(exclude={"body"}) (exact equality) |
| `test_show_request_success_full_value_equality` | AC7 | result == fake_record.model_dump() (exact equality) |

**Quality-runner evidence (post-fix):**
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 43 passed, 0 failed (was 39)
- Lint: clean (ruff exit 0)

**AC coverage (value equality):**
| AC | Tests |
|----|-------|
| AC6 create_request non-normalized full equality | 1 new test — result == model_dump() | {"guidance": []} |
| AC6 create_request normalization path full equality | 1 new test — record fields == model_dump(), guidance non-empty |
| AC7 list_requests item full equality | 1 new test — item == model_dump(exclude={"body"}) |
| AC7 show_request full equality | 1 new test — result == model_dump() |

[[2026-05-25T21:46:47+02:00]]
## Review Evidence
- Verdict: FAIL
- Routing: backlog
- Summary: The implementation and task-scoped proof are locally sound, but the authoritative durable registry contract is still red after the new MCP tools were added.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1-AC3 | The durable MCP surface-contract snapshot still models the pre-1855 registry, so the module proof surface remains contradictory. The new request tools are registered in server.py, but EXPECTED_TOOLS in serve/mcp-kanban/tests/test_mcp_surface_contract.py was not updated, and an independent scoped rerun fails on that exact mismatch. | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459, :494, :514; serve/mcp-kanban/tests/test_mcp_surface_contract.py:14-16, :42, :239-243; quality-runner scoped rerun on serve/mcp-kanban/tests/test_mcp_surface_contract.py: 4 passed, 1 failed, test_live_registry_contains_exactly_nine_tools, "Unexpected in registry: frozenset({'list_requests', 'create_request', 'show_request'})" | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the proof surface so AC1-AC3 explicitly require the authoritative registry-contract snapshot to stay in sync with server.py when tools are added, then return the task to todo for repair of the stale EXPECTED_TOOLS snapshot. | serve/mcp-kanban/tests/test_mcp_surface_contract.py, serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | Failing durable contract at serve/mcp-kanban/tests/test_mcp_surface_contract.py:239-243 and quality-runner report above |

## Observations
- AC1-AC4 still map cleanly to the implementation in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459, :494, :514, and :750.
- The latest task-scoped proof repairs do close the earlier false-green gaps: create_request/list_requests delegation checks at serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:809, :852, :882, :923, :947 and full value-equality checks at :1091, :1124, :1166, :1191 are specific enough for the local adapter behavior.
- This is a repeated review cycle. Per reviewer routing rules, remaining blockers route to backlog rather than todo.

[[2026-05-25T21:59:18+02:00]]
## Architecture Review (Re-scope — Surface-Contract Snapshot Repair)

### Context
Fifth reviewer cycle: durable surface-contract test `test_live_registry_contains_exactly_nine_tools` in `serve/mcp-kanban/tests/test_mcp_surface_contract.py` still hardcodes 9 tools in `EXPECTED_TOOLS`. The 3 new tools (`create_request`, `list_requests`, `show_request`) are registered in `server.py` but missing from the snapshot, causing a registry-mismatch failure.

The test file header explicitly documents the update contract: \"When a tool is intentionally added or removed, update EXPECTED_TOOLS in the same commit that modifies the tool registration in server.py.\"

### Action Taken
Added AC8 (Surface-contract snapshot update) requiring:
- `EXPECTED_TOOLS` expanded to include `create_request`, `list_requests`, `show_request` (12 total)
- Test function renamed to reflect the new 12-tool count

AC1-AC7 unchanged. No implementation defect — test-writer will update the durable snapshot constant and test name.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (snapshot repair cycle)

### Verdict: APPROVE (re-scope)
Advanced to todo for test-writer surface-contract snapshot repair.

[[2026-05-25T22:26:10+02:00]]
## Test-Writer Notes
- Retry (AC8 surface-contract snapshot repair): updated `serve/mcp-kanban/tests/test_mcp_surface_contract.py`.
  - `EXPECTED_TOOLS` expanded from 9 to 12 tools: added `create_request`, `list_requests`, `show_request`.
  - `test_live_registry_contains_exactly_nine_tools` → `test_live_registry_contains_exactly_twelve_tools`.
- Builder skip: test-only retry — all tests pass against current implementation.

**Quality-runner evidence (post-fix):**
- `serve/mcp-kanban/tests/test_mcp_surface_contract.py`: 5 passed, 0 failed (was 4 passed, 1 failed)
- `serve/mcp-kanban/tests/test_mcp_request_tools_1855.py`: 43 passed, 0 failed
- Total: 48 passed, 0 failed
- Lint: clean (ruff exit 0)

**AC8 proof surface:**
- `serve/mcp-kanban/tests/test_mcp_surface_contract.py::TestFromAC_ToolRegistryContract::test_live_registry_contains_exactly_twelve_tools` — verifies live registry == 12-tool EXPECTED_TOOLS set

[[2026-05-25T22:55:52+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1855 to docs | AC mapped to code and evidence sufficient.
- Builder and retry evidence is sufficient and internally consistent: quality-runner reported 43 passed / 0 failed in serve/mcp-kanban/tests/test_mcp_request_tools_1855.py, 5 passed / 0 failed in serve/mcp-kanban/tests/test_mcp_surface_contract.py, lint clean on touched paths, and prior builder coverage for owlbear_mcp_kanban.server at 38% with no subsequent source changes.
- AC1 maps to serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:459-489. Forwarding proof covers task_id, kind, title, summary, agent, options, and body at serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:809, :852, and :882. Full success payload equality is proved at :1091 and normalized-path payload fidelity plus non-empty guidance is proved at :1124.
- AC2 maps to serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:494-510. Non-default status forwarding is proved at serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:923 and :947. Exact item equality to model_dump(exclude={"body"}) is proved at :1166.
- AC3 maps to serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:514-525. UUID pre-validation and no-engine-call boundaries are proved at serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:667, :687, and :742. Exact full payload equality is proved at :1191.
- AC4 maps to serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:749-757. readOnlyHint=False and docstring proof is in serve/mcp-kanban/tests/test_mcp_request_tools_1855.py:774 and :782; durable idempotent/readOnly guards align in tests/test_mcp_kanban.py:1585 and :1590.
- AC8 durable surface-contract proof is repaired and now consistent with the live registry: EXPECTED_TOOLS includes the three request tools at serve/mcp-kanban/tests/test_mcp_surface_contract.py:42, and the live twelve-tool contract is exercised at :218.
- Challenger cross-check required by the behavioral proof bundle returned proceed with no blocking weaknesses.

## Observations
- Earlier weaker success-path tests remain in the task suite, but the exact-equality and full-delegation tests now provide the operative proof surface, so they are no longer gating risk.
- No blocking implementation defect or contradictory durable proof remains in the current slice.

[[2026-05-25T23:18:37+02:00]]
## Docs Gate

**Verdict: PASS**

### Convention Mapping
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` → `serve/mcp-kanban/README.md`
- `serve/mcp-kanban/tests/` → `serve/mcp-kanban/README.md`

### Checklist

**Item 1 — README Verification:** Three task-caused issues found and fixed in `serve/mcp-kanban/README.md`:
1. Tool count updated from 9 → 12 (line 19).
2. Added three new tool rows to the tools table: `create_request`, `list_requests`, `show_request` with exact signatures from `server.py:459–525`.
3. Removed false "is read-only" claim for `pick_tasks` (contradicted by AC4 `readOnlyHint=False` change); replaced with accurate description of sweep-request write behaviour.
4. Added lifecycle semantics entries for `create_request`, `list_requests`, `show_request` for audience completeness.

Layer-1 grep: "exposes 12 tools" present; "is read-only" absent; all three new tools present in table and lifecycle section. Layer-2 editorial: README coherent, no contradictions, audience-appropriate.

**Item 2 — External Attribution:** N/A — no external sources cited in builder notes; implementation follows established internal patterns.

**Item 3 — Research Doc:** N/A — no research artifact created for this task.

**Item 4 — Deletion Detection:** N/A — no source files deleted.

### Scratch Cleanup
No scratch files created for task 1855.

[[2026-05-26T00:32:01+02:00]]
## Audit
### Regression Detection
- quality-runner env fallback: pytest full-suite timeout; direct execution used
- mcp-kanban domain: 595 passed, 0 failed (serve/mcp-kanban/tests/ + tests/test_mcp_kanban.py)
- ruff on task-touched paths: clean (exit 0)
- root test suite: 3798 passed, 127 failed, 14 skipped, 5 errors; all failures in unrelated domains (cockpit_view, memory_primitives, manifest_loader, decisions, content_store, storage_re_exports, qdrant_source_identity, cockpit_models); zero overlap with mcp-kanban changes
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changed files in serve/mcp-kanban/ and tests/test_mcp_kanban.py; exclusively mcp-kanban domain)
- purpose match: PASS (adds three MCP request tools and fixes pick_tasks annotation as specified)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
Initial AC was specific for implementation direction (params, error mapping, ToolAnnotations, return shapes, UUID4 validation). However, proof contract specificity required 4 re-scope rounds (AC5-AC8) driven by reviewer findings about weak test assertions. Implementation was correct from the first builder commit; all rework was proof-quality only.

### Commit Integrity
- upstream commit presence: PASS (builder 417245fd, test-writer fcf632c9/447b3039/ae729189/b0485492/697726c2/715dea28)
- doc-writer deliverable: UNCOMMITTED (serve/mcp-kanban/README.md changes verified correct in working tree but not committed; process concern noted per w-task-verification Step 4)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
- AC quality score 3: -.03
- No other rubric deductions (regression PASS, intent PASS, lint PASS, reviewer evidence present and detailed)

### Confidence: .97
### Action: archive
