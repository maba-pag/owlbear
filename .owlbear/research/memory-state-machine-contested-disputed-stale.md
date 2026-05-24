# State Machine — Contested, Disputed, Stale States

> **Owning task:** #1840 — P2-01: State machine — contested, disputed, stale states
> **Date:** 2026-05-24 **Status:** Complete

## 1. Context and Question

Task #1840 adds three lifecycle states (contested, disputed, stale) to MemoryState and defines their recall visibility and curator resolution transitions. Questions: (a) ordering in _state_rank_for_list, (b) recall filter extension, (c) resolve method design, (d) dual-package enum sync.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| serve/memory/src/owlbear_memory/engine.py | Codebase | 1.0 — existing state machine, transition pattern |
| serve/memory/src/owlbear_memory/models.py | Codebase | 1.0 — MemoryState enum definition |
| serve/mcp-memory/src/owlbear_mcp_memory/tools.py | Codebase | 1.0 — _state_rank_for_list + recall_memory filter |
| .owlbear/briefs/draft-memory-voting/brief.md | Project doc | 1.0 — authoritative brief for AC6 |
| Wikipedia content moderation model (flag-dispute-resolve) | Web/pattern | 0.8 — two-phase moderation prior art |
| KG fact-checking surveys (two-source confirmation) | Academic | 0.7 — independent confirmation requirement |
| .owlbear/research/memory-engine-state-machine-occ.md | Prior research | 0.9 — original state machine design (#1668) |

## 3. Analysis

### 3.1 Enum Extension

Trivial: add 3 members to MemoryState(StrEnum) in both serve/memory/ and serve/mcp-memory/ (identical copies). Values: contested, disputed, stale. No Pydantic model changes needed — state field already typed MemoryState.

### 3.2 State Rank Ordering

Current _state_rank_for_list (curator list view): PENDING=0, CURATED=1, APPROVED=2, other=3.

| State | Rank | Rationale |
|-------|------|-----------|
| CONTESTED | 1 | Same tier as CURATED — recall-visible, needs attention |
| DISPUTED | 3 | Excluded tier — same as DELETED |
| STALE | 3 | Excluded tier — same as DELETED |

### 3.3 Recall Visibility

Current recall filter: {APPROVED, CURATED}. Per AC:

| State | Recall visible? | Change |
|-------|----------------|--------|
| CONTESTED | Yes | Add to visible set |
| DISPUTED | No | Already excluded (not in visible set) |
| STALE | No | Already excluded (not in visible set) |

Implementation: change recall filter from entry.state in {APPROVED, CURATED} to entry.state in {APPROVED, CURATED, CONTESTED}. Add contested to the inline state_rank dict for sort order.

### 3.4 Resolve Method Design

| Criterion | Option A: Standalone resolve() | Option B: Extend edit() |
|-----------|-------------------------------|------------------------|
| Clarity | High — explicit curator action | Low — overloaded semantics |
| Pattern consistency | Matches approve() pattern | Deviates from existing method roles |
| Validation | Simple allowlist of source states | Complex conditional logic |
| OCC | Standard — matches other mutations | Standard |

Decision: Standalone resolve(entry_id, expected_updated_at) method on MemoryEngine.

Allowed transitions: {CONTESTED, DISPUTED, STALE} -> APPROVED. Raise TransitionError for all other source states (pending, approved, curated, deleted).

### 3.5 Impact on Existing Operations

| Operation | Impact |
|-----------|--------|
| edit() | Block from contested/disputed/stale — require resolution first |
| delete() | Allow soft-delete from new states (same as curated/approved) |

Conservative: block edit() from contested/disputed/stale to prevent edit-to-escape-dispute bypass.

## 4. Recommendation

Straightforward T1 implementation following existing patterns:
1. Extend enum (both packages)
2. Extend _state_rank_for_list (contested=1, disputed/stale=3)
3. Extend recall filter (add CONTESTED to visible set)
4. Add resolve() method (allowlist: contested/disputed/stale -> approved)
5. Block edit() on new states (conservative — resolve first)
6. Allow delete() on new states (soft-delete)

Confidence: 0.90 — well-scoped, follows existing patterns, no architectural risk.

Challenge: SKIP — T1 trivial extension with clear AC, no ambiguous trade-offs.

## 5. Follow-up Tasks

No decomposition needed — task #1840 is already atomic with clear AC. Advances to backlog.
