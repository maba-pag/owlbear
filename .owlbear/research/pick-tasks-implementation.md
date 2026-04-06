# Implementation Research: pick_tasks MCP Tool

> **Owning task:** #621 — Implement pick_tasks tool in owlbear-kanban server
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #621 requires migrating gate + sort logic from the orchestrator's planner
package into the owlbear-kanban MCP server as a new `pick_tasks` tool.

**Key questions:**
1. Can mcp-kanban import from orchestrator's planner? If not, how to migrate?
2. Should gates be inlined in server.py or placed in a separate module?
3. How does `pick_tasks` interact with the existing `list_tasks` tool?
4. What data type should gates operate on — Pydantic models or raw dicts?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `serve/mcp-kanban/pyproject.toml` | 1.0 | Deps: only `mcp[cli]` — no orchestrator dependency |
| 2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 1.0 | 503 LOC, tool patterns, `_run_kanban`, `list_tasks` strips body |
| 3 | `serve/orchestrator/src/owlbear/planner/gates.py` | 1.0 | Source gate logic: 3 predicates + 2 regex patterns, ~60 LOC |
| 4 | `serve/orchestrator/src/owlbear/planner/selector.py` | 1.0 | PRIORITY_RANK, STATUS_RANK, sort key, DISPATCH_CAP=20 |
| 5 | `serve/orchestrator/src/owlbear/planner/models.py` | .90 | Planner uses Pydantic `Task` model (different from KanbanTask) |
| 6 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | .90 | `KanbanTask.body` is `str | None` — gates must guard |
| 7 | `.owlbear/research/pick-tasks-test-design.md` | .95 | #620 research: test patterns, mock approach, gate behavior |
| 8 | #619 task body (architecture decision) | 1.0 | Tool signature, return format, responsibility boundaries |

## 3. Analysis

### 3.1 Package Isolation (Critical)

mcp-kanban depends only on `mcp[cli]`, not on the orchestrator (source 1).
The orchestrator's `Task` model uses Pydantic with `datetime` fields and an
`alias="class"` config — incompatible with mcp-kanban's `KanbanTask` (source 5–6).

**Gate logic must be copied and adapted, not imported.**

### 3.2 Body Field Gotcha

`list_tasks` strips `body` from output for token efficiency (source 2, L206–214).
`pick_tasks` needs `body` for TDD gate (`## Test-Writer Notes`) and clarity gate
(bullet AC detection). It must call `_run_kanban` independently with `list --json`.

Additionally, `KanbanTask.body` is `str | None` (source 6). The orchestrator's
gates assume `body: str`. Every body access needs a `task.get("body") or ""` guard.

### 3.3 Placement Options

| Criterion | A: Inline server.py | B: New dispatch.py |
|-----------|---------------------|--------------------|
| KISS/YAGNI | .95 | .75 |
| Files touched | 1 | 2 |
| server.py growth | 503 → ~560 LOC | 503 → ~525 LOC |
| Readability | .80 | .90 |
| Matches precedent | N/A | .85 (models.py) |
| Direct testability | .80 (via tool) | .85 (unit + tool) |

### 3.4 Data Type: Raw Dicts vs KanbanTask

`list_tasks` uses `json.loads()` → raw dicts (source 2). Using the same pattern
for `pick_tasks` avoids Pydantic validation overhead and the `body=None` model
quirk. Gate functions operate on `dict` with `task["title"]`, `task["status"]`,
`task.get("body") or ""`.

### 3.5 Migration Mapping

| Orchestrator source | pick_tasks equivalent |
|--------------------|-----------------------|
| `gates._AND_PATTERN` | `_PICK_AND_RE` (module-level compiled regex) |
| `gates._AC_PATTERN` | `_PICK_AC_RE` (module-level compiled regex) |
| `gates._CLARITY_STATUSES` | `_PICK_CLARITY_STATUSES` frozenset |
| `gates.check_gates(Task)` | `_passes_gates(dict) -> bool` (composite) |
| `selector.PRIORITY_RANK` | `_PRIORITY_RANK` dict |
| `selector.STATUS_RANK` | `_STATUS_RANK` dict |
| `selector.select_tasks()` | Inlined in `pick_tasks()` tool body |
| `selector.STATUS_AGENT_MAP` | **Not migrated** — orchestrator's responsibility |
| `selector.crash_failures` | **Not migrated** — orchestrator's responsibility |

### 3.6 Error Handling

Standard mcp-kanban pattern: `rc != 0` → `ToolError(stderr or stdout)`.
JSON parse failure → `ToolError(f"Invalid task JSON: {stdout[:200]}")`.
All tasks fail gates → return `{"dispatch": []}` (not an error).

## 4. Recommendation (confidence: .85)

**Option A — Inline in server.py.** Rationale:

1. Gates are ~30 LOC of pure functions — not complex enough to warrant a module.
2. Only `pick_tasks` uses them — YAGNI says extract when reuse appears.
3. `list_tasks` already does its own JSON parsing inline — same pattern.
4. server.py at ~560 LOC stays within reasonable bounds.
5. Single-file change is simpler for the builder.

If the builder prefers separation (Option B), that's equally valid — flag as
implementation discretion, not a design constraint.

Challenge: N/A — T1 implementation task. Architecture decided in #619.
Tier: T1 (autonomous) — executing an approved architecture with established patterns.

## 5. Follow-up Tasks

No new follow-up tasks needed. Subtasks #620–#624 already exist under #619.
The builder for #621 has everything needed from this research and #620's research.
