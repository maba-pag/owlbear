---
id: 1343
title: 'Config validation cleanup: remove agent_name while preserving lazy agent_map'
status: review
priority: needed
created: 2026-05-04T15:10:51.036581+00:00
updated: 2026-05-05T09:18:35.099732+00:00
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
claimed_at: 2026-05-05T09:18:35.099732+00:00
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