# Recall — Reserved Explore and Challenge Slots

> **Owning task:** #1843 — P2-04: Recall — reserved explore and challenge slots
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1843 replaces the flat top-N recall sort `(state_rank, -confidence, id)` with score-based sorting `(state_rank, -score, id)` and adds reserved explore/challenge slot allocation. Questions: (a) is a multi-pool selection approach sound for this use case, (b) what are the edge cases around dedup and bootstrap, (c) where should constants live.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` (recall_memory) | Codebase | 1.0 — current implementation |
| `serve/memory/src/owlbear_memory/engine.py` (compute_score, constants) | Codebase | 1.0 — scoring available from #1841 |
| `serve/mcp-memory/src/owlbear_mcp_memory/models.py` (MemoryEntry) | Codebase | 1.0 — field availability confirmed |
| `.owlbear/briefs/draft-memory-voting/brief.md` | Project doc | 1.0 — authoritative design spec |
| Milvus — exploration vs exploitation in recommendations | Prior art | 0.8 — epsilon-greedy slot allocation |
| Shaped.ai — Explore vs Exploit in recommendation systems | Prior art | 0.8 — fixed exploration percentage design |
| Leitner system (spaced repetition) | Prior art | 0.7 — low-review-count items get priority |
| Multi-armed bandit epsilon-greedy algorithms (various) | Prior art | 0.7 — reserved random/exploration fraction |

## 3. Analysis

### 3.1 Algorithm Design — Three-Pool Selection

The design uses fixed-count reserved slots rather than probabilistic epsilon-greedy. Comparison:

| Approach | Mechanism | Pro | Con |
|----------|-----------|-----|-----|
| Fixed slots (proposed) | 2 explore + 2 challenge = 4 of 20 reserved | Deterministic, testable, simple | Can't adapt allocation ratio |
| Epsilon-greedy | 20% random selection | Adapts to pool size | Non-deterministic, hard to test |
| UCB1 (bandit) | Confidence-bounded exploration | Optimal convergence | Complex, overkill for <1000 entries |
| MMR (diversification) | λ-weighted relevance vs diversity | Rich trade-off control | Requires similarity metric |

**Verdict:** Fixed slots is the right choice — KISS-aligned, deterministic (testable), and sufficient for the entry counts involved (~20–200 entries typical).

### 3.2 Pool Selection Order and Dedup

AC2 specifies dedup priority: explore > challenge > regular. This determines selection order:

1. **Explore** (SLOT_EXPLORE=2): lowest `outstanding_count + unremarkable_count + didnt_use_count`, tiebreak `id ASC`
2. **Challenge** (SLOT_CHALLENGE=2): from remaining, lowest `outstanding_count`, tiebreak `id ASC`
3. **Regular** (limit - 4): from remaining, `(state_rank, -score, id)`, take top N

This three-pass approach is O(n log n) for each sort. With typical pool sizes (<200), performance is negligible.

### 3.3 Edge Cases

| Scenario | Behavior | AC reference |
|----------|----------|--------------|
| entries < limit | Return all, sorted by final sort key | AC2 |
| entries = 0 | Return empty string (existing behavior) | Implicit |
| All counters = 0 (bootstrap) | Explore picks lowest id; challenge picks lowest id from remaining | AC4 |
| Entry qualifies for explore AND challenge | Occupies explore only (dedup) | AC2 |
| limit < 4 (e.g., limit=2) | Regular pool = max(0, limit-4) = 0; only explore fills | Arithmetic edge |

The `limit < 4` edge needs handling: `regular_count = max(0, capped_limit - SLOT_EXPLORE - SLOT_CHALLENGE)`. Explore and challenge should also be capped at available remaining entries.

### 3.4 Constant Placement

| Location | Pro | Con |
|----------|-----|-----|
| `serve/mcp-memory/src/.../tools.py` | Near consumer; recall is only user | Not importable for tests w/o importing tools |
| `serve/memory/src/.../engine.py` | Alongside OUTSTANDING_BOOST etc | Slot allocation is presentation concern, not model |

**Recommendation:** Place in `tools.py` (module-level). The constants define MCP tool behavior, not core model semantics. Test imports from tools module directly — consistent with how tests already import `recall_memory`.

## 4. Recommendation

**T1 — Autonomous implementation.** (Confidence: 0.92)

Implementation is a ~30-line modification to `recall_memory` in `tools.py`: replace the flat sort+slice with three-pool selection, add two module-level constants, and change the sort key from `-entry.confidence` to `-entry.score`.

Challenge: SKIP — prescriptive ACs, trivial algorithm, no design alternatives, single implementation path.

No new follow-up tasks needed — decomposition in #1839 is complete and task scope is fully defined.

## 5. Implementation Approach

1. Add `SLOT_EXPLORE = 2` and `SLOT_CHALLENGE = 2` constants at module level in `tools.py`
2. In `recall_memory`, after existing state/scope/category filtering:
   - If `len(entries) <= capped_limit`: sort by `(state_rank, -score, id)`, return all
   - Else: three-pool selection (explore → challenge → regular), merge, final sort by `(state_rank, -score, id)`
3. Replace sort key `-entry.confidence` with `-entry.score` in all paths
4. Handle `limit < 4` gracefully (cap explore/challenge to available budget)
