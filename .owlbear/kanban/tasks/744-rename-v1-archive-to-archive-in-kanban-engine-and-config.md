---
id: 744
title: Rename v1-archive to archive in kanban engine and config
status: backlog
priority: nice-to-have
created: '2026-04-10T06:55:30.179602+00:00'
updated: '2026-04-10T06:55:30.179602+00:00'
tags:
- cleanup
- kanban
- v1-analysis
parent: null
depends_on:
- 741
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---

## Objective

Rename the kanban archive directory from `v1-archive` to `archive`. The `v1-archive` name is a historical artifact from the v1→v2 migration; the engine now uses it for all archived tasks (v2-era included).

## Context

Created during architecture review of #741. The v1-archive directory contains 1016 tasks — 317 of which are v2-era archived tasks. The kanban engine actively reads from and writes to this directory. Renaming makes the purpose clear and removes the last v1-naming artifact from the kanban system.

## What to change

- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`: Change `_ARCHIVE_DIR_NAME = "v1-archive"` to `_ARCHIVE_DIR_NAME = "archive"`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`: Update docstrings referencing "v1-archive"
- `tests/test_kanban_engine_compound.py`: Update 2 references to `v1-archive`
- `tests/test_kanban_engine_listing.py`: Update 8 references to `v1-archive`
- `.owlbear/kanban/v1-archive/` → `.owlbear/kanban/archive/` (rename directory)
- Config file references (`.cspell.json`, `.editorconfig`, `.mega-linter.yml`, `.vscode/settings.json`): Update `v1-archive` → `archive`

## Acceptance Criteria

- [ ] `_ARCHIVE_DIR_NAME` in engine.py changed to `"archive"`
- [ ] All engine.py docstrings updated to say "archive/" instead of "v1-archive/"
- [ ] Test files updated to use "archive" directory name
- [ ] `.owlbear/kanban/v1-archive/` renamed to `.owlbear/kanban/archive/`
- [ ] Config files (.cspell.json, .editorconfig, .mega-linter.yml, .vscode/settings.json) updated
- [ ] All existing tests pass
- [ ] Git commit with clear message
