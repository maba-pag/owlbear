---
id: 803
title: Tests — refresh_config + config staleness fix
status: research
priority: needed
created: '2026-04-10T21:20:57.293478+00:00'
updated: '2026-04-10T21:20:57.293478+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `refresh_config()` reloads YAML from disk
- Tests verify `refresh_config()` updates `_config`, tasks_dir, archive_dir, and rank maps
- Tests verify `create_task` uses fresh config (staleness scenario: modify config on disk → create → new config reflected)
- Tests verify `refresh_config()` after external config change → `move_task` validates against new statuses
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`