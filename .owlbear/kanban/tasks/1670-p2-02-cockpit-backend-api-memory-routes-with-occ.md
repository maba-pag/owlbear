---
id: 1670
title: 'P2-02: Cockpit backend API — memory routes with OCC'
status: research
priority: needed
created: 2026-05-18T17:43:36.416614+02:00
updated: 2026-05-18T17:43:36.416614+02:00
tags:
  - phase-2
  - scope:cockpit
  - backend
parent: 1659
depends_on:
  - 1668
ac:
  - GET /api/memories returns 200 with MemoriesResponse containing entries list 
    (each matching MemoryEntryResponse schema with all model fields) and 
    parse_errors integer count
  - POST /api/memories/{id}/approve accepts {expected_updated_at} body, returns 
    200 with updated entry on success; returns 404 when id not found, 409 when 
    expected_updated_at mismatches, 422 when state transition invalid
  - POST /api/memories/{id}/edit accepts partial fields plus 
    expected_updated_at, returns 200 with updated entry; approved entries 
    transition to curated; same error codes as approve
  - POST /api/memories/{id}/delete accepts {expected_updated_at} body, returns 
    200 on success; pending entries hard-deleted, curated/approved soft-deleted;
    same error codes for not-found/conflict/invalid-transition
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1659 and `.owlbear/briefs/draft-cockpit-memory-tab/brief.md`

## Scope

Add memory management API routes to the cockpit backend using the extracted MemoryEngine.

### In Scope
- `routes/memory.py` with 4 endpoints: GET list, POST approve, POST edit, POST delete
- Pydantic request/response models: MemoriesResponse, MemoryEntryResponse, ApproveRequest, EditRequest, DeleteRequest
- DI: `Depends(get_memory_engine)` providing MemoryEngine instance
- Error mapping: NotFoundError→404, ConcurrencyError→409, ValidationError/TransitionError→422
- Follow existing cockpit error envelope pattern
- Config: `MEMORY_DIR` env var (default `.owlbear/memory/`)
- MtimeScanCache for engine caching (same pattern as kanban cache)

### Out of Scope
- Frontend components (P3-01, P3-02)
- SSE/live updates (deferred post-V1)
- Git auto-commit on mutations (brief decision D11)
- Memory creation endpoint (deferred)

## Technical Context
- Existing cockpit routes pattern: `serve/cockpit/src/owlbear_cockpit/routes/`
- Existing error envelope: see cockpit boundary tests
- DI pattern: `get_engine` from `owlbear_cockpit.main`