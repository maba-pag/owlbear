---
id: 818
title: Extract engine to serve/kanban/ + workspace config
status: research
priority: critical
created: '2026-04-10T21:22:28.674120+00:00'
updated: '2026-04-10T21:22:28.674120+00:00'
tags:
- phase-2
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 817
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `serve/kanban/pyproject.toml` exists with deps: ruamel.yaml, pydantic (no MCP)
- Engine files moved to `serve/kanban/src/owlbear_kanban/`: engine.py, models.py, task_io.py, config_loader.py, activity_log.py, agent_names.py
- `__init__.py` exports: KanbanEngine, Task, TaskSummary, BoardConfig
- Root `pyproject.toml` updated: uv workspace members, coverage paths, ruff paths
- `uv sync` succeeds
- #817 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 2, step 2. Depends on #817 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`