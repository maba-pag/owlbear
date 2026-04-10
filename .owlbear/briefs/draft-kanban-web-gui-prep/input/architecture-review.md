# MCP-Kanban Architecture Review — Input for Ideation

> This document summarizes a deep architecture review of the `owlbear-mcp-kanban` package,
> conducted April 2026, in preparation for adding a web GUI to the kanban board.
> The review questions intent, architecture, implementation, and interfaces.

## Current State

### Package: `serve/mcp-kanban/`

9 source files, ~1600 LOC total. Single `pyproject.toml` with `dependencies = ["mcp[cli]>=1.26", "ruamel.yaml>=0.18"]`.

| File | Lines | Responsibility |
|------|-------|----------------|
| `server.py` | 530 | MCP tool defs, lifespan, dispatch gating, schema monkey-patching, output transformation |
| `engine.py` | 340 | Core CRUD + compound ops (claim/release/start_work/end_work) |
| `engine_models.py` | 85 | Internal models: `BoardConfig`, `TaskRecord` |
| `models.py` | 40 | MCP boundary model: `KanbanTask` |
| `task_io.py` | 200 | File read/write (YAML frontmatter + markdown), slug generation, path containment |
| `config_loader.py` | 135 | `config.yml` load/save with ruamel.yaml round-trip |
| `activity_log.py` | 30 | Append-only JSONL activity logging (one function) |
| `agent_names.py` | 200 | Two word lists for random agent name generation |
| `__main__.py` | 5 | Entry point |

### Data Flow

```
MCP Client (VS Code agent) → JSON-RPC/stdio → server.py → engine.py → task_io/config_loader → filesystem
```

### Test Coverage

~13 test files, ~500+ test functions covering engine, I/O, models, config, claims, compound ops, activity, MCP tool annotations, tool exclusion.

---

## Core Problem

The current package couples **core kanban logic** (engine, models, I/O) with the **MCP transport layer** (server.py) in a single package with a single dependency list. A web GUI cannot reuse the core without importing the MCP SDK.

The next phase is adding a web GUI for board visualization and user interaction. This GUI needs to:
1. Read/write tasks (same engine)
2. Show dispatch status (same gating logic)
3. Let users manage tasks (same CRUD)
4. Provide real-time board state (same data source)

---

## Identified Issues

### Structural

| # | Finding | Details |
|---|---------|---------|
| S1 | **Three task representations** | Same entity has 3 shapes: `TaskRecord` (engine), `KanbanTask` (MCP boundary, `claimed` bool), lean dict (`list_tasks` hand-built). Inconsistent, hard to extend. |
| S2 | **Dispatch policy in server.py** | `pick_tasks` gating (`_check_pick_gates`, `_PICK_NON_IMPL_TAGS`, priority/status ranking) is pipeline policy in the transport layer. ~60 lines, most-changed area. Not reusable by web GUI. |
| S3 | **Config staleness** | `create_task` reloads config; all other mutations use constructor-cached config. Inconsistent. |
| S4 | **Private API monkey-patching** | `outputSchema` and param descriptions injected via `mcp._tool_manager._tools` (FastMCP private internals). Functional but fragile. |
| S5 | **Linear status progression** | `end_work(outcome="success")` always advances to `statuses[idx+1]`. Pipeline-specific. Web GUI needs arbitrary transitions. |
| S6 | **No delete operation** | Only archive. Web users expect delete. |
| S7 | **Hardcoded kanban dir** | `Path(".owlbear/kanban")` resolved from CWD. No env var override. |
| S8 | **MCP dependency coupling** | `mcp[cli]` in package dependencies means core logic can't be imported without MCP SDK. |

### Strengths (keep)

- Atomic file writes (`tempfile.mkstemp` + `Path.replace()`)
- Timestamp string preservation (Go nanosecond compatibility)
- Config round-trip with comment/order preservation (ruamel.yaml)
- Path containment validation (null-byte, traversal, Windows reserved names)
- Append-only activity audit trail
- Cooperative claim timeout protocol
- Comprehensive test suite

---

## Key Decision for Ideation

**Should the kanban engine be extracted into a standalone package (`owlbear-kanban-core`) that both the MCP server and web GUI depend on?**

### Option A: Internal reorganization only

Reorganize files within the current package. Keep one `pyproject.toml`. Both MCP and web GUI import from `owlbear_mcp_kanban`.

- Pro: Minimal change, no new packages
- Con: Web GUI still drags in MCP SDK dependency; package name is misleading (`mcp_kanban` but used by non-MCP consumers)

### Option B: Two packages (`owlbear-kanban-core` + `owlbear-mcp-kanban`)

Core package has no MCP dependency. MCP package depends on core + `mcp[cli]`. Web GUI depends on core only.

- Pro: Clean dependency isolation, honest package naming, clean import boundary
- Con: Two pyproject.toml files, more workspace package management

### Option C: Single package, MCP as optional dependency

Keep one package but make `mcp[cli]` optional. Server.py lazy-imports MCP. Core importable without MCP installed.

- Pro: One package, clean imports
- Con: Unusual pattern, easy to accidentally break

---

## Neccessary Actions identified

The following actions from the review should be adressed :

| Title | Priority |
|-------|----------|
| Unify task output model at engine level | needed |
| Extract dispatch gating to dispatch_policy module | needed |
| Reload config on mutating engine operations | important |
| Isolate FastMCP schema patches in utility function | important |
| Add delete_task operation with archive-first safety | important |
| Add KANBAN_DIR env var override for kanban directory | important |
| Standardize MCP tool descriptions to single-line | needed |
| Validate status and priority on create_task | important |

---

## Constraints

- OwlBear uses `uv` workspace packages (monorepo with `pyproject.toml` per package)
- All development on `dev` branch
- Tests in root `tests/` directory (not per-package)
- The web GUI is probably TypeScript (separate technology), consuming the Python engine likely via HTTP API or MCP-over-SSE
- Pipeline agents (orchestrator, builder, etc.) are the primary current consumers of the MCP server
- User visibility into board state is the primary web GUI use case
