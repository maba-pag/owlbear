# Frontend Performance Benchmark: Kanban Board at 700 Tasks + Virtualization Decision

> **Owning task:** #959 — Frontend performance benchmark: kanban board at 700 tasks + virtualization decision
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Parent brief #920 targets 700 tasks as baseline scale. The kanban board component (`KanbanBoard.tsx`) renders all tasks as bare DOM — no virtualization, no memoization. Questions: (a) Does 700 tasks cause measurable jank? (b) Should we add react-virtuoso or react-window? (c) What benchmarks prove the answer?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/KanbanBoard.tsx` — component implementation, ~200 LOC | 0.95 |
| S2 | `tests/benchmarks/bench_list_tasks.py` — backend benchmark pattern (700/1500 tasks) | 0.85 |
| S3 | `.owlbear/research/933-kanban-board-green.md` — GREEN phase: deferred virtualization | 0.90 |
| S4 | npm: react-virtuoso v4.18.5 — 57KB min / 18.4KB gzip, 0 deps, 2.5M/wk | 0.85 |
| S5 | npm: react-window v2.2.7 — 12.5KB min / 6.5KB gzip, 0 deps, 5.4M/wk | 0.85 |
| S6 | bundlephobia.com — bundle size verification for S4 and S5 | 0.80 |
| S7 | Vitest docs — `bench` API (experimental, Tinybench-based) | 0.75 |
| S8 | `.owlbear/research/955-e2e-kanban-board-tests.md` — Playwright for scroll/density | 0.80 |
| S9 | Google RAIL model — 100ms "instant", 1000ms "lose focus" | 0.75 |

## 3. Analysis

### 3.1 DOM Node Estimate at 700 Tasks

| Element | Nodes/item | Count | Total |
|---------|-----------|-------|-------|
| Card div | 1 | 700 | 700 |
| Title span + text | 2 | 700 | 1,400 |
| Block badge (10% tasks) | 2 | 70 | 140 |
| Claimed indicator (15%) | 2 | 105 | 210 |
| Column div + header | 3 | 7 | 21 |
| Board container | 1 | 1 | 1 |
| **Total** | | | **~2,470** |

~2,500 DOM nodes. Modern browsers handle 10,000+ without layout issues. React 19 reconciliation handles this scale for initial mount.

### 3.2 Re-Render Risk (Challenger C2 — Critical)

Current code has **zero memoization**. Every state change re-renders all 700 cards:

- `handleContextMenu` recreated each render (inline function)
- `tasks.filter()` creates new array per column per render (7×)
- `[...tasks].sort()` copies + sorts per column per render (7×)
- Each `Card` receives new closure via `onContextMenu`

**A single right-click triggers 700 Card re-renders.** This is the dominant perf risk — not initial mount. Future features (polling, move operations) amplify this.

**Mitigation (zero bundle cost):** `React.memo` on `Card`/`Column`, `useMemo` on filter/sort, `useCallback` on `handleContextMenu`. This should be a prerequisite before measuring, AND the benchmark should test both paths.

### 3.3 Column Skew (Challenger C5)

Uniform 100/column is unrealistic. Real boards accumulate tasks at `backlog` and `done`. Skewed scenario: 400 backlog / 150 done / 30 each remaining. A 400-card column at ~50px/card = 20,000px scroll height — still manageable without virtualization, but re-render cost scales linearly with the largest column.

### 3.4 Benchmarking Approach

| Tier | Tool | What it measures | Signal quality |
|------|------|------------------|----------------|
| Structural | Vitest + jsdom | DOM node count assertion | High — deterministic |
| Mount time | Playwright | Real browser render (LCP or `performance.measure`) | High — real pipeline |
| Scroll | Playwright | Frame drops in 100+ card column | High — real paint |
| Re-render | Playwright | State change → re-render time | High — real pipeline |
| ~~jsdom timing~~ | ~~Vitest~~ | ~~`performance.now()` around render~~ | **Dropped** — no layout/paint |

jsdom has no layout engine. Timing assertions in jsdom measure React reconciliation in Node.js, not browser render cost. DOM count assertion in jsdom is valid; timing is not.

### 3.5 Virtualization Library Comparison (If Needed)

| Criterion | react-window 2.2.7 | react-virtuoso 4.18.5 |
|-----------|--------------------|-----------------------|
| Bundle (gzip) | 6.5 KB | 18.4 KB |
| Dependencies | 0 | 0 |
| Weekly downloads | 5.4M | 2.5M |
| Variable row height | Manual measurement | Auto (ResizeObserver) |
| DnD integration | External lib required | Built-in custom components |
| React 19 | Native | Native |
| API complexity | Low (fixed height) | Low (auto-sizes) |

**DnD changes the calculus.** react-window is smaller, but DnD is a known future requirement (see #933 follow-ups). react-window + DnD lib = ~20-35KB total. react-virtuoso at 18.4KB with built-in scroll-during-drag = simpler integration. If we ever virtualize, **react-virtuoso is the pragmatic choice** despite the larger bundle.

## 4. Recommendation

**Defer virtualization. Optimize memoization first. Prove with benchmarks.**

1. Add `React.memo` / `useMemo` / `useCallback` to eliminate re-render cascade (zero bundle cost)
2. Write benchmark tests covering: DOM count (jsdom), mount time (Playwright), scroll (Playwright), re-render after state change (Playwright), skewed column distribution
3. If benchmarks pass at 700 tasks: no virtualization needed
4. If benchmarks fail: add react-virtuoso (not react-window) due to DnD compat

**Threshold criteria:**
- Mount time: <500ms (AC target), <200ms ideal (RAIL "instant")
- Scroll: <5% frame drops in 100+ card column
- Re-render: <100ms for state change with 700 cards
- DOM count: <5,000 nodes total

**Confidence: 0.78**

Challenge: `reconsider` — challenger confidence 0.45. Revised after: fixing DOM count arithmetic (C1), adding re-render benchmark (C2), dropping jsdom timing (C3), adding skewed distribution (C5), switching library recommendation to react-virtuoso for DnD compat (C6). Acknowledged PDS overhead as future risk.

## 5. Follow-up Tasks

1. Memoization optimization: Add React.memo/useMemo/useCallback to KanbanBoard.tsx
2. Benchmark tests: jsdom DOM-count + Playwright mount/scroll/re-render at 700 tasks (uniform + skewed)
