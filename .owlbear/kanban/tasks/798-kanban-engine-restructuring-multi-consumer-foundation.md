---
id: 798
title: Kanban Engine Restructuring — Multi-Consumer Foundation
status: backlog
priority: needed
created: '2026-04-10T21:10:19.882817+00:00'
updated: '2026-04-13T00:16:05.800551+00:00'
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
[[2026-04-12]]
## Architecture Review

### Assessment: Parent/Epic Container — No Pipeline Advancement

Task #798 is a parent container with 5 outcomes spanning 3 phases. It is not an implementable task — all work has been decomposed into subtasks. The parent should remain in `backlog` until all children are done, then be archived.

### Children Status

| Phase | Task | Title | Status |
|-------|------|-------|--------|
| P1 | #828 | Impl — Config staleness fix in create_task | done |
| P1 | #844 | Tests — Config staleness fix in create_task | docs |
| P1 | #845 | Tests — TaskSummary adoption in list_tasks | backlog |
| P1 | #846 | Impl — TaskSummary adoption in list_tasks | review |
| P2 | #819 | Tests — MCP adapter slimming regression | done |
| P2 | #822 | Remove compat alias + migrate all imports | done |
| P2 | #831 | Tests — Remove legacy engine_models.py | done |
| P2 | #832 | Impl — Remove legacy engine_models.py | done |
| P3 | #823 | Tests — pick_dispatchable() | research |
| P3 | #824 | Create dispatch.py with pick_dispatchable() | review (blocked) |
| P3 | #825 | Tests — Server pick_tasks thin wrapper | done |
| P3 | #826 | Slim server pick_tasks to thin wrapper | in-progress |

### Codebase Verification

Verified against actual codebase — the brief's target topology is largely achieved:

- `serve/kanban/src/owlbear_kanban/` exists with `engine.py`, `models.py`, `task_io.py`, `config_loader.py`, `activity_log.py`, `agent_names.py`, `dispatch.py`
- `Task`, `TaskSummary`, `BoardConfig` models canonical in engine
- `board_config()`, `refresh_config()`, `valid_transitions()`, revision counter all implemented
- Activity log has `actor` field, status/priority validation in place, timestamp sort uses `datetime.fromisoformat()`
- `KanbanTask` boundary model in MCP server
- Boundary test confirms: `owlbear_kanban` has zero owlbear-namespace deps; `owlbear_mcp_kanban` depends only on `owlbear_kanban`
- `pick_dispatchable()` extracted to `dispatch.py` with proper gate predicates

### Known Issue — server.py pick_tasks Gate Bug

The current `pick_tasks` in `server.py` (lines ~335-398) uses `engine.list_tasks()` which returns `TaskSummary` (no `body` field). The gate function `_check_pick_gates()` then checks `task.get("body") or ""` — always empty. This means:
- Clarity gate rejects ALL active-status tasks (body is empty, AC pattern never matches)
- TDD gate may reject valid in-progress tasks (no body to check for `## Test-Writer Notes`)
- `pick_dispatchable()` in `dispatch.py` correctly reads full `Task` objects from disk

Task #826 (in-progress) addresses this by delegating to `pick_dispatchable()`.

### Remaining Work

4 active children remain: #844 (docs — nearly done), #845 (backlog — needs arch review), #846 (review), #826 (in-progress). Two tasks in research/blocked: #823 (research, dependency #822 is done — may be ready to advance), #824 (blocked: Quality-Runner unavailable).

### Verdict: NO ADVANCE — stays in backlog as parent container
### Action Taken: Released claim. Parent should be archived when all 12 children reach done/archived.
[[2026-04-12]]
## Architecture Review (3rd pass — status refresh)

### Assessment: Parent/Epic Container — No Pipeline Advancement

Task #798 remains a parent container with 5 outcomes spanning 3 phases. Not implementable — all work is in child tasks.

### Updated Children Status (2026-04-12)

| Phase | Task | Title | Status |
|-------|------|-------|--------|
| P1 | #828 | Config staleness fix (impl) | archived |
| P1 | #844 | Config staleness fix (tests) | docs |
| P1 | #845 | TaskSummary adoption (tests) | backlog (3x rejected — redundant, all AC already implemented) |
| P1 | #846 | TaskSummary adoption (impl) | review |
| P2 | #819 | MCP adapter slimming (tests) | done |
| P2 | #822 | Compat alias removal | archived |
| P2 | #831 | Remove engine_models (tests) | archived |
| P2 | #832 | Remove engine_models (impl) | archived |
| P3 | #823 | pick_dispatchable (tests) | research (dep #822 done — ready to advance) |
| P3 | #824 | dispatch.py (impl) | review |
| P3 | #825 | pick_tasks thin wrapper (tests) | archived |
| P3 | #826 | pick_tasks thin wrapper (impl) | in-progress |

