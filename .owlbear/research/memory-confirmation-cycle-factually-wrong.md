# Confirmation Cycle — Factually-Wrong to Contested/Disputed

> **Owning task:** #1845 — P2-06: Confirmation cycle — factually-wrong to contested/disputed
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

The memory voting system needs a two-step confirmation cycle to prevent single-agent nuclear blocks. When an agent marks a memory entry as "factually wrong," the entry should not be immediately excluded from recall. Instead, it requires independent confirmation from a different task before exclusion.

**Question:** What is the correct implementation pattern for `record_factually_wrong(entry_id, task_id, expected_updated_at)` within the existing engine, and how should the `contested_by_task` tracking field integrate with the dual-package model?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/memory/src/owlbear_memory/engine.py` (resolve, approve) | Codebase | 1.0 |
| 2 | `serve/memory/src/owlbear_memory/models.py` (MemoryEntry) | Codebase | 1.0 |
| 3 | `serve/memory/src/owlbear_memory/storage.py` (frontmatter) | Codebase | 0.9 |
| 4 | `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | Codebase | 0.9 |
| 5 | `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` (write) | Codebase | 0.9 |
| 6 | Wikipedia dispute resolution model | Web | 0.7 |
| 7 | Stack Overflow flag/disputed system | Web | 0.7 |
| 8 | M-of-N quorum authentication (APNIC) | Web | 0.5 |

## 3. Analysis

### Implementation Approach — Trade-off Matrix

| Criterion | A: Engine method (rec.) | B: Logic in assess_memories | C: Separate contest/dispute |
|-----------|------------------------|----------------------------|-----------------------------|
| Pattern consistency | Follows resolve()/approve() | Mixed concerns in tool | Over-split for 2-step flow |
| Testability | Isolated engine unit tests | Needs MCP context mocking | Same as A but more surface |
| KISS | Single method, clear FSM | Entangles counter updates | Two methods for one concept |
| Dependency fit | #1846 depends on #1845 cleanly | Circular: tool contains dep logic | Same as A |
| Confidence | **0.92** | 0.40 | 0.55 |

**Recommendation:** Option A — single `record_factually_wrong()` engine method.

### Field Placement

`contested_by_task: str | None = None` on both `MemoryEntry` models. Backward-compatible default. Added to frontmatter serialization in both packages (same pattern as existing counter fields).

### OCC Guard Design (AC4 discrepancy)

AC4 specifies: "raise **ConflictError**" — but existing engine uses `ConcurrencyError` for identical OCC semantics. Two options:

| Option | Pro | Con |
|--------|-----|-----|
| Reuse `ConcurrencyError` | KISS, existing pattern, no new error class | AC text says "ConflictError" |
| Add new `ConflictError` | Matches AC literally | Adds a type for identical semantics; confuses consumers |

**Recommendation:** Reuse `ConcurrencyError` — architect should confirm during AC refinement.

### Optional OCC (None = skip)

Unlike `approve()`/`resolve()`/`edit()` which require `expected_updated_at`, this method makes it optional. Implementation: `if expected_updated_at is not None: self._validate_occ(entry, expected_updated_at)`. Simple conditional before existing helper.

### Voteable State Guard

AC3 defines voteable as `{approved, curated, contested}`. Calling on `{pending, deleted, stale, disputed}` raises `TransitionError`. This matches the brief's AC2 voteable set.

### State Transitions

```
approved/curated + first factually_wrong → contested (contested_by_task = task_id)
contested + same task_id → no-op (return entry unchanged)
contested + different task_id → disputed (excluded from recall)
```

### Files Requiring Changes (6 files, 2 packages)

1. `serve/memory/src/owlbear_memory/models.py` — add `contested_by_task` field
2. `serve/memory/src/owlbear_memory/engine.py` — add `record_factually_wrong()` method
3. `serve/memory/src/owlbear_memory/storage.py` — add field to frontmatter dict
4. `serve/mcp-memory/src/owlbear_mcp_memory/models.py` — add `contested_by_task` field
5. `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` — add field to write dict
6. `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — add field to `_entry_to_dict`

## 4. Recommendation

T1 implementation following existing engine method patterns. No architectural risk. No new dependencies. Straightforward extension of state machine already implemented by #1840.

Confidence: **0.92**

Challenge: SKIP — prescriptive ACs, single valid approach, trivial extension of patterns proven in #1840/#1841.

### Open item for architect

AC4 says "ConflictError" — recommend architect refines to "ConcurrencyError" for consistency with existing OCC pattern, or explicitly adds a new error class if semantic distinction is intended.

## 5. Follow-up Tasks

No new follow-up tasks needed — decomposition in parent #1839 already complete. Task #1845 proceeds directly to architecture review.
