---
id: 817
title: Tests — Engine package boundary + public API
status: todo
priority: critical
created: '2026-04-10T21:22:21.043519+00:00'
updated: '2026-04-12T20:32:33.815797+00:00'
tags:
- phase-2
- type:test
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 802
- 804
- 806
- 808
- 810
- 812
- 814
- 816
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `from owlbear_kanban import KanbanEngine, Task, TaskSummary` works
- Tests verify engine package does NOT import `mcp` or any transport package (boundary test)
- Tests verify engine public API surface: KanbanEngine methods, Task, TaskSummary, BoardConfig exports
- Tests verify MCP adapter is allowed to import `owlbear_kanban`
- Tests fail RED before extraction

## Context

Phase 2, step 1. Depends on all Phase 1 implementation tasks completing.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research

- Research doc: .owlbear/research/engine-package-boundary-817.md
- Sources: 5 studied, 4 high-relevance (score ≥ 0.9)
- Recommendation: Single new test file + ALLOWED_IMPORTS update, following existing AST-scanning conventions (confidence: 0.90)
- Follow-up tasks created: none needed — #818 (GREEN extraction) already exists and is in-progress
- Decision requests: none

## Validation Pass (2026-04-12)

Existing research doc confirmed current against codebase state:
- Engine extracted to serve/kanban/ (owlbear_kanban) — completed by #818
- All 8 boundary tests pass GREEN (4.57s)
- ALLOWED_IMPORTS updated correctly in test_package_boundary.py
- KanbanEngine public API: 14 methods/properties confirmed
- Engine has zero MCP/transport imports (AST-verified)
- server.py imports from owlbear_kanban (AST-verified)
- No discrepancies between research doc and current state

## Challenge Results

- Challenger: FALLBACK — trivial recommendation following existing patterns; no alternative approaches to evaluate
- Confidence in original: 0.90
- Key challenges: N/A
- Researcher response: N/A
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Boundary + API surface tests only — one concern |
| Interface clarity | PASS | AC specifies exact imports, exact models, exact API members (14 methods/properties + 3 model exports) |
| Dependency correctness | FAIL | All 8 listed deps (#802, #804, #806, #808, #810, #812, #814, #816) are at `research` — superseded by later task IDs. See DEPENDS_ON-CORRECTION below |
| Module layering | PASS | Tests scan engine for transport imports; adapter allowed to import engine — correct direction |
| TDD compliance | PASS | This IS the test task (type:test). Partner GREEN task #818 completed extraction |
| KISS/YAGNI | PASS | Minimal scope — 8 tests, one file, one ALLOWED_IMPORTS update |
| Premise challenge | PASS | Boundary tests are essential for package extraction; existing pattern in test_package_boundary.py validates approach |
| Pattern consistency | PASS | AST-scanning pattern matches existing test_package_boundary.py conventions exactly |
| Security surface | PASS | No new system boundaries — read-only AST analysis of source files |
| Single domain | PASS | Kanban domain only |

### Challenge Results

- Challenger: FALLBACK — challenger agent unavailable; trivial approval following established patterns with codebase-verified deliverables already in place
- Architect response: N/A

### Codebase Verification

- Test file: `tests/test_engine_package_boundary_817.py` (149 lines, 8 tests, 4 classes)
- ALLOWED_IMPORTS: `test_package_boundary.py` lines 40-53 — `owlbear_kanban: set()` and `owlbear_mcp_kanban: {"owlbear_kanban"}` present
- Engine package: `serve/kanban/src/owlbear_kanban/__init__.py` exports KanbanEngine, Task, TaskSummary, BoardConfig, pick_dispatchable
- All tests pass GREEN per Validation Pass (4.57s)

### DEPENDS_ON-CORRECTION

Task #817 should have `depends_on: []` (empty list). All 8 listed dependencies (#802, #804, #806, #808, #810, #812, #814, #816) are at `research` status — they were superseded by later task decompositions visible in parent #798's children list. The research doc itself confirms: "#817's RED tests don't require Phase 1 completion — they reference the target interface (which fails with ImportError regardless)." Retaining stale deps blocks dispatch.

### Verdict: APPROVE
### Action Taken: Advanced to todo. DEPENDS_ON-CORRECTION flagged for orchestrator to clear stale dependency list before dispatch.