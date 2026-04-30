---
id: 1221
title: Engine — lazy agent_map validation at pick_tasks only
status: done
priority: needed
created: 2026-04-30 16:31:18.568412+00:00
updated: 2026-04-30T22:50:37.685048+00:00
tags:
- cockpit
- kanban-engine
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-04-30T22:50:37.685048+00:00
archival_reason:
archival_refs: []
---

## Objective
Move agent_map completeness validation from engine __init__ to pick_tasks() so non-dispatcher consumers (cockpit) aren't blocked by incomplete config.

## Acceptance Criteria
- [ ] `KanbanEngine.__init__` no longer raises ConfigError for missing agent_map entries (td:1)
- [ ] `pick_tasks()` validates agent_map completeness at the top of the method, before filtering/sorting/wave assembly — raises `ConfigError(ERR_INVALID_STATUS)` when any status in `config.pipeline.statuses` is absent from `config.agents.agent_map` (td:2)
- [ ] Cockpit starts successfully with `agent_map: {}` in grouped config (td:1)
- [ ] MCP pick_tasks raises ConfigError with missing-entry message when agent_map is incomplete (td:1)

## Files
- `serve/kanban/src/owlbear_kanban/engine.py`

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Moves one validation check from init to use-site |
| Interface clarity | PASS | AC specifies exact error code, location, and invariant |
| Dependency correctness | PASS | No external deps; single-module change |
| Module layering | PASS | Validation stays within engine.py, moves from _validate_engine_config to AgentView.pick_tasks |
| TDD compliance | PASS | Test-writer will create tests for new behavior |
| KISS/YAGNI | PASS | Minimal relocation of existing logic |
| Premise challenge | PASS | Cockpit is blocked by dispatcher-only validation — valid reason to separate concerns |
| Pattern consistency | PASS | Follows validation-at-use-site pattern (similar to wave_size validation already in pick_tasks) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban-engine only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| pick_tasks with empty agent_map | Missing status key in map | ConfigError(ERR_INVALID_STATUS) | Yes — raised before wave assembly | Clear error message, no silent degradation |
| KanbanEngine init with empty agent_map | Previously raised, now passes | N/A | Yes — deferred to pick_tasks | Cockpit unblocked |

### Challenge Results
- Challenger: reconsider (confidence 0.44)
- Concerns: AC2 underspecified placement, test suite contract drift, MCP startup semantics
- Architect response: Accepted AC2 refinement (added "at the top of the method, before filtering/sorting/wave assembly" and explicit invariant definition). Rejected broader concerns — test suites encoding old behavior will be updated by builder (expected for deliberate contract changes). MCP startup benefiting from relaxed init is correct behavior.

### Test Depth
- Max depth: 2 (AC2 has error path + success path)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC2 for placement and invariant precision, approved to todo

[[2026-04-30]]
Architecture review complete. Refined AC2 to specify validation placement (top of pick_tasks, before wave assembly) and exact invariant (every status in config.pipeline.statuses must have a key in agent_map). Challenger raised concerns about test suite contract drift and MCP startup — accepted AC precision refinement, rejected broader concerns as expected consequences of deliberate contract change. All 10 criteria PASS.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_engine_lazy_agent_map_1221.py
- Classes: TestFromAC_InitNoLongerRaises, TestFromAC_PickTasksValidatesAgentMap, TestFromAC_CockpitInitWithEmptyAgentMap, TestFromAC_McpPickTasksRaisesForIncompleteAgentMap
- Tests per category: happy 0, edge 2, error 7, boundary 2
- Total: 11 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1: __init__ no longer raises for missing agent_map | test_init_accepts_empty_agent_map, test_init_accepts_partial_agent_map |
| AC2: pick_tasks raises ConfigError(ERR_INVALID_STATUS) at top, before filtering | test_pick_tasks_raises_config_error_for_empty_agent_map, test_pick_tasks_raises_config_error_for_partial_agent_map, test_pick_tasks_error_code_is_err_invalid_status, test_pick_tasks_error_message_names_missing_statuses, test_pick_tasks_validates_before_filtering_with_tasks_present |
| AC3: Cockpit starts with agent_map: {} | test_cockpit_engine_init_succeeds_with_empty_agent_map, test_cockpit_engine_board_config_accessible_with_empty_agent_map |
| AC4: MCP pick_tasks raises ToolError (from ConfigError) for incomplete agent_map | test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map, test_mcp_pick_tasks_tool_error_message_contains_missing_entries |

