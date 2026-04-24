# Archived-Task Metadata Edit Persistence Path

> **Owning task:** #1120 — B-XX: Archived-task metadata edit persistence path
> **Date:** 2026-04-25 **Status:** Complete

## 1. Context and Question

The #1070 reviewer found that `AgentView.edit_task` on an archived task fails
at persistence time. AgentView can *read* archived tasks (archive-dir fallback
in `show_task`) and validates archival fields correctly, but the downstream call
to core `engine.edit_task` crashes because core only searches `tasks/` for the
file. Even if that lookup succeeded, `write_task` in storage.py always writes to
`tasks/`, creating a duplicate instead of updating `archive/`.

**Question:** What is the minimal, KISS-aligned fix to make archived-task edits
persist, and what scope of editing should be allowed on archived tasks?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L920-1020 (core edit_task), L803-842 (show_task archive fallback), L1513-1531 (_find_task_path), L1870-2020 (AgentView.edit_task) | Code | 1.0 |
| 2 | `serve/kanban/src/owlbear_kanban/storage.py` L355-410 (write_task) | Code | 1.0 |
| 3 | `.owlbear/briefs/kanban-mcp-surface-v2/decisions.md` R5, D7 | Brief | 0.9 |
| 4 | `.owlbear/briefs/kanban-mcp-surface-v2/synthesis.md` D7 | Brief | 0.9 |
| 5 | `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md` §1.5 | Brief | 1.0 |
| 6 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L316-361 | Code | 0.8 |
| 7 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` L186-210 | Code | 0.8 |

## 3. Analysis

### 3.1 Failure Chain

```
AgentView.edit_task(42, archival_reason="dropped")
  → show_task("42")           ✓ finds task in archive/
  → validates archival fields  ✓ passes
  → engine.edit_task("42", …)
    → _find_task_path("42", self._tasks_dir)  ✗ FileNotFoundError
```

Two independent defects block the success path:

| Defect | Location | Root Cause |
|--------|----------|------------|
| D1: Path lookup | `engine.py` L975 | `_find_task_path` only searches `_tasks_dir` |
| D2: Write target | `storage.py` L373 | `write_task` always writes to `tasks/` |

### 3.2 Both Consumers Affected

| Consumer | Call Path | Status |
|----------|-----------|--------|
| MCP server | `server.py` L361 → `agent_view().edit_task()` → core | Broken |
| Cockpit | `mutation.py` L205 → `engine.edit_task()` (core directly) | Broken |

The Cockpit route bypasses AgentView and calls core `edit_task` directly, so
it hits D1 without any archival validation.

### 3.3 Scope Decision: D7 vs R5

| Decision | Source | Scope |
|----------|--------|-------|
| D7 (synthesis) | `synthesis.md` L125-127 | Archival metadata only; all other params forbidden on archived |
| R5 (decisions) | `decisions.md` L18 | Full edit access, subject to S4 (completed-requires-done) |
| paper-integration §1.5 | Brief B authority | No non-archival-field gate present |

**Current code state:** AgentView has no gate blocking non-archival params
(body, priority, parent, tags, deps) on archived tasks. Only archival fields on
*non-archived* tasks are gated (`ERR_ARCHIVAL_FIELDS_FORBIDDEN`).

### 3.4 Implementation Options

| Option | Change | LOC est. | Pros | Cons |
|--------|--------|----------|------|------|
| A: Core fallback + archive-aware write | `_find_task_path` gains archive fallback; `write_task` gains optional `target_dir` | ~25 | Single code path, KISS | `write_task` signature widens |
| B: Core fallback + path-based write | `edit_task` tracks source path; writes directly via `atomic_write` to same path | ~30 | `write_task` untouched | Duplicates serialization logic |
| C: AgentView-only bypass | AgentView handles archive edits without core | ~40 | Core stays simple | Mutation logic duplicated between core and AgentView |

## 4. Recommendation

**Option A** — confidence: 0.85

Teach `_find_task_path` to accept a fallback directory (or have core `edit_task`
try archive after tasks/ miss). Add a `target_dir` parameter to `write_task`
(defaulting to `tasks/` for backwards compatibility). This is the smallest diff
that fixes both D1 and D2 without duplicating logic.

### Scope recommendation

Follow **R5** (full edit access on archived tasks, subject to S4). Rationale:
- paper-integration §1.5 (Brief B authority) has no non-archival-field gate
- Current AgentView code has no such gate
- Adding a gate would be new behavior beyond the stated fix
- D7's narrower scope can be revisited as a separate policy task if desired

Challenge: FALLBACK — challenger subagent not invoked (trivial persistence
bug fix, no architecture alternatives to challenge).

## 5. Follow-up Tasks

| ID | Title | Rationale |
|----|-------|-----------|
| #1121 | RED: archived-task edit persistence tests | Test the success path for editing archived task metadata (archival_reason, archival_refs, body, priority) |
| #1122 | GREEN: fix archived-task edit persistence | Implement Option A: _find_task_path archive fallback + write_task target_dir param |
