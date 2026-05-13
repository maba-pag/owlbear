---
id: 1519
title: 'P3-01: Tests for MCP server ac/proof_bundle tool parameters'
status: backlog
priority: needed
created: 2026-05-13T02:29:38.031602+00:00
updated: 2026-05-13T02:30:18.981520+00:00
tags:
  - phase-3
  - scope:mcp-kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1518
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Unit tests for MCP create_task, edit_task tool parameter passthrough; show_task response fields
Out of scope: Engine internals, migration, skill files

## Acceptance Criteria
- AC1: MCP `create_task` tool accepts `ac: list[str]` and `proof_bundle: str` params and passes them to engine `create_task()`
- AC2: MCP `edit_task` tool accepts `ac`, `add_ac`, `remove_ac`, and `proof_bundle` params and maps them to engine `edit_task()` kwargs
- AC3: MCP `show_task` response includes `ac` and `proof_bundle` fields from `TaskFull` model

Proof bundle: behavioral