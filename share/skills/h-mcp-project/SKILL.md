---
name: h-mcp-project
description: "Handbook: owlbear-project MCP tool reference — project metadata, README, and structure"
user-invocable: false
---

# MCP Project Tool Reference

The `owlbear-project` MCP server exposes project metadata and file-system context as read-only tools and resources over stdio transport. Registered in `.vscode/mcp.json` as `owlbear-project`.

## Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `project_info` | Return metadata from `owlbear-project.json` | `dict` with `name`, `type`, `project_path`, `owlbear_path`, `created_at`; or `ToolError` if missing |
| `project_list` | List all registered projects from `{owlbear-root}/store/projects/` | `list[{name, path}]`; empty list when directory missing |
| `project_readme` | Return `README.md` content from project root | UTF-8 string; `"error: No README.md found in project root."` when absent |
| `project_structure` | Return indented directory tree (max depth 3) | Indented text tree; excludes `.git`, `__pycache__`, `node_modules`, `.venv`, `.mypy_cache` |

## Resources

| URI | Description |
|-----|-------------|
| `project://readme` | Same content as `project_readme` tool |
| `project://structure` | Same content as `project_structure` tool |

## project_info Details

Reads `owlbear-project.json` from the current working directory (the project root where VS Code spawns the server). When the file is missing or unparseable, raises `ToolError` (MCP `isError: true`) — other tools remain functional.

Response shape:

```json
{
  "name": "my-project",
  "type": "python-uv",
  "project_path": "/path/to/my-project",
  "owlbear_path": "/path/to/owlbear",
  "created_at": "2026-01-01T00:00:00+00:00"
}
```

## project_list Details

Scans `{owlbear-root}/store/projects/` for `.json` files. Each file is a project pointer written by `setup/init.py` during project registration.

Response shape:

```json
[
  {"name": "my-project", "path": "/path/to/my-project"},
  {"name": "other-project", "path": "/path/to/other-project"}
]
```

The `owlbear-root` is resolved from `OWLBEAR_ROOT` env var, with `..` (parent of CWD) as fallback.

## Error Handling

`project_info` raises `ToolError` when `owlbear-project.json` is missing. All other tools follow the `error: ` prefix convention for error strings. No other tool raises an exception to the MCP transport.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_ROOT` | `..` (parent of CWD) | Path to the owlbear installation root |
| `PROJECT_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated tool names to remove |

`PROJECT_TOOLS_EXCLUDE` accepts: `project_info`, `project_list`, `project_readme`, `project_structure`. Unknown names silently ignored.

## Known Gotchas

- **`project_info` raises `ToolError` on missing config.** When `owlbear-project.json` is missing, it raises `ToolError` (not an error string), but the server stays up. Other tools remain functional.
- **`project_list` depends on `OWLBEAR_ROOT`.** If the env var is unset and CWD is not inside a project directory with a parent owlbear installation, the fallback `..` may scan the wrong location.
