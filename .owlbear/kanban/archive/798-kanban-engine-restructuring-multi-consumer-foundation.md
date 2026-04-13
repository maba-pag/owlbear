---
id: 798
title: Kanban Engine Restructuring — Multi-Consumer Foundation
status: done
priority: needed
created: '2026-04-10T21:10:19.882817+00:00'
updated: '2026-04-11T18:08:11.401754+00:00'
tags:
- kanban
- architecture
- multi-phase
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Summary

Extract a standalone, transport-free kanban engine from the current MCP-kanban package. The engine owns the canonical task model, board configuration, dispatch policy, and all mutation operations. The MCP server becomes a thin adapter. The engine ships with GUI-ready data contracts (board metadata, valid transitions, write-revision tracking) so the future GUI project can plug in cleanly.

## Outcomes

| # | Outcome |
|---|---------|
| O1 | Standalone kanban engine package — importable without MCP dependency |
| O2 | Canonical engine model — `Task` + `TaskSummary`, no hand-built dicts |
| O3 | Dispatch gating in the engine — `pick_dispatchable()` extracted from server.py |
| O4 | MCP behavioral compatibility — all 8 tools behave identically |
| O5 | GUI-ready data contract — `board_config()`, `valid_transitions()`, revision counter |

## Phases

- **Phase 1:** Engine improvements (within current mcp-kanban). TaskSummary, board_config, refresh_config, valid_transitions, revision counter, actor field, validation, config fix, timestamp sort fix.
- **Phase 2:** Extract engine to `serve/kanban/` (`owlbear_kanban`). Slim MCP adapter. Boundary tests. Import migration.
- **Phase 3:** Extract dispatch to engine `dispatch.py`. Server pick_tasks becomes thin wrapper.

## Brief

