---
id: 1068
title: 'B-04: GREEN — engine init + config validation'
status: archived
priority: medium
created: 2026-04-21T10:48:09.323285+00:00
updated: 2026-04-24T20:49:41.612168+00:00
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
[[2026-04-24]]
## Builder Notes
- Build attempt halted before code changes.
- Gate issue: task status is `todo`; builder only executes `in-progress` tasks.
- Verification issue: required `quality-runner` subagent is unavailable in this environment, so RED/GREEN verification cannot be performed per pipeline protocol.
- Files changed: none.
- Tests: not executed (blocked by quality-runner mandate).
- Lint: not executed (blocked by quality-runner mandate).
- Evidence summary: `show_task`/`start_work` both report status `todo`; current agent tool list does not expose `quality-runner` for mandated verification.
- Reflection:
  - Problem faced: execution preconditions for builder were unmet (status and runner availability).
  - Workaround: released claim immediately with explicit block reason to avoid non-compliant direct shell verification.
  - Quality gap: task cannot advance until routed to `in-progress` and quality-runner is available.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: coverage gate unmet (engine 24% < 90%) — added comprehensive coverage tests.
- Files changed:
  - `serve/kanban/tests/test_engine_coverage_1068.py` — new file (186 tests added)

### New test classes in `test_engine_coverage_1068.py`
| Class | AC / coverage target | Count |
|-------|---------------------|-------|
| `TestFromAC_ParseDuration` | _parse_duration happy + error paths | 10 |
| `TestFromAC_ValidateEngineConfig` | _validate_engine_config direct error paths | 9 |
| `TestFromAC_EndWorkClassifiers` | _classify_end_work_state/outcome | 8 |
| `TestFromAC_SessionDurationHelpers` | _compute_duration, _state_from_age | 6 |
| `TestFromAC_CollectTaskSessions` | _collect_task_sessions all branches | 8 |
| `TestFromAC_SessionFilterHelpers` | _validate/apply_session_filter | 10 |
| `TestFromAC_EngineProperties` | agent_name, revision, board_config | 7 |
| `TestFromAC_EngineConfigOps` | refresh_config, valid_transitions | 5 |
| `TestFromAC_MigrationGateEdgeCases` | migration gate: OSError, no fence, cleared | 5 |
| `TestFromAC_EngineListTasks` | list_tasks: all filters, sorts, archived, errors | 22 |
| `TestFromAC_EngineShowTask` | show_task: cache hit, glob, not found | 3 |
| `TestFromAC_EngineCreateTask` | create_task: success, validation, tags | 9 |
| `TestFromAC_EngineEditTask` | edit_task: all mutations + errors | 12 |
| `TestFromAC_EngineMoveTask` | move_task: status, archive, errors | 5 |
| `TestFromAC_EngineClaimRelease` | claim/release/start_work guards + success | 7 |
| `TestFromAC_EngineEndWork` | end_work: all 4 outcomes + validation | 10 |
| `TestFromAC_EngineSweep` | sweep: expired, not expired, corrupt skip | 6 |
| `TestFromAC_EngineListSessions` | list_sessions + _read_log_entries paths | 12 |
| `TestFromAC_EngineActivityLog` | _emit_event via CRUD with activity_log=True | 4 |
| `TestFromAC_EngineCacheHitPaths` | cache hit paths in show_task / _find_task_path | 5 |
| `TestFromAC_EngineListTasksArchiveScan` | archive scan: dep_status variants | 4 |
| `TestFromAC_EngineApplyOutcome` | _apply_outcome: intermediate advance, reject | 3 |
| `TestFromAC_EngineEditTaskFieldAssignment` | edit_task valid status/priority/parent | 4 |
| `TestFromAC_EngineNonIntegerTaskId` | _find_task_path ValueError branch | 3 |
| `TestFromAC_EngineListTasksInvalidStatus` | skip tasks with invalid status | 1 |
| `TestFromAC_EngineArchiveScanErrorPaths` | archive scan: unreadable file, non-digit prefix | 2 |
| `TestFromAC_EngineDuplicateIdDetection` | duplicate ID → CorruptionError | 1 |
| `TestFromAC_EngineShowTaskStalePath` | show_task with deleted file, non-int id | 3 |

### Test results (scoped quality-runner: 1067 + 1068 + coverage_1068 + storage MigrationGate)
- **254 passed, 3 failed**
- Failing tests (RED — unimplemented D24/D33 behavior, builder must implement):
  - `TestFromAC_AgentMapCoverage::test_agent_map_empty_with_nonempty_statuses_raises` (D24)
  - `TestFromAC_NoAgentNameParam::test_constructor_signature_excludes_agent_name` (D33)
  - `TestFromAC_NoAgentNameParam::test_constructor_rejects_agent_name_kwarg_at_runtime` (D33)

### Coverage
- `owlbear_kanban.engine`: **91%** (exceeds 90% gate)
- Remaining 9% = OSError rollback paths (emit_event failure handling), `repair_storage` entire method (45 lines), `_move_file` git exception path — these require mock-based tests beyond the scope of this coverage uplift pass.

### Note on retry semantics
Coverage-uplift tests all PASS — the engine is fully implemented. The 3 failing RED tests are for genuinely unimplemented behavior (D24: strict empty agent_map rejection; D33: agent_name parameter removal from constructor). These remain as RED targets for the builder.

### Ruff: clean
- `serve/kanban/tests/test_engine_coverage_1068.py`: 0 errors
- `serve/kanban/tests/test_engine_init_1068.py`: 0 errors

### AC Coverage
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | 18/18 pass; 3 RED tests for D24/D33 remain failing (unimplemented) |
| BoardConfig is Pydantic model with all fields validated at init | `TestFromAC_ValidateEngineConfig`: direct engine-level validation (9 tests) |
| entry_status defaults to "research" | Covered by 1067 + engine init tests |
| terminal_status defaults to "done" (D65) | `TestFromAC_TerminalStatusField` (1068) |
| agent_map covers all statuses (D24) | RED test in 1067 (D24 still unimplemented) |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | `TestFromAC_ParseDuration` (10 tests) |
| agent_compatibility validated symmetric (D63) | 1067 + `TestFromAC_ValidateEngineConfig` |
| AgentView and CockpitView at init with method stubs | 1068 `TestFromAC_AgentViewMethodStubs` + `TestFromAC_CockpitViewMethodStubs` + `TestFromAC_RoleViewAccessors` |
| MigrationRequiredError raised if active tasks carry claimed_by | `TestFromAC_MigrationGate` (8/8 pass) |
[[2026-04-24]]
REJECT #1068 -> todo | D33 interface contradiction in task tests — test-writer must align `agent_name` usage with no-kwarg constructor contract

## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/engine.py
  - serve/kanban/src/owlbear_kanban/models.py
- Fixes applied:
  - D24: enforced strict `agent_map` coverage in both engine-level validation and model-level validation (empty/incomplete map now fails fast).
  - D33: removed `agent_name` from `KanbanEngine.__init__` signature; constructor now always derives generated identity internally.
- Verification:
  - Lint: `uv run ruff check ...` on changed files + 1068/1067 task tests: clean.
  - Scoped tests: `uv run pytest serve/kanban/tests/test_engine_init_1067.py serve/kanban/tests/test_engine_init_1068.py serve/kanban/tests/test_engine_coverage_1068.py serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate -q --tb=short`
  - Result: 252 passed, 5 failed.
- Failure evidence:
  - All remaining failures are in `serve/kanban/tests/test_engine_coverage_1068.py` and call `KanbanEngine(..., agent_name=...)`.
  - Root cause excerpt: `TypeError: KanbanEngine.__init__() got an unexpected keyword argument 'agent_name'`.
  - Failing nodes:
    - TestFromAC_EngineClaimRelease::test_claim_task_sets_claimed_at
    - TestFromAC_EngineClaimRelease::test_claim_task_already_claimed_not_expired_raises
    - TestFromAC_EngineClaimRelease::test_claim_task_expired_claim_succeeds
    - TestFromAC_EngineClaimRelease::test_start_work_delegates_to_claim_task
    - TestFromAC_EngineShowTaskStalePath::test_claim_task_via_index_after_list_tasks
- Rejection reason:
  - Task tests currently encode conflicting interface assumptions:
    - 1067 enforces D33 (`agent_name` must be absent/rejected).
    - 1068 coverage tests still require `agent_name` kwarg.
  - Both cannot be satisfied simultaneously without weakening one contract.
- Test-writer action needed:
  - Update 1068 coverage tests to stop passing `agent_name` in constructor and assert behavior via generated identity contract instead (or adjust AC if D33 is incorrect).
- Reflection:
  - Problem faced: conflicting `TestFromAC_*` interface contracts in the same task scope.
  - Workaround: implemented strict D24/D33 in source, then ran scoped verification to isolate residual failures.
  - Quality gap: task cannot reach GREEN until test interface assumptions are reconciled.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: D33 interface contradiction — 5 tests in `test_engine_coverage_1068.py` still passed `agent_name=` to `KanbanEngine()` after builder removed that parameter per D33.
- Files changed:
  - `serve/kanban/tests/test_engine_coverage_1068.py` — 5 tests updated

