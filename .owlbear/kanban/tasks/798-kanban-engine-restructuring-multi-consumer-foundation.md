---
id: 798
title: Kanban Engine Restructuring — Multi-Consumer Foundation
status: backlog
priority: needed
created: '2026-04-10T21:10:19.882817+00:00'
updated: '2026-04-10T21:10:19.882817+00:00'
tags:
- kanban
- architecture
- multi-phase
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Summary

Extract a standalone, transport-free kanban engine from the current MCP-kanban package. The engine owns the canonical task model, board configuration, dispatch policy, and all mutation operations. The MCP server becomes a thin adapter. The engine ships with GUI-ready data contracts (board metadata, valid transitions, write-revision tracking) so the future GUI project can plug in cleanly.

## Outcomes

| # | Outcome |
|---|---------|
| O1 | Standalone kanban engine package — importable without MCP dependency |
| O2 | Canonical engine model — `Task` + `TaskSummary`, no hand-built dicts |
| O3 | Dispatch gating in the engine — `pick_dispatchable()` extracted from server.py |
| O4 | MCP behavioral compatibility — all 8 tools behave identically |
| O5 | GUI-ready data contract — `board_config()`, `valid_transitions()`, revision counter |

## Phases

- **Phase 1:** Engine improvements (within current mcp-kanban). TaskSummary, board_config, refresh_config, valid_transitions, revision counter, actor field, validation, config fix, timestamp sort fix.
- **Phase 2:** Extract engine to `serve/kanban/` (`owlbear_kanban`). Slim MCP adapter. Boundary tests. Import migration.
- **Phase 3:** Extract dispatch to engine `dispatch.py`. Server pick_tasks becomes thin wrapper.

## Brief

Full brief at `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`