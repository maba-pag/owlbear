---
id: 1273
title: 'P1-07: Implement MCP tool layer with access control'
status: todo
priority: needed
created: 2026-05-02T03:43:38.542522+00:00
updated: 2026-05-02T03:45:18.130387+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1272
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Implement the 5 MCP tools with access control, state transition enforcement, and query logic. Must pass all tests from #1272.

Brief: see parent #1266

## Scope

**In scope:**
- Rewrite `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — 5 tool functions
- `store_learning(title, content, categories, confidence, scope_agents?)` → creates pending entry via engine
- `query_memory(categories?, scope_agents?, min_confidence?, limit?)` → filtered retrieval, default curated+approved, sorted approved-first then confidence desc
- `update_entry(entry_id, content?, categories?, confidence?, promote?)` → curator-only edits, pending→curated promotion
- `delete_entry(entry_id)` → curator-only, sets state=deleted
- `approve_entry(entry_id)` → user-only, curated→approved promotion
- State transition enforcement: reject invalid transitions with clear error messages
- `allowed_agents` config: tool-level restriction mechanism (curator tools reject non-curator callers)
- Wire tools into MCP server (`server.py` or equivalent registration)
- Update `__main__.py` to start the new server

**Out of scope:**
- Engine changes (completed in #1271)
- Model changes (completed in #1269)
- Skill documentation (handled by #1274)

## Acceptance Criteria

- [ ] All tests from #1272 pass GREEN
- [ ] 5 tools registered and callable via MCP
- [ ] store_learning creates entries with state=pending
- [ ] query_memory default excludes pending/deleted, sorts correctly
- [ ] update_entry enforces curator-only access
- [ ] delete_entry enforces curator-only access
- [ ] approve_entry enforces curated→approved only (rejects other states)
- [ ] Invalid state transitions produce ToolError with descriptive message
- [ ] Server starts via `uv run` entry point