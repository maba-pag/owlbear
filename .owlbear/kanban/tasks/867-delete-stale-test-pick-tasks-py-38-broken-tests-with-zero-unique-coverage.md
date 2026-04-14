---
id: 867
title: Delete stale test_pick_tasks.py — 38 broken tests with zero unique coverage
status: in-progress
priority: nice-to-have
created: '2026-04-13T20:51:15.145212+00:00'
updated: '2026-04-14T15:07:31.782920+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `tests/test_pick_tasks.py` is deleted
- No other test files are modified
- All remaining tests pass (`uv run pytest tests/ -m "not api" -q`)

## Context

Research in `.owlbear/research/stale-test-pick-tasks-cleanup.md` (#848) confirmed all 38 tests have zero unique coverage:
- 24 behaviors fully covered by test_pick_dispatchable_823/824, test_server_pick_tasks_thin_wrapper_825, test_kanban_mcp_migration
- 10 tests obsolete (tested `_run_kanban` CLI flags that no longer exist)
- 2 tests for atomicity gate intentionally removed from dispatch.py
- 2 tests for JSON null-body scenario obsoleted by Pydantic `body: str=""` model

Confidence: 0.95. This is a trivial file deletion.
[[2026-04-14]]
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | One action: delete one stale test file |\n| Interface clarity | PASS | AC specifies file to delete and pass condition |\n| Dependency correctness | PASS | No dependencies needed |\n| Module layering | N/A | File deletion, no layering impact |\n| TDD compliance | N/A | type:test task — is itself test maintenance |\n| KISS/YAGNI | PASS | Minimal scope, trivial deletion |\n| Premise challenge | PASS | 38 broken tests confirmed by research #848; all fail with removed kanban_bin API |\n| Pattern consistency | PASS | Removing dead code aligns with engine extraction cleanup |\n| Security surface | N/A | No new system boundaries |\n| Single domain | PASS | scope:mcp-kanban only |\n\n### Codebase Verification\n- Confirmed 38 test functions in test_pick_tasks.py, all using obsolete `AppContext(kanban_bin=...)` pattern\n- Replacement suites verified: test_pick_dispatchable_823.py (37+ tests), test_pick_dispatchable_824.py (28+ tests), test_server_pick_tasks_thin_wrapper_825.py (14 tests)\n- Zero imports of test_pick_tasks.py from other files\n- No conftest.py or pytest config dependencies on this file\n\n### Challenge Results\n- Challenger: proceed — deletion safe on all four challenge fronts (coverage, references, config, documentation)\n- Caveat noted: atomicity gate removal was a prior Phase 2 design decision, not in scope of this task\n- Architect response: accepted\n\n### Verdict: APPROVE\n### Action Taken: Advanced to todo. AC is precise and verifiable. Research backing is thorough with test-by-test coverage mapping.
[[2026-04-14]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no tests applicable.
- Task is a file deletion: `tests/test_pick_tasks.py` removal. No new Python interfaces introduced.
- Passing through to builder.