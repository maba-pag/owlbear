---
id: 674
title: Fix stale `packages/` path constants in root test files
status: backlog
priority: needed
created: 2026-04-08T17:12:36.9831345+02:00
updated: 2026-04-08T17:12:36.9831345+02:00
tags:
    - scope:tests
    - ' type:fix'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis (`.owlbear/research/analysis-synthesis.md`) identified stale path constants in root test files. The `packages/` → `serve/` rename (task #601) missed at least 2 runtime `Path` constants:

- `test_approve_memory_531.py` — `_PACKAGE_DIR = _REPO_ROOT / "packages" / "mcp-memory"`
- `test_mcp_kanban_server.py` — `_MCP_KANBAN_PYPROJECT = ... / "packages" / "mcp-kanban" / "pyproject.toml"`

There may be additional occurrences.

## Acceptance Criteria

- [ ] AC1: Grep all files under `tests/` for `packages/` path references (both string literals and `Path` objects)
- [ ] AC2: Update every operational `Path` constant from `packages/` to `serve/`
- [ ] AC3: Do NOT change comments, docstrings, or historical references — only runtime paths
- [ ] AC4: All affected tests pass after the fix (`uv run pytest tests/test_approve_memory_531.py tests/test_mcp_kanban_server.py -x`)
- [ ] AC5: No remaining `Path(... / "packages" / ...)` constructions in `tests/` that reference current serve packages
