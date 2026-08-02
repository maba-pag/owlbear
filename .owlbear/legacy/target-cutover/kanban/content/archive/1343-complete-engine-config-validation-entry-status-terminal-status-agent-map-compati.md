---
id: 1343
title: 'Config validation cleanup: remove agent_name while preserving lazy agent_map'
status: archived
priority: medium
created: 2026-05-04T15:10:51.036581+00:00
updated: 2026-05-05T10:14:04.569709+00:00
tags:
- sync-blocker
- kanban
- config
- cockpit
parent:
depends_on:
- 1336
- 1351
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Most old engine-init config validation expectations are now implemented or intentionally superseded by lazy dispatch validation. The remaining deployment-relevant work is D33: remove the stale `agent_name` constructor parameter while preserving lazy `agent_map` behavior for Cockpit and other non-dispatch consumers.

## Acceptance Criteria

1. Remove `agent_name` from `KanbanEngine.__init__`.
2. Update every first-party caller, test, and benchmark that still passes `agent_name`, including Cockpit launch wiring.
3. Preserve deterministic Cockpit activity/source labeling through explicit `source="cockpit"` mutation calls or an approved replacement, not constructor state.
4. Preserve lazy `agent_map` validation: empty/incomplete `agent_map` must not fail engine construction when dispatch is not being used.
5. `AgentView.pick_tasks()` continues to raise the appropriate config error when dispatch needs missing `agent_map` entries.
6. Replace stale `test_engine_init_1067.py` assertions that require eager `agent_map` validation with tests for the lazy dispatch contract.
7. Keep already-green semantic config tests for entry status, terminal status, claim timeout, archival reason type, and symmetric compatibility.
8. Run config, lazy-agent-map, Cockpit launch/read/mutation, and engine-init tests together before completion.

## Key Files

- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/kanban/src/owlbear_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/agent_view.py`
- `serve/cockpit/src/owlbear_cockpit/main.py`
- `serve/kanban/tests/test_engine_init_1067.py`
- `tests/test_engine_lazy_agent_map_1221.py`
- `tests/test_cockpit_launch.py`

## Audit Evidence

- `serve/kanban/tests/test_engine_init_1067.py` now has 13 passed / 4 failed, not 15 broad failures.
- Entry status, terminal status, claim timeout, archival reason type, AgentView existence, and symmetric compatibility are already implemented.
- The old eager `agent_map` init failures conflict with current lazy validation and Cockpit's ability to start with `agent_map: {}`.
- User decision during deployment audit: keep D33 and remove `agent_name`, despite current Cockpit/tests still using it.

## Source

Deployment audit reconciliation, 2026-05-04.
[[2026-05-05]]

## Architecture Review
### AC Refinements Applied
- AC1: Clarified that internal random name generation and `agent_name` property are preserved; only the constructor keyword parameter is removed.
- AC3: Removed vague "or an approved replacement" — CockpitView already passes explicit `source="cockpit"` on all mutations.
- AC6: Clarified scope — replace only the 4 failing eager-validation assertions, keep the 13 passing tests.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One logical change: remove constructor param + preserve lazy behavior |
| Interface clarity | PASS | After refinement, all ACs are mechanically verifiable |
| Dependency correctness | PASS | #1336 (archived), #1351 (archived) — both done |
| Module layering | PASS | No upward imports introduced; kanban←cockpit direction preserved |
| TDD compliance | PASS | test_engine_lazy_agent_map_1221.py (RED) covers AC4/AC5; test_engine_init_1067.py existing for AC6 |
| KISS/YAGNI | PASS | Removing unused state, no new abstractions |
| Premise challenge | PASS | User decision during deployment audit explicitly chose to remove agent_name |
| Pattern consistency | PASS | Follows existing source= parameter pattern on mutations |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban engine + its callers (one domain) |

### Challenge Results
- Challenger: block (confidence 0.18)
- Architect response: REBUTTED — challenger confused backlog approval with code review. All "critical" issues describe current code state (work not yet done). Session/claim concern is non-issue: internal `_agent_name` + property preserved, only constructor override removed.

### Test Depth
- AC1: (td:2) — constructor signature + internal random name preservation
- AC2: (td:1) — mechanical removal, one grep proves no callers remain
- AC3: (td:1) — existing CockpitView tests already assert source="cockpit"
- AC4: (td:2) — test_engine_lazy_agent_map_1221 AC1/AC3 must go GREEN
- AC5: (td:2) — test_engine_lazy_agent_map_1221 AC2/AC4 must go GREEN
- AC6: (td:2) — rewrite stale assertions to test lazy contract
- AC7: (td:0) — just verify still green
- AC8: (td:0) — integration run gate
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC1 and AC3 for precision, added test-depth annotations, advanced to todo.

[[2026-05-05]]
Architecture review complete. AC verified against codebase: agent_name used only in claim_task detail (Cockpit doesn't claim); source labeling already explicit via CockpitView; lazy agent_map is the intended design. Refined AC1/AC3/AC6 for precision. Challenger rebutted (confused backlog approval with code review). All criteria PASS. Advanced to todo.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_config_cleanup_1343.py
- Classes: TestFromAC_RemoveAgentNameParam, TestFromAC_CallerCleanup
- Tests per category: happy 0, edge 2 (agent_name=None, sig+property combined), error 2 (TypeError for string, sig boundary), boundary 1 (caller source inspection)
- Total: 5 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | TD | Tests | Status |
|----|----|----|--------|
| AC1 — remove agent_name param, preserve property | td:2 | 4 tests in TestFromAC_RemoveAgentNameParam | RED ✓ |
| AC2 — update Cockpit caller | td:1 | test_cockpit_run_does_not_pass_agent_name | RED ✓ |
| AC3 — CockpitView source="cockpit" preserved | td:1 | Covered by existing mutation tests (no failing tests available) | covered |
| AC4 — lazy agent_map preserved | td:2 | test_engine_lazy_agent_map_1221 TestFromAC_InitNoLongerRaises / TestFromAC_CockpitInitWithEmptyAgentMap — will break when builder removes param, must go GREEN after fix | existing RED |
| AC5 — pick_tasks validates agent_map | td:2 | test_engine_lazy_agent_map_1221 TestFromAC_PickTasksValidatesAgentMap — already GREEN, preserved | existing |
| AC6 — replace stale D24 assertions | td:2 | Builder rewrites TestFromAC_AgentMapCoverage in test_engine_init_1067.py; lazy contract already in test_engine_lazy_agent_map_1221 | builder-owned |
| AC7 | td:0 | pass-through | — |
| AC8 | td:0 | pass-through | — |

### Failure evidence
- test_constructor_signature_excludes_agent_name: AssertionError — agent_name IS in sig
- test_passing_agent_name_string_raises_type_error: DID NOT RAISE TypeError
- test_passing_agent_name_none_raises_type_error: DID NOT RAISE TypeError
- test_agent_name_property_preserved_after_param_removal: AssertionError — agent_name still in sig
- test_cockpit_run_does_not_pass_agent_name: AssertionError — main.py still has agent_name="cockpit"

### Builder notes
- AC4 regression: test_engine_lazy_agent_map_1221's TestFromAC_CockpitInitWithEmptyAgentMap passes agent_name="cockpit" — builder must update those calls too (AC2 scope)
- AC6: delete TestFromAC_AgentMapCoverage from test_engine_init_1067.py and replace with lazy-contract tests (init succeeds, pick_tasks raises); the lazy behavior is already implemented
[[2026-05-05]]
## Builder Notes
- Implementation files:
  - serve/kanban/src/owlbear_kanban/engine.py
  - serve/cockpit/src/owlbear_cockpit/main.py
  - serve/kanban/tests/test_engine_init_1067.py
- Caller/test/benchmark cleanup (removed `agent_name=` constructor kwarg from first-party `KanbanEngine(...)` callsites):
  - serve/kanban/tests/test_idtofilename_cache_943.py
  - serve/kanban/tests/test_idtofilename_cache_944.py
  - serve/kanban/tests/test_list_sessions.py
  - serve/kanban/tests/test_list_sessions_952.py
  - serve/kanban/tests/test_storage_1050.py
  - tests/benchmarks/bench_list_tasks.py
  - tests/test_cockpit_decisions_api.py
  - tests/test_cockpit_decisions_api_1189.py
  - tests/test_cockpit_decisions_api_1190.py
  - tests/test_cockpit_decisions_api_1194.py
  - tests/test_cockpit_events_1234.py
  - tests/test_cockpit_events_1262.py
  - tests/test_cockpit_kanban_routes.py
  - tests/test_cockpit_launch.py
  - tests/test_cockpit_mutation_api.py
  - tests/test_cockpit_mutation_api_1132.py
  - tests/test_cockpit_mutation_api_1134.py
  - tests/test_cockpit_mutation_api_1135.py
  - tests/test_cockpit_mutation_api_1239.py
  - tests/test_cockpit_mutation_api_1243.py
  - tests/test_cockpit_mutation_race.py
  - tests/test_cockpit_read_api.py
  - tests/test_cockpit_read_api_1223.py
  - tests/test_cockpit_routes.py
  - tests/test_cockpit_view_1240.py
  - tests/test_cockpit_view_1244.py
  - tests/test_decisions_1218.py
  - tests/test_engine_cockpit_deps_1222.py
  - tests/test_engine_lazy_agent_map_1221.py
  - tests/test_occ_frontend_wire_1137.py
  - tests/test_schema_roundtrip_1338.py
  - tests/test_config_cleanup_1343.py (restored TypeError assertion callsites using removed kwarg)
- Behavioral fixes applied:
  - Removed `agent_name` from `KanbanEngine.__init__` signature and constructor logic.
  - Preserved internal random session naming and `agent_name` property behavior.
  - Updated Cockpit launch wiring to construct engine without constructor `agent_name` state.
  - Replaced stale eager `agent_map` init assertions in `serve/kanban/tests/test_engine_init_1067.py` with lazy-contract checks:
    - init succeeds with incomplete/empty `agent_map`
    - `AgentView.pick_tasks()` raises `ConfigError(code="ERR_INVALID_STATUS")` when dispatch needs missing entries
  - Kept explicit runtime contract tests that passing `agent_name=` now raises `TypeError`.
- Verification evidence (quality-runner, scoped):
  - Tests passed: 272
  - Tests failed: 0
  - Lint: clean (ruff)
  - Coverage report in scoped run:
    - `serve.cockpit.src.owlbear_cockpit.main`: 98%
    - `serve.kanban.src.owlbear_kanban.engine`: 48%
  - Suite included config, lazy-agent-map, cockpit launch/read/mutation, and engine-init test groups per AC8.
- Commit:
  - 343673c1
  - `fix: remove agent_name constructor parameter (#1343, builder)`

### Reflection
- Mechanical caller cleanup touched a broad first-party test surface; post-pass verification and targeted restoration were required to preserve intentional TypeError assertions.
- Keeping `agent_name` runtime-rejection tests is important to lock the D33 contract after constructor-parameter removal.
- Rewriting D24 assertions in `test_engine_init_1067.py` to lazy-dispatch checks aligns module tests with current architecture and prevents regressions toward eager validation.
[[2026-05-05]]
## Review Evidence
### Test Results
- pytest: 370 passed, 0 failed
- Scope rerun: config, lazy-agent-map, cockpit launch/read/mutation, and engine-init suites together per AC8

### Lint: clean
- ruff: 0 violations across engine/main plus scoped test files

### Coverage
- serve.kanban.src.owlbear_kanban.engine: 48%
- serve.cockpit.src.owlbear_cockpit.main: 98%
- Module-level engine coverage is informational only here. The changed D33/lazy-agent-map paths are directly exercised by task-local and adjacent suites; the 48% figure is not a diff-scoped miss.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. Remove `agent_name` from `KanbanEngine.__init__` | `tests/test_config_cleanup_1343.py::TestFromAC_RemoveAgentNameParam`; `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_NoAgentNameParam` | Yes — signature and runtime kwarg rejection fail if constructor still accepts `agent_name` | COVERED |
| 2. Update every first-party caller/test/benchmark still passing `agent_name` | `tests/test_config_cleanup_1343.py::TestFromAC_CallerCleanup` plus repo-wide `grep_search` over `**/*.py` (matching the architect's td:1 mechanical-cleanup proof model) | Yes — Cockpit launch smoke test fails if `run()` forwards the kwarg; repo-wide grep would surface any remaining live first-party caller/test/benchmark using `agent_name=` | COVERED |
| 3. Preserve Cockpit source labeling via explicit `source="cockpit"` mutations | `tests/test_cockpit_mutation_api.py::TestFromAC_AuditLogging` | Yes — mutation audit-log tests fail if cockpit-sourced entries disappear; explicit `source="cockpit"` kwargs remain wired on mutation paths | COVERED |
| 4. Preserve lazy `agent_map` validation for non-dispatch engine construction | `tests/test_engine_lazy_agent_map_1221.py::TestFromAC_CockpitInitWithEmptyAgentMap`; `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_AgentMapCoverage::test_init_allows_empty_agent_map` | Yes — eager validation in `__init__` would fail these tests | COVERED |
| 5. `AgentView.pick_tasks()` still raises config error when dispatch needs missing `agent_map` entries | `tests/test_engine_lazy_agent_map_1221.py::TestFromAC_PickTasksValidatesAgentMap`; `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_AgentMapCoverage::test_pick_tasks_raises_for_empty_agent_map` | Yes — missing `ConfigError(ERR_INVALID_STATUS)` would fail | COVERED |
| 6. Replace stale eager-validation assertions in `test_engine_init_1067.py` with lazy-contract tests | `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_AgentMapCoverage`; `tests/test_engine_lazy_agent_map_1221.py::TestFromAC_PickTasksValidatesAgentMap` | Yes — stale eager-init assertions are gone and replaced by init-pass + pick_tasks-fail lazy-contract checks | COVERED |
| 7. Keep already-green semantic config tests green | `serve/kanban/tests/test_engine_init_1067.py` entry/terminal/claim-timeout/compatibility cases; `tests/test_schema_roundtrip_1338.py` archival-reason round-trip | Yes — any regression in those existing config semantics would fail the scoped rerun | COVERED |
| 8. Run config, lazy-agent-map, cockpit launch/read/mutation, and engine-init tests together | quality-runner scoped rerun over 18 paths | Yes — the combined rerun would fail on any regression in the required groups | COVERED |

#### Security Review
- No issues found in the scoped implementation. No new injection, traversal, unsafe deserialization, or secret-handling risk surfaced in `serve/kanban/src/owlbear_kanban/engine.py` or `serve/cockpit/src/owlbear_cockpit/main.py`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_AgentMapCoverage` | Replaced stale eager-init assertions with lazy-contract assertions (`__init__` succeeds, `pick_tasks()` raises `ERR_INVALID_STATUS`) per AC6 | STRENGTHENED |
| `serve/kanban/tests/test_engine_init_1067.py::TestFromAC_NoAgentNameParam` | Added runtime kwarg rejection proof alongside signature proof | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact signature absence, `TypeError`, exact `ERR_INVALID_STATUS`, and explicit `source="cockpit"` assertions |
| Negative/error-path coverage | STRONG | Runtime kwarg rejection and empty/partial `agent_map` dispatch failures are exercised |
| Manual mutation reasoning | ADEQUATE | Re-adding constructor `agent_name`, removing explicit cockpit source, or moving `agent_map` validation out of `pick_tasks()` would break mapped proofs or repo-wide caller search |
| Test independence | STRONG | Isolated tmp-path boards and fixture-local engine instances |
| Descriptive test names | STRONG | Task-local and adjacent tests clearly describe the contract they enforce |

#### Data Safety
- No issues found. The reviewed change does not weaken OCC/rollback behavior or introduce new shared-state hazards.

#### Implementation-Aware Gaps
- No untested significant task-owned paths found. Code-reader raised pre-existing launch-suite assertion looseness around board-path resolution, but that concern is outside this task's AC and unrelated to the D33 cleanup; the task-owned path is the constructor/caller cleanup plus lazy dispatch contract, and those paths are directly exercised.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Narrative drift only: some test docstrings still describe Cockpit identity as constructor-driven (`tests/test_cockpit_mutation_api.py`, `tests/test_cockpit_routes.py`), but executable code and assertions are aligned with explicit `source="cockpit"` mutation labeling.
- Confidence deduction applied because this environment did not provide direct `git diff` / `git status` inspection; builder commit presence was verified via `.git/logs`, and current repo state was verified via file reads plus repo-wide grep.
- Confidence deduction applied because `vscode_listCodeUsages` had no Python reference provider; caller-surface verification used repo-wide grep instead.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py:343,356,421`; `tests/test_config_cleanup_1343.py:85,96,124`; `serve/kanban/tests/test_engine_init_1067.py:288,295,306` | `TestFromAC_RemoveAgentNameParam`; `TestFromAC_NoAgentNameParam` | PASS |
| 2 | `serve/cockpit/src/owlbear_cockpit/main.py:74`; `tests/test_config_cleanup_1343.py:156,167`; repo-wide grep found remaining executable `agent_name=` only in intentional negative tests at `tests/test_config_cleanup_1343.py:106,122` and `serve/kanban/tests/test_engine_init_1067.py:306`; benchmark callsites clean at `tests/benchmarks/bench_list_tasks.py:265,300` | `TestFromAC_CallerCleanup` + repo-wide grep | PASS |
| 3 | `serve/cockpit/src/owlbear_cockpit/view.py:183,210`; `tests/test_cockpit_mutation_api.py:509,520,541,602` | `TestFromAC_AuditLogging` | PASS |
| 4 | `tests/test_engine_lazy_agent_map_1221.py:456,465`; `serve/kanban/tests/test_engine_init_1067.py:164` | `TestFromAC_CockpitInitWithEmptyAgentMap`; `TestFromAC_AgentMapCoverage::test_init_allows_empty_agent_map` | PASS |
| 5 | `serve/kanban/src/owlbear_kanban/agent_view.py:370,378`; `tests/test_engine_lazy_agent_map_1221.py:245,253,349`; `serve/kanban/tests/test_engine_init_1067.py:183` | `TestFromAC_PickTasksValidatesAgentMap`; `TestFromAC_AgentMapCoverage::test_pick_tasks_raises_for_empty_agent_map` | PASS |
| 6 | `serve/kanban/tests/test_engine_init_1067.py:154,164,183`; `tests/test_engine_lazy_agent_map_1221.py:245,253,349` | `TestFromAC_AgentMapCoverage`; `TestFromAC_PickTasksValidatesAgentMap` | PASS |
| 7 | `serve/kanban/tests/test_engine_init_1067.py:74,112,203,243`; `tests/test_schema_roundtrip_1338.py:355`; scoped quality-runner rerun green | Existing semantic config suites | PASS |
| 8 | quality-runner scoped rerun: 370 passed, 0 failed across config + lazy-map + cockpit launch/read/mutation + engine-init paths | Combined scoped suite | PASS |

### Confidence: 0.93
### Verdict: PASS
[[2026-05-05]]
## Docs Gate

### Step 0
- Review Evidence section: PRESENT ✓
- Task status: docs ✓

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | Yes | PASS | `## Review Evidence` section present with full AC table, 370 passed, confidence 0.93 |
| 1 | Descriptive prose docs | Yes | FIXED | `serve/cockpit/README.md` §"Audit Trail" stale — said engine initialised with `agent_name="cockpit"`; updated to reflect `CockpitView` passes `source="cockpit"` explicitly per mutation |
| 2 | Module docstrings | Yes | PASS | `engine.py` module docstring (line 15) refers to `claim_task()` and `agent_name` property — both preserved; constructor docstring Args lists only `kanban_dir` and `activity_log` — accurate; `main.py` has no class/function docstrings affected |
| 3 | External attribution | N/A | N/A | No external repos or articles cited; source is internal deployment audit |
| 4 | Research doc | N/A | N/A | No research doc produced for this task |
| 5 | Diagram maintenance | Yes | UPDATED | `cockpit.excalidraw` (describes `serve/cockpit/src/**`) → footer updated from `2026-05-04 (3b857809)` to `2026-05-05 (76e620fb)`; `kanban.excalidraw` (describes `serve/kanban/src/**`) → updated from `(ad980c4f)` to `(76e620fb)`; `mcp-topology.excalidraw` (describes `serve/kanban/src/**`) → updated from `(f260e033)` to `(76e620fb)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted by this task |

### Files updated
- `serve/cockpit/README.md` — removed stale `agent_name="cockpit"` constructor reference, replaced with accurate `source="cockpit"` explanation
- `share/diagrams/cockpit.excalidraw` — footer updated
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated

### Commit
- `d528f5a3` — docs: update cockpit README and diagram footers for agent_name removal (#1343, doc-writer)

### Scratch files
- No `.owlbear/scratch/1343-*` files found — nothing to clean

### Child tasks created
- None
[[2026-05-05]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Remove agent_name from __init__ | engine.py:343-348 signature has only kanban_dir + activity_log; internal _agent_name preserved at L359 | PASS |
| 2. Update every first-party caller | grep agent_name cockpit/main.py returns nothing; 60 task-scoped tests pass cleanly | PASS |
| 3. Preserve source="cockpit" labeling | Reviewer mapped to TestFromAC_AuditLogging; mutation tests pass | PASS |
| 4. Lazy agent_map preserved | test_engine_lazy_agent_map_1221 + test_engine_init_1067 lazy-contract tests pass | PASS |
| 5. pick_tasks raises config error | test_engine_lazy_agent_map_1221::TestFromAC_PickTasksValidatesAgentMap passes | PASS |
| 6. Replace stale eager assertions | test_engine_init_1067::TestFromAC_AgentMapCoverage rewired to lazy contract | PASS |
| 7. Keep semantic config tests green | 60 scoped tests pass (includes entry/terminal/claim/compat) | PASS |
| 8. Combined integration run | Scoped suite: 60 passed, 0 failed | PASS |

### Test Results
- Full suite: 4490 passed, 250 failed (all pre-existing, none in task scope)
- Task-scoped: 60 passed, 0 failed
- test_cockpit_events_1234 failure confirmed pre-existing (reproduced at parent commit)
- ruff: 13 violations, all in serve/knowledge/ and serve/tools/ (outside task scope)

### Architect Quality: 4/5
AC lines specific and mechanically verifiable after refinement. Original AC3 vagueness ("or an approved replacement") was properly fixed in arch review. Test-depth annotations and challenge results documented.

### Deduction Breakdown
- Start: 1.00
- Full-suite failures in task scope: none (-.00)
- Lint in task scope: none (-.00)
- AC lines without evidence: 0 (-.00)
- Reviewer evidence: detailed, PASS verdict, comprehensive AC table (-.00)
- AC quality 4/5: no deduction (threshold is <=3)
- Confidence penalty for pre-existing 250 failures obscuring signal: -.02

### Confidence: .98
### Action: archive

### Commits Verified
| Commit | Type | Agent |
|--------|------|-------|
| d0a88c3d | test | test-writer |
| 343673c1 | fix | builder |
| d528f5a3 | docs | doc-writer |