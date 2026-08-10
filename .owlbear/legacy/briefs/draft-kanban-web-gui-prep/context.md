# Kanban Web GUI Prep — Context

<!-- Incremental: updated after each moment -->

## Problem Statement

The kanban engine works for pipeline agents via MCP. Adding a human GUI requires two structural changes:

1. **Consumer-agnostic interface.** The engine logic (`engine.py`, `task_io.py`, etc.) is already transport-free, but it's packaged with MCP, and the canonical task shape is fragmented across four representations (engine `TaskRecord`, MCP `KanbanTask`, `list_tasks` hand-built dict, orchestrator model). A clear "board API" module with a single task model is needed — one that both MCP and a future GUI adapter can import without dragging in transport dependencies.

2. **Dispatch policy ownership.** Task gating and priority ranking logic is duplicated between the MCP server and the orchestrator. It needs a single canonical home (likely in the engine or a policy module) so all consumers get consistent task selection.

Beyond these, the architecture review surfaced implementation items (config staleness, schema monkey-patching, hardcoded paths, etc.) that should be triaged as part of this work.

### What this is NOT
- The GUI itself (separate ideation)
- GUI technology choices
- Concurrency control (accepted risk for single-laptop system)

### Prior work
- `draft-kanban-native` brief: replaced kanban-md Go binary with native Python engine (completed)
- This project is the next step: restructuring that engine for multi-consumer access

## Outcomes

| # | Outcome | Success Indicator |
|---|---------|-------------------|
| O1 | **Standalone kanban engine package** — importable without MCP dependency; MCP server is a thin adapter over it | `from owlbear_kanban import KanbanEngine` works; server.py contains only MCP wiring |
| O2 | **Canonical engine model** — engine owns one task model; consumers (MCP server, task selector) derive their own boundary shapes from it | Single `Task` model in engine; no hand-built dicts; boundary models trace back to engine model |
| O3 | **Dispatch gating in the engine** — task eligibility predicates and priority ranking extracted from server.py into the engine or a policy module | pick_tasks logic is importable and testable independently of MCP; no inline gating constants in server.py |
| O4 | **MCP behavioral compatibility** — all 8 MCP tools behave identically after restructuring | Existing MCP tool tests pass unchanged; board loads correctly; claim/release/status semantics preserved |
| O5 | **GUI-ready data contract** — valid_transitions(), revision counter, board_config() expose the metadata a GUI needs | Engine exposes valid transitions per status, board metadata, and a write-revision counter for cheap polling |

## Landscape Summary (M3)

### Current Architecture
- **mcp-kanban package** (~1900 LOC): `engine.py` (560), `server.py` (670), `task_io.py` (300), `engine_models.py` (90), `models.py` (40), `config_loader.py` (80), `activity_log.py` (20)
- **Orchestrator planner** (~270 LOC): dead code — entire CLI dispatch pipeline superseded by VS Code agents using MCP
- **Tests**: 19 kanban engine test files; 5 planner test files (dead); 6 orchestrator test files import planner models (will need cleanup in separate brief)

### Key Findings
1. **Orchestrator planner is dead code** — the CLI dispatch pipeline (planner, loop, waves, CLI dispatch/run) is unused. Project moved to VS Code agent workflows. Cleanup is a separate brief.
2. **Only two active consumers**: MCP server (agents) and future GUI.
3. **Only two task models to reconcile**: `TaskRecord` (engine) and `KanbanTask` (MCP boundary).
4. **Engine is already transport-free** — `engine.py`, `task_io.py`, `config_loader.py` don't import MCP. The coupling is packaging-only (one pyproject.toml).
5. **Dispatch gating** in server.py's `pick_tasks` (~60 lines inline) — sole live location. Needs extraction to engine.
6. **Schema monkey-patching**: server.py patches `mcp._tool_manager._tools` — fragile private API access, isolated in adapter.
7. **list_tasks returns hand-built lean dicts** — third ad-hoc representation, replaced by TaskSummary.
8. **Config staleness** — create_task reloads config for next_id but doesn't update cached self._config. Other methods use stale cache.
9. **Timestamp sort broken** — string comparison with mixed TZ offsets produces wrong ordering.

## Revised Phasing (Fix-then-extract)

| Phase | Scope |
|-------|-------|
| **1 — Engine improvements** | Fix config staleness, add TaskSummary, board_config(), refresh_config(), valid_transitions(), revision counter, actor field on activity log, rename TaskRecord→Task, status/priority validation |
| **2 — Extract engine package** | Move engine files to serve/kanban/ (owlbear_kanban). New pyproject.toml. Update imports. Boundary tests. Engine arrives complete. |
| **3 — Extract dispatch** | Move pick_tasks gating to engine dispatch.py. Server's pick_tasks tool becomes thin wrapper. |
