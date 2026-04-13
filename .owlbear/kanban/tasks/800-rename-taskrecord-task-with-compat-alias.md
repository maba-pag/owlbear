---
id: 800
title: Rename TaskRecord → Task with compat alias
status: review
priority: needed
created: '2026-04-10T21:20:34.453928+00:00'
updated: '2026-04-13T02:27:05.414633+00:00'
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
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | N/A | Task superseded — evaluation moot |
| Interface clarity | N/A | Superseded |
| Dependency correctness | N/A | Superseded; #799 (dep) also superseded |
| Module layering | N/A | Superseded |
| TDD compliance | N/A | Superseded; RED tests impossible for completed work |
| KISS/YAGNI | N/A | Superseded |
| Premise challenge | **FAIL** | Work already completed by #818 (engine extraction, `TaskRecord`→`Task`), #821 (compat alias removal tests), #822 (alias removal + import migration). `engine_models.py` does not exist. Zero `TaskRecord` refs remain. |
| Pattern consistency | N/A | Superseded |
| Security surface | N/A | No new boundaries |
| Single domain | N/A | Superseded |

### Codebase Evidence

1. `engine_models.py` — does not exist (file_search: 0 results)
2. `TaskRecord` — 0 references in `serve/**/*.py`
3. `Task` canonical at `owlbear_kanban.models` — confirmed: `engine.py`, `task_io.py`, `dispatch.py`, `__init__.py`, `server.py` all import `Task` from `owlbear_kanban.models`
4. Superseding tasks: #818 (done), #821 (archived), #822 (archived)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `Task` canonical in `engine_models.py` | SUPERSEDED — file doesn't exist; `Task` canonical in `owlbear_kanban.models` | None possible |
| `TaskRecord = Task` compat alias | SUPERSEDED — alias created and removed by #822 | None possible |
| All internal engine refs use `Task` | ALREADY DONE — verified in engine.py, task_io.py, dispatch.py, server.py | None possible |
| #799 tests pass GREEN | SUPERSEDED — #799 itself superseded (3 research + 2 arch review cycles, identical findings) | None possible |
| MCP tests unchanged (O4) | ALREADY DONE — server.py imports `Task` from `owlbear_kanban.models` | None possible |

### Challenge Results
- Challenger: SKIPPED — superseded task with factual evidence, no subjective design decision to challenge

### Verdict: APPROVE (superseded — fast-track to archive)

All five AC items are either already satisfied by existing code or structurally impossible. Advancing to `todo` to break the review loop (sibling #799 completed 3 research + 2 arch review cycles with identical "superseded" verdicts). Downstream agents should fast-track to archive — zero implementation work remains.

**ORCHESTRATOR: Archive this task. All work completed by #818/#821/#822.**
[[2026-04-13]]
## Test-Writer Notes
- Non-impl pass-through: task fully superseded — no testable new interfaces exist.

**Supersession evidence (from arch-review + research):**
| AC Line | State | Reason |
|---------|-------|--------|
| `Task` canonical in `engine_models.py` | SUPERSEDED | `engine_models.py` does not exist; `Task` canonical in `owlbear_kanban.models` |
| `TaskRecord = Task` compat alias | SUPERSEDED | Alias created by #818, tested by #821, removed by #822 — 0 `TaskRecord` refs in `serve/` |
| All internal engine refs use `Task` | ALREADY DONE | `engine.py`, `task_io.py`, `dispatch.py`, `server.py` all import `Task` from `owlbear_kanban.models` |
| #799 tests pass GREEN | SUPERSEDED | #799 itself is superseded (3 research + 2 arch review cycles confirm) |
| MCP tests unchanged (O4) | ALREADY DONE | `server.py` imports `Task` from `owlbear_kanban.models` |

**RED phase decision:** Every AC item resolves to existing GREEN behavior. Writing tests would produce passing tests (forbidden). No ImportError or NotImplementedError paths exist for this AC.

**Recommendation for builder / orchestrator: Archive #800.** All work completed by #818 (engine extraction), #821 (compat alias removal tests, archived), #822 (alias removal + import migration, archived).
[[2026-04-13]]
## Builder Notes

**Verdict: DONE (superseded — zero implementation)**

### Verification (builder sanity check)
- `engine_models.py`: confirmed does not exist (file_search: 0 results)
- `TaskRecord` in `serve/**/*.py`: confirmed 0 references (grep: no matches)
- `Task` canonical at `owlbear_kanban.models`: verified by prior research/arch-review cycles

### AC Status (all 5 items)
| AC | Result |
|----|--------|
| `Task` canonical in `engine_models.py` | SUPERSEDED — file doesn't exist; `Task` lives in `owlbear_kanban.models` |
| `TaskRecord = Task` compat alias | SUPERSEDED — alias was created (#818), tested (#821), removed (#822) |
| All internal engine refs use `Task` | ALREADY DONE — `engine.py`, `task_io.py`, `dispatch.py`, `server.py` all import `Task` |
| #799 tests pass GREEN | SUPERSEDED — #799 is superseded by same prior work |
| MCP tests unchanged (O4) | ALREADY DONE — confirmed by research/arch review |

### Files Changed
None — superseded task, no implementation work required.

### Test Results
No new tests. Prior cycle: all MCP kanban tests GREEN (verified by research agent).

### Lint
N/A — no files modified.

### Superseding Tasks
- #818 (done): extracted engine, renamed `engine_models.py` → `models.py`, `TaskRecord` → `Task`
- #821 (archived): compat alias removal tests
- #822 (archived): alias removal + import migration

**Advancing to review for archive.**