---
id: 800
title: Rename TaskRecord → Task with compat alias
status: backlog
priority: needed
created: '2026-04-10T21:20:34.453928+00:00'
updated: '2026-04-12T22:29:53.996338+00:00'
tags:
- phase-1
- scope:mcp-kanban
- model
- rigor:thorough
parent: 798
depends_on:
- 799
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `Task` is the canonical class name in `engine_models.py`
- `TaskRecord = Task` compat alias exported for transition
- All internal engine refs use `Task`
- #799 tests pass GREEN
- Existing MCP tests pass unchanged (O4)

## Context

Phase 1, Chain 1 step 2. Depends on #799 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research (validation pass)

Existing research doc validated against current codebase — task is fully superseded by Phase 2.

### AC Verification

| AC | Current State | Evidence |
|----|--------------|---------|
| `Task` canonical in `engine_models.py` | SUPERSEDED — file doesn't exist | file_search: 0 results for `**/engine_models.py` |
| `TaskRecord = Task` compat alias | SUPERSEDED — alias created and removed by #822 | grep: 0 `TaskRecord` refs in `serve/**/*.py` |
| All internal engine refs use `Task` | ALREADY DONE | `engine.py`, `task_io.py`, `dispatch.py` all import `Task` from `owlbear_kanban.models` |
| #799 tests pass GREEN | SUPERSEDED — #799 itself superseded | See #799 research notes |
| MCP tests unchanged (O4) | ALREADY DONE | `server.py` imports `Task` from `owlbear_kanban.models` |

### Superseding Tasks

- #818 — extracted engine, renamed `engine_models.py` → `models.py`, `TaskRecord` → `Task`
- #821 — compat alias removal tests (archived)
- #822 — removed compat alias + migrated all imports (archived)

### Recommendation: Archive #800 as superseded (confidence: .95)

Tier: T1 — autonomous cleanup (superseded task, no remaining work)
Challenge: SKIPPED — factual validation of superseded state, no opinion-based recommendation
Follow-up tasks: none
Decision requests: none