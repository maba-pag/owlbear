---
id: 543
title: 'Test: TypedDict return types for outputSchema on mcp-project'
status: todo
priority: important
created: 2026-04-02T07:53:54.8951737+02:00
updated: 2026-04-04T07:32:46.6822253+02:00
started: 2026-04-02T07:54:11.3863978+02:00
tags:
    - scope:mcp
    - ' type:test'
    - ' test'
    - ' phase-2'
class: standard
---

## Acceptance Criteria

- [x] Schema-pinning test: `fn_metadata.output_schema` for `project_info` has top-level `properties` with keys: name, type, project_path, owlbear_path, created_at (all `type: string`)
- [x] Schema-pinning test: `fn_metadata.output_schema` for `project_list` items schema contains `name` and `path` properties (inside FastMCP `result` wrapper)
- [x] ToolError test: `project_info` raises `ToolError` (from `mcp.server.fastmcp.exceptions`) when `project_file is None`
- [x] ~~All new tests fail (RED phase)~~ Pipeline note: implementation was committed (df21f2f) before RED-phase review. AC1-AC3 verified with 15 passing tests.

## Design Notes

- Access `fn_metadata.output_schema` via `mcp._tool_manager._tools` (same pattern as mcp-kanban schema overrides)
- `project_info` returns TypedDict directly: fields at top-level `properties`
- `project_list` returns `list[TypedDict]`: fields inside FastMCP `{result: {items: ...}}` wrapper
- Test file: `packages/mcp-project/tests/test_typeddict_outputschema_542.py`
