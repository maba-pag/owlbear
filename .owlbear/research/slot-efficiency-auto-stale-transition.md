# Slot-Efficiency — Auto-Stale Transition

> **Owning task:** #1844 — P2-05: Slot-efficiency — auto-stale transition
> **Date:** 2026-05-25 **Status:** Complete

## 1. Context and Question

Task #1844 implements a predicate function `check_slot_efficiency` and a transition method that auto-moves entries to `stale` when `didnt_use` assessments dominate. The formula: `didnt_use_count > STALE_THRESHOLD × max(outstanding_count + unremarkable_count, 1)` — i.e., an entry must be unused 50× more than its active assessments before demotion.

Questions: (a) function placement and signature design, (b) transition method pattern (idempotent vs. error-raising), (c) integration point for callers (#1846 assess_memories), (d) boundary behavior at threshold.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/memory/src/owlbear_memory/engine.py` | Codebase | 1.0 — existing transition patterns (approve, resolve, delete) |
| `serve/memory/src/owlbear_memory/models.py` | Codebase | 1.0 — MemoryEntry, MemoryState enum |
| `.owlbear/research/memory-state-machine-contested-disputed-stale.md` | Prior research | 0.9 — state machine design for #1840 |
| `.owlbear/briefs/draft-memory-voting/brief.md` | Project doc | 1.0 — authoritative brief, AC4 slot-efficiency spec |
| Wikipedia: Cache replacement policies (LFU, SIEVE) | Web | 0.7 — ratio-based eviction precedent |
| Redis LFU eviction (frequency counter with decay) | Web | 0.6 — frequency-proportional demotion pattern |
| Exchange Online Auto-Archive (threshold-based archiving) | Web | 0.5 — threshold-triggers-move pattern |

## 3. Analysis

### 3.1 Formula Semantics

The formula `didnt_use > 50 × max(outstanding + unremarkable, 1)` creates a proportional threshold:

| outstanding + unremarkable | Stale when didnt_use > |
|---------------------------|----------------------|
| 0 | 50 (50 × 1) |
| 1 | 50 (50 × 1) |
| 2 | 100 (50 × 2) |
| 5 | 250 (50 × 5) |
| 10 | 500 (50 × 10) |

This matches LFU-style "proven engagement extends runway" — entries with any positive signal get proportionally more chances. The `max(..., 1)` floor prevents division-by-zero semantics and ensures zero-engagement entries still need 51 assessments before staling.

### 3.2 Function Placement

| Option | Placement | Pro | Con |
|--------|-----------|-----|-----|
| A | Module-level function (like `compute_score`) | Pure, testable, no engine coupling | Caller must combine with transition |
| B | MemoryEngine method only | Encapsulated | Can't unit-test predicate without engine |

**Decision: Option A.** AC1 explicitly specifies `check_slot_efficiency(entry: MemoryEntry) -> bool` as a standalone function. Place alongside `compute_score` at module level in `engine.py`.

### 3.3 Transition Method Design

| Criterion | Option A: Error-raising (like approve/resolve) | Option B: Idempotent/silent (AC-specified) |
|-----------|-----------------------------------------------|-------------------------------------------|
| AC compliance | Violates AC2: "no error raised" for invalid states | Matches AC2+AC3 exactly |
| Composability | Caller must pre-check state | Fire-and-forget from assess_memories loop |
| Engine consistency | Matches approve/resolve pattern | Differs — but AC is authoritative |
| Safety | Explicit failure visible | Silent no-op on wrong state (intended) |

**Decision: Option B.** The AC explicitly requires "entries already in stale, disputed, deleted, or pending state are unaffected (no error raised)" — idempotent/silent return.

### 3.4 Method Signature & OCC

The AC describes: a method takes an entry, checks the predicate, transitions if allowed, returns updated or unchanged.

Key design choice: Does the transition method require OCC (expected_updated_at)?

| With OCC | Without OCC |
|----------|-------------|
| Consistent with approve/resolve/edit | Simpler call site from assess_memories |
| Prevents races on concurrent assess | assess_memories already has OCC on counter update |
| Requires caller to pass timestamp | Can operate on in-memory entry directly |

**Decision: Without OCC.** The transition is called *after* counters are already updated (within the same assess_memories flow). The entry object passed in is already fresh from the preceding write. Adding OCC here adds complexity without safety benefit since the upstream mutation holds the concurrency guard.

Proposed signature: `MemoryEngine.try_stale_transition(entry: MemoryEntry) -> MemoryEntry`

### 3.5 Integration with #1846 (assess_memories)

The natural call site: after each `didnt_use` bucket assessment in `assess_memories`, call `try_stale_transition(updated_entry)`. Only `didnt_use` assessments can trigger staleness (outstanding/unremarkable don't increase `didnt_use_count`), so the check could be narrowed to that bucket — but running it unconditionally is simpler and harmless.

## 4. Recommendation

Implement as two artifacts in `serve/memory/src/owlbear_memory/engine.py`:

1. **`check_slot_efficiency(entry: MemoryEntry) -> bool`** — pure predicate, module-level
2. **`MemoryEngine.try_stale_transition(entry: MemoryEntry) -> MemoryEntry`** — idempotent engine method that calls predicate, guards on state, writes if transition valid

Export `check_slot_efficiency` from `__init__.py` for direct test access.

Confidence: **0.90** — AC is highly specific; minimal design latitude. Only uncertainty: method naming and whether to export predicate separately (recommended for testability).

Challenge: proceed — confidence in original: 0.90. No challenger invocation needed for T1/implementation-obvious tasks with explicit AC.

## 5. Follow-up Tasks

Task is ready for test-writing and implementation. Dependencies #1840 (state machine) and #1841 (model fields) must land first — both provide the STALE state, counters, and STALE_THRESHOLD constant that this task consumes. No additional research tasks needed; proceed to architecture/TDD.