RED strategy:
- AC1/AC3 tests: fail at KanbanEngine.__init__ (currently raises ConfigError for missing agent_map)
- AC2/AC4 tests: fail because pick_tasks() does not yet validate agent_map; tests use refresh_config() to inject incomplete config without triggering init validation
[[2026-04-30]]
## Builder Notes
- Blocked before implementation: required quality-runner precheck could not execute due workspace TOML parse failure.
- quality-runner error: duplicate key `dependencies` in `serve/cockpit/pyproject.toml` (line 7), which prevents pytest/ruff execution via uv.
- No code changes made.
- Cannot verify RED baseline or GREEN gate until the pyproject error is fixed.
[[2026-04-30]]
## Builder Notes
- Implementation: moved `agent_map` completeness validation from `KanbanEngine.__init__` to the top of `AgentView.pick_tasks` in `serve/kanban/src/owlbear_kanban/engine.py`.
- Behavior change:
  - `KanbanEngine.__init__` no longer raises `ConfigError(ERR_INVALID_STATUS)` when `agent_map` is incomplete.
  - `pick_tasks()` now raises `ConfigError(ERR_INVALID_STATUS)` with message `agent_map missing status entries: [...]` before filtering/sorting/wave assembly when any pipeline status is missing from `agent_map`.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- Commit: `151ab35d5a37a7bd00b63574f98de42ebe5c2837`
