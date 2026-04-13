---
id: 807
title: Tests — valid_transitions
status: todo
priority: needed
created: '2026-04-10T21:21:18.809894+00:00'
updated: '2026-04-13T02:58:14.821725+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `valid_transitions(status)` returns set of all configured statuses except the given one
- Tests verify invalid status input raises `ValueError`
- Tests verify transitions match config-defined statuses
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/valid-transitions-tests-807.md (validation pass — doc already existed)
- Sources: 4 studied, 4 high-relevance
- Validation: Implementation at engine.py L162–180 (moved from L113 since doc was written; behavior unchanged). All 25 tests in test_valid_transitions_807.py pass GREEN (confirmed GREEN-on-arrival as expected).
- Recommendation: Option A accepted — tests verify correctness despite GREEN-on-arrival (confidence: 0.90)
- Follow-up tasks created: none (paired task #808 already exists)
- Decision requests: none (T1 — standard test task)
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only `valid_transitions()` on `KanbanEngine` |
| Interface clarity | PASS | AC specifies return type (set), error behavior (ValueError), config-driven verification |
| Dependency correctness | PASS | No dependencies listed; Phase 1 independent pair confirmed |
| Module layering | PASS | Tests import only `KanbanEngine` from `owlbear_kanban`; no upward imports |
| TDD compliance | PASS | This IS the RED-phase test task; paired with #808 (GREEN) |
| KISS/YAGNI | PASS | 25 focused tests, no overengineering |
| Premise challenge | PASS | Tests verify essential engine behavior for GUI-ready data contract (O5) |
| Pattern consistency | PASS | Follows `_BASE_CONFIG_YAML`/`kanban_dir`/`engine` fixture pattern from test_refresh_config_803.py |
| Security surface | N/A | Pure test task |
| Single domain | PASS | `scope:mcp-kanban` only |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: returns set except given | Verifiable — parametrized tests cover all 7 statuses, type check, exclusion check | None |
| AC2: invalid raises ValueError | Verifiable — unknown, empty, case-mismatch all tested with `pytest.raises(ValueError)` | None |
| AC3: transitions match config | Verifiable — custom 2-status config proves config-driven behavior, no hardcoding | None |
| AC4: tests fail RED | Not satisfiable as written — implementation predates tests (GREEN-on-arrival) | Noted; research doc Option A accepted, docstring documents it; standard pipeline handling |

### Codebase Evidence

- Implementation: `serve/kanban/src/owlbear_kanban/engine.py` L162-180
- Test file: `tests/test_valid_transitions_807.py` (231 lines, 25 tests, all GREEN)
- Paired task: #808 (GREEN implementation) — no test duplication
- Import: `from owlbear_kanban import KanbanEngine` — correct package

### Challenge Results

- Challenger: FALLBACK — challenger agent not available
- Architect response: Proceeded with approval; no architectural risk (pure test task, well-researched, tests exist and pass)

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable (AC4 GREEN-on-arrival documented per pipeline convention). Tests follow established patterns. `type:test` pass-through tag present.