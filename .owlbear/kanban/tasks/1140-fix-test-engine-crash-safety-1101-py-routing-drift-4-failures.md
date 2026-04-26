---
id: 1140
title: Fix test_engine_crash_safety_1101.py routing drift — 4 failures
status: backlog
priority: needed
created: 2026-04-26T16:56:45.310009+00:00
updated: 2026-04-26T17:01:17.632032+00:00
tags:
- scope:kanban,phase:engine,tdd:fix
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Legacy suite reconciliation — `serve/kanban/tests/test_engine_crash_safety_1101.py` has 4 failing tests. The `create_task`/`allocate_next_id` routing expectations don't match current engine code after Brief B changes.

## Acceptance Criteria
- [ ] `test_ac1_crash_after_id_allocation_burns_id` — updated for current routing
- [ ] `test_ac2_config_saved_before_write_task_executes` — updated for current routing
- [ ] `test_ac2_create_task_routes_through_allocate_next_id` — updated for current routing
- [ ] `test_ac3_create_task_contract_preserved_with_new_routing` — updated for current routing
- [ ] No regressions in remaining tests in the file
- [ ] ruff clean

## Context
See `.owlbear/research/1078-cockpitview-coverage-gate-blocker.md` §3.2. Medium effort — requires understanding current `create_task` flow and updating mock/spy expectations.
[[2026-04-26]]
## Research
- Research doc: .owlbear/research/1140-crash-safety-suite-drift.md
- Sources: 5 studied, 4 high-relevance (all codebase)
- Recommendation: Config fixture update only — no mock/spy changes needed (confidence: 0.92)
- Follow-up tasks created: none (task already correctly scoped)
- Decision requests: none (T1 autonomous fix)

## Challenge Results
- Challenger: FALLBACK — single clear root cause, no competing options
- Confidence in original: 0.92

## Key Findings
1. All 4 tests fail at KanbanEngine init — ConfigError for missing agent_map. Never reach routing assertions.
2. Root cause: legacy config fixture missing agent_map, entry_status, terminal_status, and 6 other required fields.
3. Engine already refactored to use storage.allocate_next_id() (engine.py L930). Routing assertions will pass once fixture is fixed.
4. Patch targets verified correct — no mock/spy updates needed.
5. Effort revised: Medium → Low. Single fixture update + docstring cleanup.