- RED verification (quality-runner): 11 failed / 0 passed in `tests/test_engine_lazy_agent_map_1221.py` before implementation.
- GREEN verification (quality-runner): 11 passed / 0 failed in `tests/test_engine_lazy_agent_map_1221.py`.
- Lint (quality-runner): clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_lazy_agent_map_1221.py`.
- Coverage (quality-runner, scoped run): `owlbear_kanban.engine` at 13% with task-scoped tests.
- Evidence summary: AC1/AC3 now pass via lazy init behavior; AC2 enforced at `pick_tasks` method entry with required error code/message; AC4 passes because MCP `pick_tasks` surfaces engine `ConfigError` as `ToolError` via existing mapping.

Post-task reflection:
- Moving validation to use-site prevented non-dispatch consumers (cockpit) from being blocked by dispatcher-only invariants.
- Keeping the same error code/message contract avoided ripple changes in MCP error mapping.
- Scoped coverage is low on a large module; AC-focused tests still fully validate the changed behavior path.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner (task suite): pytest 11 passed, 0 failed, 0 skipped in `tests/test_engine_lazy_agent_map_1221.py`
- quality-runner (regression spot-check): pytest 71 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_engine_pick_tasks_1074.py` and `serve/mcp-kanban/tests/test_mcp_read_tools.py`

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_lazy_agent_map_1221.py`

### Coverage
- task-scoped coverage reported `owlbear_kanban.engine` at 13% module-wide. This is informational only for this large module; the changed error path is exercised by the task suite and adjacent success-path suites remain green.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `KanbanEngine.__init__` no longer raises for missing `agent_map` entries | `test_init_accepts_empty_agent_map`, `test_init_accepts_partial_agent_map` | Yes. Constructor still calls `_validate_engine_config`, but that helper no longer contains the `agent_map` completeness check. A constructor-time regression would fail these tests. | COVERED |
| AC2: `pick_tasks()` validates completeness at top of method, before filtering/sorting/wave assembly, raising `ERR_INVALID_STATUS` | `test_pick_tasks_raises_config_error_for_empty_agent_map`, `test_pick_tasks_raises_config_error_for_partial_agent_map`, `test_pick_tasks_error_code_is_err_invalid_status`, `test_pick_tasks_error_message_names_missing_statuses`, `test_pick_tasks_validates_before_filtering_with_tasks_present` | Partially. The raise/code behavior is covered, but the placement proof is lax: the placement test only proves that `ConfigError` eventually occurs, not that filtering/sorting/wave assembly were skipped. | LAX |
| AC3: Cockpit starts successfully with `agent_map: {}` | `test_cockpit_engine_init_succeeds_with_empty_agent_map`, `test_cockpit_engine_board_config_accessible_with_empty_agent_map` | Yes for the task-scoped root cause. Cockpit startup constructs `KanbanEngine(..., agent_name="cockpit")` before startup work proceeds. If init still raised, these tests would fail. | COVERED |
| AC4: MCP `pick_tasks` raises missing-entry error when `agent_map` is incomplete | `test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map`, `test_mcp_pick_tasks_tool_error_message_contains_missing_entries` | Partially. The ToolError raise path is covered, but the missing-entry message assertion is lax: any one of several substrings is accepted. | LAX |

#### Security Review
- No issues found. The change is a local config completeness check in `serve/kanban/src/owlbear_kanban/engine.py` and existing MCP error mapping still forwards `KanbanError.user_message` via `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` coverage in the current snapshot. The current task test file still contains all four AC families recorded in the test-writer note.
- Small confidence deduction only: the available toolset did not expose a direct commit diff, so integrity was verified from the current snapshot, builder notes, and reflog evidence rather than a raw diff.

#### Test Quality
- FAIL: assertion specificity is weak in `tests/test_engine_lazy_agent_map_1221.py:276` and `tests/test_engine_lazy_agent_map_1221.py:391`. Both message checks use permissive substring-any assertions, so wrong messages can still pass.
- FAIL: AC2 placement proof is weak in `tests/test_engine_lazy_agent_map_1221.py:284`. That test proves eventual failure, not that validation happens before filtering, sorting, or wave assembly.
- Remaining dimensions are acceptable: names are descriptive, tests are independent (`tmp_path` boards + fresh engine instances), and negative/error-path coverage is present.

#### Data Safety
- No issues found.

#### Implementation-Aware Test Gap Analysis
- No implementation defect found in the reviewed code.
- Constructor path: `KanbanEngine.__init__` still calls `_validate_engine_config` in `serve/kanban/src/owlbear_kanban/engine.py:437`, and the helper body in `serve/kanban/src/owlbear_kanban/engine.py:112` no longer checks `agent_map` completeness.
- Validation placement: `pick_tasks()` now computes `missing_statuses` and raises `ConfigError(ERR_INVALID_STATUS)` in `serve/kanban/src/owlbear_kanban/engine.py:2330` before decision resolution, task scan/filtering, sorting, and wave assembly.
- Adjacent regression spot-check remained green: existing engine/MCP pick_tasks suites passed 71/71.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- FRICTION, not LOOP. There are two builder-note sections: the first was blocked by an external workspace TOML parse error; the second completed after that environment issue was cleared. No repeated identical repair loop is evident.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_validate_engine_config` no longer enforces `agent_map` completeness (`serve/kanban/src/owlbear_kanban/engine.py:112`), constructor still uses the helper (`serve/kanban/src/owlbear_kanban/engine.py:437`), and task tests passed. | `test_init_accepts_empty_agent_map`, `test_init_accepts_partial_agent_map` | PASS |
| AC2 | Guard now exists at `serve/kanban/src/owlbear_kanban/engine.py:2330` with `ERR_INVALID_STATUS` / `agent_map missing status entries: [...]`, before later `pick_tasks` stages; task tests passed. | `test_pick_tasks_*` group | PASS |
| AC3 | Cockpit startup path constructs `KanbanEngine(..., agent_name="cockpit")` in `serve/cockpit/src/owlbear_cockpit/main.py:72`; task tests passed for empty-map grouped config. | `test_cockpit_engine_init_succeeds_with_empty_agent_map`, `test_cockpit_engine_board_config_accessible_with_empty_agent_map` | PASS |
| AC4 | MCP `pick_tasks` maps `KanbanError.user_message` directly into `ToolError` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:74`; task tests passed and adjacent MCP read-tool suites stayed green. | `test_mcp_pick_tasks_*` group | PASS |

### Deductions
- `-0.10` AC2 placement proof is not binding enough for the stated "top of method / before filtering-sorting-wave assembly" contract.
- `-0.05` AC4 message assertion is too permissive to prove the intended missing-entry message contract.
- `-0.02` No direct commit diff available in current toolset; integrity evidence relied on current snapshot + reflog + task notes.

### Verdict
- FAIL
- Confidence: 0.83
- Action: reject to `todo`.

### Required Follow-up
1. Strengthen AC2 so the test fails if validation happens after filtering, sorting, or wave assembly. A non-call or ordered-call proof is needed; eventual `ConfigError` is not enough.
2. Strengthen AC4 message proof to assert the exact propagated missing-entry content (or the exact expected missing-status set), not any-substring membership.
3. Keep the current source change unless stronger tests expose a real behavioral mismatch.

### Post-task Reflection
- Implementation matched the task contract; the gate failed on proof quality, not source behavior.
- Adjacent engine/MCP pick_tasks suites are useful to separate regression risk from task-owned proof weakness.
- Weak substring assertions remain a recurring false-green pattern in reviewer work.
- Lack of direct diff access adds minor confidence cost; current-snapshot + reflog verification is workable but weaker than a raw diff.
[[2026-04-30]]
## Test-Writer Notes
- Retry: strengthened 2 weak assertions cited by reviewer. All 13 tests pass against current impl — builder skip applied.
- Test file: tests/test_engine_lazy_agent_map_1221.py
- Classes: TestFromAC_InitNoLongerRaises, TestFromAC_PickTasksValidatesAgentMap, TestFromAC_CockpitInitWithEmptyAgentMap, TestFromAC_McpPickTasksRaisesForIncompleteAgentMap
- Tests per category: happy 0, edge 2, error 9, boundary 2
- Total: 13 tests, all PASS (green against existing implementation)
- ruff: clean
- Commit: 62c1fed8

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1: __init__ no longer raises | test_init_accepts_empty_agent_map, test_init_accepts_partial_agent_map |
| AC2: pick_tasks validates at top, before filtering | test_pick_tasks_raises_config_error_for_empty_agent_map, test_pick_tasks_raises_config_error_for_partial_agent_map, test_pick_tasks_error_code_is_err_invalid_status, test_pick_tasks_error_message_names_missing_statuses, test_pick_tasks_validates_before_filtering_with_tasks_present, **test_pick_tasks_validates_before_list_tasks_is_called** (new — non-call ordering proof) |
| AC3: Cockpit starts with empty agent_map | test_cockpit_engine_init_succeeds_with_empty_agent_map, test_cockpit_engine_board_config_accessible_with_empty_agent_map |
| AC4: MCP raises ToolError with exact missing-entry message | test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map, test_mcp_pick_tasks_tool_error_message_contains_missing_entries, **test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses** (new — asserts all 4 missing statuses individually) |

Retry changes:
- Added test_pick_tasks_validates_before_list_tasks_is_called: monkeypatches engine.list_tasks with a spy; asserts spy call count == 0 after ConfigError is raised — proves ordering without relying on eventual exception alone.
- Added test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses: asserts each of ('todo', 'in-progress', 'review', 'done') individually in the ToolError string — replaces permissive any() check.
- Builder skip: test-only retry, all 13 tests pass against current implementation.

[[2026-04-30]]
## Builder Notes
- Scope: non-implementation builder pass-through after test-writer retry; no source or test edits were required in this invocation.
- Verification (quality-runner, scoped): 13 passed, 0 failed, 0 skipped in tests/test_engine_lazy_agent_map_1221.py.
- Lint: clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_engine_lazy_agent_map_1221.py.
- Coverage: module report shows owlbear_kanban.engine at 13% (overall scoped run 22%); this is informational for the large module and unchanged from prior task evidence.
- Evidence summary: AC-targeted tests remain green, including strengthened ordering/message assertions from the retry, so behavior is stable for review.

Post-task reflection:
- Test-only retries can leave tasks in in-progress even when implementation is already correct; fresh independent verification keeps the gate reliable.
- Scoped quality-runner output is sufficient to confirm no regression in the task-owned contract.
- Coverage percentage at module granularity can under-represent AC-path validation in very large files; pairing with explicit AC-mapped tests is important.
[[2026-04-30]]
## Review Evidence
### Test Results
- quality-runner (task suite): pytest 13 passed, 0 failed, 0 skipped in tests/test_engine_lazy_agent_map_1221.py
- quality-runner (regression spot-check): pytest 70 passed, 0 failed, 0 skipped across tests/test_cockpit_launch.py and serve/mcp-kanban/tests/test_mcp_read_tools.py

### Lint
- clean for serve/kanban/src/owlbear_kanban/engine.py and tests/test_engine_lazy_agent_map_1221.py

### Coverage
- task-scoped coverage reported owlbear_kanban.engine at 13% module-wide. Informational only for this large module; the changed guard path is directly exercised by the task suite.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: KanbanEngine.__init__ no longer raises ConfigError for missing agent_map entries | tests/test_engine_lazy_agent_map_1221.py:190 and tests/test_engine_lazy_agent_map_1221.py:349 against serve/kanban/src/owlbear_kanban/engine.py:446 and serve/kanban/src/owlbear_kanban/engine.py:112 | Yes. Reintroducing constructor-time agent_map completeness validation would fail both plain-engine and cockpit-labeled init tests. | COVERED |
| AC2: pick_tasks validates agent_map completeness at the top of the method, before filtering/sorting/wave assembly, and raises ERR_INVALID_STATUS | tests/test_engine_lazy_agent_map_1221.py:249 and tests/test_engine_lazy_agent_map_1221.py:304 against serve/kanban/src/owlbear_kanban/engine.py:2330, serve/kanban/src/owlbear_kanban/engine.py:2336, and serve/kanban/src/owlbear_kanban/engine.py:2345 | Yes. The suite binds the error code/message and now proves list_tasks is never called when validation fails, so moving the guard below filtering would fail. | COVERED |
| AC3: Cockpit starts successfully with agent_map: {} in grouped config | tests/test_engine_lazy_agent_map_1221.py:349 and tests/test_engine_lazy_agent_map_1221.py:358, plus serve/cockpit/src/owlbear_cockpit/main.py:72 and regression tests/test_cockpit_launch.py:438 / tests/test_cockpit_launch.py:473 | Yes for the task’s stated root cause. Cockpit startup reaches KanbanEngine(..., agent_name="cockpit") before uvicorn; a constructor-time regression would fail the task tests and break the durable startup path. | COVERED |
| AC4: MCP pick_tasks surfaces the missing-entry failure with the missing-status message when agent_map is incomplete | tests/test_engine_lazy_agent_map_1221.py:378 and tests/test_engine_lazy_agent_map_1221.py:431, plus serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:74 and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:658 | Yes at the MCP boundary. The handler maps KanbanError/ConfigError to ToolError using user_message, and the task suite now asserts ToolError plus all missing statuses individually. | COVERED |

#### Security Review
- No issues found. The change is a local config completeness guard that raises before task enumeration or dispatch assembly.

#### Test Integrity
- No evidence of weakened or removed TestFromAC coverage in the current snapshot.
- Reflog confirms the scoped commits cited in the task body: implementation commit 151ab35d5a37a7bd00b63574f98de42ebe5c2837 and test-strengthening commit 62c1fed8b0427ee04feb949495f03ad8fa8e461b.

#### Test Quality
- Assertion specificity: STRONG. AC2 now has a non-call ordering proof at tests/test_engine_lazy_agent_map_1221.py:304; AC4 now asserts all four missing statuses at tests/test_engine_lazy_agent_map_1221.py:431.
- Negative/error-path coverage: STRONG. Empty-map and partial-map paths are both exercised for engine and MCP boundaries.
- Manual mutation reasoning: ADEQUATE. Reintroducing init-time validation, removing the ERR_INVALID_STATUS code, moving the guard below list_tasks, or dropping missing-status names from the MCP error would fail named tests.
- Test independence and naming: STRONG.

#### Data Safety
- No issues found.

#### Implementation-Aware Gap Analysis
- No significant untested path within AC scope. The moved guard is present in serve/kanban/src/owlbear_kanban/engine.py:2330 before the first list/filter stage at serve/kanban/src/owlbear_kanban/engine.py:2345, and adjacent cockpit/MCP regression suites remain green.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- code-reader flagged AC3/AC4 as lax when read only from the top checklist wording. I did not treat that as blocking because the latest task body, the live cockpit startup path, and the MCP adapter contract narrow the actual runtime contract: cockpit is unblocked by constructor success, and MCP surfaces engine ConfigError as ToolError with the same user_message.
- Top-level AC4 wording could be sharpened in a future task to say ToolError-from-ConfigError explicitly at the MCP boundary.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | _validate_engine_config still runs at init (serve/kanban/src/owlbear_kanban/engine.py:446) but the moved agent_map check now lives in pick_tasks, not init. Task tests pass. | test_init_accepts_empty_agent_map; test_init_accepts_partial_agent_map | PASS |
| AC2 | Guard computes missing_statuses and raises ERR_INVALID_STATUS/message at serve/kanban/src/owlbear_kanban/engine.py:2330-2336 before list_tasks at serve/kanban/src/owlbear_kanban/engine.py:2345. Task tests pass. | test_pick_tasks_error_code_is_err_invalid_status; test_pick_tasks_validates_before_list_tasks_is_called | PASS |
| AC3 | Cockpit startup constructs KanbanEngine(..., agent_name="cockpit") at serve/cockpit/src/owlbear_cockpit/main.py:72; task tests prove empty agent_map no longer blocks that constructor path; cockpit launch regression suite passes. | test_cockpit_engine_init_succeeds_with_empty_agent_map; test_cockpit_engine_board_config_accessible_with_empty_agent_map | PASS |
| AC4 | MCP pick_tasks catches KanbanError and maps user_message to ToolError via serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:74 and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:658; task tests assert ToolError and all missing statuses. | test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map; test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses | PASS |

### Deductions
- -0.03 AC3 proof is composite (task-owned constructor tests plus durable cockpit startup regression tests) rather than a single dedicated run()-with-empty-agent_map task test.
- -0.02 Test integrity was verified from current snapshot plus reflog commit presence rather than a raw diff view.

### Confidence: 0.95
### Verdict: PASS
### Action: advance to docs

### Post-task Reflection
- The prior review failure was resolved by test-proof strengthening; no further source change was needed.
- Boundary ACs required reading the live cockpit and MCP adapters, not just the task-owned test file.
- Reflog search is an acceptable fallback for commit presence when raw diff access is unavailable, but it should carry a small confidence cost.
[[2026-04-30]]
## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | Yes | PASS | Two `## Review Evidence` sections present; second is the retry reviewer pass, verdict PASS |
| 0b | Doc-index loaded | Yes | PASS | `.owlbear/doc-index.md` read |
| 1 | Prose docs | Yes | UPDATED | `serve/kanban/README.md` — two stale claims corrected (see below) |
| 2 | Module docstrings | Yes | UPDATED | `serve/kanban/src/owlbear_kanban/engine.py` — `pick_tasks` docstring updated |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc in task body |
| 5 | Diagram maintenance | Yes | UPDATED | `share/diagrams/kanban.excalidraw` describes `serve/kanban/src/**` — footer updated to `2026-05-01 (927cce5a)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request |
| 7 | Deletion detection | No | N/A | No deleted files |

### Files Updated
- `serve/kanban/README.md` — (1) `pick_tasks` pipeline description now mentions the upfront `agent_map` completeness validation guard before the five-step pipeline; (2) migration note corrected from "before starting the engine" to "engine starts fine with empty agent_map, but `pick_tasks` raises `ConfigError(ERR_INVALID_STATUS)` until the map is complete"
- `serve/kanban/src/owlbear_kanban/engine.py` — `pick_tasks` docstring: added pre-pipeline validation description, updated `Raises` section to include `ConfigError(ERR_INVALID_STATUS)` for incomplete agent_map
- `share/diagrams/kanban.excalidraw` — footer updated from `f584b298` to `927cce5a`

### Commit
`0de43485` — docs: update pick_tasks docs for lazy agent_map validation (#1221, doc-writer)

### Scratch Files
None — no `1221-*` scratch files found.