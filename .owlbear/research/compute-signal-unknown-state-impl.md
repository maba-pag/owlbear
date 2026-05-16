# computeSignal Unknown State — Implementation Research

> **Owning task:** #1605 — P1-07: Extend computeSignal with unknown state
> **Date:** 2026-05-16 **Status:** Complete (superseded)

## 1. Context and Question

Task #1605 was decomposed as the GREEN-phase implementation pair for #1599 (RED-phase tests). The question is whether any implementation work remains.

**Answer: No.** The builder on #1599 already implemented the full change (commit `a6e26299`), including the `CardSignal` type extension and guard clause. All 23 tests pass.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/utils/computeSignal.ts` | Codebase | 1.0 — current impl, already has `'unknown'` in union + guard clause |
| 2 | `serve/cockpit/web/src/__tests__/computeSignal.test.ts` | Codebase | 1.0 — 23/23 tests passing including 6 unknown-state tests |
| 3 | Task #1599 body (builder notes) | Kanban | 0.9 — confirms impl commit `a6e26299` and GREEN verification |
| 4 | `.owlbear/research/compute-signal-unknown-state.md` | Research | 0.8 — prior research for #1599, identifies same AC wording issues |

## 3. Analysis

### AC Verification Against Current Code

| AC (as written) | Correction needed | Current state | Status |
|-----------------|------------------|---------------|--------|
| AC-1: `computeSignal(null)` and `computeSignal({})` return an object with state `'unknown'` | Returns string `'unknown'`, not object (same correction applied in #1599) | Guard at L11-13: `if (!task \|\| typeof task.id !== 'number') return 'unknown'` | DONE |
| AC-2: Existing 5-state behavior unchanged for valid inputs (green/yellow/red/gray/stale) | Actual states: dr-pending/blocked/claimed/deps-unmet/ready (same correction applied in #1599) | 17 original tests pass unchanged | DONE |

### Implementation Already Present

```typescript
// computeSignal.ts — lines 1, 11-13 (commit a6e26299)
export type CardSignal = '...' | 'unknown'
// ...
if (!task || typeof task.id !== 'number') {
  return 'unknown'
}
```

### Remaining Gaps (Out of Scope for #1605)

| Gap | Scope owner |
|-----|-------------|
| Card.tsx doesn't render a visual cue for `'unknown'` signal | Future task (if `unknown` becomes user-visible) |
| No `[data-signal="unknown"]` CSS selector | Same — cosmetic, not functional |

Both gaps were noted in #1599's review observations and are explicitly out of scope per #1605's task body ("computeSignal extension only").

## 4. Recommendation

**Archive #1605 as superseded by #1599** (confidence: 0.95).

The OwlBear TDD pipeline executed the GREEN phase within #1599's builder step, which is the standard lifecycle: test-writer writes failing tests → builder makes them pass → reviewer verifies. Task #1605 was created as a separate decomposition unit for the impl work, but that work was completed atomically within #1599.

Challenge: skipped (no recommendation to challenge — factual finding that work is already done).

## 5. Follow-up Tasks

None. No remaining implementation work. The noted display-layer gaps (Card.tsx, CSS) are out of scope and would be addressed if/when `unknown` signals need visual rendering.
