---
id: 1268
title: 'P1-02: Test — MemoryEntry model validation and state machine'
status: todo
priority: needed
created: 2026-05-02T03:43:27.840296+00:00
updated: 2026-05-02T03:45:18.099640+00:00
tags:
- phase-1
- scope:mcp-memory
- tests
parent: 1266
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Write failing tests that define the MemoryEntry Pydantic model contract: field types, validation constraints, state enum, category enum, confidence range, and required vs optional fields.

Brief: see parent #1266

## Scope

**In scope:**
- Test file: `tests/test_memory_models.py` (workspace root tests/)
- Validate 9-value category enum (multi-value list field)
- Validate 4-state enum: pending, curated, approved, deleted
- Validate confidence range [0.7, 1.0] — reject < 0.7 and > 1.0
- Validate required fields: id, title, content, categories, confidence, state, created_at, updated_at
- Validate optional fields: scope_agents (list or None)
- Validate title is non-empty string
- Validate categories is non-empty list

**Out of scope:**
- Engine file I/O (tested in #1270)
- Slug generation (tested in #1270)
- MCP tool behavior (tested in #1272)

## Acceptance Criteria

- [ ] Tests import `MemoryEntry` from `owlbear_mcp_memory.models`
- [ ] Tests FAIL (RED) — model does not yet implement new schema
- [ ] Confidence < 0.7 raises ValidationError
- [ ] Confidence > 1.0 raises ValidationError
- [ ] Invalid category value raises ValidationError
- [ ] Missing required field raises ValidationError
- [ ] Valid entry with all fields constructs successfully
- [ ] State field defaults to "pending" when omitted
- [ ] Categories accepts multi-value list from 9-value enum