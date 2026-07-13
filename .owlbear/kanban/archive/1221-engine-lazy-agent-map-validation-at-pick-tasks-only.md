---
id: 1221
title: Engine — lazy agent_map validation at pick_tasks only
status: archived
priority: medium
created: 2026-04-30 16:31:18.568412+00:00
updated: 2026-05-01T03:18:38.465932+00:00
tags:
- cockpit
- kanban-engine
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Move agent_map completeness validation from engine __init__ to pick_tasks() so non-dispatcher consumers (cockpit) aren't blocked by incomplete config.

## Acceptance Criteria
- [ ] `KanbanEngine.__init__` no longer raises ConfigError for missing agent_map entries (td:1)
- [ ] `pick_tasks()` validates agent_map completeness immediately after the effective-wave-size guard, before the `resolve_pending_drs` call and before filtering/sorting/wave assembly — raises `ConfigError(ERR_INVALID_STATUS)` when any status in `config.pipeline.statuses` is absent from `config.agents.agent_map` (td:2)
- [ ] Cockpit starts successfully with `agent_map: {}` in grouped config (td:1)
- [ ] MCP pick_tasks raises ConfigError with missing-entry message when agent_map is incomplete (td:1)
- [ ] `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` updated to assert that `_validate_engine_config` does NOT raise when `agent_map` is incomplete — the completeness check was moved to `pick_tasks`; `_validate_engine_config` no longer validates agent_map coverage (td:1)

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
[[2026-04-30]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `__init__` no longer raises ConfigError for missing agent_map entries | `_validate_engine_config` at engine.py:112 no longer contains agent_map check; constructor still calls helper at engine.py:446; task tests pass. | PASS |
| AC2: `pick_tasks()` validates at top before filtering/sorting/wave assembly, raises `ERR_INVALID_STATUS` | Guard at engine.py:2330–2336; `test_pick_tasks_validates_before_list_tasks_is_called` proves ordering via monkeypatched list_tasks (call count == 0 after ConfigError). | PASS |
| AC3: Cockpit starts with `agent_map: {}` in grouped config | Cockpit startup path constructs `KanbanEngine(..., agent_name="cockpit")` at cockpit/main.py:72; task tests pass; cockpit launch regression suite passed. | PASS |
| AC4: MCP `pick_tasks` surfaces missing-entry ConfigError as ToolError | MCP adapter at server.py:74/658 maps KanbanError.user_message → ToolError; `test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses` asserts all 4 missing statuses individually. | PASS |

### Test Results
- **Full suite (quality-runner):** 3510 passed, 138 failed, 8 skipped — pytest exit 1
- **Task suite:** 13 passed, 0 failed (tests/test_engine_lazy_agent_map_1221.py) — green
- **Lint:** clean (engine.py, task test file, serve/kanban/README.md)
- **Coverage DB:** corruption detected during report; does not affect pass/fail verdict

### Full-Suite Regression Analysis
Of the 138 failures, 137 are pre-existing failures from other in-flight tasks (#1223 sessions envelope, #1202, #1201, #1225, task 1068 other tests, etc.) that pre-date or are independent of #1221.

**1 failure is directly caused by #1221:**
- `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises`

This test (last modified by task #1174's builder at 3fc7f105 — before #1221) asserts that `KanbanEngine.__init__` raises `ConfigError` matching `"agent_map"` when entries are missing. After commit 151ab35d, `__init__` deliberately no longer raises → test fails. This is a cross-task regression introduced by #1221's implementation. The builder changed engine.py but did not update the stale test from task #1068.

The architect's notes acknowledged "test suites encoding old behavior will be updated by builder" — this did not happen for test_engine_coverage_1068.py.

### Commit Integrity
- 151ab35d — `fix: defer agent_map validation to pick_tasks (#1221, builder)` — engine.py only, 20+/8− lines ✓
- 62c1fed8 — `test: strengthen AC2 ordering proof and AC4 exact message assertion (#1221, test-writer)` — task test file only, 65 insertions ✓
- 0de43485 — `docs: update pick_tasks docs for lazy agent_map validation (#1221, doc-writer)` — README.md, engine.py (docstring), kanban.excalidraw ✓

### Architect Quality: 4/5
AC is specific, placement-constrained, and well-scoped. Minor gap: AC1 did not note that existing init-time agent_map validation tests (test_engine_coverage_1068.py) needed migration/removal as part of the deliberate contract change. This omission contributed to the builder leaving a stale test.

### Deductions
| Criterion | Deduction |
|-----------|-----------|
| Cross-task regression: test_engine_coverage_1068.py::test_agent_map_missing_status_raises broken by 151ab35d | −0.05 |
| No direct diff access; integrity verified via current snapshot + reflog | −0.02 |

### Confidence: 0.93

### Action: Reject to backlog

**Required fix:** Update `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` to reflect the new contract: assert that `__init__` does NOT raise for incomplete agent_map, or convert the test to verify that `pick_tasks` raises instead. No source change should be needed.
[[2026-05-01]]
## Architecture Review (Round 2)
### Context
Task returned from auditor via backlog-reject. Auditor required: update stale test in `test_engine_coverage_1068.py`. Implementation also regressed — a concurrent in-flight task overwrote `engine.py`; current live code still has the agent_map check in `_validate_engine_config` (line 143) and `pick_tasks` has no guard. Builder must re-implement.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same as Round 1 — one validation moved from init to use-site |
| Interface clarity | PASS | AC2 refined: placement now specifies "after effective-wave-size guard, before resolve_pending_drs" |
| Dependency correctness | PASS | Single-module change, no new deps |
| Module layering | PASS | Validation stays in engine.py |
| TDD compliance | PASS | Tests in test_engine_lazy_agent_map_1221.py exist (currently RED due to implementation regression) |
| KISS/YAGNI | PASS | No scope change |
| Premise challenge | PASS | Cockpit blocking remains the valid reason; unchanged |
| Pattern consistency | PASS | Validation-at-use-site, same as wave_size check |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban-engine only |

### AC Refinements Applied
| AC | Change | Reason |
|----|--------|--------|
| AC2 | Added "immediately after the effective-wave-size guard, before the `resolve_pending_drs` call" to pin exact placement | Challenger: prior wording left placement ambiguous relative to resolve_pending_drs |
| AC5 (new) | `test_engine_coverage_1068.py::test_agent_map_missing_status_raises` must assert non-raising for incomplete agent_map | Auditor required fix; challenger confirmed it was only in rejection notes, not the AC block |

### Implementation Regression Note
Live `engine.py` has the agent_map check at `_validate_engine_config:143` and `pick_tasks` has no guard (concurrent task overwrote the change). Builder must re-implement from scratch. The 13 tests in `test_engine_lazy_agent_map_1221.py` are currently RED — correct RED baseline for builder.

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Concerns: AC5 not in AC block, AC2 placement ambiguous vs resolve_pending_drs, live code regressed
- Architect response: Accepted all three — added AC5 to AC block, refined AC2 placement, noted implementation regression. Design itself unchanged and sound.

### Test Depth
- Max depth: 2 (AC2)
- Test-writer: PROCEED (validate existing tests are RED; add AC5 test to test_engine_coverage_1068.py)

### Verdict: APPROVE (after REFINE)
### Action Taken: Added AC5, refined AC2 placement, noted implementation regression; approved to todo
[[2026-04-30]]
## Architecture Review (Round 2) — Summary

REFINE → APPROVE.

AC changes:
- AC2 refined: placement now explicitly "immediately after the effective-wave-size guard, before the `resolve_pending_drs` call" — pins exact location in pick_tasks.
- AC5 added: `test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` must be updated to assert non-raising for incomplete agent_map (td:1). This was the auditor's required fix; challenger confirmed it was only in the rejection note, not the AC block.

Implementation regression detected: concurrent task overwrote `engine.py`; live code still has agent_map check in `_validate_engine_config:143` and `pick_tasks` has no guard. The 13 task tests are currently RED — correct baseline. Builder must re-implement from scratch.

Challenger: reconsider (0.56) — accepted all three concerns; all resolved by AC refinements above.

All 10 criteria PASS. Design sound and unchanged.

[[2026-05-01]]
## Test-Writer Notes
- Retry (Round 2 arch review): existing 13 tests verified RED + AC5 test updated in separate file.
- Test files:
  - `tests/test_engine_lazy_agent_map_1221.py` — 13 tests (unchanged, all RED due to implementation regression)
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` — updated to assert non-raising (RED: currently raises ConfigError)
- Classes: TestFromAC_InitNoLongerRaises, TestFromAC_PickTasksValidatesAgentMap, TestFromAC_CockpitInitWithEmptyAgentMap, TestFromAC_McpPickTasksRaisesForIncompleteAgentMap
- Tests per category: happy 0, edge 2, error 9, boundary 2 (unchanged 1221 file) + 1 AC5 update
- Total: 14 tests, all FAIL
- ruff: clean (serve/kanban/tests/test_engine_coverage_1068.py)

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1: __init__ no longer raises | test_init_accepts_empty_agent_map, test_init_accepts_partial_agent_map |
| AC2: pick_tasks validates at top, before wave assembly | test_pick_tasks_raises_config_error_for_empty_agent_map, test_pick_tasks_raises_config_error_for_partial_agent_map, test_pick_tasks_error_code_is_err_invalid_status, test_pick_tasks_error_message_names_missing_statuses, test_pick_tasks_validates_before_filtering_with_tasks_present, test_pick_tasks_validates_before_list_tasks_is_called |
| AC3: Cockpit starts with empty agent_map | test_cockpit_engine_init_succeeds_with_empty_agent_map, test_cockpit_engine_board_config_accessible_with_empty_agent_map |
| AC4: MCP raises ToolError with all missing statuses named | test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map, test_mcp_pick_tasks_tool_error_message_contains_missing_entries, test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses |
| AC5: test_engine_coverage_1068.py::test_agent_map_missing_status_raises asserts non-raising | updated in-place — old `pytest.raises(ConfigError)` replaced with plain call, RED because impl still raises |

Round 2 scope: no new tests written; existing 13 remain RED from implementation regression. AC5 required updating stale test in test_engine_coverage_1068.py from expects-raise to expects-no-raise (now RED, will green after builder removes agent_map check from _validate_engine_config).
[[2026-05-01]]
## Builder Notes
- Implementation: moved `agent_map` completeness validation out of `_validate_engine_config` and into `AgentView.pick_tasks` immediately after effective-wave-size validation and before `resolve_pending_drs` in `serve/kanban/src/owlbear_kanban/engine.py`.
- Contract update: `pick_tasks` docstring now reflects the upfront validation step and `ConfigError(ERR_INVALID_STATUS)` raise condition for incomplete `agent_map`.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- Commit: `062b2644c8d664abc224da5a71b2774c8fc53e36`
- RED verification (quality-runner): task-owned tests were failing before implementation (constructor raised on incomplete map; pick_tasks missing guard).
- GREEN verification (quality-runner, scoped): 14 passed, 0 failed, 0 skipped for:
  - `tests/test_engine_lazy_agent_map_1221.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises`
- Lint (quality-runner): clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_lazy_agent_map_1221.py`, and `serve/kanban/tests/test_engine_coverage_1068.py`.
- Coverage (quality-runner scoped): `owlbear_kanban.engine` 13% (module-wide in a large file); AC-targeted paths for moved validation are covered by the 14 passing task-owned tests.
- Regression spot-check (quality-runner): 71 passed, 0 failed across `serve/kanban/tests/test_engine_pick_tasks_1074.py` and `serve/mcp-kanban/tests/test_mcp_read_tools.py`.

Post-task reflection:
- Concurrent edits had restored constructor-time validation; re-applying the invariant at the pick-time boundary resolves cockpit/init blocking while preserving dispatch safety.
- Tight scoping of the AC5 node test avoids unrelated legacy failures in `test_engine_coverage_1068.py` from obscuring task-owned proof.
- Moving the check without changing error code/message keeps MCP adapter behavior stable and avoids downstream contract churn.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner (task-owned scoped run): pytest 14 passed, 0 failed, 0 skipped for `tests/test_engine_lazy_agent_map_1221.py` and `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises`
- quality-runner (broader legacy sweep, context only): pytest 234 passed, 7 failed when the whole `serve/kanban/tests/test_engine_coverage_1068.py` file was included. Those failures were unrelated legacy reds; gating uses the scoped rerun above.

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_lazy_agent_map_1221.py`, and `serve/kanban/tests/test_engine_coverage_1068.py`

### Coverage
- task-scoped coverage reported `owlbear_kanban.engine` at 13% module-wide. Informational only for this large module; the verdict is driven by AC proof quality, not the module aggregate.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `KanbanEngine.__init__` no longer raises `ConfigError` for missing `agent_map` entries | `tests/test_engine_lazy_agent_map_1221.py::test_init_accepts_empty_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_init_accepts_partial_agent_map` | Yes. Reintroducing constructor-time `agent_map` completeness validation would fail both init tests. | COVERED |
| AC2: `pick_tasks()` validates completeness immediately after the effective-wave-size guard, before `resolve_pending_drs`, before filtering/sorting/wave assembly, and raises `ERR_INVALID_STATUS` | `tests/test_engine_lazy_agent_map_1221.py::test_pick_tasks_*` group | No for the full AC. The suite proves `ConfigError` presence, error code/message, and pre-`list_tasks` ordering, but it does not prove the guard remains before `resolve_pending_drs`, and it does not prove the guard remains after the effective-wave-size check when both conditions are invalid. | MISSING |
| AC3: Cockpit starts successfully with `agent_map: {}` in grouped config | `tests/test_engine_lazy_agent_map_1221.py::test_cockpit_engine_init_succeeds_with_empty_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_cockpit_engine_board_config_accessible_with_empty_agent_map` | Yes for the engine-owned startup gate. If init still rejected incomplete maps, cockpit construction would fail. | COVERED |
| AC4: MCP `pick_tasks` raises the missing-entry error when `agent_map` is incomplete | `tests/test_engine_lazy_agent_map_1221.py::test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses` | Yes. The tests require the MCP boundary to surface the engine error and name all missing statuses. | COVERED |
| AC5: `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` now asserts non-raising for incomplete `agent_map` | `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` | Yes. Restoring `agent_map` completeness validation inside `_validate_engine_config` would fail this test immediately. | COVERED |

#### Security Review
- No issues found. The change is a local config completeness guard with no new external sink.

#### Test Integrity
- No evidence of weakened or removed `TestFromAC_*` assertions in the current snapshot.
- Reflog confirms the cited task commits exist: `62c1fed8b0427ee04feb949495f03ad8fa8e461b` (test-writer) and `062b2644c8d664abc224da5a71b2774c8fc53e36` (builder).
- Small confidence deduction only: direct raw diff access was not available, so integrity was verified from the current snapshot, task notes, and reflog evidence.

#### Test Quality
- FAIL: AC2 ordering proof is still incomplete. `tests/test_engine_lazy_agent_map_1221.py:304` only proves `list_tasks` is not called; it does not observe `resolve_pending_drs`.
- FAIL: no task-owned test covers the conflict case where `effective_wave < 1` and `agent_map` is incomplete, so the refined “immediately after the effective-wave-size guard” ordering is not mutation-resistant.
- Remaining dimensions are acceptable: assertions for AC1/AC3/AC4/AC5 are specific, names are mostly descriptive, and tests are independent.

#### Data Safety
- No issues found.

#### Implementation-Aware Gap Analysis
- No implementation defect found in the live source.
- `_validate_engine_config` no longer checks `agent_map` completeness at `serve/kanban/src/owlbear_kanban/engine.py:114`.
- `KanbanEngine.__init__` still uses that validator at `serve/kanban/src/owlbear_kanban/engine.py:439`.
- `pick_tasks` now performs the moved check at `serve/kanban/src/owlbear_kanban/engine.py:2333` after the wave guard at `serve/kanban/src/owlbear_kanban/engine.py:2327`, before `resolve_pending_drs` at `serve/kanban/src/owlbear_kanban/engine.py:2348`, and before `list_tasks` at `serve/kanban/src/owlbear_kanban/engine.py:2352`.
- Because the source matches the contract, this gate fails on proof quality only.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- FRICTION, not LOOP. The task body contains multiple builder sections across retries, but the approaches changed (environment block, initial implementation, pass-through after test-only retry, re-implementation after concurrent overwrite). No repeated identical repair loop is evident.

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_coverage_1068.py:260` still carries the old `...raises` test name even though the body now asserts the opposite. That is naming drift only; not a blocking issue.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_validate_engine_config` at `serve/kanban/src/owlbear_kanban/engine.py:114` no longer enforces `agent_map` completeness, while `__init__` still calls it at `serve/kanban/src/owlbear_kanban/engine.py:439`; scoped tests passed. | init tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC2 | Live guard raises `ERR_INVALID_STATUS` from `serve/kanban/src/owlbear_kanban/engine.py:2333-2339`, after the wave guard at `serve/kanban/src/owlbear_kanban/engine.py:2327` and before `resolve_pending_drs` / `list_tasks` at `serve/kanban/src/owlbear_kanban/engine.py:2348` / `:2352`; scoped tests passed. | `test_pick_tasks_*` group | PASS |
| AC3 | Cockpit startup constructs `KanbanEngine(..., agent_name="cockpit")` at `serve/cockpit/src/owlbear_cockpit/main.py:72`; scoped tests passed. | cockpit tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC4 | MCP maps `KanbanError.user_message` to `ToolError` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:76`, and `pick_tasks` entrypoint is at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:658`; scoped tests passed. | MCP tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC5 | Legacy validator test now requires non-raising behavior at `serve/kanban/tests/test_engine_coverage_1068.py:260`; scoped test passed. | `test_agent_map_missing_status_raises` | PASS |

### Deductions
- `-0.10` AC2 test coverage still does not bind the full refined placement contract (`after effective-wave-size guard`, `before resolve_pending_drs`).
- `-0.02` Commit integrity relied on current snapshot + reflog instead of a raw diff.

### Verdict
- FAIL
- Confidence: 0.88
- Action: reject to `backlog`.
- Routing reason: this task already contains a prior review failure in the body history; this repeat review failure uses the loop-breaker route even though the remaining issue is proof quality rather than implementation correctness.

### Required Follow-up
1. Add a task-owned sequencing proof that `resolve_pending_drs` is not called when `agent_map` is incomplete.
2. Add a conflict-path test proving `ERR_INVALID_WAVE_PARAM` wins when both `effective_wave < 1` and `agent_map` is incomplete, which binds the “immediately after the effective-wave-size guard” requirement.
3. Keep the current source behavior unless the stronger tests expose a real defect.

### Post-task Reflection
- The live implementation now matches the refined Round 2 AC; the remaining gate is test-proof only.
- Exact placement ACs need ordered-call or precedence tests, not just eventual exception assertions.
- Broad legacy suite runs can surface unrelated red; scoped reruns are necessary for fair gating.
- Reflog evidence is workable for commit presence when raw diff access is unavailable, but it carries a small confidence cost.

## AC Update (Round 3 Arch Review)

**AC4 correction:** MCP `pick_tasks` raises `ToolError` (wrapping `ConfigError` user_message via MCP adapter at `server.py:76`) when `agent_map` is incomplete — not `ConfigError` directly. The original AC4 wording was stale; tests already assert `ToolError`.

**New AC lines:**
- [ ] AC6 (`td:1`): `tests/test_engine_lazy_agent_map_1221.py` — ordering proof: `resolve_pending_drs` is **never called** when `agent_map` is incomplete. Test: monkeypatch `sys.modules["owlbear_kanban.decisions"]` with a `MagicMock()` before calling `av.pick_tasks()`; assert `mock_decisions.resolve_pending_drs.call_count == 0`.
- [ ] AC7 (`td:1`): `tests/test_engine_lazy_agent_map_1221.py` — `effective_wave` conflict proof: config with `wave_size: 0` AND `agent_map: {}` loaded via `refresh_config()`; `av.pick_tasks()` (no explicit `wave_size` arg) must raise `ValidationError(code="ERR_INVALID_WAVE_PARAM")`, not `ConfigError`; proves the `effective_wave < 1` guard at `engine.py:2327` executes before the agent_map check at `engine.py:2333`. Test must import `ValidationError` from `owlbear_kanban.errors`.

**Builder note for next pass:** Source is already correct (commit `062b2644`). Builder must skip implementation and run quality-runner verification only (scoped run on `tests/test_engine_lazy_agent_map_1221.py`).

[[2026-05-01]]
## Architecture Review (Round 3)
### Context
Task returned from reviewer (Round 2 sweep, loop-breaker route). Implementation at `engine.py:2333–2338` is correct (verified live: guard after effective_wave check at line 2327, before `resolve_pending_drs` at line 2348, before `list_tasks` at line 2352). 14/14 task-owned tests pass. Two test proofs were missing.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged from Round 2 |
| Interface clarity | PASS | AC6/AC7 add explicit proof requirements; AC4 corrected |
| Dependency correctness | PASS | No new deps |
| Module layering | PASS | Validation stays in engine.py |
| TDD compliance | PASS | Test-writer adds AC6+AC7 tests |
| KISS/YAGNI | PASS | Minimal scope — test proof only |
| Premise challenge | PASS | Unchanged |
| Pattern consistency | PASS | Unchanged |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban-engine only |

### AC Refinements Applied
| AC | Change | Reason |
|----|--------|--------|
| AC4 | Corrected to `ToolError` (not `ConfigError`) | Live MCP adapter raises `ToolError`; stale AC4 text said `ConfigError` |
| AC6 (new, td:1) | `resolve_pending_drs` non-call proof via `sys.modules` monkeypatch | Reviewer required: no test binds "before resolve_pending_drs" placement |
| AC7 (new, td:1) | `effective_wave < 1` conflict: config `wave_size: 0` + no explicit param → `ERR_INVALID_WAVE_PARAM` wins | Challenger: `wave_size=0` explicit param hits line 2319 (wrong guard); config-driven 0 correctly targets `effective_wave < 1` at line 2327 |

### Challenger Results
- Challenger: reconsider (0.48) — three concerns raised; all resolved:
  - Critical (AC7 proof mismatch): corrected — AC7 now uses config `wave_size: 0` + no explicit `wave_size` param, targeting `effective_wave < 1` guard at line 2327 specifically
  - Moderate (AC4 stale wording): corrected — `ToolError` replaces `ConfigError`
  - Minor (routing): noted — builder-skip instruction added

### Test Depth
- AC6: (td:1), AC7: (td:1)
- Test-writer: PROCEED (add 2 tests to `tests/test_engine_lazy_agent_map_1221.py`; builder skips implementation — source is already correct)

### Verdict: APPROVE (after REFINE)
### Action Taken: AC4 corrected, AC6+AC7 added; approved to todo
[[2026-05-01]]
## Architecture Review (Round 3)

REFINE → APPROVE.

AC changes:
- AC4 corrected: "ToolError (wrapping ConfigError)" — the MCP adapter raises ToolError, not ConfigError; stale original wording fixed.
- AC6 added (td:1): resolve_pending_drs non-call proof — monkeypatch sys.modules["owlbear_kanban.decisions"] with MagicMock, call av.pick_tasks(), assert mock_decisions.resolve_pending_drs.call_count == 0.
- AC7 added (td:1): effective_wave conflict proof — config with wave_size: 0 AND agent_map: {} loaded via refresh_config(); av.pick_tasks() (no explicit wave_size arg) must raise ValidationError(code="ERR_INVALID_WAVE_PARAM"), proving effective_wave < 1 guard at engine.py:2327 executes before agent_map check at engine.py:2333.

Challenger: reconsider (0.48) — all three concerns resolved: AC7 proof-contract mismatch corrected (config-driven zero, not explicit param), AC4 stale wording fixed, builder-skip noted.

Implementation at engine.py:2333–2338 is correct. 14/14 task-owned tests pass. Test-writer: add 2 tests. Builder: skip implementation, run verification only.
[[2026-05-01]]
## Test-Writer Notes
- Retry (Round 3 arch review): added 2 new tests for AC6 and AC7. All 15 tests PASS against current implementation — builder skip applied (direct-to-review advance).
- Test files:
  - `tests/test_engine_lazy_agent_map_1221.py` — 15 tests, all PASS
- Classes: TestFromAC_InitNoLongerRaises, TestFromAC_PickTasksValidatesAgentMap, TestFromAC_CockpitInitWithEmptyAgentMap, TestFromAC_McpPickTasksRaisesForIncompleteAgentMap
- Tests per category: happy 0, edge 2, error 9, boundary 4
- Total: 15 tests, all PASS (green against existing implementation)
- ruff: clean
- Commit: d80c3b61

AC coverage:
| AC line | Tests |
|---------|-------|
| AC1: __init__ no longer raises | test_init_accepts_empty_agent_map, test_init_accepts_partial_agent_map |
| AC2: pick_tasks validates at top, before filtering | test_pick_tasks_raises_config_error_for_empty_agent_map, test_pick_tasks_raises_config_error_for_partial_agent_map, test_pick_tasks_error_code_is_err_invalid_status, test_pick_tasks_error_message_names_missing_statuses, test_pick_tasks_validates_before_filtering_with_tasks_present, test_pick_tasks_validates_before_list_tasks_is_called |
| AC3: Cockpit starts with empty agent_map | test_cockpit_engine_init_succeeds_with_empty_agent_map, test_cockpit_engine_board_config_accessible_with_empty_agent_map |
| AC4: MCP raises ToolError with all missing statuses named | test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map, test_mcp_pick_tasks_tool_error_message_contains_missing_entries, test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses |
| AC5: test_engine_coverage_1068.py::test_agent_map_missing_status_raises asserts non-raising | already updated in prior retry (serve/kanban/tests/test_engine_coverage_1068.py) |
| AC6: resolve_pending_drs non-call proof | **test_pick_tasks_validates_before_resolve_pending_drs** (new — monkeypatches sys.modules["owlbear_kanban.decisions"], asserts call_count == 0 after ConfigError) |
| AC7: effective_wave conflict proof — ERR_INVALID_WAVE_PARAM wins over ERR_INVALID_STATUS | **test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard** (new — config wave_size:0 + agent_map:{}, asserts ValidationError(ERR_INVALID_WAVE_PARAM) not ConfigError) |

Round 3 changes:
- Added _BASE_CONFIG_ZERO_WAVE_EMPTY_AGENT_MAP fixture (wave_size: 0, agent_map: {})
- Added test_pick_tasks_validates_before_resolve_pending_drs: monkeypatches sys.modules["owlbear_kanban.decisions"] via MagicMock; ConfigError is raised before decisions import so call_count must be 0.
- Added test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard: reloads config with wave_size:0 + agent_map:{}; no explicit wave_size arg → effective_wave=0<1 → ValidationError(ERR_INVALID_WAVE_PARAM) wins before agent_map guard.
- Builder skip: test-only retry, all 15 tests pass against current implementation.
[[2026-05-01]]
## Builder Notes
- Scope: verification-only builder pass (Round 3 builder-skip path); no source or test edits in this invocation.
- Files changed: none.
- Verification (quality-runner, scoped): 16 passed, 0 failed, 0 skipped for:
  - `tests/test_engine_lazy_agent_map_1221.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises`
- Lint: clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_lazy_agent_map_1221.py`, and `serve/kanban/tests/test_engine_coverage_1068.py`.
- Coverage: `owlbear_kanban.engine` at 13% (overall run 23%); informational for this large module and consistent with prior task-scoped evidence.
- Evidence summary: AC-focused proofs including AC6/AC7 remain green against the current implementation; no additional builder implementation was required.

Post-task reflection:
- Builder-skip verification avoided unnecessary churn while still producing fresh GREEN evidence.
- Including the AC5 node test in scoped verification keeps cross-task stale-contract regressions contained.
- Module-wide coverage remains low for a large file; AC-path confidence comes from targeted test proofs and clean lint.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner (task-owned scoped): pytest 16 passed, 0 failed, 0 skipped for `tests/test_engine_lazy_agent_map_1221.py` and `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises`
- quality-runner (boundary spot-check): pytest 70 passed, 0 failed, 0 skipped across `tests/test_cockpit_launch.py` and `serve/mcp-kanban/tests/test_mcp_read_tools.py`

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_lazy_agent_map_1221.py`, and `serve/kanban/tests/test_engine_coverage_1068.py`

### Coverage
- task-scoped coverage: `owlbear_kanban.engine` 13% module-wide (196/1457 statements)
- Informational only for this large module. The gate is diff-scoped; the moved guard path is directly exercised by AC1/AC2/AC5/AC6/AC7 tests.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `KanbanEngine.__init__` no longer raises `ConfigError` for missing `agent_map` entries | `tests/test_engine_lazy_agent_map_1221.py::test_init_accepts_empty_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_init_accepts_partial_agent_map` | Yes. Reintroducing constructor-time `agent_map` completeness validation would fail both init tests immediately. | COVERED |
| AC2: `pick_tasks()` validates completeness immediately after the effective-wave-size guard, before `resolve_pending_drs`, and before filtering/sorting/wave assembly; raises `ConfigError(ERR_INVALID_STATUS)` | `tests/test_engine_lazy_agent_map_1221.py::test_pick_tasks_*` group, including `test_pick_tasks_validates_before_list_tasks_is_called`, `test_pick_tasks_validates_before_resolve_pending_drs`, and `test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard` | Yes. The suite binds the error code, pre-`list_tasks` ordering, pre-`resolve_pending_drs` ordering, and precedence of the earlier `effective_wave` guard. | COVERED |
| AC3: Cockpit starts successfully with `agent_map: {}` in grouped config | `tests/test_engine_lazy_agent_map_1221.py::test_cockpit_engine_init_succeeds_with_empty_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_cockpit_engine_board_config_accessible_with_empty_agent_map` | Yes for the task-owned root cause. `serve/cockpit/src/owlbear_cockpit/main.py:72` constructs `KanbanEngine(..., agent_name="cockpit")` before uvicorn starts, so restoring eager init validation would break the startup path at that constructor boundary. The broader cockpit launch suite also stayed green. | COVERED |
| AC4: MCP `pick_tasks` raises `ToolError` with missing-entry message when `agent_map` is incomplete | `tests/test_engine_lazy_agent_map_1221.py::test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map`, `tests/test_engine_lazy_agent_map_1221.py::test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses` | Yes. The tests require the MCP boundary to surface `ToolError` and name all missing statuses individually. | COVERED |
| AC5: `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` now asserts non-raising for incomplete `agent_map` | `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_ValidateEngineConfig::test_agent_map_missing_status_raises` | Yes. Restoring the old `_validate_engine_config` completeness check would fail this test immediately. | COVERED |
| AC6: `resolve_pending_drs` is never called when `agent_map` is incomplete | `tests/test_engine_lazy_agent_map_1221.py::test_pick_tasks_validates_before_resolve_pending_drs` | Yes. The monkeypatched decisions module remains untouched because the `ConfigError` is raised before import/call. | COVERED |
| AC7: `ERR_INVALID_WAVE_PARAM` wins when `effective_wave < 1` and `agent_map` is incomplete | `tests/test_engine_lazy_agent_map_1221.py::test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard` | Yes. The test asserts the exact `ValidationError` code from the earlier guard, so reordering would fail it. | COVERED |

#### Security Review
- No issues found. The live change is local config validation in `serve/kanban/src/owlbear_kanban/engine.py` before decisions import and task scan.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions observed in the current snapshot.
- Reflog confirms the scoped commits exist: `062b2644c8d664abc224da5a71b2774c8fc53e36` (builder) and `d80c3b61016443bd3a97841b629bfb673f6de158` (test-writer).

#### Test Quality
- Assertion specificity: ADEQUATE. Binding assertions exist for error code, `list_tasks` non-call, `resolve_pending_drs` non-call, MCP `ToolError`, all-missing-status names, and `effective_wave` precedence. One older direct ConfigError message test at `tests/test_engine_lazy_agent_map_1221.py:315` still accepts generic `"missing"`; this is non-blocking because AC2 is already bound by stronger tests.
- Negative/error-path coverage: STRONG.
- Manual mutation reasoning: STRONG. Reintroducing eager init validation, moving the guard below `resolve_pending_drs` or `list_tasks`, or letting `ERR_INVALID_STATUS` beat `ERR_INVALID_WAVE_PARAM` would fail named tests.
- Independence and naming: ADEQUATE. Tests are isolated via fresh tmp boards; one legacy AC5 test name still says `_raises` after the contract moved.

#### Data Safety
- No issues found.

#### Implementation-Aware Gap Analysis
- No implementation defect found in the live source.
- `_validate_engine_config` no longer checks `agent_map` completeness at `serve/kanban/src/owlbear_kanban/engine.py:114-166`.
- `KanbanEngine.__init__` still calls that validator at `serve/kanban/src/owlbear_kanban/engine.py:448`.
- `pick_tasks` now enforces the moved check after the `effective_wave` guard and before `resolve_pending_drs` / `list_tasks` at `serve/kanban/src/owlbear_kanban/engine.py:2327-2352`.
- Boundary regression spot-check stayed green on cockpit launch and MCP read tools.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
- FRICTION, not LOOP.
- Builder note sections in body: 5.
- Approach variation is real: environment block, initial implementation, verification-only pass, re-implementation after overwrite, final verification-only pass.

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_engine_coverage_1068.py:260` still uses the old `_raises` method name even though the body now asserts non-raising.
- `tests/test_engine_lazy_agent_map_1221.py` still contains some RED-phase commentary about the old failure mode; comments are stale but assertions are current.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_validate_engine_config` at `serve/kanban/src/owlbear_kanban/engine.py:114-166` no longer enforces `agent_map` completeness, while `__init__` still calls it at `serve/kanban/src/owlbear_kanban/engine.py:448`; scoped tests passed. | init tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC2 | The live guard raises `ERR_INVALID_STATUS` after the `effective_wave` guard and before `resolve_pending_drs` / `list_tasks` in `serve/kanban/src/owlbear_kanban/engine.py:2327-2352`; scoped tests passed. | `test_pick_tasks_*` group | PASS |
| AC3 | `serve/cockpit/src/owlbear_cockpit/main.py:72` constructs `KanbanEngine(..., agent_name="cockpit")` before uvicorn; grouped empty-map task tests passed; cockpit launch regression spot-check passed. | cockpit tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC4 | MCP maps `KanbanError.user_message` to `ToolError` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:77-78`, and `pick_tasks` enters the engine path at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:658-683`; scoped tests passed. | MCP tests in `tests/test_engine_lazy_agent_map_1221.py` | PASS |
| AC5 | Legacy validator test now requires non-raising behavior at `serve/kanban/tests/test_engine_coverage_1068.py:260-269`; scoped test passed. | `test_agent_map_missing_status_raises` | PASS |
| AC6 | `resolve_pending_drs` call site remains below the moved guard in `serve/kanban/src/owlbear_kanban/engine.py:2348`; direct non-call test passed. | `test_pick_tasks_validates_before_resolve_pending_drs` | PASS |
| AC7 | `effective_wave < 1` raises `ERR_INVALID_WAVE_PARAM` before the moved `agent_map` guard in `serve/kanban/src/owlbear_kanban/engine.py:2327-2339`; direct precedence test passed. | `test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard` | PASS |

### Deductions
- `-0.03` Direct raw diff was unavailable; integrity was verified from the current snapshot plus reflog commit presence instead.
- `-0.02` AC3 is proved as a task-owned root-cause composite (`run()` constructs `KanbanEngine(...)` before uvicorn, and the grouped empty-map constructor tests stay green) rather than by a dedicated `run()` test with empty `agent_map`.

### Verdict
- PASS
- Confidence: 0.93
- Action: advance to docs

### Post-task Reflection
- The missing proof from the prior review is now present: `resolve_pending_drs` non-call and `effective_wave` precedence are both bound by direct tests.
- AC wording drift on the MCP boundary mattered; the authoritative runtime contract is `ToolError` carrying `KanbanError.user_message`.
- Composite boundary proof can be sufficient when the live entry point fails only at a single constructor call, but it carries a small confidence cost relative to an exact entrypoint test.
[[2026-05-01]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | Yes | PASS | Latest `## Review Evidence` section present; Round 3 reviewer verdict: PASS (confidence 0.93) |
| 0b | Doc-index loaded | Yes | PASS | `.owlbear/doc-index.md` read; `kanban.excalidraw` describes `serve/kanban/src/**` |
| 1 | Descriptive prose docs | Yes | UPDATED | `serve/kanban/README.md` — (1) "five-step pipeline" corrected to "six-step pipeline" with validation as step 1; (2) migration note corrected from "before starting the engine" to "before calling `pick_tasks()`" |
| 2 | Module docstrings | Yes | VERIFIED | `pick_tasks` docstring already accurate from previous docs pass — six-step pipeline with step 1 validate, Raises includes `ConfigError(ERR_INVALID_STATUS)` |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc in task body |
| 5 | Diagram maintenance | Yes | UPDATED | `share/diagrams/kanban.excalidraw` describes `serve/kanban/src/**` — footer updated from `9cc65998` to `8e9d7030` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | No deleted files |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN | Docstring verified accurate |
| `tests/test_engine_lazy_agent_map_1221.py` | OUT | Test file — not edited |
| `serve/kanban/tests/test_engine_coverage_1068.py` | OUT | Test file — not edited |

### Context Note
Previous docs gate commit `0de43485` was in history but a subsequent commit `4a64f9ff` ("docs: update README to clarify create_dr function signature…") overwrote the README changes. Re-applied both README corrections.

### Files Updated
- `serve/kanban/README.md` — six-step pipeline description + migration note
- `share/diagrams/kanban.excalidraw` — footer updated to `2026-05-01 (8e9d7030)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/q1221-pytest.log`
- `.owlbear/scratch/q1221-red-baseline.log`
- `.owlbear/scratch/qr-1221-pytest.txt`
- `.owlbear/scratch/qr-1221-ruff.txt`

### Commit
`fdf0409d` — docs: update pick_tasks docs for lazy agent_map validation (#1221, doc-writer)
[[2026-05-01]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `__init__` no longer raises for missing agent_map | `_validate_engine_config` at engine.py:112-166 has no agent_map check; init still calls helper at engine.py:448; init tests pass. | PASS |
| AC2: `pick_tasks()` validates at top, after wave guard, before `resolve_pending_drs`/filtering | Guard at engine.py:2328-2335; wave guard at engine.py:2322-2326; non-call proofs for list_tasks (L339), resolve_pending_drs (L371), and wave-guard precedence (L401) all pass. | PASS |
| AC3: Cockpit starts with agent_map: {} | cockpit/main.py:72 constructs KanbanEngine before uvicorn; task tests + cockpit launch regression (70/70) pass. | PASS |
| AC4: MCP raises ToolError with all missing statuses named | server.py:76 maps KanbanError.user_message to ToolError; task tests assert ToolError and all 4 missing statuses individually. | PASS |
| AC5: test_engine_coverage_1068.py::test_agent_map_missing_status_raises asserts non-raising | test_engine_coverage_1068.py:260 uses plain call to _validate_engine_config (no pytest.raises); scoped test passes. | PASS |
| AC6: resolve_pending_drs never called when agent_map is incomplete | test_pick_tasks_validates_before_resolve_pending_drs (L371) monkeypatches sys.modules["owlbear_kanban.decisions"]; call_count == 0 after ConfigError. | PASS |
| AC7: ERR_INVALID_WAVE_PARAM wins over ERR_INVALID_STATUS when effective_wave less than 1 | test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard (L401) uses wave_size:0 config plus agent_map:{}; asserts ValidationError(ERR_INVALID_WAVE_PARAM). | PASS |

### Test Results
- Full suite (quality-runner mode=full): 3341 passed, 109 failed, 4 skipped -- no task-attributed failures; 109 are pre-existing background failures from other in-flight tasks. Prior audit's AC5 regression (test_agent_map_missing_status_raises) is absent from failure set (count dropped from 138 to 109).
- Task suite (scoped, per builder/reviewer): 16 passed, 0 failed (15 in test_engine_lazy_agent_map_1221.py + 1 AC5 node in test_engine_coverage_1068.py)
- Lint: clean for engine.py, task test file, and test_engine_coverage_1068.py

### Reviewer Evidence
Two Review Evidence sections present. Latest (Round 3, reviewer) verdict: PASS, confidence 0.93. All 7 AC lines mapped. Test quality assessment: STRONG for AC2 (three ordering proofs), ADEQUATE overall. Accepted.

### Commit Integrity
- 062b2644 -- fix: defer agent_map completeness validation to pick_tasks (#1221, builder) -- engine.py only
- d80c3b61 -- test: add AC6/AC7 ordering proofs for pick_tasks validation (#1221, test-writer) -- test file only
- fdf0409d -- docs: update pick_tasks docs for lazy agent_map validation (#1221, doc-writer) -- README, engine.py docstring, kanban.excalidraw

### Architect Quality: 4/5
AC required 3 rounds to reach full specificity (missed AC5 stale-test migration, AC6 resolve_pending_drs ordering proof, AC7 wave-guard conflict proof in initial spec). Final AC block is specific, complete, and verifiable. Architect responded well to challenger and auditor feedback -- gaps were real but not fundamental.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC3 composite proof (constructor test + launch regression vs dedicated run() test) | -0.02 |
| Diff access via snapshot + reflog only | -0.02 |

### Confidence: 0.96
### Action: archive