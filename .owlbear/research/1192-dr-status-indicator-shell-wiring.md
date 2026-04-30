# DR Status Indicator Shell Integration

> **Owning task:** #1192 — P3-04: Implement DR status indicator + popover
> **Date:** 2026-04-30 **Status:** Complete

## 1. Context and Question

Task #1192 requires `DRStatusIndicator` to render in Shell's status bar alongside
`HealthBadge`, connected to `usePendingDRs`. The component and hook already exist
with 49/49 tests passing from #1191. The question: what integration work remains?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/cockpit/web/src/Shell.tsx` — current Shell layout | 1.00 |
| `serve/cockpit/web/src/components/DRStatusIndicator.tsx` — built component | 1.00 |
| `serve/cockpit/web/src/hooks/usePendingDRs.ts` — built hook | 1.00 |
| `serve/cockpit/web/src/__tests__/Shell_1162.test.tsx` — HealthBadge wiring precedent | 0.95 |
| `serve/cockpit/web/src/components/HealthBadge.tsx` — analogous pattern | 0.90 |
| `serve/cockpit/web/src/components/ResolveModal.tsx` — downstream consumer | 0.75 |

## 3. Analysis

### 3.1 Current State

| Artifact | Status |
|----------|--------|
| `DRStatusIndicator.tsx` | ✅ Built, tested (24 tests) |
| `usePendingDRs.ts` | ✅ Built, tested (25 tests) |
| Shell integration | ❌ Not wired — Shell does not import either |
| `onItemClick` → modal | ❌ Shell has no state/handler for DR selection |

### 3.2 Implementation Approach — Shell Wiring

Follow the exact HealthBadge precedent from `Shell_1162.test.tsx`:

1. Import `usePendingDRs` hook and `DRStatusIndicator` component
2. Call `usePendingDRs()` in Shell (default 60s interval)
3. Render `<DRStatusIndicator count={…} items={…} onItemClick={…} />` in
   `header.shell__status-bar` alongside HealthBadge
4. Add `selectedDRId` state in Shell; `onItemClick` sets it
5. ResolveModal rendering deferred to #1194 (AC: OUT scope)

### 3.3 onItemClick Wiring Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Shell holds `selectedDRId` state, passes setter as `onItemClick` | Simple, #1194 just conditionally renders ResolveModal | Shell grows slightly |
| B | Custom event dispatch (`dispatchEvent`) | Decoupled | Over-engineered for 1 consumer |
| C | Emit via React context/state manager | Scalable | YAGNI, adds complexity |

**Recommendation:** Option A (confidence: 0.92). Same pattern as HealthBadge's
`isOpen` toggle. #1194 can later render `<ResolveModal dr={…} />` gated on
`selectedDRId !== null`. Minimal diff, proven pattern.

Challenge: N/A — trivial wiring, no architectural trade-off to challenge.

## 4. Recommendation

This is purely a **wiring task** (~15 LOC Shell change). All components/hooks are
built and tested. Implementation follows the HealthBadge integration precedent
exactly. Confidence: **0.92**.

No blockers. No decisions needed. T1 (autonomous).

## 5. Follow-up Tasks

None required — the task itself is the implementation. Ready for backlog → todo.
