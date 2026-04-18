# TanStack Query vs Plain Polling for Kanban Board

> **Owning task:** #960 — TanStack Query migration + mtime-aware polling for kanban board
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #960 requires: 3s polling for `/api/tasks`, mtime-aware conditional refetch (skip re-render if unchanged), and a status bar traffic-light (green/yellow/red) in Shell.tsx. The current `useBoard()` in `KanbanBoard.tsx` is a one-shot `useEffect` + `fetch()` (~35 lines). Should we adopt TanStack Query or use plain `setInterval` + `useRef` polling?

Key architectural constraint: the traffic-light lives in `Shell.tsx` but `useBoard()` runs inside `KanbanBoard` (a child route). The poll health state must propagate upward regardless of library choice — this requires lifting the hook or adding a context provider.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | TanStack Query v5 docs — overview | https://tanstack.com/query/latest/docs/framework/react/overview | 0.9 |
| 2 | TanStack Query — polling guide | https://tanstack.com/query/latest/docs/framework/react/guides/polling | 0.9 |
| 3 | TanStack Query — testing guide | https://tanstack.com/query/latest/docs/framework/react/guides/testing | 0.8 |
| 4 | TanStack Query — important defaults | https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults | 0.8 |
| 5 | @tanstack/react-query (npm) | https://www.npmjs.com/package/@tanstack/react-query | 0.7 |
| 6 | Codebase: KanbanBoard.tsx useBoard() | serve/cockpit/web/src/KanbanBoard.tsx L43-78 | 1.0 |
| 7 | Codebase: backend read.py + MtimeScanCache | serve/cockpit/src/owlbear_cockpit/routes/read.py | 1.0 |
| 8 | Codebase: Shell.tsx traffic-light spans | serve/cockpit/web/src/Shell.tsx L28-29 | 1.0 |

## 3. Analysis

### 3.1 Feature Comparison

| Criterion | Plain setInterval (rec) | TanStack Query (bp) |
|-----------|------------------------|---------------------|
| **New deps** | 0 | 1 (+@tanstack/query-core) |
| **Bundle impact** | 0 KB | ~15-20 KB gzip |
| **3s polling** | `setInterval` + `useRef` | `refetchInterval: 3_000` |
| **Mtime skip** | Custom: compare `mtime` in response, skip `setState` | Custom: same logic in queryFn (not built-in) |
| **Yellow = slow** | Custom: `performance.now()` timing | Custom: same (TQ doesn't expose request duration) |
| **Error retry** | Custom: counter + backoff | Built-in: 3 retries + exponential backoff |
| **Dedup** | Manual: `AbortController` per tick | Built-in |
| **Structural sharing** | N/A (mtime skip is cheaper) | Built-in (but moot if mtime-skip is implemented) |
| **Test migration** | None (existing fetch stubs work) | 26 tests need QueryClientProvider wrapper |
| **Code delta** | ~50-60 LoC (replace useBoard) | ~30 LoC hook + QueryClientProvider in main.tsx |
| **Future mutations** | Add manually when needed | Built-in `useMutation` + cache invalidation |
| **KISS alignment** | High | Moderate — unused features (dedup, stale-while-revalidate) |

### 3.2 Mtime-Aware Polling (applies to both approaches)

The backend `/api/tasks` returns `{ tasks: [...], mtime: int }`. The polling logic:
1. Poll every 3s with `fetch('/api/tasks')`
2. Parse response JSON (lightweight — already text decoded)
3. Compare `response.mtime` with stored `lastMtime` ref
4. If unchanged: skip `setTasks()` — no re-render
5. If changed: update tasks and lastMtime

This is 3-5 lines of logic on top of either approach. TanStack Query's `structuralSharing` is redundant when you can short-circuit with a number comparison.

### 3.3 Board Config Polling Strategy

`/api/board` returns statuses, priorities, and valid_transitions — quasi-static config that only changes when the kanban YAML is edited. Polling it at 3s is wasteful. Recommendation: fetch `/api/board` once on mount; poll only `/api/tasks` at 3s. Refetch board on demand or at a much longer interval (60s+).

### 3.4 Shell ↔ KanbanBoard State Wiring

The traffic-light is in `Shell.tsx` (parent), but poll state originates in `KanbanBoard` (child route). Options:
- **(rec)** Lift `useBoard` into Shell or a shared context; pass data down to KanbanBoard via props or context
- Create a `BoardProvider` context that both Shell (traffic-light) and KanbanBoard consume
- Event bus (over-engineered for this)

This is an architectural decision independent of the fetch library choice.

### 3.5 Risk Matrix

| Risk | Plain setInterval | TanStack Query |
|------|-------------------|----------------|
| Overlapping requests (>3s response) | Medium — needs AbortController | Low — built-in |
| Test flakiness | Low — no change | Medium — retries, gc, refetchOnFocus |
| Bundle bloat | None | Low (~15-20KB) |
| Learning curve | None | Low-moderate |
| Future extensibility | Medium — manual wiring for mutations | High — built-in mutations |

## 4. Recommendation

**(rec)** Plain `setInterval` + `useRef` polling — confidence: 0.80

The mtime-aware skip, yellow-state timing, and Shell wiring are custom code in both approaches. TanStack Query's core value-adds (dedup, stale-while-revalidate, mutation cache) are unused by the current AC. With only one polling consumer and existing fetch-stub tests, adding a dependency is premature.

**(bp)** Adopt TanStack Query when a second data consumer appears (task detail polling, activity feed, or mutations). This follows the project's "avoid abstractions until the third repetition" principle.

Challenge: `reconsider` — confidence in original (TanStack Query): 0.45. Revised to plain polling after challenger identified KISS/YAGNI conflict, overstated mtime benefits, yellow-state gap, Shell wiring gap, and test migration cost. Accepted all major challenges.

## 5. Follow-up Tasks

1. **RED: useBoard polling tests** — write failing tests for 3s polling, mtime-skip, error states
2. **GREEN: useBoard polling implementation** — plain setInterval + useRef + AbortController
3. **Architecture: Shell ↔ KanbanBoard state wiring** — lift poll state for traffic-light access
