# Extract Engine to serve/kanban/ + Workspace Config

> **Owning task:** #818 — Extract engine to serve/kanban/ + workspace config
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Phase 2 of the kanban engine restructuring (#798). After Phase 1 delivers `Task`, `TaskSummary`, `BoardConfig`, revision counter, and other engine improvements inside `serve/mcp-kanban/`, this task extracts the engine files into a standalone `serve/kanban/` package (`owlbear_kanban`) so it can be imported without MCP dependencies. The MCP server becomes a thin adapter depending on `owlbear-kanban`.

**Key question:** What's needed to cleanly extract the engine, update workspace config, and keep all tests passing?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/knowledge/pyproject.toml` + `serve/mcp-knowledge/pyproject.toml` | Codebase | 1.0 — exact precedent for engine/adapter split |
| S2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/` (all .py files) | Codebase | 1.0 — subject files |
| S3 | `tests/test_package_boundary.py` | Codebase | 0.9 — must be updated for new namespace |
| S4 | Root `pyproject.toml` (ruff, coverage, uv workspace) | Codebase | 0.9 — config changes needed |
| S5 | Brief `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Codebase | 1.0 — target topology and rationale |
| S6 | ~25 test files importing `owlbear_mcp_kanban.engine*` | Codebase | 0.8 — import migration scope |

## 3. Analysis

### 3.1 Engine File MCP Independence (confirmed)

All 6 engine files (`engine.py`, `engine_models.py`, `task_io.py`, `config_loader.py`, `activity_log.py`, `agent_names.py`) import only: `pydantic`, `ruamel.yaml`, `yaml` (PyYAML), stdlib. **Zero MCP imports.** Extraction is clean.

### 3.2 Hidden Dependency: PyYAML

| File | YAML lib | Usage |
|------|----------|-------|
| `task_io.py` | `import yaml` (PyYAML) | Custom `SafeLoader` subclass, `yaml.dump()` for task serialization |
| `config_loader.py` | `from ruamel.yaml import YAML` | Config file load/save |

**AC lists deps as `ruamel.yaml, pydantic`.** But `task_io.py` needs PyYAML. Currently works because `mcp[cli]` pulls it in transitively. After extraction, it won't be available.

| Option | Pros | Cons | Rec |
|--------|------|------|-----|
| A: Add `pyyaml` to deps | Zero-scope change, matches current code | Two YAML libs in one package | **(rec)** |
| B: Migrate task_io to ruamel.yaml | Single YAML lib, cleaner | Extra scope, custom SafeLoader needs rewrite | **(bp)** |

**Recommendation:** Option A for #818 (extraction scope). Option B as optional follow-up.

### 3.3 Workspace Config Changes

| Config | Current | After extraction |
|--------|---------|-----------------|
| `[tool.uv.workspace] members` | `["serve/*"]` | No change — glob auto-discovers `serve/kanban/` |
| `[tool.coverage.run] source_pkgs` | 7 entries, no `owlbear_kanban` | Add `"owlbear_kanban"` |
| `[tool.ruff] src` | 6 entries, no `serve/kanban/src` | Add `"serve/kanban/src"` |
| `test_package_boundary.py` ALLOWED_IMPORTS | `owlbear_mcp_kanban: set()` | Add `owlbear_kanban: set()`, change `owlbear_mcp_kanban: {"owlbear_kanban"}` |

### 3.4 Package Topology (matches brief)

```
serve/kanban/
  pyproject.toml          # deps: ruamel.yaml, pydantic, pyyaml
  src/owlbear_kanban/
    __init__.py            # exports: KanbanEngine, Task, TaskSummary, BoardConfig
    engine.py              # from engine.py (intra-imports updated)
    models.py              # from engine_models.py (renamed)
    task_io.py             # intra-imports updated
    config_loader.py       # intra-imports updated
    activity_log.py        # no intra-imports to update
    agent_names.py         # no intra-imports to update
```

### 3.5 Import Migration Scope

| Category | Files | Change |
|----------|-------|--------|
| Engine intra-package | 3 (`engine.py`, `task_io.py`, `config_loader.py`) | `owlbear_mcp_kanban.X` → `owlbear_kanban.X` |
| MCP adapter (`server.py`) | 1 | Engine imports → `owlbear_kanban.*`; keep `owlbear_mcp_kanban.models` |
| Test files (engine tests) | ~14 | `owlbear_mcp_kanban.engine*` → `owlbear_kanban.*` |
| Test files (MCP tests) | ~11 | No change — import `owlbear_mcp_kanban.server` / `.models` |
| `serve/mcp-kanban/pyproject.toml` | 1 | Add `owlbear-kanban` dep with `workspace = true` source |

### 3.6 File Rename: engine_models.py → models.py

The brief targets `models.py` in the engine package. No collision — the MCP package keeps its own `models.py` (`KanbanTask`). The rename is part of the move (no in-place rename needed; source file stays at old location until deleted/cleared).

## 4. Recommendation

Direct extraction following the `knowledge` / `mcp-knowledge` precedent. The codebase already uses this exact pattern. All engine files are MCP-free. The only gap in the AC is the missing `pyyaml` dependency.

**Confidence: 0.90** — High confidence. Proven pattern, confirmed clean boundary, well-scoped.

Challenge: FALLBACK — researcher mode does not have challenger subagent available.

### AC Modification Required

Add `pyyaml` to the dependency list in `serve/kanban/pyproject.toml`: `ruamel.yaml, pydantic, pyyaml`.

## 5. Follow-up Tasks

| Task | Status | Rationale |
|------|--------|-----------|
| Migrate task_io.py from PyYAML to ruamel.yaml | Optional follow-up | Removes redundant YAML lib; not blocking for extraction |
