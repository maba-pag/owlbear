---
id: 1181
title: 'P1-02: Implement decisions.py module'
status: research
priority: critical
created: 2026-04-30T00:51:35.539925+00:00
updated: 2026-04-30T00:52:52.489360+00:00
tags:
- phase-1
- scope:kanban
- type:impl
parent: 1179
depends_on:
- 1180
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `decisions.py` module exists at `serve/kanban/src/owlbear_kanban/decisions.py`
- `create_dr(task_id, agent, request_type, body) → Path` function implemented per brief spec
- `resolve_pending_drs(engine) → list[ResolvedDR]` function implemented per brief spec
- File format: simplified 5-field frontmatter (task_id, agent, request_type, created, response)
- Slug generation from first ~40 chars of body
- Atomic file creation via `open(path, 'x')`
- Rollback: file deleted if engine.block_task fails
- Resolve logic: append body summary, conditional unblock, move to resolved/
- Per-file error isolation in resolve loop (never stalls caller)
- Unknown response values: log warning, skip
- All tests from #1180 pass

## Scope

- IN: `decisions.py` module only
- OUT: MCP tool registration, pick_tasks caller, guidance text

Brief: see parent #1179
