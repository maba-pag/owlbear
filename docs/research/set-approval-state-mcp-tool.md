# set_approval_state MCP Tool Design

> **Owning task:** #529 — Add set_approval_state MCP tool to memory-mcp
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #529 (from #528 curator-workflow research §3B, Option C) adds a 5th MCP tool to
memory-mcp for approval state transitions. DR #387 approved the full architecture.
#525 implemented the 4 base tools. This research validates the design, resolves
implementation details, and identifies AC gaps.

Key question: How should `set_approval_state` integrate with the existing tool set,
particularly `mark_for-deletion` which overlaps for the `→deleted` transition?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Curator workflow research | `docs/research/curator-workflow-memory-mcp.md` §3B, §3D, §3G | .95 |
| S2 | Existing tools.py | `packages/mcp-memory/src/owlbear_mcp_memory/tools.py` | .95 |
| S3 | MemoryEntry model | `packages/mcp-memory/src/owlbear_mcp_memory/models.py` | .90 |
| S4 | DR #387 (resolved) | `docs/decisions/resolved/387-memory-mcp-architecture.md` | 1.0 |
| S5 | MCP ToolAnnotations spec | `modelcontextprotocol.io/specification/2025-11-25` schema | .85 |
| S6 | MCP conventions | `.github/copilot-instructions.md` § MCP Server Conventions | .90 |

## 3. Analysis

### 3A. State Machine Design

AC specifies 3 valid transitions:

| From | To | Semantics |
|------|----|-----------|
| pending | approved | User confirms entry as permanent knowledge |
| pending | deleted | User rejects entry (soft-delete) |
| deleted | pending | User restores a false-positive deletion |

Invalid transitions (return soft error): approved→pending, approved→deleted,
deleted→approved, and same-state (e.g., pending→pending).

**Deliberate omissions:** `approved→deleted` is handled by `mark_for-deletion` (S2,
line 220+) which operates on any non-deleted entry. `approved→pending` is omitted
because approved entries are permanent knowledge — demoting them would undermine
user trust in the approval workflow. Future AC may add this if needed.

### 3B. Relationship to mark_for-deletion

| Concern | Resolution |
|---------|-----------|
| Overlap for →deleted | Intentional. Different audiences: `mark_for-deletion` is curator-accessible, `set_approval_state` is user-only (S1 §3D) |
| DRY violation | No — different permission models, different idempotency semantics. `mark_for-deletion` is idempotent (no-op on already-deleted). `set_approval_state` rejects invalid transitions |
| Deprecation | Not needed. Both tools serve distinct roles in the pipeline |

### 3C. ToolAnnotations

Per MCP spec (S5) and codebase conventions (S6):

| Hint | Value | Rationale |
|------|-------|-----------|
| readOnlyHint | False | Modifies approval_state |
| idempotentHint | False | Same-state calls error (not in valid transitions). Matches AC "not idempotent" |
| destructiveHint | True | One of 3 transitions (→deleted) is destructive. Safe default per MCP spec |
| openWorldHint | False | Closed domain (SQLite). MCP spec: "the world of a memory tool is not [open]" |

### 3D. Implementation Pattern (following S2)

- **Params:** `entry_id: str`, `new-state: str`
- **Validation:** Check entry exists (ToolError if not), validate `new-state` is valid
  literal, validate transition is in allowed set
- **Timestamps:** Set `updated_at` always. Set `deleted_at` when →deleted. Clear
  `deleted_at` (NULL) when deleted→pending
- **Return:** `str` — confirmation message on success, `error: ...` for invalid
  transition. ToolError for not-found (consistent with mark_for-deletion, S2)
- **SQL:** Parameterized queries, wrapped in `asyncio.to_thread` (S2 pattern)

### 3E. AC Gaps Identified

| Gap | Severity | Recommendation |
|-----|----------|---------------|
| `__all__` update in server.py | Low | Add to implementation; follows #525 pattern (S2) |
| Return type unspecified | Low | Return `str` per MCP conventions (S6) |
| TOCTOU on concurrent transitions | Low | SQLite WAL serializes writes. User-only tool has negligible concurrency risk |

## 4. Recommendation (.78 confidence)

Implement per AC with these clarifications: (a) soft error strings for invalid
transitions, ToolError for not-found; (b) timestamp handling for deleted_at on
both deletion and restoration; (c) str return type; (d) `__all__` update in
server.py. mark_for-deletion coexists — different audience, different semantics.

Challenge: reconsider — confidence in original: .60. Challenger raised: (1)
mark_for-deletion overlap (rebutted: intentional coexistence, different permission
models), (2) missing transitions (accepted: documented as deliberate omissions),
(3) ToolAnnotations contradictions (partially accepted: destructiveHint=True is
correct per MCP default, but noted the mixed nature), (4) __all__ gap (accepted:
added to implementation notes). Revised confidence from .85 to .78.

## 5. Follow-up Tasks

Task #529 is already the implementation task. No additional follow-up tasks needed.
The AC needs minor refinements (return type, __all__, timestamp handling) which
the architect will address at the backlog gate.
