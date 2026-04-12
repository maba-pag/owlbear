# Test Design: pick_dispatchable() Engine Function

> **Owning task:** #823 — Tests — pick_dispatchable()
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #823 is TDD RED phase for `pick_dispatchable()` — the engine-level dispatch
function defined in the Phase 3 brief. The function doesn't exist yet (`dispatch.py`
not created); tests must exercise the contract in #824 AC.

**Questions:**
1. What fixture pattern: real engine or mock? How does the test access `body` for gate checks?
2. What's the exact gate + sort + cap contract from existing code and brief?
3. Are there data flow issues to flag for the builder (#824)?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` | 1.0 | `KanbanEngine`, `list_tasks() -> list[TaskSummary]`, `show_task()` |
| 2 | `serve/kanban/src/owlbear_kanban/models.py` | 1.0 | `Task` (has body), `TaskSummary` (no body, extra=ignore) |
| 3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L320-410 | 1.0 | Existing `_check_pick_gates`, rank maps, `pick_tasks` tool |
| 4 | `serve/orchestrator/src/owlbear/planner/gates.py` | .95 | Original TDD + clarity gates, `_NON_IMPL_TAGS` frozenset |
| 5 | `tests/test_kanban_engine_listing.py` | .90 | Engine test fixture pattern: real engine, tmp dirs, task files |
| 6 | `tests/test_pick_tasks.py` | .85 | Existing MCP-level pick_tasks tests (mock-based) |
| 7 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | 1.0 | Phase 3 spec, package topology, dispatch design |
| 8 | `.owlbear/briefs/.../voices/architect.md` L95-130 | .95 | Dispatch policy design: hardcoded rank maps rationale |
| 9 | `tests/test_kanban_mcp_migration.py` L595-834 | .85 | Engine-backed `pick_tasks` tests, mock engine pattern |

## 3. Analysis

### 3.1 Fixture Pattern: Real Engine with Temp Filesystem

Real `KanbanEngine` with task files on disk. Rationale:

| Criterion | Real engine | Mock engine |
|-----------|------------|-------------|
| Tests body-dependent gates | Yes — task files include body | Yes if mock returns Task |
| Builder freedom | High — no assumptions about internal API | Low — couples to list_tasks contract |
| Matches engine test precedent | Yes (source 5) | No |
| Setup complexity | Medium (~30 LOC helpers) | Low |
| Confidence in integration | .90 | .70 |

**Recommendation:** Real engine (confidence: .85). The `_make_kanban_dir` / `_add_task`
helpers from source 5 provide a proven pattern. The test-writer can reuse or adapt them.

### 3.2 Data Flow Issue: list_tasks Returns TaskSummary (No Body)

`engine.list_tasks()` converts full `Task` objects to `TaskSummary` (source 1, L211):
```python
return [TaskSummary.model_validate(t.model_dump()) for t in tasks]
```
`TaskSummary` has `extra="ignore"` (source 2) — `body` is silently stripped.

`pick_dispatchable` needs `body` for TDD gate (`## Test-Writer Notes`) and clarity
gate (bullet/numbered AC). The builder of #824 must solve this — options:
1. Add `full: bool = False` parameter to `list_tasks()` returning `list[Task]`
2. Have `dispatch.py` read task files directly via `task_io.read_task()`
3. New engine method `list_full_tasks() -> list[Task]`

Tests using real engine + filesystem are agnostic to this choice.

### 3.3 Gate Contract (from source 3 + 4)

| Gate | Trigger condition | Pass | Fail |
|------|-------------------|------|------|
| TDD | status == "in-progress" | Has `## Test-Writer Notes` in body OR has non-impl tag | No notes AND no non-impl tag |
| Clarity | status in {todo, in-progress, review, docs, done} | Body has `^\s*(-\s\|\d+\.\s)` pattern | No bullet/numbered items |

Non-impl tags (source 3): research, docs, type:config, type:docs, test, type:test,
agent, quality, type:user-action.

**No atomicity gate** in AC or current `_check_pick_gates` — only TDD + clarity.

### 3.4 Rank Maps (Execution Priority, from source 3)

Priority: critical(0) < needed(1) < important(2) < nice-to-have(3) < someday(4)
Status: done(0) < docs(1) < review(2) < in-progress(3) < todo(4) < backlog(5) < research(6)

Sort key: `(priority_rank, status_rank)` ascending. These are intentionally ≠ config
display order (source 8).

### 3.5 Test Structure

| # | Class | AC covered | Key assertions |
|---|-------|------------|----------------|
| 1 | `TestFromAC_PickDispatchableImport` | importable without MCP | `from owlbear_kanban.dispatch import pick_dispatchable`; no `mcp` in module imports |
| 2 | `TestFromAC_PickDispatchableSignature` | returns list[Task] | Return type check, default limit=25, keyword-only params |
| 3 | `TestFromAC_PickDispatchableTDDGate` | TDD gate | in-progress w/o notes excluded; with notes included; non-impl tag exempt |
| 4 | `TestFromAC_PickDispatchableClarityGate` | Clarity gate | todo w/o bullets excluded; with bullets included; research exempt |
| 5 | `TestFromAC_PickDispatchablePriorityRanking` | Priority sort | critical before someday; all 5 levels ordered |
| 6 | `TestFromAC_PickDispatchableStatusRanking` | Status sort | done before research; all 7 levels ordered |
| 7 | `TestFromAC_PickDispatchableLimit` | Limit cap | limit=3 caps; default=25 caps |
| 8 | `TestFromAC_PickDispatchableTagFilter` | Tag filtering | tag kwarg filters results |

Estimated: ~150 LOC. Test file: `tests/test_pick_dispatchable_823.py`.

## 4. Recommendation (confidence: .85)

**T1 — Autonomous.** Standard TDD RED phase with well-established patterns.

Use real `KanbanEngine` with temp filesystem fixtures (pattern from source 5).
Import `pick_dispatchable` from `owlbear_kanban.dispatch` — RED immediately since
`dispatch.py` doesn't exist.

Builder note for #824: `engine.list_tasks()` strips `body` via TaskSummary
conversion. `pick_dispatchable` must use a different path to access task bodies.

Challenge: N/A — T1 test task with established patterns, no recommendation to challenge.

## 5. Follow-up Tasks

None needed. #824 (implementation) already exists and depends on #823.
The data flow finding (body access) is documented here for the #824 builder.
