# Brief: Kanban Engine Restructuring — Multi-Consumer Foundation

## Summary

Extract a standalone, transport-free kanban engine from the current MCP-kanban package. The engine owns the canonical task model, board configuration, dispatch policy, and all mutation operations. The MCP server becomes a thin adapter. The engine ships with GUI-ready data contracts (board metadata, valid transitions, write-revision tracking) so the future GUI project can plug in cleanly.

## Problem Statement

The kanban engine works for pipeline agents via MCP. Adding a human GUI requires two structural changes the current architecture doesn't support:

1. **Consumer-agnostic interface.** The engine logic is transport-free in code, but packaged with MCP. The canonical task shape is fragmented across two models plus a hand-built dict. No consumer can import the engine without pulling in MCP dependencies.

2. **GUI-ready data contract.** The engine exposes no board metadata (valid statuses, priorities, transitions), no change-detection signal for efficient polling, and no validated list projection — all things a GUI needs from day one.

Additionally, config staleness, missing input validation, and broken timestamp sorting are pre-existing issues that would compound if a second consumer were layered on top.

## Outcomes

| # | Outcome | Success Indicator |
|---|---------|-------------------|
| O1 | **Standalone kanban engine package** — importable without MCP dependency; MCP server is a thin adapter | `from owlbear_kanban import KanbanEngine` works; `server.py` contains only MCP wiring, boundary conversion, and schema metadata |
| O2 | **Canonical engine model** — engine owns one `Task` model; MCP server derives `KanbanTask` at boundary; `TaskSummary` replaces hand-built dicts | Single `Task` model in engine (`extra='allow'`); no hand-built dicts; `TaskSummary` for list views; boundary models trace back to engine model |
| O3 | **Dispatch gating in the engine** — `pick_dispatchable()` with gate predicates and priority ranking extracted from server.py | `pick_dispatchable` is importable and testable without MCP; no inline gating in `server.py` |
| O4 | **MCP behavioral compatibility** — all 8 MCP tools behave identically | Existing MCP tool tests pass unchanged; board loads correctly; claim/release/status semantics preserved |
| O5 | **GUI-ready data contract** — `board_config()`, `valid_transitions()`, revision counter | Engine exposes valid statuses/priorities, legal transitions per status, and a per-instance write-revision counter |

## Solution Approach

### Phase 1 — Engine Improvements (within current `serve/mcp-kanban/`)

All changes happen in the existing package structure. No packaging changes.

| Work Item | Detail |
|-----------|--------|
| Rename `TaskRecord` → `Task` | `engine_models.py`; `TaskRecord = Task` compat alias for transition |
| `TaskSummary` model | Schema-validated list projection (id, title, status, priority, tags, blocked, block_reason, claimed, parent, depends_on). Replaces hand-built `_strip` dicts in `server.py`. Adapter updates `outputSchema` patching to match. |
| `board_config()` | Returns `model_copy()` of cached config (valid statuses, priorities, display order) |
| `refresh_config()` | Reloads from disk, updates `self._config` + all derived state (tasks_dir, archive_dir, rank maps) |
| Config staleness fix | `create_task` updates `self._config` after reload; consistent with `refresh_config()` behavior |
| `valid_transitions(status)` | Returns all configured statuses except current. `end_work`'s linear behavior documented as agent-specific. |
| Revision counter | `self._revision: int` property, incremented on every write. Per-instance; loss on restart forces one full refresh. Cross-process detection deferred to GUI brief. |
| Activity log `actor` field | New JSONL entries get `actor`; old entries lack it (backward-compatible). All engine call sites updated. |
| Status/priority validation | `create_task`, `edit_task` raise `ValueError` for invalid values. MCP adapter maps to `ToolError` (existing pattern from `move_task`). |
| Timestamp sort fix | Parse to `datetime` for sort key computation; stored format unchanged. |

### Phase 2 — Extract Engine Package

| Work Item | Detail |
|-----------|--------|
| `serve/kanban/` package | New `pyproject.toml` (deps: ruamel.yaml, pydantic). Package: `owlbear_kanban` |
| Move engine files | `engine.py`, `models.py`, `task_io.py`, `config_loader.py`, `activity_log.py`, `agent_names.py` → `src/owlbear_kanban/` |
| Slim `serve/mcp-kanban/` | Keeps `server.py`, `models.py` (KanbanTask), `__main__.py`. Adds `owlbear-kanban` dependency |
| Remove compat alias | `TaskRecord = Task` alias removed; all imports updated |
| Workspace config | uv workspace members, root `pyproject.toml` coverage/ruff paths updated |
| Boundary tests | Engine: must NOT import `mcp` or transport packages. MCP adapter: allowed to import `owlbear_kanban`. Existing boundary test updated. |
| Import migration | Full `grep -r` to find and update all import sites across workspace |

### Phase 3 — Extract Dispatch

| Work Item | Detail |
|-----------|--------|
| `dispatch.py` in engine | `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]`. Owns gate predicates (TDD, clarity), priority/status rank maps. |
| Slim server `pick_tasks` | Thin wrapper: calls `pick_dispatchable()`, converts to `KanbanTask`, formats dispatch response |
| Dispatch tests | New test file in engine test surface; existing `pick_tasks` MCP tests continue passing |

