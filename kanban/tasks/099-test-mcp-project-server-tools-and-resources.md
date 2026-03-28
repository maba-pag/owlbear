---
id: 99
title: 'Test: mcp-project server tools and resources'
status: ideation
priority: needed
created: 2026-03-28T04:04:45.3489882+01:00
updated: 2026-03-28T04:04:45.3489882+01:00
tags:
    - phase-1
    - scope:mcp
    - test
depends_on:
    - 68
class: standard
---

## Objective
TDD RED phase: write failing tests for mcp-project server tools and resources before builder implements.

## Test Scenarios
- [ ] project_info returns expected dict when owlbear-project.json exists
- [ ] project_info returns error string when owlbear-project.json missing
- [ ] project_list returns list of projects from registry dir
- [ ] project_list returns empty list when registry dir missing
- [ ] project://readme returns README.md content when present
- [ ] project://readme returns fallback message when README.md missing
- [ ] project://structure returns indented tree with correct depth limit (max 3)
- [ ] project://structure excludes .git, __pycache__, node_modules, .venv, .mypy_cache
- [ ] AppContext populated correctly from owlbear-project.json
- [ ] AppContext.project_file is None when owlbear-project.json missing
- [ ] app_lifespan reads OWLBEAR_ROOT env var with '..' fallback
- [ ] build_tree helper produces correct output for known directory structure
- [ ] build_tree respects max_depth parameter
- [ ] build_tree respects custom exclude set

## Context
Parent impl task: #17.
Test file: packages/mcp-project/tests/test_server.py (server tools/resources), packages/mcp-project/tests/test_tree.py (tree helper)
Depends on #68 (model must be implemented for imports)
Import: from owlbear_mcp_project.server import mcp (ImportError expected in RED)
Pattern: follow #89 (mcp-kanban test task) structure
