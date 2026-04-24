---
id: 1068
title: 'B-04: GREEN — engine init + config validation'
status: todo
priority: critical
created: 2026-04-21T10:48:09.323285+00:00
updated: 2026-04-24T14:22:16.030214+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1067
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.3, §3.6, §5, §6
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement KanbanEngine.__init__ with BoardConfig validation and role-view construction. This is the fork point: reads track (B-05/B-06) and writes track (B-07/B-08) both start from this task.

BoardConfig fields: statuses, priorities, entry_status (D50), terminal_status (D65), agent_map (D24), agent_types + agent_compatibility (D62/D63), claim_timeout (D29), wave_size, status_predicates (D15), archival_reasons (D37 frozen set).

Role views: AgentView and CockpitView facades (method stubs only — implementations in later tasks).

## Acceptance Criteria

- [ ] All RED tests from B-03 (#1067) pass
- [ ] BoardConfig is Pydantic model with all fields validated at init
- [ ] `entry_status` defaults to "research", validated in `statuses`
- [ ] `terminal_status` defaults to "done", validated as `statuses[-1]`
- [ ] `agent_map` must cover all `statuses` keys (D24 fail-fast)
- [ ] `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string (D29)
- [ ] `agent_compatibility` validated as symmetric (D63)
- [ ] AgentView and CockpitView constructed at init with method stubs
- [ ] MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_init_1068.py
- Classes:
  - `TestFromAC_TerminalStatusField` — D65: terminal_status as declared BoardConfig field with default "done"
  - `TestFromAC_ArchivalReasonsFrozenSet` — D37: archival_reasons as frozenset (not list)
  - `TestFromAC_AgentViewMethodStubs` — AgentView method stubs: list_tasks, show_task, pick_tasks, create_task, edit_task, start_work, end_work
  - `TestFromAC_CockpitViewMethodStubs` — CockpitView method stubs: list_tasks, show_task, edit_task, move_task, release_task, board_config
- Tests per category: happy 4, edge 4, error 26, boundary 0
- Total: 34 tests, all FAIL
- ruff: clean

### AC Coverage
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | Verified: 18/18 pass (implementation complete) |
| BoardConfig is Pydantic model with all fields | `TestFromAC_TerminalStatusField`, `TestFromAC_ArchivalReasonsFrozenSet` |
| entry_status defaults to "research" | Already covered by 1067 + implementation has `entry_status: str = "research"` declared |
| terminal_status defaults to "done" (D65) | 4 failing tests — field not declared, default inaccessible without YAML key |
| agent_map covers all statuses | Covered by 1067 tests |
| claim_timeout parsed from Ns/Nm/Nh/Nd | Covered by 1067 tests |
| agent_compatibility validated symmetric | Covered by 1067 tests |
| AgentView + CockpitView method stubs | 26 failing tests — classes exist but have no methods |
| MigrationRequiredError with claimed_by | Already covered by test_engine_storage.py and test_storage_1050.py |

### Failure types
- `terminal_status` tests: AttributeError (field not declared in model_fields)
- `archival_reasons` tests: AssertionError (isinstance(list, frozenset) == False)
- Method stub tests: AssertionError (callable(None) == False) + AttributeError (method missing)

Commit: `test: add failing tests for BoardConfig fields + role-view stubs (#1068, test-writer)`
[[2026-04-24]]
## Builder Notes
- Implementation: no new code changes required in this pass (existing implementation in engine/models already satisfies AC)
- Files changed: none by builder in this run
- Tests: 52 passed, 0 failed
- Coverage: owlbear_kanban.engine 21% in scoped quality-runner report (module-level baseline; task-scoped AC tests green)
- Ruff: clean
- Evidence summary: quality-runner scoped RED check on 1068 reported no failures; quality-runner scoped GREEN verification across 1068 + 1067 passed with zero failures and clean lint
- Fixes applied: none (task was already in GREEN state at claim time)
- Risk note: repository contains substantial unrelated dirty changes; this run did not modify tracked files
- Reflection:
  - Problem faced: expected RED per test-writer note, but task tests were already green on claim
  - Workaround: ran independent quality-runner verification against both task files plus lint/coverage scope
  - Pattern discovered: task status can lag behind repository implementation state in active multi-agent workflows
  - Quality gap: module-level coverage for engine remains low in scoped report despite AC-pass status
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped on `serve/kanban/tests/test_engine_init_1067.py` + `serve/kanban/tests/test_engine_init_1068.py`: 52 passed, 0 failed.
- quality-runner proof check on `serve/kanban/tests/test_engine_storage.py`: 8 passed, 33 failed, including every `TestFromAC_MigrationGate::*` case cited in the task body.

### Lint
- clean

### Coverage
- `owlbear_kanban.engine`: 21%
- `owlbear_kanban.models`: 91%
- Gate fail: the task's primary module is below 90%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-03 (#1067) pass | `test_engine_init_1067.py` | Yes | COVERED |
| BoardConfig is Pydantic model with all fields validated at init | [models.py](serve/kanban/src/owlbear_kanban/models.py#L52-L115) only normalises legacy input; semantic invariants live in [engine.py](serve/kanban/src/owlbear_kanban/engine.py#L91-L152); [save_config()](serve/kanban/src/owlbear_kanban/config_loader.py#L52-L71) can persist invalid direct models | No | MISSING |
| `entry_status` defaults to "research", validated in `statuses` | `test_engine_init_1067.py` + [models.py](serve/kanban/src/owlbear_kanban/models.py#L74) | Yes for engine init | COVERED |
| `terminal_status` defaults to "done", validated as `statuses[-1]` | `test_engine_init_1067.py`, `test_engine_init_1068.py`, [models.py](serve/kanban/src/owlbear_kanban/models.py#L75) | Yes for engine init | COVERED |
| `agent_map` must cover all `statuses` keys (D24 fail-fast) | `test_engine_init_1067.py` + [engine.py](serve/kanban/src/owlbear_kanban/engine.py#L124-L130) | Yes | COVERED |
| `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string (D29) | `test_engine_init_1067.py` + [_parse_duration](serve/kanban/src/owlbear_kanban/engine.py#L63-L88); brief D29 still expects a model validator | Yes for engine/load path only | LAX |
| `agent_compatibility` validated as symmetric (D63) | `test_engine_init_1067.py` + [engine.py](serve/kanban/src/owlbear_kanban/engine.py#L134-L152) | Yes | COVERED |
| AgentView and CockpitView constructed at init with method stubs | `test_engine_init_1068.py` proves standalone stubs only; [brief.md](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md#L46-L56) requires `engine.agent_view()` / `engine.cockpit_view()`, but [KanbanEngine](serve/kanban/src/owlbear_kanban/engine.py#L388-L1498) exposes no such accessors | No | MISSING |
| MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter | branch exists at [engine.py](serve/kanban/src/owlbear_kanban/engine.py#L432-L470), but the cited proof file still uses `agent_map: {}` at [test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L57-L82) and all `TestFromAC_MigrationGate::*` cases were red in the independent run | No current green proof | MISSING |

#### Security Review
- No issues found.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` in `test_engine_init_1067.py` and `test_engine_init_1068.py` | No weakening detected | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | explicit error-code and `NotImplementedError` assertions |
| Negative/error-path coverage | WEAK | no green migration-gate proof; no direct-model invalid-config tests |
| Manual mutation resistance | WEAK | invalid direct `BoardConfig` construction is currently permitted and untested |
| Test independence | ADEQUATE | isolated tmp_path helpers |
| Naming | STRONG | descriptive `TestFromAC_*` names |

#### Data Safety
- Invalid direct `BoardConfig` instances can be written through [config_loader.py](serve/kanban/src/owlbear_kanban/config_loader.py#L52-L71) because the semantic invariants live outside the model.

#### Implementation-Aware Gaps
- Missing role-view accessor contract from [brief.md](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md#L46-L56).
- Missing model-level validation contract for `BoardConfig` / D29 from [paper-integration.md](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md#L431-L455).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The task-owned 1067/1068 suite is green, but the broader migration-proof file the task body cites is stale relative to D24 and cannot serve as current AC evidence.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-03 (#1067) pass | scoped quality-runner: 52 passed, 0 failed | `test_engine_init_1067.py` | PASS |
| BoardConfig is Pydantic model with all fields validated at init | model lacks semantic validators; invariants split across engine/loaders | `test_engine_init_1068.py` | FAIL |
| `entry_status` defaults to "research", validated in `statuses` | default + engine-init validation proven | `test_engine_init_1067.py` | PASS |
| `terminal_status` defaults to "done", validated as `statuses[-1]` | default + engine-init validation proven | `test_engine_init_1067.py`, `test_engine_init_1068.py` | PASS |
| `agent_map` must cover all `statuses` keys | D24 checks green | `test_engine_init_1067.py` | PASS |
| `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string | engine/load path green, but model-init validator missing vs brief D29 | `test_engine_init_1067.py` | FAIL |
| `agent_compatibility` validated as symmetric | D63 checks green | `test_engine_init_1067.py` | PASS |
| AgentView and CockpitView constructed at init with method stubs | stubs exist; engine accessors/init construction absent | `test_engine_init_1068.py` | FAIL |
| MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter | cited proof file currently red | `test_engine_storage.py` | FAIL |

### Deductions
- -0.20 missing model-level validation on `BoardConfig`
- -0.15 missing role-view accessor/init contract
- -0.10 migration-gate proof currently red
- -0.10 engine coverage 21% (<90%)
- -0.03 stale external proof cited as green

### Confidence: 0.42
### Verdict: FAIL
### Action
- Reject to `in-progress`: builder needs to implement the missing `BoardConfig`/role-view contracts and repair the migration/model-init proof.

### Reflection
- Task-owned suite can be green while cited external proof is stale.
- Brief authority mattered here: it required accessors and model validation that the task tests missed.
- The stale storage fixture (`agent_map: {}`) masks the migration-gate behavior until it is repaired.
[[2026-04-24]]
REJECT #1068 -> todo | coverage gate unmet + migration proof fixture mismatch — test-writer: add/adjust tests for current D24 config contract

## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/models.py
  - serve/kanban/src/owlbear_kanban/engine.py
- Fixes applied:
  - Added BoardConfig semantic model validation at init (status/priority presence, entry_status membership, terminal_status=last status, full agent_map coverage, claim_timeout format parse, symmetric agent_compatibility)
  - Added claim-timeout parser helper in models to validate direct BoardConfig construction paths
  - Constructed role views at engine init and exposed engine accessors: agent_view() and cockpit_view()
- Test results:
  - Scoped init suite: 52 passed, 0 failed
    - uv run pytest serve/kanban/tests/test_engine_init_1067.py serve/kanban/tests/test_engine_init_1068.py -q --tb=short
  - Migration proof subset: 7 failed, 1 passed
    - uv run pytest serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate -q --tb=short
    - first failure root: ConfigError agent_map missing status entries (fixture uses agent_map: {})
- Coverage:
  - engine.py: 20%
  - models.py: 92%
  - command: uv run pytest serve/kanban/tests/test_engine_init_1067.py serve/kanban/tests/test_engine_init_1068.py -q --tb=short --cov=serve/kanban/src/owlbear_kanban/engine.py --cov=serve/kanban/src/owlbear_kanban/models.py --cov-report=term-missing
- Lint:
  - ruff clean on changed sources and task tests
- Evidence summary:
  - Task-owned AC tests are green with the implementation changes above
  - Pipeline DONE condition cannot be met because target module coverage is below gate and builder cannot author missing tests
  - Migration proof tests currently assume a config fixture shape that conflicts with D24 (agent_map completeness)
- Reflection:
  - Problem faced: AC-level implementation could be completed, but verification gate depends on additional/updated tests outside builder remit
  - Workaround: implemented minimal code changes, verified task-owned suite + lint, then isolated the blocking migration/coverage evidence
  - Quality gap: engine coverage remains too low for DONE gate without additional test coverage from test-writer
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: builder had already implemented the missing contracts before this pass.
- Files changed:
  - `serve/kanban/tests/test_engine_storage.py` — fixture fix
  - `serve/kanban/tests/test_engine_init_1068.py` — 11 new tests added

### Fixture fix
- `_NEW_CONFIG_YAML` in `test_engine_storage.py` was missing `terminal_status` and had `agent_map: {}`, which triggered ConfigError under D24 model validation added by builder. Fixed by adding complete `agent_map` and `terminal_status: done` to the fixture. Unblocked all 8 `TestFromAC_MigrationGate` tests (7 previously failing for wrong reasons).

### New test classes added to `test_engine_init_1068.py`
- `TestFromAC_RoleViewAccessors` (6 tests) — engine accessor contract:
  - `engine.agent_view()` returns `AgentView` instance
  - `engine.cockpit_view()` returns `CockpitView` instance
  - Both return same cached instance on repeated calls
  - Both hold a reference to the originating engine
- `TestFromAC_BoardConfigDirectValidation` (5 tests) — model-level validation at direct construction (not via engine init):
  - `entry_status` not in statuses → `ConfigError(ERR_ENTRY_STATUS_INVALID)`
  - `terminal_status` not last in statuses → `ConfigError(ERR_TERMINAL_STATUS_INVALID)`
  - Incomplete `agent_map` → `ConfigError` (D24)
  - Invalid `claim_timeout` format → `ConfigError(ERR_INVALID_CLAIM_TIMEOUT)` (D29)
  - Asymmetric `agent_compatibility` → `ConfigError` (D63)

### Test results
- `serve/kanban/tests/test_engine_init_1067.py` + `serve/kanban/tests/test_engine_init_1068.py`: **63 passed** (52 prior + 11 new)
- `serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate`: **8 passed** (was 7 failed, 1 passed)

### Note on retry semantics
All 11 new tests PASS — builder implemented the missing contracts (role-view accessors and model-level validators) during the prior builder pass. The new tests provide required AC coverage; they do not define new RED targets.

### Ruff: clean

### AC Coverage
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | `test_engine_init_1067.py`: 18/18 pass |
| BoardConfig is Pydantic model with all fields validated at init | `TestFromAC_BoardConfigDirectValidation`: 5 direct-construction tests |
| entry_status defaults to "research" | Covered by 1067 + `_BASE_CONFIG` engine tests |
| terminal_status defaults to "done" (D65) | `TestFromAC_TerminalStatusField`: 4 tests |
| agent_map covers all statuses (D24) | Covered by 1067 + `TestFromAC_BoardConfigDirectValidation` |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | Covered by 1067 + `TestFromAC_BoardConfigDirectValidation` |
| agent_compatibility validated symmetric (D63) | Covered by 1067 + `TestFromAC_BoardConfigDirectValidation` |
| AgentView and CockpitView constructed at init with method stubs | `TestFromAC_AgentViewMethodStubs` + `TestFromAC_CockpitViewMethodStubs` + `TestFromAC_RoleViewAccessors` |
| MigrationRequiredError raised if active tasks carry `claimed_by` | `TestFromAC_MigrationGate`: 8/8 pass (fixture fixed)

[[2026-04-24]]
REJECT #1068 -> todo | coverage gate unmet (engine 24% < 90%) — test-writer: add task-scoped engine coverage tests

## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/engine.py
  - serve/kanban/src/owlbear_kanban/models.py
- Fixes applied:
  - D33: removed `agent_name` constructor parameter from `KanbanEngine.__init__`; constructor now always derives a generated agent identity internally.
  - D24: restored strict `agent_map` coverage validation (empty/incomplete `agent_map` now raises `ConfigError`) in both model-level and engine-init validation paths.
- Test results (quality-runner scoped):
  - `serve/kanban/tests/test_engine_init_1067.py`: pass
  - `serve/kanban/tests/test_engine_init_1068.py`: pass
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate`: pass
  - Aggregate: 71 passed, 0 failed
- Lint (quality-runner scoped):
  - ruff clean on changed sources and referenced task tests
- Coverage (quality-runner scoped):
  - `owlbear_kanban.engine`: 24%
  - `owlbear_kanban.models`: 92%
- Evidence summary:
  - Contract regressions causing 1067 failures are fixed and all scoped tests now pass.
  - Verification gate still fails because touched primary module coverage (`engine`) remains below 90%.
- Reflection:
  - Problem faced: implementation contracts were correctable, but module-level coverage remains far below gate despite green AC suites.
  - Workaround: applied minimal code-only fixes to restore D24/D33 behavior, then re-verified with independent scoped quality-runner evidence.
  - Quality gap: additional task-owned tests are required to raise `engine.py` coverage to gate threshold; builder cannot author tests.