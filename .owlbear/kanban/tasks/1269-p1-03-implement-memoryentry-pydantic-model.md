---
id: 1269
title: 'P1-03: Implement MemoryEntry Pydantic model'
status: todo
priority: needed
created: 2026-05-02T03:43:31.714748+00:00
updated: 2026-05-02T03:45:18.109281+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1267
- 1268
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Implement the new MemoryEntry Pydantic model replacing the old SQLite-oriented schema. Must pass all tests from #1268.

Brief: see parent #1266

## Scope

**In scope:**
- Rewrite `serve/mcp-memory/src/owlbear_mcp_memory/models.py`
- 9-value category enum: knowledge, behaviour, pitfall, process, tool, goal, personality, preference, context
- 4-state enum: pending, curated, approved, deleted
- Confidence field with [0.7, 1.0] validator
- Required: id (UUIDv4), title (non-empty str), content (str), categories (list[Category], min 1), confidence, state, created_at, updated_at (ISO timestamps)
- Optional: scope_agents (list[str] | None)
- State defaults to "pending"

**Out of scope:**
- File I/O, slug generation, engine logic (handled by #1271)
- MCP tool integration (handled by #1273)
- pyproject.toml dep changes (if pyyaml needed, add in #1271)

## Acceptance Criteria

- [ ] All tests from #1268 pass GREEN
- [ ] MemoryEntry model validates confidence in [0.7, 1.0]
- [ ] Category enum has exactly 9 values
- [ ] State enum has exactly 4 values with "pending" default
- [ ] No SQLite references remain in models.py