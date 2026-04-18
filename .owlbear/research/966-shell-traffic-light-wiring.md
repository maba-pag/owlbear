# Shell Traffic-Light State Wiring Architecture

> **Owning task:** #966 — Architecture: lift useBoard state for Shell traffic-light wiring
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Shell.tsx has a `<span data-testid="traffic-light" />` in its status bar. The poll health state (green/yellow/red) originates from `usePolling` — a 3s interval hook that tracks connection health via fetch response status and elapsed time. `useBoard()` lives inside KanbanBoard (a child route). The question: how should Shell access poll health?

The task body lists three options: lift hook to Shell, create BoardProvider context, or use React Router outlet context. Research identified a fourth, simpler option.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | Codebase: `Shell.tsx` — traffic-light span at L27 | 1.0 |
| 2 | Codebase: `KanbanBoard.tsx` — useBoard() at L43-95 | 1.0 |
| 3 | Codebase: `usePolling.ts` — health hook, not wired in | 1.0 |
| 4 | Codebase: `Shell.test.tsx` — 19 tests, fetch stub pattern | 1.0 |
| 5 | React docs: Passing Data Deeply with Context | 0.8 |
| 6 | Codebase: `App.tsx` — BrowserRouter → Shell routing | 0.9 |
| 7 | Prior research: `.owlbear/research/960-tanstack-query-vs-plain-polling.md` | 0.9 |

## 3. Analysis

### 3.1 Option Comparison

| Criterion | Direct usePolling in Shell (rec) | React Context (BoardProvider) | Outlet Context |
|-----------|--------------------------------|-------------------------------|----------------|
| **New files** | 0 | 1 (~60-80 LoC) | 0 (but restructure) |
| **Shell.tsx changes** | ~5 LoC (import + call + bind) | ~3 LoC (consume context) | ~3 LoC (consume context) |
| **KanbanBoard changes** | 0 | Remove useBoard, consume context | useOutletContext() |
| **Routing changes** | 0 | 0 | Restructure Shell → layout route |
| **Existing test impact** | 0 tests changed | ~50+ tests need provider wrapper | ~50+ tests need routing change |
| **New test scope** | ~5 tests (Shell traffic-light) | ~5 tests + wrapper updates | ~5 tests + wrapper updates |
| **New deps** | 0 | 0 | 0 |
| **KISS/YAGNI** | High | Low — premature abstraction | Low — routing refactor |
| **Type safety** | Full (typed hook return) | Full (typed context) | Manual assertion |
| **Future extensibility** | Add context when 2nd consumer appears | Already in place | Already in place |

### 3.2 Why Direct Polling Wins

The AC requires Shell to read `health` — a single `HealthState` value. Shell does NOT need `board`, `tasks`, `loading`, or `error`. The entire Context architecture solves a problem the AC doesn't require.

`usePolling` already exists, is fully tested (10 tests in `usePolling.test.ts`), and returns exactly `{ health, skipNextPoll }`. Shell imports it, calls it, binds `health` to the traffic-light span. Done.

### 3.3 Dual-Fetch Concern

Shell's `usePolling` polls `GET /api/tasks` every 3s for health. KanbanBoard's `useBoard` fetches `/api/tasks` on mount. This creates two fetch streams to the same endpoint. Mitigations:
- `usePolling` is lightweight — checks `res.ok`, no body parsing
- Backend `MtimeScanCache` makes repeated reads cheap
- The "without duplication" AC refers to not duplicating the useBoard hook, not HTTP requests
- A future unified polling task can consolidate if needed

### 3.4 Risk Matrix

| Risk | Direct usePolling | React Context | Outlet Context |
|------|-------------------|---------------|----------------|
| Test breakage | None | High (~50 tests) | High (~50 tests) |
| Over-engineering | None | Medium | Medium |
| Future refactor cost | Low (add context later) | None (already done) | None (already done) |
| Dual fetch overhead | Low (backend cached) | None (single source) | None (single source) |

## 4. Recommendation

**(rec)** Direct `usePolling` in Shell — confidence: **0.88**

Shell.tsx calls `usePolling('/api/tasks')` and binds `health` to the traffic-light span. KanbanBoard is unchanged. Zero new files, zero test breakage, ~5 LoC change.

**(bp)** React Context (BoardProvider) — defer until a second consumer needs shared board state across routes. This follows "avoid abstractions until the third repetition."

Challenge: `reconsider` — original Context recommendation scored 0.45 confidence. Challenger identified: LoC underestimate (60-80 LoC not 30-40), test impact mislabeled (50+ tests not "Low"), dual-fetch coordination unaddressed, and the direct-polling blind spot. Accepted all major challenges. Revised to direct polling approach.

## 5. Follow-up Tasks

No new follow-up tasks needed — implementation AC is scoped on #966 itself.

### Implementation Plan for Builder

1. Shell.tsx: import `usePolling`, call `usePolling('/api/tasks')`, bind `health` to traffic-light span via `data-health` attribute
2. Shell.test.tsx: mock `usePolling` module, test green/yellow/red states on traffic-light span
3. KanbanBoard.tsx: no changes
4. No new dependencies, no routing changes