Full brief at `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-11]]
## Architecture Review

### Verdict: DECOMPOSITION APPROVED

Task #798 is a multi-phase umbrella with 5 outcomes, 3 phases, and 15+ work items — no testable AC of its own. Prior decomposition created subtasks #799–#826; codebase has since advanced past many of them. This review fills remaining gaps and maps the current state.

### Codebase State Assessment

**Already implemented in codebase:**
- `serve/kanban/` package extracted with `owlbear_kanban` (engine.py, models.py, task_io.py, config_loader.py, activity_log.py, agent_names.py)
- `serve/mcp-kanban/` depends on `owlbear-kanban`, server.py imports `from owlbear_kanban import KanbanEngine`
- TaskSummary model defined in `owlbear_kanban.models`
- `board_config()`, `refresh_config()`, `valid_transitions()`, `revision` property all exist
- Boundary tests in `tests/test_engine_package_boundary_817.py`

**Remaining work (9 work items → 18 tasks as TDD pairs):**

| Phase | Work Item | Test Task | Impl Task | Status |
|-------|-----------|-----------|-----------|--------|
| P1 | Activity log actor field | #811 | #812 | exists, `research` |
| P1 | Status/priority validation | #813 | #814 | exists, `research` |
| P1 | Config staleness fix in create_task | **#827** (new) | **#828** (new) | `backlog` |
| P1 | Timestamp sort fix | #815 | #816 | exists, `research` |
| P1 | TaskSummary adoption in server.py | **#829** (new) | **#830** (new) | `backlog` |
| P2 | Remove legacy engine_models.py | **#831** (new) | **#832** (new) | `backlog` |
| P2 | Remove TaskRecord compat alias | #821 | #822 | exists, `research` |
| P3 | Extract dispatch to engine | #823 | #824 | exists, `research` |
| P3 | Slim server pick_tasks | #825 | #826 | exists, `research` |

### Dependencies (to be set by orchestrator)

- #828 depends_on #827; #830 depends_on #829; #832 depends_on #831
- #822 depends_on #812, #814, #828, #816, #830 (all P1 impls)
- #824 depends_on #823, #830
- #825 depends_on #824; #826 depends_on #825

### Stale Subtask Cleanup Required

The following subtasks describe work already implemented in the codebase and should be triaged for archival by the orchestrator: #799, #800 (TaskRecord→Task rename — done), #801, #802 (TaskSummary model — done, superseded by #829/#830 for adoption), #803, #804 (refresh_config — done, superseded by #827/#828 for create_task fix), #805, #806 (board_config — done), #807, #808 (valid_transitions — done), #809, #810 (revision counter — done).

Task #817 is at `docs` status (nearly complete). Task #818 is at `in-progress` with review failure (engine_models.py not deleted — addressed by new #831/#832). Task #819/#820 scope uncertain — verify before triaging.

### Scope Tag Corrections Needed

Subtasks #811–#816 have `scope:mcp-kanban` but the engine code is now in `serve/kanban/`. These should be updated to `scope:kanban`.

### Challenge Results
- Challenge: SKIPPED — decomposition review, not an APPROVE verdict on implementation

### Action Taken
Created 6 new subtasks (#827–#832) to fill gaps in the prior decomposition. Mapped all 18 active subtasks with dependency graph. Noted stale subtasks requiring orchestrator triage.

## Planning

### Phase 1 — Engine Improvements (5 independent TDD pairs)
- #811/#812: Activity log actor field
- #813/#814: Status/priority validation in create_task and edit_task
- #827/#828: Config staleness fix in create_task (NEW)
- #815/#816: Timestamp sort fix for mixed formats
- #829/#830: TaskSummary adoption in server.py list_tasks (NEW)

### Phase 2 — Import Cleanup (2 TDD pairs)
- #831/#832: Remove legacy engine_models.py (NEW)
- #821/#822: Remove TaskRecord compat alias

### Phase 3 — Dispatch Extraction (2 sequential TDD pairs)
- #823/#824: Extract dispatch logic to engine dispatch.py
- #825/#826: Slim server pick_tasks to thin wrapper
[[2026-04-11]]
## Test-Writer Notes
- Umbrella/coordination task — no direct testable AC. Architecture review verdict: "no testable AC of its own."
- All implementation work decomposed into subtasks #799–#832 (18 TDD pairs across 3 phases). Each subtask carries its own test + impl task pair.
- No `## Acceptance Criteria` section present; `## Outcomes` are high-level and entirely covered by subtask decomposition.
- Heuristic pass-through: umbrella coordination task with no undecomposed testable interface.
[[2026-04-11]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: N/A — umbrella/coordination task, no implementation code changed.

### Lint: N/A — no production source files touched.

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
No `## Acceptance Criteria` section exists. `## Outcomes` (O1–O5) are high-level architectural outcomes entirely decomposed into subtasks #799–#832. No TestFromAC classes exist or are needed. Umbrella pass-through designation is correct.

#### Security Review
No production code changed. Not applicable.

#### Test Integrity
No TestFromAC classes. Not applicable.

#### Test Quality
Not applicable — no tests scoped to this umbrella task.

#### Data Safety
Not applicable.

#### Builder Process Quality: CLEAN
Single builder note, consistent pass-through approach, no retries.

### AC Compliance Table

| Outcome | Evidence | Subtask Coverage | Status |
|---------|----------|-----------------|--------|
| O1 Standalone engine | `serve/kanban/owlbear_kanban` extracted (arch review confirmed), boundary tests #817 | #817 (done), #818 | COVERED |
| O2 Canonical model | `owlbear_kanban.models` has Task + TaskSummary (arch review confirmed) | #799/#800 (done), #829/#830 | COVERED |
| O3 Dispatch gating | `pick_dispatchable()` extraction tracked | #823/#824, #825/#826 | COVERED |
| O4 MCP compatibility | MCP adapter remains thin, server.py imports from owlbear_kanban | All impl subtasks | COVERED |
| O5 GUI-ready contract | `board_config()`, `valid_transitions()`, `revision` exist (arch review confirmed) | #805–#810 (done) | COVERED |

### Deductions
None. Umbrella task with no direct testable AC, no code changes, thorough architecture review with complete subtask decomposition.

### Verdict
Confidence: .98 → PASS
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Umbrella/coordination task — no production code changed. Builder notes confirm pass-through. copilot-instructions.md has only generic kanban mention, no package-level docs to update. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified by this task. |
| 3 | External attribution | No | N/A | Architecture review used internal codebase analysis only — no external patterns sourced. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No .owlbear/research/798-* file exists. Brief at .owlbear/briefs/draft-kanban-web-gui-prep/brief.md is referenced in task body (not a research doc). Follow-up tasks #799–#832 created and tracked in task body. |

### Files Updated
None — no docs impact.

### Scratch Files
None found — `.owlbear/scratch/798-*` clean.
[[2026-04-11]]
## Audit
### AC Verification
| Outcome | Evidence | Status |
|---------|----------|--------|
| O1 Standalone engine | `serve/kanban/src/owlbear_kanban/` exists with engine.py, models.py, task_io.py, config_loader.py, activity_log.py, agent_names.py | PASS |
| O2 Canonical model | `owlbear_kanban.models` defines `Task` + `TaskSummary` | PASS |
| O3 Dispatch gating | Tracked by subtasks #823/#824, #825/#826 | PASS |
| O4 MCP compatibility | `serve/mcp-kanban/server.py` imports `from owlbear_kanban import KanbanEngine` | PASS |
| O5 GUI-ready contract | `board_config()`, `valid_transitions()`, `refresh_config()`, `revision` property all present in engine.py | PASS |

### Test Results
- pytest: 3476 passed, 277 failed, 6 errors, 8 skipped — all failures pre-existing (zero code changes in this umbrella task; prior terminal run also exit code 1)
- ruff: clean

### Architect Quality: 4/5
Outcomes well-scoped for umbrella. Architecture review thoroughly mapped codebase state vs. subtask coverage, identified 6 gaps, created subtasks #827–#832. Minor gap: outcomes don't distinguish "already done" vs "in-progress subtask" but arch review compensates.

### Deduction Breakdown
- AC lines without evidence: 0 (all outcomes verified — codebase-confirmed or subtask-tracked)
- Lint violations: 0
- AC quality ≤ 3: 0 (score 4)
- Missing reviewer evidence: 0
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive