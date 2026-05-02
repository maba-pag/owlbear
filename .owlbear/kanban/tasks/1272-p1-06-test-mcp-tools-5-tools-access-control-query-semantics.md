---
id: 1272
title: 'P1-06: Test — MCP tools (5 tools, access control, query semantics)'
status: todo
priority: needed
created: 2026-05-02T03:43:35.329682+00:00
updated: 2026-05-02T03:45:18.128140+00:00
tags:
- phase-1
- scope:mcp-memory
- tests
parent: 1266
depends_on:
- 1271
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Write failing tests for all 5 MCP tools: store_learning, query_memory, update_entry, delete_entry, approve_entry. Cover access control, state transitions, query filtering, and sort order.

Brief: see parent #1266

## Scope

**In scope:**
- Test file: `tests/test_memory_tools.py` (workspace root tests/)
- `store_learning`: any agent can create pending entry; validates required fields; rejects confidence < 0.7
- `query_memory`: returns curated+approved by default; supports category filter, scope_agents filter, min_confidence filter; sort: approved first → curated, then confidence desc; excludes pending and deleted from default
- `update_entry`: curator-only; can edit content, categories, confidence; can promote pending→curated; rejects non-curator agent
- `delete_entry`: curator-only; sets state=deleted; rejects non-curator
- `approve_entry`: user-only (via curator); promotes curated→approved; rejects if not in curated state
- State transition enforcement: cannot skip states (pending→approved invalid), cannot promote deleted entries
- `allowed_agents` config mechanism tested

**Out of scope:**
- Engine internals (tested in #1270)
- Model validation (tested in #1268)
- Actual MCP server transport (unit-test the tool functions directly)

## Acceptance Criteria

- [ ] Tests FAIL (RED) — tool module does not yet implement new API
- [ ] store_learning creates pending entry with valid inputs
- [ ] query_memory returns correct default sort order (approved first, then confidence desc)
- [ ] query_memory excludes pending entries by default
- [ ] update_entry rejects non-curator caller
- [ ] update_entry promotes pending→curated
- [ ] delete_entry marks entry as deleted state
- [ ] approve_entry promotes curated→approved
- [ ] approve_entry rejects if entry not in curated state
- [ ] Invalid state transitions raise appropriate errors