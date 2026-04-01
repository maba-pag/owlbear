---
name: mcp-project
description: "Query project metadata, README, and directory structure via the owlbear-project MCP server. Covers all 4 tools and 2 resources: project_info, project_list, project_readme, project_structure, project://readme, project://structure."
user-invocable: false
---

# MCP Project Skill

The `owlbear-project` MCP server exposes project metadata and file-system context
as read-only tools and resources over stdio transport.

## Server registration

The server is registered in `.vscode/mcp.json` as `owlbear-project`.

## Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `project_info` | Return metadata for the current project from `owlbear-project.json` | `dict` with `name`, `type`, `project_path`, `owlbear_path`, `created_at`; or an error string when config is absent |
| `project_list` | List all registered projects from `{owlbear_root}/data/projects/` | `list[{name, path}]`; empty list when directory is missing or contains no `.json` files |
| `project_readme` | Return the content of `README.md` from the project root | UTF-8 string; `"error: No README.md found in project root."` when absent |
| `project_structure` | Return an indented directory tree (max depth 3) of the project root | Indented text tree, excludes `.git`, `__pycache__`, `node_modules`, `.venv`, `.mypy_cache` |

## Resources

| URI | Description |
|-----|-------------|
| `project://readme` | Same content as `project_readme` tool — README.md from CWD, or `"No README.md found in project root."` |
| `project://structure` | Same content as `project_structure` tool — indented tree at max depth 3 |

## project_info details

`project_info` reads `owlbear-project.json` from the current working directory
(the project root where VS Code spawns the server). When the file is missing or
unparseable, the tool returns a descriptive error string rather than raising — the
server degrades gracefully to allow other tools to remain functional.

Successful response shape:

```json
{
  "name": "my-project",
  "type": "python-uv",
  "project_path": "/path/to/my-project",
  "owlbear_path": "/path/to/owlbear",
  "created_at": "2026-01-01T00:00:00+00:00"
}
```

## project_list details

`project_list` scans `{owlbear_root}/data/projects/` for `.json` files. Each file
is a project pointer written by `scripts/setup.py` during project registration.

Response shape per entry:

```json
[
  {"name": "my-project", "path": "/path/to/my-project"},
  {"name": "other-project", "path": "/path/to/other-project"}
]
```

The `owlbear_root` is resolved from the `OWLBEAR_ROOT` environment variable, with
`..` (parent of CWD) as the fallback.

## Error handling

All tools follow the `error: ` prefix convention for error strings, consistent with
other owlbear MCP servers. No tool raises an exception to the MCP transport — errors
are returned as string values.

## Configuration

The `owlbear-project` MCP server reads the following environment variables at startup:

| Variable | Default | Description |
|----------|---------|-------------|
| `OWLBEAR_ROOT` | `..` (parent of CWD) | Path to the owlbear installation root |
| `PROJECT_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated list of tool names to remove from the server |

### PROJECT_TOOLS_EXCLUDE

Set this variable to hide specific tools from the MCP server. This is useful when a client
should only have access to a subset of project operations.

**Syntax:** comma-separated tool names, whitespace around names is stripped.

```
PROJECT_TOOLS_EXCLUDE=project_list,project_structure
```

Valid names: `project_info`, `project_list`, `project_readme`, `project_structure`.

Unknown names are silently ignored. If the variable is not set or is empty, all tools
are registered (backwards-compatible default).
