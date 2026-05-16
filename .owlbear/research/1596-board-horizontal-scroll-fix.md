# Board Horizontal Scroll Fix

> **Owning task:** #1596 — P0-06: Board horizontal scroll fix
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

The cockpit board grid uses `repeat(auto-fit, minmax(200px, 1fr))` in `KanbanBoard.tsx` L321. With 7 status columns at a typical workspace width of ~864px, `auto-fit` creates implicit row tracks and **wraps** excess columns instead of overflowing horizontally — despite `overflow-x: auto` on the container. The fix must make the grid produce a single row of fixed-minimum-width columns that overflow horizontally.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/cockpit/web/src/KanbanBoard.tsx` L318–328 — current grid inline styles | Codebase | 0.95 |
| S2 | `serve/cockpit/web/src/components/Column.css` — `.column { min-width: 200px }` | Codebase | 0.90 |
| S3 | `serve/cockpit/web/e2e/board-scroll-1593.spec.ts` — RED tests (AC assertions) | Codebase | 0.95 |
| S4 | CSS-Tricks: Auto-Sizing Columns — auto-fill vs auto-fit (2017-12-29) | Web | 0.90 |
| S5 | MDN: `repeat()` CSS function — syntax for `<integer>` vs `auto-fill`/`auto-fit` | Web | 0.85 |
| S6 | SO: "CSS grid only columns, no wrap" (2021-01-22) | Web | 0.80 |
| S7 | `.owlbear/research/1593-board-horizontal-scroll-tests.md` — sibling test research | Codebase | 0.95 |

## 3. Analysis

### 3.1 Root Cause

`auto-fit` (S4, S5) creates as many tracks as fit in the available width, then **collapses** empty tracks. When items exceed the available width, the grid doesn't overflow — CSS Grid spec says `auto-fit`/`auto-fill` create tracks within the available space, so `scrollWidth ≈ clientWidth`. The `overflow-x: auto` is present but never triggers because the grid never generates content wider than its container.

### 3.2 Options

| Criterion | A: `repeat(N, minmax(200px, 1fr))` | B: `repeat(N, 200px)` | C: Flexbox row |
|-----------|-----------------------------------|-----------------------|----------------|
| Approach | Dynamic N from `board.statuses.length` | Fixed 200px per column | `display: flex; flex-wrap: nowrap` |
| Column sizing | 200px min, expands with 1fr when space allows | Exactly 200px always | 200px via `min-width` + `flex: 0 0 auto` |
| Overflow behavior | Scrolls when `N × 200px > container` | Always scrolls if total > container | Scrolls via `overflow-x: auto` |
| Few-column case (≤3) | Columns expand to fill (1fr) | Columns stay 200px, gap on right | Columns stay 200px, gap on right |
| Code change | 1 line: template string interpolation | 1 line: template string interpolation | 3–4 lines: switch display model |
| Existing test compat | Tests expect `[data-column]` on grid children | Same | Different parent layout model |
| KISS score | High — minimal change, preserves grid | High — minimal change, loses flexibility | Medium — changes layout model |
| Risk | Low — well-understood CSS | Low — rigid sizing may look sparse | Medium — flexbox + grid mismatch |

### 3.3 Assessment

**Option A** is the clear winner:

- **Dynamic column count** (`board.statuses.length`) adapts to any number of statuses without hardcoding.
- **`minmax(200px, 1fr)`** preserves the existing behavior where columns expand to fill when few statuses exist (≤3 columns at typical viewport).
- **Minimal diff:** change `'auto-fit'` → `${board.statuses.length}` in the template string. One token change.
- **Test alignment:** The RED tests in S3 expect `repeat(7, minmax(200px, 1fr))` behavior.
- **No layout model change** — stays CSS Grid, no test infrastructure impact.

**Option B** loses the `1fr` expansion, making the board look sparse when few columns are present.
**Option C** changes the layout model entirely — unnecessary complexity for a one-token fix.

## 4. Recommendation

**Use Option A: `repeat(${board.statuses.length}, minmax(200px, 1fr))`**

Confidence: **0.92**

The change is a single-token replacement in the `gridTemplateColumns` inline style (L321 of `KanbanBoard.tsx`):

```diff
- gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
+ gridTemplateColumns: `repeat(${board.statuses.length}, minmax(200px, 1fr))`,
```

This produces `repeat(7, minmax(200px, 1fr))` for the default 7-status board → 7 × 200px = 1400px minimum → overflows the ~864px workspace → horizontal scroll activates. When the viewport is wide enough, `1fr` lets columns expand.

Challenge: SKIPPED — trivial one-line CSS property change, no architectural decisions, no external dependencies.

## 5. Follow-up Tasks

None needed — #1596 is the implementation task itself. The RED tests (#1593) and implementation (#1596) are already paired in the decomposition. No additional research or decision requests required.

### Tier Classification

**T1 — Autonomous.** Bug fix / CSS refactor. No new capability, no architecture change, no user-facing behavior change beyond fixing the broken scroll.