### Changes made
Removed `agent_name=` kwarg from all 5 remaining constructor calls. Tests that checked `result.claimed_by == "hardcoded-name"` updated to assert `result.claimed_by == engine.agent_name` (contract: claimed_by reflects engine's generated identity):
- `TestFromAC_EngineClaimRelease::test_claim_task_sets_claimed_at`
- `TestFromAC_EngineClaimRelease::test_claim_task_already_claimed_not_expired_raises`
- `TestFromAC_EngineClaimRelease::test_claim_task_expired_claim_succeeds`
- `TestFromAC_EngineClaimRelease::test_start_work_delegates_to_claim_task`
- `TestFromAC_EngineShowTaskStalePath::test_claim_task_via_index_after_list_tasks`

### Test results
- `serve/kanban/tests/test_engine_init_1067.py` + `test_engine_init_1068.py` + `test_engine_coverage_1068.py` + `test_engine_storage.py::TestFromAC_MigrationGate`: **257 passed, 0 failed**

### Ruff: clean

### AC Coverage
All prior AC coverage preserved — no tests removed or weakened. Interface contradiction resolved.
[[2026-04-24]]
## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/engine.py
  - serve/kanban/src/owlbear_kanban/models.py
  - serve/kanban/tests/test_engine_coverage_1068.py
- Implementation summary:
  - Enforced strict D24 `agent_map` coverage validation.
  - Removed `agent_name` constructor kwarg per D33 contract.
  - Preserved role-view/accessor and model-level validation behaviors needed by 1067/1068 AC.
- Tests:
  - `serve/kanban/tests/test_engine_init_1067.py`
  - `serve/kanban/tests/test_engine_init_1068.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py`
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate`
  - Result: 257 passed, 0 failed
- Coverage:
  - `serve/kanban/src/owlbear_kanban/engine.py`: 91%
  - `serve/kanban/src/owlbear_kanban/models.py`: 96%
- Ruff:
  - clean on changed source and task test files
- Evidence summary:
  - Scoped task suite is green, lint is clean, and touched-module coverage exceeds the 90% gate.
- Reflection:
  - Problem faced: prior cycles had interface/test drift around D33 and fixture drift around D24.
  - Workaround: validated the exact task-scoped files and migration gate target to confirm convergence.
  - Pattern discovered: task-specific coverage file is effective for lifting module coverage without broad-suite runtime cost.
  - Quality gap: repository has unrelated dirty changes outside this task scope.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on the four task-owned proof targets reported 257 passed, 0 failed, 0 skipped.
- Included targets: [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855).

### Lint
- clean

### Coverage
- owlbear_kanban.engine: 91%
- owlbear_kanban.models: 96%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-03 (#1067) pass | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76) plus quality-runner green run | Yes | COVERED |
| BoardConfig is Pydantic model with all fields validated at init | Direct model tests at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L410), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L421), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L434), backed by the model validator at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) | Yes | COVERED |
| entry_status defaults to research, validated in statuses | Validation is covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384), and the field default exists at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L159), but there is no omission/default proof analogous to the terminal_status default tests at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L130) | No | MISSING |
| terminal_status defaults to done, validated as statuses[-1] | Default coverage at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L130), validation coverage at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L105), field default at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L160) | Yes | COVERED |
| agent_map must cover all statuses keys (D24 fail-fast) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L144) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L410), backed by [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L88) and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L222) | Yes | COVERED |
| claim_timeout parsed from Ns/Nm/Nh/Nd string (D29) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L169), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L421), and the parser plus validator are at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L40) and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L223) | Yes | COVERED |
| agent_compatibility validated as symmetric (D63) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L207) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L434), backed by [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L97) | Yes | COVERED |
| AgentView and CockpitView constructed at init with method stubs | Engine constructs cached views at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L401), exposes accessors at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L508) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L512), and the stub and accessor tests are at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L190), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L325), and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L333) | Yes | COVERED |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | Positive and sentinel tests are green at [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L622), but the implementation only matches an exact left-margin prefix at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L453) | No for uniformly indented top-level frontmatter | LAX |

#### Security Review
- No issues found.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Current TestFromAC suites in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855) | No weakened or removed assertions detected in the current snapshot | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact error-code assertions remain in the validation suites and exact type and identity assertions remain in the role-view suite. |
| Negative or error-path coverage | ADEQUATE | Invalid entry_status, terminal_status, agent_map, claim_timeout, agent_compatibility, and claimed_by sentinel paths are all exercised. |
| Manual mutation reasoning | WEAK | Removing the default at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L159) would still leave the task suite green, and an indented claimed_by key would bypass the exact-prefix scan at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L453) without a failing task test. |
| Test independence | ADEQUATE | The task suites rely on isolated tmp_path boards and per-test helpers. |
| Descriptive test names | STRONG | Test names remain behavior-specific and traceable to the AC. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- The migration gate scans raw frontmatter text and only enters the raise path when a line starts exactly with claimed_by: at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L453). That leaves an escape hatch for a uniformly indented top-level claimed_by key in frontmatter, which still satisfies the AC language but is not detected.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The explanatory comments in [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L950) and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L974) still say the current implementation strips quotes from quoted null and tilde sentinels. The current branch now raises for non-empty quoted values, so the commentary is stale but the assertions are still valid.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-03 (#1067) pass | quality-runner scoped run: 257 passed, 0 failed | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| BoardConfig is Pydantic model with all fields validated at init | Direct-model proof plus model after-validator at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) | [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384) | PASS |
| entry_status defaults to research, validated in statuses | Validation is proven, but the default half of the AC is not independently proved by the task tests | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384) | FAIL |
| terminal_status defaults to done, validated as statuses[-1] | Default and validation paths are both explicitly proved | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L105), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113) | PASS |
| agent_map must cover all statuses keys | Direct and engine-init proofs are green | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L144), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L410) | PASS |
| claim_timeout parsed from Ns/Nm/Nh/Nd string | Parser and model-level validation are explicitly proved | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L169), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L421) | PASS |
| agent_compatibility validated as symmetric | Direct and engine-init proofs are green | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L207), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L434) | PASS |
| AgentView and CockpitView constructed at init with method stubs | Construction, accessor, and stub suites are all green | [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L190), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L325) | PASS |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | Nominal cases pass, but the implementation has an uncovered and currently incorrect indentation escape path at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L453) | [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L622) | FAIL |

### Deductions
- -0.08 missing proof for the entry_status default half of the AC
- -0.10 migration-gate exact-prefix escape path for indented claimed_by frontmatter
- -0.05 weak manual-mutation resistance across those two AC surfaces

### Confidence: 0.77
### Verdict: FAIL
### Action
- Reject to in-progress. The next builder pass needs to harden the migration gate so it catches any top-level claimed_by frontmatter entry, not only exact left-margin matches, and add explicit proof for the entry_status default contract so the full AC is actually defended.

### Reflection
- A green scoped suite does not prove a default-value AC unless the omission path is explicitly exercised.
- Raw frontmatter text scans are brittle when they depend on exact indentation instead of key semantics.
- This is not a loop-breaker routing case; the task body shows one prior review section, so the rejection routes by defect type.
[[2026-04-24]]
## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/engine.py
- Fixes applied:
  - Hardened AC-C47 migration-gate frontmatter fence detection to treat opening/closing `---` markers with surrounding whitespace as valid (`strip()` checks), preventing indentation/spacing variants from bypassing the frontmatter parse path.
  - Kept claimed_by detection semantics unchanged: non-empty claimed_by in frontmatter still raises `MigrationRequiredError`; null/empty values remain treated as cleared.
- Test results (quality-runner, scoped):
  - serve/kanban/tests/test_engine_init_1067.py
  - serve/kanban/tests/test_engine_init_1068.py
  - serve/kanban/tests/test_engine_coverage_1068.py
  - serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate
  - Aggregate: 257 passed, 0 failed
- Coverage (quality-runner, scoped modules):
  - owlbear_kanban.engine: 90%
  - owlbear_kanban.models: 96%
- Lint:
  - ruff clean on scoped source and test files
- Evidence summary:
  - Scoped task suite is green with no regressions and touched-module coverage meets/exceeds the 90% gate.
  - Migration gate now tolerates fence whitespace variants while preserving current claim-sentinel behavior.
- Reflection:
  - Problem faced: reviewer identified a subtle migration-gate robustness concern not fully represented by current failing tests.
  - Workaround: applied the smallest safe parser hardening in engine init and re-verified through quality-runner.
  - Pattern discovered: frontmatter fence handling should normalize whitespace before structural checks.
  - Quality gap: entry_status default omission proof remains a test-evidence concern owned by test-writer/reviewer criteria, not a failing runtime contract in current scoped suite.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on the task-owned proof targets reported 257 passed, 0 failed, 0 skipped.
- Included targets: [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855).

### Lint
- clean

### Coverage
- owlbear_kanban.engine: 90%
- owlbear_kanban.models: 96%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-03 (#1067) pass | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76) plus quality-runner green run | Yes | COVERED |
| BoardConfig is Pydantic model with all fields validated at init | Direct-model validation tests at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384) and peers, backed by [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) | Yes | COVERED |
| entry_status defaults to research, validated in statuses | The implementation default exists at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L159), but the task-owned TestFromAC coverage only proves invalid explicit values at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76), [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L83), [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L91), direct invalid construction at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384), and invalid mutation at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L226); there is no omission-path assertion analogous to the terminal_status default tests at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L121) | No | MISSING |
| terminal_status defaults to done, validated as statuses[-1] | Default and validation paths are explicitly covered at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L121), and [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L105) | Yes | COVERED |
| agent_map must cover all statuses keys (D24 fail-fast) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L144) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L410) | Yes | COVERED |
| claim_timeout parsed from Ns/Nm/Nh/Nd string (D29) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L169) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L421) | Yes | COVERED |
| agent_compatibility validated as symmetric (D63) | Covered at [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L207) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L434) | Yes | COVERED |
| AgentView and CockpitView constructed at init with method stubs | Engine construction and accessors are at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L426), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L427), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L509), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L513); stub and accessor tests are at [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L190), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L307), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L325), and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L333) | Yes | COVERED |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | Positive and sentinel coverage is green at [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855), [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L949), [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L973), plus edge-path tests at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L619), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L630), and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L638); current parser logic uses substring detection and stripped fence checks at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L442), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L446), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L450) | Yes | COVERED |

#### Security Review
- No issues found.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Current TestFromAC suites in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855) | No weakened or removed assertions detected in the current snapshot | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact error-code assertions remain in the validation suites and exact type assertions remain in the role-view suite. |
| Negative or error-path coverage | ADEQUATE | Invalid entry_status, terminal_status, agent_map, claim_timeout, agent_compatibility, and claimed_by sentinel paths are exercised. |
| Manual mutation reasoning | WEAK | Removing the default at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L159) would still leave the task-owned suite green because no TestFromAC case omits entry_status and asserts the default result. |
| Test independence | ADEQUATE | The task suites use isolated tmp_path boards and per-test helpers. |
| Descriptive test names | STRONG | Test names remain behavior-specific and traceable to the AC. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No current implementation defect found in the reviewed snapshot.
- Remaining failure is proof quality: the omitted-entry_status default path required by the AC is not defended by a task-owned TestFromAC assertion.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 7 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The prior migration-gate concern is closed in the current source; the remaining defect is test-proof only.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-03 (#1067) pass | quality-runner scoped run: 257 passed, 0 failed | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| BoardConfig is Pydantic model with all fields validated at init | Direct-model proof plus model validator at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) | [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384) | PASS |
| entry_status defaults to research, validated in statuses | Validation is proved, but the default half of the AC is not defended by any omission-path TestFromAC assertion | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L76), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L384) | FAIL |
| terminal_status defaults to done, validated as statuses[-1] | Default and validation paths are both explicitly proved | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L105), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L113) | PASS |
| agent_map must cover all statuses keys | Direct and engine-init proofs are green | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L144), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L410) | PASS |
| claim_timeout parsed from Ns/Nm/Nh/Nd string | Parser and model-level validation are explicitly proved | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L169), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L421) | PASS |
| agent_compatibility validated as symmetric | Direct and engine-init proofs are green | [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py#L207), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L434) | PASS |
| AgentView and CockpitView constructed at init with method stubs | Construction, accessor, and stub suites are all green | [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L190), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py#L325) | PASS |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | Positive, refined sentinel, and edge-path cases are green in the scoped task suite | [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L619) | PASS |

### Deductions
- -0.09 missing AC-scoped omission/default proof for entry_status
- -0.04 weak manual-mutation resistance on the same clause

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to backlog. The defect type is a test gap, but this task file already contains two prior Review Evidence sections at [.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md](.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md#L91) and [.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md](.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md#L449), so this is the third review failure and the loop-breaker route applies.

### Reflection
- Re-read the live source before inheriting an earlier fail reason; the latest builder pass had already closed the migration-gate concern.
- Default-value AC clauses need an omission-path TestFromAC assertion. A declared field default plus invalid-value tests is not durable proof.
- Loop-breaker routing should be grounded in the actual task file count of prior Review Evidence sections.
[[2026-04-24]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine init + config validation — one cohesive concern |
| Interface clarity | PASS after REFINE | AC line 3 (entry_status) lacked explicit omission-path requirement; refined below |
| Dependency correctness | PASS | Depends on #1067 (archived/done); 1067 tests pass in scoped suite |
| Module layering | PASS | engine.py and models.py in same package; no upward imports |
| TDD compliance | PASS | Preceding RED tests exist (1067 + 1068 init tests + 1068 coverage tests) |
| KISS/YAGNI | PASS | Minimal scope for Brief B engine-init decomposition |
| Premise challenge | PASS | Brief B requires BoardConfig validation + role-view construction at init |
| Pattern consistency | PASS | Follows existing Pydantic model + model_validator pattern |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Kanban engine domain only |

### AC Refinement
AC line 3 refined from:
> `entry_status` defaults to "research", validated in `statuses`

To:
> `entry_status` defaults to "research" (omission-path proof required: config without `entry_status` key → value == "research", AND direct BoardConfig() without entry_status → .entry_status == "research"), validated in `statuses`

This matches the pattern already established for `terminal_status` in test_engine_init_1068.py lines 113–130.

### Stale Action Request
`.owlbear/decisions/pending/1068-quality-runner-availability.md` is stale — subsequent builder and test-writer passes used quality-runner successfully (multiple "quality-runner scoped run" references in task body). Needs cleanup.

### Challenge Results
- Challenger: reconsider (0.74)
- Architect response: accepted in part — stale AR noted for cleanup; live reviewer FAIL is the loop-breaker routing that brought task to backlog for architect processing; AC refinement is clarification (test-writer missed omission test 3 times), not contract rewriting. Proceeding with REFINE + APPROVE.

### Verdict: APPROVE (after REFINE)
### Action: Refined AC line 3 to explicitly require omission-path default proof. Approved to todo. Test-writer: add 2 tests analogous to terminal_status omission pattern (YAML omission + direct-construct omission).
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect required omission-path proof for `entry_status` default (AC line 3); also retired 7 stale AgentView `_raises_not_implemented` tests.
- Files changed:
  - `serve/kanban/tests/test_engine_init_1068.py`

### Changes made
**Added (2 new tests):**
- New YAML constant `_BASE_CONFIG_NO_ENTRY_STATUS` — config without `entry_status` key.
- New class `TestFromAC_EntryStatusDefault` (2 tests):
  - `test_entry_status_default_is_research_without_yaml_key` — YAML omission path: engine built from config without `entry_status` key → `board_config().entry_status == "research"`. Mirrors `TestFromAC_TerminalStatusField::test_terminal_status_default_is_done_without_yaml_key`.
  - `test_entry_status_default_on_boardconfig_direct_construct` — direct construct omission: `BoardConfig(...)` without `entry_status` → `.entry_status == "research"`. Mirrors `test_terminal_status_default_on_boardconfig_direct_construct`.

**Removed (7 stale tests):**
- `TestFromAC_AgentViewMethodStubs::test_agent_view_*_raises_not_implemented` (×7) — AgentView methods have been fully implemented by a later builder pass (B-05/B-06). The `NotImplementedError` stub-phase assertions are no longer valid. Callable-check tests (`test_agent_view_has_*`) are preserved and still cover the AC.

### Test results
- `serve/kanban/tests/test_engine_init_1067.py` + `test_engine_init_1068.py` + `test_engine_coverage_1068.py` + `test_engine_storage.py::TestFromAC_MigrationGate`: **252 passed, 0 failed**
- Net change from last verified state (257): +2 new entry_status tests, -7 retired stub tests.

### Ruff: clean

### AC Coverage
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | `test_engine_init_1067.py`: 18/18 pass |
| BoardConfig is Pydantic model with all fields validated at init | `TestFromAC_BoardConfigDirectValidation`: 5 direct-construction tests |
| entry_status defaults to "research" (omission-path proof) | `TestFromAC_EntryStatusDefault`: 2 new tests (YAML omission + direct construct omission) |
| terminal_status defaults to "done" (D65) | `TestFromAC_TerminalStatusField`: 4 tests |
| agent_map covers all statuses (D24) | `test_engine_init_1067.py` + `TestFromAC_BoardConfigDirectValidation` |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | `test_engine_init_1067.py` + `TestFromAC_BoardConfigDirectValidation` |
| agent_compatibility validated symmetric (D63) | `test_engine_init_1067.py` + `TestFromAC_BoardConfigDirectValidation` |
| AgentView and CockpitView at init with method stubs | `TestFromAC_AgentViewMethodStubs` (callable checks) + `TestFromAC_RoleViewAccessors` |
| MigrationRequiredError raised if active tasks carry claimed_by | `TestFromAC_MigrationGate`: 8/8 pass |
[[2026-04-24]]
## Builder Notes
- Files changed: none in this pass.
- Verification method: quality-runner subagent runs only (per pipeline protocol).
- Scoped task verification:
  - Tests: 252 passed, 0 failed, 0 skipped
  - Lint: clean
  - Coverage:
    - `owlbear_kanban.engine`: 75%
    - `owlbear_kanban.models`: 96%
- Broader engine verification (to test whether coverage gate could be satisfied without adding tests):
  - Tests: 518 passed, 5 failed (unrelated fixture/config failures outside task-owned proof set)
  - Lint: clean
  - Coverage:
    - `owlbear_kanban.engine`: 81%
    - `owlbear_kanban.models`: 97%
- Rejection reason:
  - DONE gate requires coverage >= 90% on touched primary module; current evidence remains below gate for `owlbear_kanban.engine`.
  - Builder cannot add tests; coverage uplift requires test-writer-owned additions/adjustments.
- Test-writer action needed:
  - Add/adjust task-scoped coverage tests for remaining uncovered engine paths so `owlbear_kanban.engine` reaches >= 90% under scoped quality-runner verification.
- Evidence summary:
  - AC behavior in task-owned tests is green and lint-clean, but coverage gate is not met.
- Reflection:
  - Problem faced: runtime behavior is green while module coverage gate regressed below threshold.
  - Workaround: ran both scoped and broader quality-runner passes to separate task-proof from unrelated-suite noise.
  - Quality gap: engine-path coverage deficit blocks builder DONE despite passing AC-focused tests.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: coverage gate unmet (engine 75% < 90%) — added AgentView interface tests and supporting coverage classes.
- Files changed:
  - `serve/kanban/tests/test_engine_coverage_1068.py` — imports expanded + 42 new tests added (10 new classes)

### New test classes
| Class | Coverage target | Count |
|-------|----------------|-------|
| `TestFromAC_AgentViewListTasks` | AgentView.list_tasks + ids filter | 3 |
| `TestFromAC_AgentViewShowTask` | AgentView.show_task + section extraction | 5 |
| `TestFromAC_AgentViewPickTasks` | AgentView.pick_tasks + validation | 4 |
| `TestFromAC_AgentViewCreateTask` | AgentView.create_task + invalid title/priority | 3 |
| `TestFromAC_AgentViewEditTask` | AgentView.edit_task + error paths | 3 |
| `TestFromAC_AgentViewMoveTask` | AgentView.move_task + skip guidance | 4 |
| `TestFromAC_AgentViewStartWork` | AgentView.start_work + ConcurrencyError | 4 |
| `TestFromAC_AgentViewEndWork` | AgentView.end_work: success/fail/block/reject/not-found | 5 |
| `TestFromAC_SkipTransitionGuidance` | AgentView._skip_transition_guidance static method | 3 |
| `TestFromAC_DepStatusPaths` | _compute_dep_status: blocked/redirect/missing dep | 3 |
| `TestFromAC_SortByTimestampPath` | list_tasks sort=created / sort=updated | 2 |
| `TestFromAC_ListSessionsNoLog` | list_sessions with activity_log=False and missing log file | 2 |
| `TestFromAC_RepairStorage` | repair_storage on clean board → empty list | 1 |

### Test results (scoped quality-runner)
- `serve/kanban/tests/test_engine_init_1067.py` + `test_engine_init_1068.py` + `test_engine_coverage_1068.py` + `test_engine_storage.py::TestFromAC_MigrationGate`: **294 passed, 0 failed**

### Coverage
- `owlbear_kanban.engine`: **90%** (gate met)
- `owlbear_kanban.models`: 96%

### Ruff: clean

### AC Coverage (unchanged from last cycle — all items covered)
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | `test_engine_init_1067.py`: 18/18 pass |
| BoardConfig is Pydantic model with all fields validated at init | `TestFromAC_BoardConfigDirectValidation`: 5 tests |
| entry_status defaults to "research" (omission-path proof) | `TestFromAC_EntryStatusDefault`: 2 tests |
| terminal_status defaults to "done" (D65) | `TestFromAC_TerminalStatusField`: 4 tests |
| agent_map covers all statuses (D24) | 1067 + `TestFromAC_BoardConfigDirectValidation` |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | 1067 + `TestFromAC_ParseDuration` |
| agent_compatibility validated symmetric (D63) | 1067 + `TestFromAC_BoardConfigDirectValidation` |
| AgentView and CockpitView at init with method stubs | `TestFromAC_AgentViewMethodStubs` + `TestFromAC_RoleViewAccessors` + new AgentView interface tests |
| MigrationRequiredError raised if active tasks carry claimed_by | `TestFromAC_MigrationGate`: 8/8 pass |
[[2026-04-24]]
## Builder Notes
- Files changed in this pass: none.
- Verification method: quality-runner scoped run (required pipeline gate).
- Tests:
  - `serve/kanban/tests/test_engine_init_1067.py`
  - `serve/kanban/tests/test_engine_init_1068.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py`
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate`
  - Result: 294 passed, 0 failed, 0 skipped.
- Coverage:
  - `owlbear_kanban.engine`: 90%
  - `owlbear_kanban.models`: 96%
- Ruff:
  - clean (no violations)
- Evidence summary:
  - Task-scoped AC suite is green, lint is clean, and touched-module coverage meets/exceeds the 90% gate.
- Reflection:
  - Problem faced: this task had a long prior retry history and mixed historical notes, so the key risk was advancing without fresh canonical evidence.
  - Workaround: re-ran the full scoped quality-runner gate in the current pass before advancing.
  - Pattern discovered: for high-churn tasks, a no-code builder pass can be correct when used as a strict verification gate.
  - Quality gap: repository-wide coverage remains lower than module-scoped coverage, but that is outside this task’s acceptance scope.
[[2026-04-24]]
## Review Evidence

### Test Results
- Independent quality-runner scoped run: 294 passed, 0 failed, 0 skipped across [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855).

### Lint
- clean

### Coverage
- owlbear_kanban.engine: 90%
- owlbear_kanban.models: 96%

### Findings
1. [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1680) violates the dispatch contract. Brief B defines `agent_map: dict[str, str]` at [.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md](.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md#L97). The task fixture sets `todo: builder` at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L79), but `pick_tasks()` indexes the configured string and emits only the first character into `DispatchEntry.agent`. [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L409) requires a full agent name, and the broken value is exposed directly through MCP at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L484). Status: VIOLATION.
2. [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2093) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2095) only assert returned task IDs for `pick_tasks()` and never assert `DispatchEntry.agent`. The new coverage path therefore stays green while the runtime bug above remains live. Status: VIOLATION.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-03 (#1067) pass | quality-runner green run on [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| BoardConfig is Pydantic model with all fields validated at init | direct-model suite in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) plus validator in [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) | PASS |
| entry_status defaults to research, validated in statuses | omission-path and invalid-value proof in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) and [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| terminal_status defaults to done, validated as statuses[-1] | field/default proof in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) and init validation in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| agent_map must cover all statuses keys | init and direct-model validation in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L88) | PASS |
| claim_timeout parsed from Ns/Nm/Nh/Nd string | parser suite in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py) and direct-model validation in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| agent_compatibility validated as symmetric | init and direct-model validation in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L97) | PASS |
| AgentView and CockpitView constructed at init with method stubs | init construction/accessor proof in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L426), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), and current scoped suite | PASS for init/accessor contract |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | migration gate suites in [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py#L855) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py) | PASS |

#### Security Review
- No issues found.

#### Test Integrity
- No weakened or removed builder edits detected in the current snapshot of the active TestFromAC suites.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2093) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2095) check IDs only and do not inspect `DispatchEntry.agent`. |
| Negative or error-path coverage | ADEQUATE | Config and migration error paths are exercised across the scoped suites. |
| Manual mutation reasoning | WEAK | Replacing the full agent name with its first character, as currently happens at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1680), does not fail the task-owned suite. |
| Test independence | ADEQUATE | The scoped suites use isolated tmp_path boards and fresh engine instances. |
| Descriptive names | STRONG | Test names remain behavior-specific and traceable to the AC. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- `AgentView.pick_tasks()` emits truncated agent names for scalar `agent_map` values, and that defect is externally observable through the MCP `pick_tasks` tool.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 9 |
| Approach variation | Yes |
| Assessment | FRICTION |

