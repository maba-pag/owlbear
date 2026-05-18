---
id: 1669
title: 'P2-01: Rewire mcp-memory to import from owlbear-memory engine package'
status: research
priority: needed
created: 2026-05-18T17:43:21.686691+02:00
updated: 2026-05-18T17:43:21.686691+02:00
tags:
  - phase-2
  - scope:mcp-memory
  - backend
parent: 1659
depends_on:
  - 1668
ac:
  - serve/mcp-memory/pyproject.toml declares owlbear-memory as workspace 
    dependency; tools.py imports MemoryEngine, MemoryEntry, and error types from
    owlbear_memory (no engine/models/storage code remains in owlbear_mcp_memory)
  - All existing tests in serve/mcp-memory/tests/ pass without modification to 
    test logic (only import paths in shared fixtures may change)
  - serve/mcp-memory/ retains only server.py, tools.py, __main__.py, and git.py 
    as thin MCP adapters delegating to MemoryEngine methods
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Rewire the existing `serve/mcp-memory/` package to depend on the new `owlbear-memory` engine package instead of maintaining its own engine/models.

### In Scope
- Add `owlbear-memory` workspace dependency to `serve/mcp-memory/pyproject.toml`
- Replace imports in `tools.py` to use `owlbear_memory.MemoryEngine`, `owlbear_memory.MemoryEntry`, etc.
- Remove `engine.py` and `models.py` from `serve/mcp-memory/src/owlbear_mcp_memory/`
- Update any shared test fixtures with new import paths
- Verify existing test suite passes

### Out of Scope
- Changing MCP tool behavior or signatures
- Adding new MCP tools
- Cockpit API (P2-02)

## Downstream Impact
- Existing tests in `serve/mcp-memory/tests/` cover the MCP tool surface
- No external consumers import from `owlbear_mcp_memory.engine` or `owlbear_mcp_memory.models` directly

Existing proof scope: serve/mcp-memory/tests/