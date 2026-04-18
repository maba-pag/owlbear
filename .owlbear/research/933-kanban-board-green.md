# Kanban Board GREEN Phase — Research

> **Owning task:** #933 — P2-05: GREEN — Kanban board surface
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Implement the kanban board component to pass 26 RED tests from #931. The tests cover columns, cards (priority sort, block/claimed indicators), context menu with valid transitions, loading state, and error state. The AC also lists untested items: DnD, status bar wiring, scroll behavior.

**Key questions:** (a) Component file location — test import path? (b) Data fetching — plain fetch or TanStack Query? (c) DnD — include now or defer? (d) 700-task DOM performance? (e) Context menu — display-only or wired to move endpoint?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` — 26 RED tests, import path, data contract | 0.95 |
| S2 | `serve/cockpit/src/owlbear_cockpit/models.py` — API response schemas (TaskSummaryOut, BoardOut) | 0.95 |
| S3 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — POST /tasks/{id}/move endpoint | 0.90 |
| S4 | `.owlbear/research/931-kanban-board-tests.md` — RED test strategy, jsdom feasibility matrix | 0.90 |
| S5 | `.owlbear/research/955-e2e-kanban-board-tests.md` — Playwright for DnD/density/scroll | 0.85 |
| S6 | `serve/cockpit/web/package.json` — deps: React 19, PDS 3.34, no DnD/TanStack Query | 0.90 |
| S7 | npm: @dnd-kit/react 0.4.0, @dnd-kit/core 6.3.1, @atlaskit/pragmatic-drag-and-drop 1.8.0 | 0.80 |
| S8 | `serve/cockpit/web/src/Shell.tsx` — layout grid, route placeholder at `/` | 0.85 |
| S9 | `serve/cockpit/web/src/tokens.css` — PDS light theme custom properties | 0.80 |

## 3. Analysis

### 3.1 File Location (Critical — Challenger C1)

Test line 5: `import KanbanBoard from '../KanbanBoard'`. Test is in `src/__tests__/`. **Component must live at `src/KanbanBoard.tsx`** — not `src/surfaces/kanban/` as the AC's aspirational file list suggests. The AC file paths are a future structure target; the RED tests define the actual contract.

Internal sub-components (Column, Card, ContextMenu) as private helpers in the same file. Extract to separate files only if the file exceeds ~200 lines. Default export required.

### 3.2 Data Fetching

| Option | Pros | Cons | Rework cost |
|--------|------|------|-------------|
| Plain fetch hook | KISS, tests stub `fetch()` directly, zero deps | No polling, no dedup, no cache | Medium — must migrate for poll |
| TanStack Query | Polling, dedup, devtools, optimistic updates | New dep, tests still stub fetch | Low — incremental adoption |

**Decision: Plain fetch hook** for GREEN phase. Tests exercise `fetch()` stubs — hook must use `fetch()` internally. TanStack Query migration is a deliberate deferred cost for the polling task (follow-up). The hook contract (`useBoard(): { board, tasks, loading, error }`) is stable regardless of internals.

### 3.3 DnD Library (Deferred — Not Tested)

RED tests don't exercise drag events. E2E task #957 covers DnD with Playwright.

| Library | React 19 | Bundle | Downloads/wk | Maturity | Risk |
|---------|----------|--------|-------------|----------|------|
| @dnd-kit/react 0.4.0 | Native | ~15KB | 430K | Pre-1.0 | Medium |
| @dnd-kit/core 6.3.1 | Issues (#1654) | ~12KB | 13M | Stable but stale | Medium |
| @atlaskit/pragmatic-dnd 1.8.0 | Agnostic | ~8KB | 970K | Active | Low |

**Decision: Defer DnD to follow-up task.** GREEN phase passes 26 tests without DnD. Library choice is a separate decision when DnD RED tests exist.

### 3.4 Context Menu — Display vs Action (Challenger C2)

Tests verify menu rendering and transition items. **No test clicks a transition item to trigger a move.** The move endpoint exists (POST /tasks/{id}/move).

**Decision: Display-only in GREEN.** Clicking a transition item is a no-op. Follow-up task adds RED tests for context menu → move → refetch cycle. Rationale: TDD discipline — no untested behavior.

### 3.5 Priority Sorting (Challenger C5)

Tests expect critical-first. `BOARD.priorities` array: `['someday', 'nice-to-have', 'important', 'needed', 'critical']` — index 0..4 ascending.

**Decision: Derive sort order from `BOARD.priorities` array index**, not a hardcoded map. `priorities.indexOf(card.priority)` gives the rank. Sort descending.

### 3.6 DOM Performance at 700 Tasks (Challenger C3)

RED tests use 4 mock tasks — zero signal on scale. Parent brief targets 700 tasks.

| Approach | Complexity | When needed |
|----------|-----------|-------------|
| Bare DOM (no virtualization) | Low | Until proven slow |
| react-window / virtuoso | Medium | If rendering 100+ cards per column lags |

**Decision: Defer virtualization.** Create follow-up task for frontend performance benchmark at 700 tasks. If columns render >100 cards with visible jank, add react-virtuoso. GREEN phase is about correctness (passing tests), not perf.

### 3.7 Partial Fetch Failure (Challenger blind spot)

Board needs both `/api/board` and `/api/tasks`. Tests stub both identically. If one succeeds and one fails, show error state. Both-or-nothing is the simplest correct behavior.

## 4. Recommendation

Implement `src/KanbanBoard.tsx` as a single file with internal Column, Card, ContextMenu helpers. Plain `fetch()` hook. Default export. Derive priority sort from API response. Display-only context menu. No DnD, no virtualization, no TanStack Query.

**Confidence: 0.78**

Challenge: `reconsider` — challenger confidence in original 0.52. Revised after addressing file path conflict (C1 → resolved), context menu action gap (C2 → explicitly display-only with follow-up), 700-task perf (C3 → deferred with follow-up task), TanStack Query migration cost (C4 → acknowledged trade-off), priority sort derivation (C5 → from API index).

## 5. Follow-up Tasks

1. Wire context menu transitions to POST /move endpoint (needs RED tests first)
2. Frontend performance benchmark at 700 tasks + virtualization if needed
3. TanStack Query migration + mtime-aware polling (status bar prerequisite)
4. Status bar wiring: traffic-light poll health + column counts
5. Shell route integration: replace `<div>kanban</div>` with `<KanbanBoard />`
