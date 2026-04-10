# Architect Voice — Kanban Engine Restructuring

## Architectural Stance

**Sibling package extraction with phased migration.** Split the current `serve/mcp-kanban/` into two packages: a transport-free engine package (`owlbear_kanban`) and a thin MCP adapter (`owlbear_mcp_kanban` that depends on it). The engine owns the canonical task model, dispatch policy, and all board operations. The MCP adapter contains only MCP tool definitions, boundary models, and schema metadata. Dependency direction: MCP → Engine, never the reverse.

This is a packaging restructure of already-transport-free code. The engine logic doesn't import MCP today — the coupling is one `pyproject.toml` and shared namespace. The restructuring makes that separation explicit and importable.

## Structural Reasoning

### 1. Package Topology

```
serve/
  kanban/                           # NEW — owlbear_kanban
    pyproject.toml                  # deps: ruamel.yaml, pydantic
    src/owlbear_kanban/
      __init__.py                   # exports: KanbanEngine, Task, TaskSummary, BoardConfig
      engine.py                     # KanbanEngine class (from current engine.py)
      models.py                     # Task, TaskSummary, BoardConfig (from engine_models.py)
      task_io.py                    # filesystem read/write, path validation
      config_loader.py              # ruamel.yaml config load/save
      activity_log.py               # JSONL append logger
      agent_names.py                # adjective-noun pool
      dispatch.py                   # pick_dispatchable() — extracted from server.py

  mcp-kanban/                       # EXISTING — owlbear_mcp_kanban (slimmed)
    pyproject.toml                  # deps: owlbear-kanban, mcp[cli]
    src/owlbear_mcp_kanban/
      __init__.py
      __main__.py
      server.py                     # 8 MCP tools as thin wrappers + schema metadata
      models.py                     # KanbanTask (MCP boundary model)
```

**Why sibling packages, not nesting:** Each package has its own `pyproject.toml`, its own dependency set, and its own test surface. The engine is installable without MCP. The MCP adapter declares the engine as a dependency. uv workspace members handle the dev-time linking.

### 2. Module Boundaries

**In the engine (`owlbear_kanban`):**

| Module | Responsibility |
|--------|---------------|
| `engine.py` | `KanbanEngine` class — all board operations (list, show, create, edit, move, claim, release, start_work, end_work, board_config, refresh_config) |
| `models.py` | `Task` (renamed from `TaskRecord`, `extra='allow'`), `TaskSummary` (schema-validated list projection), `BoardConfig` and sub-models |
| `dispatch.py` | `pick_dispatchable(engine, *, limit, tag) → list[Task]` — gate predicates + priority/status ranking; policy constants live here |
| `task_io.py` | `read_task`, `write_task`, `make_task_filename`, `validate_path_containment` |
| `config_loader.py` | `load_config`, `save_config` |
| `activity_log.py` | `log_activity` (with new `actor` parameter) |
| `agent_names.py` | `ADJECTIVES`, `NOUNS` lists |

**In the MCP adapter (`owlbear_mcp_kanban`):**

| Module | Responsibility |
|--------|---------------|
| `server.py` | 8 MCP tool functions (thin wrappers calling engine methods), `KanbanTask` conversion, `AppContext`/lifespan, schema monkey-patching, `StrId` coercion, tool exclusion logic |
| `models.py` | `KanbanTask` — MCP boundary model (`claimed_by` → `claimed` bool, `extra='ignore'`, optional `file` field) |

### 3. Engine Public API

```python
class KanbanEngine:
    def __init__(self, kanban_dir: Path, *, agent_name: str | None = None) -> None: ...

    # Core CRUD
    def list_tasks(self, *, status, tag, priority, search, sort, ...) -> list[Task]: ...
    def show_task(self, task_id: str) -> Task: ...
    def create_task(self, title: str, *, body, tags, priority, status, ...) -> Task: ...
    def edit_task(self, task_id: str, *, title, body, priority, ...) -> Task: ...
    def move_task(self, task_id: str, status: str) -> Task: ...

    # Agent workflow (documented as agent-oriented, not hidden)
    def claim_task(self, task_id: str) -> Task: ...
    def release_task(self, task_id: str) -> Task: ...
    def start_work(self, task_id: str) -> Task: ...
    def end_work(self, task_id: str, *, note, outcome, ...) -> Task: ...

    # Config access
    def board_config(self) -> BoardConfig: ...   # returns defensive copy of cached config
    def refresh_config(self) -> None: ...         # reloads config + updates derived state

    @property
    def agent_name(self) -> str: ...

# Module-level dispatch function
def pick_dispatchable(engine: KanbanEngine, *, limit: int = 25, tag: str = "") -> list[Task]: ...
```

