---
id: 806
title: Add board_config()
status: todo
priority: needed
created: '2026-04-10T21:21:14.299574+00:00'
updated: '2026-04-13T02:11:33.130999+00:00'
tags:
- phase-1
- scope:mcp-kanban
- config
- rigor:thorough
parent: 798
depends_on:
- 805
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `board_config()` method on `KanbanEngine`
- Returns `model_copy()` of cached config (valid statuses, priorities, display order)
- Returned object is a defensive copy — mutating it does not affect engine state
- #805 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #805 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/board-config-impl-806.md (validation pass — findings hold)
- Sources: 5 studied, 4 high-relevance (Pydantic v2 docs, engine.py, models.py, #805 research)
- Recommendation: Option A — `model_copy(deep=True)`, T1 autonomous (confidence: 0.95)
- Implementation already applied at engine.py L92-98; one-line fix from shallow → deep copy
- Tests: 15/15 GREEN across test_board_config_805.py (5) + test_board_config_806.py (10)
- Follow-up tasks created: none (implementation complete, no further work needed)
- Decision requests: none
[[2026-04-13]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `board_config()` method on `KanbanEngine` | PASS — specific, exists at engine.py L149 | None |
| Returns `model_copy()` of cached config | PASS — uses `model_copy(deep=True)`, Pydantic-native | None |
| Defensive copy — mutation doesn't affect engine | PASS — testable via mutation + re-read assertions | None |
| #805 tests pass GREEN | PASS — verifiable by running test suite | None |
| Existing MCP tests pass (O4) | PASS — verifiable by broader suite run | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One method, one concern |
| Interface clarity | PASS | No args, returns BoardConfig copy |
| Dependency correctness | PASS | depends_on [805] — TDD pair, correct ordering |
| Module layering | PASS | Contained within serve/kanban |
| TDD compliance | PASS | #805 is preceding test task |
| KISS/YAGNI | PASS | One-line method body, minimal scope |
| Premise challenge | PASS | Needed for web GUI prep (parent #798) |
| Pattern consistency | PASS | Follows existing refresh_config() pattern, idiomatic Pydantic |
| Security surface | PASS | Read-only accessor, no new boundaries |
| Single domain | PASS | Kanban engine domain only |

### Failure Mode Map
N/A — `model_copy(deep=True)` on a valid Pydantic model cannot fail.

### Challenge Results
- Challenger: proceed (confidence 0.75 — below 0.80)
- Architect response: OVERRIDE with rebuttal
  - TDD violation: process observation, not AC or architecture defect
  - Extra-field gap: Pydantic deep copy handles extra fields correctly (challenger confirms)
  - Dependency status: normal pipeline flow, depends_on ensures ordering

### Verdict: APPROVE
### Action Taken: Advanced to todo. All AC lines verifiable, architecture sound, minimal implementation.