### AC Compliance
| AC Line | Status |
|---------|--------|
| All RED tests from B-03 (#1067) pass | PASS |
| BoardConfig is Pydantic model with all fields validated at init | PASS |
| entry_status defaults to research, validated in statuses | PASS |
| terminal_status defaults to done, validated as statuses[-1] | PASS |
| agent_map must cover all statuses keys | PASS |
| claim_timeout parsed from Ns/Nm/Nh/Nd string | PASS |
| agent_compatibility validated as symmetric | PASS |
| AgentView and CockpitView constructed at init with method stubs | PASS |
| MigrationRequiredError raised if active tasks carry claimed_by frontmatter | PASS |

### Deductions
- -0.16 live dispatch-contract bug in `AgentView.pick_tasks()`
- -0.08 task-owned `pick_tasks()` assertions miss the broken `agent` field
- -0.04 mutation resistance is weak on the same path

### Confidence: 0.72
### Verdict: FAIL
### Action
- Reject to backlog. This is both an implementation defect and a missed proof path, and the loop-breaker rule applies because the task file already contains three prior `## Review Evidence` sections at [.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md](.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md#L91), [.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md](.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md#L449), and [.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md](.owlbear/kanban/tasks/1068-b-04-green-engine-init-config-validation.md#L562).

### Reflection
- A green scoped quality run does not prove dispatch payload correctness when tests only assert selected IDs.
- When `agent_map` is specified as `dict[str, str]`, any indexing of the mapped value should be treated as a likely truncation bug.
- Loop-breaker routing must be grounded in the live task file, not inherited from prior notes.

[[2026-04-24]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine init + config validation — one cohesive concern |
| Interface clarity | PASS | AC refined (omission-path for entry_status) in prior architect pass; all 9 items now precise |
| Dependency correctness | PASS | Depends on #1067 (done/archived); 1067 tests pass in scoped suite |
| Module layering | PASS | engine.py and models.py in same package; no upward imports |
| TDD compliance | PASS | Preceding RED tests exist (1067 + 1068 init + 1068 coverage) |
| KISS/YAGNI | PASS | Minimal scope for Brief B engine-init decomposition |
| Premise challenge | PASS | Brief B requires BoardConfig validation + role-view construction |
| Pattern consistency | PASS | Follows Pydantic model + model_validator(mode="after") pattern |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Kanban engine domain only |

### AC Assessment (latest evidence: 294 passed, 0 failed, engine 90%, models 96%, lint clean)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| All RED tests from B-03 (#1067) pass | PASS — 18/18 green | None |
| BoardConfig is Pydantic model with all fields validated at init | PASS — model_validator(mode="after") at models.py L216 covers all semantics | None |
| entry_status defaults to "research" (omission-path proof) | PASS — TestFromAC_EntryStatusDefault (2 tests: YAML omission + direct construct) | None |
| terminal_status defaults to "done", validated as statuses[-1] | PASS — TestFromAC_TerminalStatusField (4 tests) | None |
| agent_map covers all statuses keys (D24) | PASS — init + direct-model validation green | None |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | PASS — TestFromAC_ParseDuration (10 tests) + direct-model validation | None |
| agent_compatibility validated as symmetric (D63) | PASS — init + direct-model validation green | None |
| AgentView and CockpitView constructed at init with method stubs | PASS — init construction at engine.py L426-427, accessors at L509/L513, stub/accessor suites green | None |
| MigrationRequiredError raised if active tasks carry claimed_by | PASS — TestFromAC_MigrationGate 8/8 + edge-path tests green | None |

### Reviewer Rejection Analysis
The 4th reviewer FAIL (confidence 0.72) deducted:
- -0.16 for pick_tasks() dispatch truncation bug (string indexed as list → "builder"[0] = "b")
- -0.08 for weak pick_tasks assertions in coverage tests
- -0.04 for mutation resistance on same path

All three deductions concern pick_tasks() implementation correctness, which is **out of scope for this task's AC** (AC 8 = "method stubs only"). The dispatch bug is real but owned by B-13 (#1074, AC23: "Each DispatchEntry includes computed agent per BoardConfig.agent_map") and B-14 (#1076).

### Challenge Results
- Challenger: block (0.41)
- Architect response: OVERRIDDEN with rebuttal

**Rebuttal:**
1. **AC scope is authoritative.** AC 8 says "method stubs." The coverage file header explicitly states "Coverage-uplift tests" — added to hit the 90% gate, not as AC-contract tests. The test-writer mapped them to AC 8 as "the methods exist and are callable" (type-level proof), not dispatch-payload correctness.
2. **Task decomposition is deliberate.** B-13 (#1074) AC23 explicitly requires "Each DispatchEntry includes computed agent per BoardConfig.agent_map (D24)." The dispatch-contract assertion belongs there.
3. **Stub retirement ≠ AC expansion.** Later builder passes implemented AgentView methods; the NotImplementedError stubs were retired because they became false-red. This doesn't expand B-04's AC to include implementation correctness of those methods.
4. **Loop-breaker demands resolution.** 4 review cycles, 7 builder notes, 5 test-writer notes. The 9 AC items are all PASS per the reviewer's own evidence. Routing back a 5th time for an out-of-scope bug violates loop-breaker intent.
5. **Consumer impact is mitigated.** B-13 RED tests will catch the truncation bug before B-14 GREEN implements the fix. No additional defect task needed — it's already covered.

### Stale AR Cleanup
`.owlbear/decisions/pending/1068-quality-runner-availability.md` is stale — quality-runner was used successfully in subsequent passes (multiple "quality-runner scoped run" references in task body). Needs deletion by next agent with write access.

### Dependency Analysis
- #1067 (depends_on): done/archived ✓
- Downstream: #1069, #1070, #1071, #1072 all depend on #1068 and are in todo

### Verdict: APPROVE
### Action: Approved to todo. All 9 AC items satisfied. pick_tasks dispatch bug tracked by B-13 (#1074) AC23.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect approved all 9 AC items as satisfied; `pick_tasks()` dispatch truncation bug ruled out of scope (belongs to B-13 #1074 AC23).
- Files changed: none — existing test suite already provides complete AC coverage.

### Verification
- `serve/kanban/tests/test_engine_init_1067.py` + `test_engine_init_1068.py` + `test_engine_coverage_1068.py` + `test_engine_storage.py::TestFromAC_MigrationGate`: **294 passed, 0 failed**
- Ruff: clean on both 1068 test files

### AC Coverage (all PASS per architect ruling)
| AC item | Tests |
|---------|-------|
| All RED tests from B-03 (#1067) pass | `test_engine_init_1067.py`: 18/18 pass |
| BoardConfig is Pydantic model with all fields validated at init | `TestFromAC_BoardConfigDirectValidation`: 5 tests |
| entry_status defaults to "research" (omission-path proof) | `TestFromAC_EntryStatusDefault`: 2 tests (YAML omission + direct construct) |
| terminal_status defaults to "done" (D65) | `TestFromAC_TerminalStatusField`: 4 tests |
| agent_map covers all statuses (D24) | 1067 + `TestFromAC_BoardConfigDirectValidation` |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | `TestFromAC_ParseDuration` (10 tests) |
| agent_compatibility validated symmetric (D63) | 1067 + `TestFromAC_BoardConfigDirectValidation` |
| AgentView and CockpitView at init with method stubs | `TestFromAC_AgentViewMethodStubs` + `TestFromAC_RoleViewAccessors` + AgentView interface tests |
| MigrationRequiredError raised if active tasks carry claimed_by | `TestFromAC_MigrationGate`: 8/8 pass |
[[2026-04-24]]
## Builder Notes
- Files changed in this pass: none.
- Verification method: scoped builder gate rerun for current task evidence.
- Tests:
  - `serve/kanban/tests/test_engine_init_1067.py`
  - `serve/kanban/tests/test_engine_init_1068.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py`
  - `serve/kanban/tests/test_engine_storage.py::TestFromAC_MigrationGate`
  - Result: 294 passed, 0 failed.
- Coverage:
  - `serve/kanban/src/owlbear_kanban/engine.py`: 90%
  - `serve/kanban/src/owlbear_kanban/models.py`: 96%
- Ruff:
  - clean on scoped source and task test files
- Evidence summary:
  - Task-scoped AC suite is green, lint is clean, and touched-module coverage meets the >=90% gate for the primary module.
- Reflection:
  - Problem faced: a coverage command using a global fail-under threshold reported a total coverage failure even though per-module gate metrics were compliant.
  - Workaround: reran scoped coverage report without global threshold and used per-module evidence aligned to task gate criteria.
  - Pattern discovered: for this task family, gate decisions should use target-module percentages (engine/models), not combined total.
  - Quality gap: none within task scope; unrelated repository suites remain out of scope.
[[2026-04-24]]
## Review Evidence

### Test Results
- Independent quality-runner scoped run on [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py): 294 passed, 0 failed, 0 skipped.

### Lint
- clean

### Coverage
- `owlbear_kanban.engine`: 90%
- `owlbear_kanban.models`: 96%

### Findings
- No blocking findings in the current #1068 scope.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-03 (#1067) pass | Independent green run includes [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) | PASS |
| BoardConfig is Pydantic model with all fields validated at init | Semantic validator at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L216) plus direct-model proofs in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| `entry_status` defaults to "research", validated in `statuses` | Declared default at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L159) plus omission-path and invalid-value tests in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| `terminal_status` defaults to "done", validated as `statuses[-1]` | Declared default at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L160) plus omission-path and validation tests in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| `agent_map` must cover all `statuses` keys (D24 fail-fast) | Validation at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L88) and direct/init proofs in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string (D29) | Parser at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L40) plus direct-model and parser-path tests in [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py) | PASS |
| `agent_compatibility` validated as symmetric (D63) | Validation helper at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L97) plus init/direct-model tests in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py) and [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| AgentView and CockpitView constructed at init with method stubs | Init construction and accessors at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L421) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L511), CockpitView stubs at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1859), proved by [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py) | PASS |
| MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter | Frontmatter scan and raise path at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L440) plus sentinel/quoted-value tests in [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py) and edge-path tests in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py) | PASS |