**Design rules:**
- Every method returns `Task` (the canonical model). No hand-built dicts, no boundary models.
- `board_config()` returns `self._config.model_copy()` — a defensive copy preventing consumers from mutating engine state. `BoardConfig` is mutable (Pydantic model with `extra='allow'`), so exposing the live object would leak mutable internal state.
- `refresh_config()` reloads from disk and updates ALL derived state: `self._config`, `self._tasks_dir`, `self._archive_dir`. This prevents split-brain behavior between config and derived paths.
- `TaskSummary` is a schema-validated projection for list views — replaces the hand-built `_strip` dict in server.py's `list_tasks`. Fields: `id`, `title`, `status`, `priority`, `tags`, `blocked`, `block_reason`, `claimed` (bool), `parent`, `depends_on`. No body, no timestamps, no file path. Constructed from `Task` via explicit method.

### 4. Dispatch Policy Design

The dispatch module (`dispatch.py`) owns:
- Gate predicates: TDD gate (in-progress needs test-writer notes or non-impl tag), clarity gate (active statuses need bullet/numbered AC)
- Priority ranking: `critical` > `needed` > `important` > `nice-to-have` > `someday`
- Status ranking: `done` > `docs` > `review` > `in-progress` > `todo` > `backlog` > `research`
- Result capping (default 25)

**These rank maps are intentionally hardcoded, not config-derived.** The engine's `list_tasks(sort="priority")` uses config-defined ordering (display/column order). The dispatch policy uses execution priority ordering ("what should an agent work on next?"). These serve different purposes: `done` tasks rank highest in dispatch (need post-processing) but last in display. Conflating them would force config.yml to encode agent workflow policy.

### 5. Migration Strategy

Four phases, each independently shippable and testable. Phase 0 is a substantial refactor and should be scoped as its own project brief.

| Phase | Scope | Key Work | Risk |
|-------|-------|----------|------|
| **0 — Drop planner** | Remove `serve/orchestrator/planner/` per D3 | Delete planner directory, excise imports from `cli.py`/`loop.py`/`waves.py`, remove `kanban-planner` wave routing, handle `retry_hint` removal in loop, update affected tests (planner tests + orchestrator tests that import planner models). **Must verify which loop.py code paths are dead vs live before deleting.** | Medium — planner is deeply wired into the orchestrator despite D3 declaring it unused |
| **1 — Extract engine** | Move engine files to `serve/kanban/` | Create new `pyproject.toml`, move files, update ALL imports (full `grep -r owlbear_mcp_kanban` to find every site), update workspace members list, coverage config, boundary tests. Rename `TaskRecord` → `Task` with `TaskRecord = Task` compat alias. No logic changes. | Low — mechanical but broad-surface |
| **2 — Extract dispatch** | Move `pick_tasks` logic to engine `dispatch.py` | Extract `_check_pick_gates`, rank maps, `pick_dispatchable()` function. Server's `pick_tasks` tool becomes thin wrapper. New dispatch-specific tests. | Low — logic unchanged, location changes |
| **3 — Engine improvements** | Additive features | `TaskSummary` model, `board_config()`/`refresh_config()`, status/priority validation in `create_task`/`edit_task`, `actor` field on `log_activity()`, fix `create_task` config cache update | Low — additive, no breaking changes |

**Phase 0 caveat:** D3 is a user decision that the planner is dead code. The Critic correctly identified that the planner has active test coverage and deep wiring into the orchestrator (CLI subcommands, dispatch loop, wave routing, retry_hint semantics). Removal is a refactoring task, not a directory deletion. Phase 0 must begin with auditing which orchestrator code paths actively use the planner at runtime vs. which are tested but never executed. This audit determines the scope of orchestrator surgery needed.

**Phase ordering is strict:** 0 → 1 → 2 → 3. Phase 0 eliminates the dual-dispatch ambiguity. Phase 1 establishes the engine package. Phase 2 moves dispatch logic into it. Phase 3 adds new capabilities.

### 6. Schema Monkey-patching

**Accept and isolate.** The private API access (`mcp._tool_manager._tools`) is an MCP adapter concern. It serves two purposes:
1. Setting `outputSchema` on tools returning structured content
2. Patching parameter descriptions and enum values for agent discoverability

**Why this is acceptable:**
- FastMCP doesn't support `outputSchema` in the `@mcp.tool()` decorator — this is an upstream gap, not our design flaw
- The patching is isolated to `server.py` in the adapter package
- Tests that validate the patching (`test_tool_annotations_494.py`, `test_mcp_kanban_kanbantask_model_495.py`) also live in the adapter test surface
- A FastMCP version bump could break both patching and tests — this is a known, scoped risk

**Escape hatch:** When FastMCP adds native `outputSchema` support, replace the patching with declarative schema. This is a one-package change.