### Progress Summary

- **Phase 2: Complete** — all 4 tasks done/archived
- **Phase 1: Nearly complete** — #828 archived, #844 in docs, #845 should be closed as redundant, #846 in review
- **Phase 3: In progress** — #824 in review, #826 in-progress, #823 still in research (but unblocked), #825 archived

### Recommendations

1. **#845** should be archived/closed — rejected 3 times as redundant (all AC items already implemented by commit 3703469e)
2. **#823** has no blockers (dep #822 archived/done) — ready for architect review when it reaches backlog
3. Parent #798 stays in backlog until all active children reach done/archived

### Verdict: NO ADVANCE — stays in backlog as parent container
### Action Taken: Released claim. 5 children archived, 1 done, 6 still in-flight. Parent should be archived when remaining children complete.
[[2026-04-13]]
## Architecture Review (4th pass — full child inventory)

### Assessment: Parent/Epic Container — No Pipeline Advancement

Task #798 remains a parent container with 5 outcomes spanning 3 phases. Not implementable — all work is in child tasks.

### CORRECTION: Previous reviews tracked only 12 children. Full inventory is 18 (6 archived + 12 active).

### Complete Children Status (2026-04-13)

| Phase | Task | Title | Status | Notes |
|-------|------|-------|--------|-------|
| P1 | #803 | Tests — refresh_config + config staleness fix | review (BLOCKED) | Quality-Runner unavailable |
| P1 | #828 | Config staleness fix (impl) | archived | — |
| P1 | #844 | Config staleness fix (tests) | archived | — |
| P1 | #845 | TaskSummary adoption (tests) | research | 3x rejected as redundant — RECOMMEND ARCHIVE |
| P1 | #846 | TaskSummary adoption (impl) | done | Builder fixed 3 failing tests, reviewer PASS .97 |
| P2 | #817 | Tests — Engine package boundary | todo | DEPENDS_ON-CORRECTION flagged (stale deps on superseded tasks) |
| P2 | #818 | Extract engine to serve/kanban/ | in-progress | Reviewer FAIL .65 — engine_models.py not deleted from mcp-kanban |
| P2 | #819 | Tests — MCP adapter slimming | done | — |
| P2 | #822 | Compat alias removal | archived | — |
| P2 | #831 | Tests — Remove engine_models.py | archived | — |
| P2 | #832 | Impl — Remove engine_models.py | archived | — |
| P3 | #823 | Tests — pick_dispatchable() | research | Dep #822 done — ready to advance |
| P3 | #824 | dispatch.py with pick_dispatchable() | review (BLOCKED) | Quality-Runner unavailable |
| P3 | #825 | Tests — Server pick_tasks thin wrapper | archived | — |
| P3 | #826 | Slim server pick_tasks to thin wrapper | in-progress | Test-writer notes done, awaiting builder |
| — | #827 | Migrate task_io.py PyYAML→ruamel | todo | nice-to-have, approved |
| — | #843 | Implement PyYAML→ruamel migration | backlog | DUPLICATE of #827 — should be archived |
| — | #851 | Fix stale ListTasks migration tests | review | Builder done, awaiting reviewer |

### Progress Summary

- **Phase 1:** 2 archived, 1 done, 1 blocked in review (#803), 1 in research/should-archive (#845) — **nearly complete**
- **Phase 2:** 3 archived, 1 done, 1 in-progress with reviewer fail (#818), 1 in todo (#817) — **blocked by #818 fix**
- **Phase 3:** 1 archived, 1 in-progress (#826), 1 blocked in review (#824), 1 in research (#823) — **in progress**
- **Other:** 1 todo (#827), 1 duplicate-backlog (#843), 1 review (#851)

### Key Blockers

1. **Quality-Runner unavailable** — blocks review of #803 and #824 (WMI/logfire hang on Windows)
2. **#818 needs 1-file fix** — delete `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` then re-review
3. **#845 stuck in research/reject loop** — should be archived (4 independent validations confirm redundancy)
4. **#843 is a duplicate** of #827 — should be archived

### Recommendations

1. Archive #845 — 4 validations confirm all AC delivered by commit 3703469e
2. Archive #843 — duplicate of #827 (flagged in #827 arch review)
3. Fix #818 — single file deletion, then re-review
4. Resolve Quality-Runner blocker — unblocks #803 and #824 reviews
5. Advance #823 from research to backlog — dependency #822 is archived/done

### Verdict: NO ADVANCE — stays in backlog as parent container
### Action Taken: Released claim. 6 children archived, 2 done, 10 still in-flight. Parent should be archived when all children reach done/archived.