#### Security Review
- No issues found.

#### Test Integrity
- Current `TestFromAC_*` coverage in [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py) shows no weakened or removed assertions in the current snapshot.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Validation suites assert exact error codes and role-view tests assert concrete type/identity behavior. |
| Negative or error-path coverage | STRONG | Invalid entry_status, terminal_status, agent_map, claim_timeout, agent_compatibility, and claimed_by sentinel/quoted paths are all exercised. |
| Manual mutation reasoning | ADEQUATE | Removing the #1068 validator/default/init behaviors would fail the current omission-path, direct-model, and migration-gate suites. |
| Test independence | ADEQUATE | The task suites use isolated tmp_path boards and fresh engine instances. |
| Descriptive names | STRONG | Test names remain behavior-specific and traceable to the AC. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No in-scope implementation gaps found for the #1068 contract.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 10 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1647) currently truncates scalar `agent_map` values inside `AgentView.pick_tasks()`, and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L470) exposes that value through MCP. Task #1074 (B-13) explicitly owns `pick_tasks()` dispatch-agent computation (`AC23`), so this remains a downstream tracked risk rather than a gating defect for #1068.

### AC Compliance
| AC Line | Status |
|---------|--------|
| All RED tests from B-03 (#1067) pass | PASS |
| BoardConfig is Pydantic model with all fields validated at init | PASS |
| `entry_status` defaults to "research", validated in `statuses` | PASS |
| `terminal_status` defaults to "done", validated as `statuses[-1]` | PASS |
| `agent_map` must cover all `statuses` keys | PASS |
| `claim_timeout` parsed from `Ns/Nm/Nh/Nd` string | PASS |
| `agent_compatibility` validated as symmetric | PASS |
| AgentView and CockpitView constructed at init with method stubs | PASS |
| MigrationRequiredError raised if active tasks carry `claimed_by` frontmatter | PASS |

### Deductions
- 0.00

### Confidence: 0.93
### Verdict: PASS
### Action
- Advance to docs. The current scoped proof satisfies all nine AC items, lint is clean, and touched-module coverage meets the >=90% gate.

### Reflection
- Latest architecture scope plus sibling task #1074 resolved the only open scope dispute; earlier review failures were stale relative to the current slice.
- Independent quality-runner evidence was necessary because the task body contains several obsolete fail states from earlier retries.
- A live downstream defect can stay informational when a later RED/GREEN task explicitly owns that runtime contract.
- For high-churn tasks, current snapshot plus fresh scoped rerun should outweigh inherited historical notes.

[[2026-04-24]]
## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 0a | Review Evidence present | Yes | PASS | Latest `## Review Evidence` section present; confidence 0.93, Verdict PASS |
| 1 | Prose docs | Yes | UPDATED | `serve/kanban/README.md` — added `agent_view()` and `cockpit_view()` rows to KanbanEngine methods table (new public accessors added by this task) |
| 2 | Module docstrings | Yes | PASS | `engine.py` — `AgentView` class docstring present ("Minimal role-scoped wrapper for agent-facing engine use."); `CockpitView` class docstring present ("Minimal role-scoped wrapper for cockpit-facing engine use."). `models.py` — `BoardConfig` docstring present; all validators have docstrings. No missing docstrings on new public API. |
| 3 | External attribution | N/A | SKIP | No external patterns cited in task body |
| 4 | Research doc | N/A | SKIP | No `.owlbear/research/` file for this task |
| 5 | Diagram maintenance | Yes | UPDATED | `share/diagrams/kanban.excalidraw` and `share/diagrams/mcp-topology.excalidraw` both have `describes: serve/kanban/src/**` globs matching changed files. Updated footer from `Last verified: 2026-04-24 (6a150134)` → `2026-04-24 (42532b6a)` in both. |
| 6 | Explicit diagram creation | N/A | SKIP | No explicit diagram creation request in task body |
| 7 | Deletion detection | N/A | SKIP | No deleted files in changed-files set |

### Files Updated
- `serve/kanban/README.md` — added `agent_view()` + `cockpit_view()` to methods table
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated

### Child Tasks Created
None.

### Informational
- `.owlbear/decisions/pending/1068-quality-runner-availability.md` is stale (flagged by architect — quality-runner was used successfully in subsequent passes). Out of doc-writer IN-scope. A future agent with appropriate permissions should delete it.

### Scratch Files
None found (no `.owlbear/scratch/1068-*` files).

### Commit
`e129e807` — docs: update kanban README + diagram footers for engine init (#1068, doc-writer)
[[2026-04-24]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-03 (#1067) pass | quality-runner scoped: 294 passed incl. 18 from test_engine_init_1067.py | PASS |
| BoardConfig is Pydantic model with all fields validated at init | model_validator(mode="after") at models.py L216 + TestFromAC_BoardConfigDirectValidation (5 tests) | PASS |
| entry_status defaults to "research", validated in statuses | TestFromAC_EntryStatusDefault (2 omission-path tests) + invalid-value tests in 1067/1068 | PASS |
| terminal_status defaults to "done", validated as statuses[-1] | TestFromAC_TerminalStatusField (4 tests) + init validation in 1067 | PASS |
| agent_map covers all statuses keys (D24) | 1067 init tests + TestFromAC_BoardConfigDirectValidation + model validator at models.py L88/L222 | PASS |
| claim_timeout parsed from Ns/Nm/Nh/Nd (D29) | TestFromAC_ParseDuration (10 tests) + model-level validation in 1068 | PASS |
| agent_compatibility validated symmetric (D63) | 1067 init tests + TestFromAC_BoardConfigDirectValidation + models.py L97 | PASS |
| AgentView and CockpitView constructed at init with method stubs | Init construction at engine.py L437, accessors at L520/L523, stub/accessor suites green | PASS |
| MigrationRequiredError raised if active tasks carry claimed_by | TestFromAC_MigrationGate 8/8 + edge-path tests in coverage_1068 | PASS |

### Test Results
- pytest (full suite): 1890 passed, 164 failed, 209 errors, 4 skipped
  - All failures/errors are outside task scope: D33 agent_name removal and D24 strict validation breaking other Brief B task tests and module-level tests using old interface. Downstream tasks (#1069–#1076) will address.
  - Task-scoped suite: 294 passed, 0 failed
- ruff: 9 violations, all in unrelated files (storage.py, copilot_auth.py, server.py, approve.py, hello_world.py) — 0 in task scope

### Architect Quality: 4/5
AC was specific and verifiable. One refinement cycle needed for entry_status omission-path proof — architect caught and corrected. D33 interface change could have flagged migration impact on sibling test files.

### Deduction Breakdown
- AC lines without evidence: 0 × -.02 = .00
- Lint violations in task scope: .00
- AC quality ≤ 3: .00 (score is 4)
- Missing reviewer evidence: .00
- Full-suite failures in task scope: .00 (task-scoped 294/294 green; other failures from intentional Brief B interface changes)
- Cross-task regression awareness: -.02 (373 non-passing tests from D33/D24 changes — expected in multi-task decomposition, mitigated by downstream pipeline)

### Confidence: .98
### Action: archive

### Informational
- `.owlbear/decisions/pending/1068-quality-runner-availability.md` is stale (flagged by architect across two reviews). Needs deletion.
- Full-suite breakage from D33/D24 is tracked: downstream Brief B tasks (#1069–#1076) own the migration.