## Target Package Topology

```
serve/
  kanban/                           # NEW — owlbear_kanban
    pyproject.toml                  # deps: ruamel.yaml, pydantic
    src/owlbear_kanban/
      __init__.py                   # exports: KanbanEngine, Task, TaskSummary, BoardConfig
      engine.py                     # KanbanEngine class
      models.py                     # Task, TaskSummary, BoardConfig
      task_io.py                    # filesystem read/write, path validation
      config_loader.py              # ruamel.yaml config load/save
      activity_log.py               # JSONL append logger
      agent_names.py                # adjective-noun pool
      dispatch.py                   # pick_dispatchable() — gate predicates + ranking

  mcp-kanban/                       # EXISTING — owlbear_mcp_kanban (slimmed)
    pyproject.toml                  # deps: owlbear-kanban, mcp[cli]
    src/owlbear_mcp_kanban/
      __init__.py
      __main__.py
      server.py                     # 8 MCP tools as thin wrappers + schema metadata
      models.py                     # KanbanTask (MCP boundary model)
```

## Out of Scope

- **GUI implementation** — separate ideation and brief
- **GUI technology choice** — standalone web, VS Code webview, etc.
- **Orchestrator planner removal** — `serve/orchestrator/planner/` and associated CLI/loop/waves code is dead but deeply wired; separate cleanup brief
- **Concurrent access controls** — accepted risk for single-laptop system (D2)
- **`delete_task` operation** — not a prerequisite; only archive exists
- **Cross-process revision detection** — per-instance counter only; GUI project decides its change-detection strategy

## Constraints & Risks

| Constraint/Risk | Mitigation |
|-----------------|------------|
| MCP schema monkey-patching (`mcp._tool_manager._tools`) | Accepted, isolated in adapter. Replace when FastMCP adds native `outputSchema`. |
| Agent-only methods accessible to any engine consumer | Documented as agent-oriented in engine API. GUI adapter must not expose `claim_task`, `start_work`, `release_task`, `end_work`, `pick_dispatchable`. Enforcement via adapter pattern. |
| Dispatch rank maps hardcoded (parallel to config display order) | Intentional: execution priority ≠ display order. `done` ranks highest in dispatch (needs post-processing) but last in display. Documented in `dispatch.py`. |
| Phase 2 changes repository packaging policy | Boundary test updated explicitly; workspace members, coverage config, ruff paths all updated in same phase. |
| Legacy timestamps (Go 7-digit nanoseconds) | Sort parses to `datetime`; stored format unchanged. Python 3.11+ `fromisoformat()` handles both formats. |

## Architecture Review Triage

| # | Finding | Disposition |
|---|---------|-------------|
| S1 | Three task representations | **Phase 1** — `TaskSummary` replaces hand-built dicts; two clean models remain |
| S2 | Dispatch policy in server.py | **Phase 3** — extracted to engine `dispatch.py` |
| S3 | Config staleness | **Phase 1** — `refresh_config()` + `create_task` fix |
| S4 | Schema monkey-patching | **Accepted** — isolated in adapter, replaced when FastMCP supports it |
| S5 | Linear status progression | **Resolved** — `move_task` already does arbitrary transitions; `end_work` linearity is by-design agent workflow |
| S6 | No delete operation | **Out of scope** — not a GUI prerequisite |
| S7 | Hardcoded kanban dir | **Resolved** — `kanban_dir` is a constructor parameter; default is an MCP adapter lifespan detail |
| S8 | MCP dependency coupling | **Phase 2** — engine extraction makes the separation explicit |

## Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Investment tier: **Shared** | Multi-consumer infrastructure, clean interfaces, thorough testing |
| D2 | Concurrent access: **Accepted risk** | Single-laptop, single-user. Optional future mitigation via `modified_since` check |
| D3 | Orchestrator planner: **Separate brief** | Dead code but deeply wired into CLI/loop/waves; orchestrator surgery, not kanban engine work |
| D4 | Phase sequencing: **Fix-then-extract** | Engine arrives complete and authoritative, not "authoritative in shape but not in behavior" |
| D5 | `valid_transitions()`: **This project** | Low cost, high value for GUI data contract |
| D6 | Revision counter: **This project** | Per-instance int, trivial to include; enables cheap GUI polling |
| D7 | Planner removal: **Separate brief** | Entire CLI dispatch pipeline (planner, loop, waves, CLI dispatch/run) is dead; cleanup scoped independently |

## Adoption Notes

- **For pipeline agents (MCP consumers):** No behavioral change. All 8 MCP tools produce identical results. Import paths change in Phase 2 but the MCP server is the stable interface.
- **For future GUI adapter:** Import `owlbear_kanban` directly. Use `board_config()` for metadata, `valid_transitions()` for move options, `revision` property for polling optimization. Do NOT expose `claim_task`, `start_work`, `release_task`, `end_work`, or `pick_dispatchable`.
- **For test maintenance:** Phase 1 adds compat alias. Phase 2 removes it and migrates all imports. Tests pass continuously throughout.
