---
id: 525
title: Implement memory-mcp tools
status: in-progress
priority: needed
created: 2026-04-01T16:11:21.612432+02:00
updated: 2026-04-03T01:48:25.5740675+02:00
started: 2026-04-02T07:38:31.230978+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 524
    - 556
class: standard
---

## Acceptance Criteria

### get_knowledge
- [ ] Params: agent_id (str, required), categories (str | None), min_confidence (float | None), limit (int, default 50)
- [ ] Returns list[dict] of entries where approval_state != 'deleted', matching union of 4 scope tiers: (agent+project, agent-only, project-only, general)
- [ ] WHERE clause: (scope_agent = :agent OR scope_agent IS NULL) AND (scope_project = :project OR scope_project IS NULL) AND approval_state != 'deleted'
- [ ] Sorted by: scope-specificity (SQL CASE WHEN 4-tier), then approval_state (approved before pending), then confidence DESC
- [ ] ToolAnnotations: readOnlyHint=True, idempotentHint=True, destructiveHint=False

### record_learning
- [ ] Params: content (str), category (str), confidence (float), agent_id (str), scope_project (str | None, defaults to AppContext.project_name), scope_agent (str | None)
- [ ] Soft error "error: confidence must be >= 0.7, got {value}" if confidence < 0.7
- [ ] Soft error "error: invalid category '{value}'. Valid: preference, knowledge, context, behavior, goal" for invalid category
- [ ] Generates uuid4 id, sets created_at/updated_at to datetime.now(UTC).isoformat(), source=agent_id, approval_state='pending'
- [ ] Returns bare UUID string on success
- [ ] ToolAnnotations: readOnlyHint=False, idempotentHint=False, destructiveHint=False

### list_entries
- [ ] Params: agent_id (str | None), category (str | None), status (str | None), include_deleted (bool, default False)
- [ ] Returns list[dict] filtered by provided params; excludes deleted entries unless include_deleted=True
- [ ] ToolAnnotations: readOnlyHint=True, idempotentHint=True, destructiveHint=False

### mark_for_deletion
- [ ] Params: entry_id (str)
- [ ] If entry already deleted (approval_state='deleted'), return success without updating (true idempotent)
- [ ] Otherwise sets approval_state='deleted', deleted_at and updated_at to UTC ISO timestamp
- [ ] Raises ToolError if entry_id not found in table
- [ ] ToolAnnotations: readOnlyHint=False, idempotentHint=True, destructiveHint=True

### Cross-cutting
- [ ] sqlite3.connect() uses check_same_thread=False (required for asyncio.to_thread from non-creating thread)
- [ ] All SQLite calls wrapped in asyncio.to_thread (per mcp-knowledge pattern)
- [ ] All SQL queries use parameterized queries (no string interpolation)
- [ ] _apply_tool_exclusions function added, reads MEMORY_TOOLS_EXCLUDE env var (per mcp-kanban/mcp-knowledge pattern), called at module level after tool registration
- [ ] __all__ in server.py updated to include all 4 tool functions + _apply_tool_exclusions
- [ ] Project identity already resolved in AppContext from scaffold (#524), use ctx.request_context.lifespan_context.project_name

### Deliberate omissions (per DR #387 Option A)
- content_hash / dedup not included (flagged in design doc 3K for future consideration)
- Database indexing deferred: low-volume table at initial scale

[[2026-04-02]] Thu 16:35
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true; docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| get_knowledge sort | Missing approval_state ordering per design doc 3F | Refined: added approved-before-pending tier |
| record_learning scope_project | Could inject into other projects | Refined: defaults to AppContext.project_name |
| mark_for_deletion idempotency | Annotation says idempotent but re-timestamps | Refined: skip if already deleted (true idempotent) |
| check_same_thread | Missing from scaffold, fatal with asyncio.to_thread | Added to cross-cutting AC |
| limit default | No default means unbounded token injection | Refined: default 50 |
| All other AC lines | Clear, verifiable, matches design doc 3E | Kept with minor formatting |

### Architecture Notes
Follows established MCP server patterns from mcp-kanban and mcp-knowledge. Scaffold (#524, done) provides AppContext with sqlite3.Connection, project_name, DDL, and WAL pragmas. MemoryEntry Pydantic model in models.py has all needed fields including category Literal type. Package boundary: owlbear_mcp_memory has no cross-package imports (ALLOWED_IMPORTS = set()). Deliberate omission of content_hash/dedup per DR #387 Option A. Indexing deferred per YAGNI (low-volume table).

### Changes Made
- Rewrote AC body with per-tool param/return specs, error messages, ToolAnnotations
- Added check_same_thread=False, asyncio.to_thread, parameterized queries, _apply_tool_exclusions to cross-cutting AC
- Added approval_state to get_knowledge sort order (approved before pending per design doc 3F)
- Added scope_project default to AppContext.project_name for record_learning
- Specified mark_for_deletion as truly idempotent (skip if already deleted)
- Added limit default 50 for get_knowledge
- Created test task #556 (Test: Implement memory-mcp tools)
- Added depends_on: [524, 556] to ensure TDD compliance

### Dependencies
- Verified: #524 (Scaffold mcp-memory package) at done status
- Verified: DR #387 (approved: true), DR #428 (approved: true)
- Added: #556 (test task, TDD RED phase)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .62
- Key challenges: C1 (check_same_thread=False fatal), C2 (approval_state sort missing), C5 (scope injection)
- Architect response: accepted C1 (added to AC), accepted C2 (added approval_state ordering), partially accepted C5 (added scope_project default, unrestricted scoping intentional per design doc 3I for curator cross-pollination). Deferred C3 (env var fallback, minor), C4 (acknowledged deliberate omission). Revised AC confidence: .88
