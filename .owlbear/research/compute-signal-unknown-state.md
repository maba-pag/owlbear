# computeSignal Unknown State Extension

> **Owning task:** #1599 — P1-06: Tests — computeSignal unknown state
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

The cockpit frontend's `computeSignal` function maps task data into one of 5 display-boundary signal states (`dr-pending | blocked | claimed | deps-unmet | ready`). When called with `null` or incomplete input (`{}`), it either throws a TypeError or silently returns `'ready'` — a false-positive availability signal. The brief (parent #1590) specifies extending `computeSignal` with an `'unknown'` state for malformed/missing inputs.

**Question:** What should the test surface look like for this extension, and are there AC inaccuracies to correct?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/web/src/utils/computeSignal.ts` | Codebase | 1.0 — current implementation (29 LOC) |
| 2 | `.owlbear/briefs/draft-cockpit-visual-redesign/brief.md` §Batch 1 AC | Brief | 0.9 — authoritative spec for unknown state |
| 3 | `serve/cockpit/web/src/__tests__/computeSignal.test.ts` | Codebase | 0.9 — existing 153-line test suite |
| 4 | `.owlbear/briefs/draft-cockpit-visual-redesign/stances/data.md` §Availability Signal | Brief | 0.8 — rationale for unknown state |

## 3. Analysis

### Current Runtime Behavior with Bad Inputs

| Input | Runtime result | Problem |
|-------|---------------|---------|
| `computeSignal(null, set)` | TypeError: `Cannot read properties of null (reading 'id')` | Crash |
| `computeSignal({} as any, set)` | `'ready'` | False positive — task appears available when data is missing |
| `computeSignal(undefined, set)` | TypeError | Crash |

### AC Corrections Applied

The planner-generated ACs had two inaccuracies:

| AC | Original (incorrect) | Corrected |
|----|---------------------|-----------|
| AC-1 | "return an **object** with state 'unknown'" | "return `'unknown'`" (string — matches existing return type) |
| AC-2 | "green/yellow/red/gray/stale" | "dr-pending, blocked, claimed, deps-unmet, ready" (actual state names) |

**Rationale:** The function returns strings, not objects. The brief confirms: `computeSignal(null)` and `computeSignal({})` return `"unknown"` state (string). The color names (green/yellow/red/gray/stale) don't appear anywhere in the codebase as signal state identifiers.

### Implementation Approach for Tests (RED Phase)

Tests should:

1. **Unknown state (new):** Assert `computeSignal(null as any, pendingDRIds)` returns `'unknown'`; assert `computeSignal({} as any, pendingDRIds)` returns `'unknown'`
2. **Regression (existing):** Re-confirm all 5 existing states still work — these tests already exist in `computeSignal.test.ts` (20+ cases), so the test-writer should add new describe blocks without modifying existing ones
3. **Signature change:** The function signature must widen to `task: SignalInput | null | undefined` for the null case to type-check without `as any`

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `CardSignal` consumers don't handle `'unknown'` | Medium | Card.tsx and CSS border-mapping need updates (task #1605 scope) |
| TypeScript strict mode rejects `null` argument | Low | Signature widening is part of impl task #1605 |

## 4. Recommendation

**Proceed (confidence: 0.90).** This is a straightforward defensive-coding extension.

- Tests add a new `describe` block for unknown-state inputs alongside existing suite
- No external dependencies, no architecture changes
- Challenge: skipped (trivial scope — single guard clause + type union extension)

## 5. Follow-up Tasks

No new follow-up tasks needed. Implementation task #1605 already exists as the paired GREEN phase task.