**Alternative considered and rejected:** Manual tool registration (bypassing `@mcp.tool()` decorators) would eliminate the patching but lose decorator ergonomics and parameter introspection for no structural benefit.

### 7. Package Boundary Governance

The existing `test_package_boundary.py` enforces that `owlbear_mcp_kanban` has no `owlbear`-namespace imports (empty allowlist). The restructuring changes this contract:

- **MCP adapter boundary:** `owlbear_mcp_kanban` is now allowed to import from `owlbear_kanban` (its declared dependency). Boundary test updated to reflect this.
- **Engine boundary (new):** `owlbear_kanban` must NOT import from `owlbear_mcp_kanban`, `mcp`, or any transport package. New boundary test enforces this.
- **Architecture standards** already permit MCP servers importing a core library — the boundary test was lagging behind.

## Key Trade-offs

| This approach costs | What it avoids |
|---|---|
| New package (pyproject.toml, workspace member, CI config) | GUI importing MCP just to use the engine |
| ~19 test file import updates + boundary test rewrite | Shared namespace confusion between engine and transport concerns |
| Phase 0 orchestrator surgery (planner removal) | Permanent dual-dispatch ambiguity |
| Hardcoded dispatch rank maps (parallel to config ranks) | Config.yml encoding agent workflow policy |
| Defensive copy in `board_config()` | Consumers mutating engine internal state |

## Warnings

1. **Phase 0 is the riskiest phase.** The planner is declared dead (D3) but deeply wired. The orchestrator loop, CLI, wave routing, and retry_hint semantics all touch planner code. Before deleting, someone must verify which runtime paths actually execute the planner vs. which are tested but dormant. Underestimating this scope is the primary delivery risk.

2. **Config staleness is a pre-existing bug, not introduced by restructuring.** `create_task` reloads config for `next_id` but doesn't update `self._config`. `end_work` uses cached config for status progression. `move_task` validates against cached statuses. When a second consumer (GUI) eventually exists, stale cached config could cause `move_task` to reject a valid status that was added via config after engine construction. `refresh_config()` is the mitigation but requires consumers to call it.

3. **`TaskRecord = Task` alias is a transition aid, not permanent.** The alias keeps existing code working during Phase 1 but should be removed in a follow-up cleanup pass. It must not persist — two names for one model is the problem we're solving.

4. **The MCP schema patching will break.** It uses private FastMCP internals. It works today, it's tested, and the blast radius is one package. But it WILL break on a FastMCP upgrade. The architecture accepts this — the alternative is worse.

5. **Engine-side validation is missing for create_task and edit_task.** Currently only `move_task` validates status against config. `create_task` and `edit_task` accept arbitrary status and priority strings. With multiple consumers, invalid values become more likely. Phase 3 adds this validation, but until then the engine silently accepts garbage.

## Peer Position Evaluation

### Agreements
- **Data voice:** Rename `TaskRecord` → `Task`, add `TaskSummary`, string timestamps with `extra='allow'`, no `file` field on canonical model, activity log actor field. Fully aligned.
- **Security voice:** Adapter-pattern trust boundaries, consumer identity via constructor, agent-only methods documented not hidden. Fully aligned.
- **End-User voice:** Canonical model, boundary projection, `board_config()`. Aligned on fundamentals.

### Deferrals (restructuring scope, not this project)
- **`valid_transitions()`** (End-User): New feature requiring a transition map. The engine currently allows arbitrary transitions by design. Belongs in the GUI project brief, not restructuring.
- **Revision counter** (End-User): Adds mutable state to the engine for a polling optimization that only one consumer (future GUI) needs. Premature with only MCP as a consumer. Defer to GUI project.
- **`get_board()`** (End-User): Grouping tasks by status is trivial (5-line dict comprehension). Not a domain operation worth encoding in the engine. Adapter concern.
- **Timestamp sort bug** (Data): Real bug — string comparison with mixed timezone offsets produces wrong ordering. Separate bug fix task, not a restructuring concern.

### Contradiction resolved
- End-User asks for `board_config()` returning queryable metadata. Data voice warns about config staleness. Security voice wants consumer identity on constructor. Resolution: `board_config()` returns a **defensive copy** of cached config (consistency with all engine methods), `refresh_config()` for explicit reload, `agent_name` already serves as consumer identity per Security voice's recommendation — no new constructor parameter needed.

## Confidence

**0.85** — Position hardened through four Critic cycles. Core architecture (sibling extraction, dependency direction, phased migration) is sound. Primary uncertainty is Phase 0 scope: the planner removal is a decided matter (D3) but the implementation effort is larger than it appears from the surface. Secondary uncertainty is whether dispatch rank maps should eventually converge with config — currently they serve different purposes, but this could become a maintenance burden if statuses/priorities change frequently.
