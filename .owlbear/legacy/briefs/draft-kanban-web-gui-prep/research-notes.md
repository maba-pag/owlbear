# Kanban Restructuring — Research Notes

## Codebase Scan

### mcp-kanban Package (serve/mcp-kanban/)

**Engine (engine.py, 560 LOC):** 15 public methods — list_tasks, show_task, create_task, edit_task, move_task, claim_task, release_task, start_work, end_work. All return TaskRecord. Config cached at construction (except create_task which reloads).

**TaskRecord (engine_models.py):** id, title, status, priority, created (str), updated (str), body, tags[], parent, depends_on[], blocked, block_reason, claimed_by, claimed_at. Extra='allow' preserves unknown fields.

**KanbanTask (models.py, MCP boundary):** Same fields but claimed_by→claimed (bool) via model_validator. Extra='ignore'. Also adds `file` field.

**server.py (670 LOC):** 8 MCP tools (list_tasks, show_task, create_task, edit_task, move_task, start_work, end_work, pick_tasks). Inline dispatch gating (~60 lines). Schema monkey-patching via mcp._tool_manager._tools private API. list_tasks returns hand-built lean dicts (not KanbanTask).

**task_io.py (300 LOC):** YAML frontmatter read/write, slug generation, path containment validation (null byte, traversal, Windows reserved). Atomic writes via tempfile.mkstemp + Path.replace().

**config_loader.py (80 LOC):** ruamel.yaml round-trip preserving comments/order. Load/save config.yml.

**activity_log.py (20 LOC):** Single function, append-only JSONL.

**pyproject.toml dependencies:** mcp[cli]>=1.26, ruamel.yaml>=0.18

### Orchestrator Planner (serve/orchestrator/src/owlbear/planner/)

**board.py:** Reads board via `kanban-md list --json` subprocess. Returns Task[] with datetime parsing.

**gates.py:** check_tdd() — in-progress needs non-impl tag OR "## Test-Writer Notes". check_clarity() — active statuses need bullet/numbered AC. Same logic as server.py but independent implementation.

**selector.py:** select_tasks() — filters crashed, applies gates, sorts by (priority_rank, status_rank), caps at 20, routes via STATUS_AGENT_MAP.

**models.py:** Task (frozen, datetime timestamps), DispatchEntry, DispatchPlan. No imports from mcp-kanban.

### Cross-Consumer Coupling
- Orchestrator and MCP-kanban are fully independent
- No shared imports, no shared library
- Gate logic duplicated — manual sync point documented in planner/__init__.py
- Orchestrator still calls kanban-md Go binary, not the Python engine

### Test Structure
- 19 kanban engine/MCP test files (direct unit tests + mock MCP context)
- 5 planner test files (direct function calls, mock subprocess)
- No cross-module test coupling
- Each layer tested independently

## Architecture Review Items (from input/architecture-review.md)

| # | Finding | Current Status |
|---|---------|---------------|
| S1 | Three task representations | Confirmed: TaskRecord, KanbanTask, orchestrator Task |
| S2 | Dispatch policy in server.py | Confirmed: ~60 lines inline gating + duplicated in planner |
| S3 | Config staleness | Confirmed: create_task reloads, others use cached |
| S4 | Private API monkey-patching | Confirmed: mcp._tool_manager._tools patching |
| S5 | Linear status progression | Partially wrong: move_task already does arbitrary transitions. end_work is linear but by design (success=advance) |
| S6 | No delete operation | Confirmed: only archive |
| S7 | Hardcoded kanban dir | Confirmed: Path(".owlbear/kanban") from CWD |
| S8 | MCP dependency coupling | Confirmed but overstated: packaging-only coupling, engine code doesn't import MCP |
