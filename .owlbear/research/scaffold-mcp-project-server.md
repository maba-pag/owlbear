# Scaffold mcp-project MCP Server Package

> **Owning task:** #41 — Scaffold mcp-project MCP server package
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #41 asks to scaffold `packages/mcp-project/` — a FastMCP MCP server exposing project metadata (tools: `set_active_project`, `list_projects`; resource: `owlbear-project.json`). The v1 codebase already has `ProjectStore`, `Project` model, and a `ProjectToolset` at `v1/src/owlbear/projects/`. The v2 architecture replaces the daemon-embedded toolset with a standalone MCP server.

**Key question:** What package structure, tool signatures, resource pattern, and `owlbear-project.json` schema should the scaffold use?

**Overlap:** Task #17 ("Build mcp-project server") has broader AC including `project://readme`, `project://structure` resources and a `SKILL.md`. #41 is the minimal scaffold; #17 adds full features on top. Recommend marking #17 as `depends_on: [41]`.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | MCP Python SDK README (v1 stable) | <https://github.com/modelcontextprotocol/python-sdk> | .95 |
| 2 | VS Code MCP Config Reference | <https://code.visualstudio.com/docs/copilot/reference/mcp-configuration> | .90 |
| 3 | v1 ProjectStore / Project model | `v1/src/owlbear/projects/store.py`, `v1/src/owlbear/projects/models.py` | .85 |
| 4 | docs/research/mcp-python-sdk.md | Local — MCP SDK deep-dive (#2) | .95 |
| 5 | docs/research/monorepo-tooling.md | Local — monorepo workspace patterns | .80 |

## 3. Analysis

### 3.1 Package structure

| Option | Pattern | KISS |
|--------|---------|------|
| A: Flat `server.py` + `__main__.py` | FastMCP quickstart pattern (Source 1) | High |
| B: Sub-packages (`tools/`, `resources/`) | Larger servers (mcp-kanban) | Medium |

**Recommendation (.90):** Option A — flat layout. Two tools + one resource fits in a single `server.py`. Split later only when needed (YAGNI).

```
packages/mcp-project/
├── pyproject.toml
├── src/
│   └── mcp_project/
│       ├── __init__.py
│       ├── __main__.py      # python -m mcp_project entry point
│       └── server.py        # FastMCP instance, tools, resource
└── tests/
    └── test_server.py
```

### 3.2 `owlbear-project.json` schema

From task #12 and #17 AC: `name, type, owlbear_path, created_at` (minimal, extensible). This lives in each project root (written by `owlbear setup`).

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Human-readable project name |
| `type` | string | Template used (bare, python-uv, etc.) |
| `owlbear_path` | string | Relative path to owlbear installation |
| `created_at` | string (ISO 8601) | When the project was initialized |

The resource decorator reads this file from CWD (since VS Code spawns the server in the workspace folder).

### 3.3 Tool signatures

| Tool | Params | Returns | Side effects |
|------|--------|---------|-------------|
| `set_active_project` | `project_name: str` | Confirmation string | Writes `config_dir/active_project` |
| `list_projects` | none | Formatted project list | None (read-only) |

The v1 `ProjectToolset` has identical semantics. The MCP tools are thin wrappers that delegate to `ProjectStore` (imported from the knowledge package or duplicated as simple file ops).

### 3.4 Resource pattern

```python
@mcp.resource("project://definition")
def project_definition() -> str:
    """Read owlbear-project.json from workspace root."""
    path = Path("owlbear-project.json")
    if not path.exists():
        return '{"error": "No owlbear-project.json found"}'
    return path.read_text(encoding="utf-8")
```

This follows the FastMCP `@mcp.resource()` decorator pattern (Source 1, §Resources).

### 3.5 VS Code registration

```json
{
  "servers": {
    "owlbearProject": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}/../owlbear", "python", "-m", "mcp_project"],
      "dev": { "watch": "packages/mcp-project/**/*.py" }
    }
  }
}
```

Naming follows VS Code camelCase convention (Source 2). Dev watch enables auto-restart.

### 3.6 pyproject.toml

Hatchling backend with `src/` layout per monorepo-tooling research (Source 5). Minimal deps: `mcp[cli]>=1.26`.

## 4. Recommendation (.85 confidence)

Scaffold with flat Option A layout. Use `mcp[cli]>=1.26` as the only dependency. Implement `set_active_project` and `list_projects` as simple file-based ops (read/write `owlbear-project.json` and `active_project` file). Expose `project://definition` as a resource. Register in `.vscode/mcp.json`.

**Risk:** `set_active_project` needs a project store directory convention. For the scaffold, use a simple `~/.owlbear/projects/` path or accept it as a config parameter. The architect should decide the storage location.

**Task #17 dependency:** Mark #17 as depending on #41 since #41 provides the package skeleton that #17 extends.

## 5. Follow-up Tasks

The scaffold task #41 itself is already created. The needed follow-ups are:

1. Update #17 to depend on #41 (prevents parallel work on the same package)
2. Create a task for `owlbear-project.json` schema definition (shared by setup script #12 and mcp-project server #41/#17)
