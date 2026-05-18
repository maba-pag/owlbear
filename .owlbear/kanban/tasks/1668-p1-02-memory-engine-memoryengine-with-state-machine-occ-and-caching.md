---
id: 1668
title: 'P1-02: Memory engine — MemoryEngine with state machine, OCC, and caching'
status: research
priority: critical
created: 2026-05-18T17:43:08.887647+02:00
updated: 2026-05-18T17:43:08.887647+02:00
tags:
  - phase-1
  - scope:memory
  - backend
parent: 1659
depends_on:
  - 1667
ac:
  - MemoryEngine.approve(id, expected_updated_at) transitions curated→approved 
    (sets approved_at and updated_at), raises TransitionError for 
    pending/approved/deleted source states
  - MemoryEngine.edit(id, fields, expected_updated_at) transitions 
    pending→curated when scope_agents provided, approved→curated (clears 
    approved_at, sets updated_at); raises TransitionError when source state is 
    deleted
  - MemoryEngine.delete(id, expected_updated_at) hard-deletes pending entries 
    (file removed from disk), soft-deletes curated/approved (state set to 
    deleted, updated_at set); raises TransitionError when source state is 
    already deleted
  - All mutation methods raise ConcurrencyError when expected_updated_at does 
    not match the on-disk entry updated_at value
  - MtimeScanCache.has_changed() returns False when directory mtime_ns is 
    unchanged since last check, enabling get_entries() to skip full reparse
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Implement the MemoryEngine class in `serve/memory/` that orchestrates storage primitives with state machine enforcement, optimistic concurrency control, and mtime-based caching.

### In Scope
- MemoryEngine class: __init__(memory_dir), load(), get_entries(), get_entry(id), approve(), edit(), delete(), save()
- State machine enforcement per brief table (pending→curated via edit, curated→approved via approve, approved→curated via edit, pending→hard-delete, curated/approved→soft-delete)
- OCC: expected_updated_at parameter on all mutations
- MtimeScanCache: skip reparse when directory mtime unchanged
- Lenient read: skip unparseable files, report parse_errors count; handle duplicate UUIDs (keep later updated_at)
- Public API exports from `owlbear_memory.__init__`

### Out of Scope
- Models and storage primitives (P1-01, dependency)
- MCP tool wiring (P2-01)
- HTTP API (P2-02)

## Technical Context
- Existing MtimeScanCache pattern already in `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`
- State machine transitions defined in brief § Engine Package
- Duplicate UUID handling: keep entry with later `updated_at`, log warning

Complexity waiver: 5 AC lines — all tightly coupled to a single class (MemoryEngine) operating on one state machine. Split would fragment the state machine verification across tasks, making correctness harder to validate.