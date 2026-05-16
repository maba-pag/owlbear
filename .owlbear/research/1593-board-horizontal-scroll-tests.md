# Board Horizontal Scroll — Test Feasibility

> **Owning task:** #1593 — P0-05: Tests — board horizontal scroll
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1593 writes failing Playwright E2E tests asserting that the board container scrolls horizontally when 6+ columns are rendered, and that columns maintain a fixed minimum width instead of shrinking. This is the RED phase of a TDD pair (#1593 → #1596).

**Key question:** What test patterns, selectors, and viewport setup produce reliable RED tests against the current `auto-fit` grid that will turn GREEN when the grid is changed to a fixed-column layout?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/KanbanBoard.tsx` L291–296 — current board grid container | 0.95 |
| S2 | `serve/cockpit/web/src/components/Column.css` — column `min-width: 200px` | 0.95 |
| S3 | `serve/cockpit/web/e2e/responsive-layout-1391.spec.ts` L314–335 — scroll measurement pattern | 0.95 |
| S4 | `serve/cockpit/web/e2e/kanban-board.spec.ts` — fixture data and API mocking pattern | 0.90 |
| S5 | `serve/cockpit/web/src/Shell.css` — grid: `56px 1fr 360px` (shell chrome) | 0.85 |
| S6 | `.owlbear/briefs/draft-cockpit-visual-redesign/brief.md` L25, L48 — scroll AC from brief | 0.90 |

## 3. Analysis

### 3.1 Current Grid Behavior

The board container uses inline styles (S1):
```css
grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
overflow-x: auto;
```

`auto-fit` creates as many 200px+ tracks as fit in one row, then **wraps remaining items to implicit rows**. With 7 statuses at 1024px viewport (workspace ≈ 608px), only 3 columns fit per row → columns wrap to 3 rows. `scrollWidth ≈ clientWidth` — no horizontal overflow occurs.

### 3.2 Post-Fix Expected Behavior (#1596)

The implementation task will change the grid to a fixed-column layout (e.g., `repeat(N, minmax(200px, …))`). With 7 columns forced into a single row, `scrollWidth = 7 × 200px = 1400px > clientWidth ≈ 608px` → horizontal scroll.

### 3.3 Test Pattern

| AC | Selector | Measurement | Assertion | RED Failure Mode |
|----|----------|-------------|-----------|-----------------|
| scrollWidth > clientWidth | `[data-column]` → `.parentElement` | `page.evaluate()` → `scrollWidth`, `clientWidth` | `scrollWidth > clientWidth` | auto-fit wraps → `scrollWidth ≈ clientWidth` |
| columns maintain min-width | `[data-column]` | `getBoundingClientRect().width` per column | each `width >= 200` | auto-fit may size columns > 200px via `1fr`, but **wraps** — test must also assert single-row layout |

Established pattern from S3 (responsive-layout-1391): locate container via `document.querySelector('[data-column]').parentElement`, measure `scrollWidth` and `clientWidth`.

### 3.4 Viewport Choice

Shell chrome: 56px (nav-rail) + 360px (sidecar) = 416px. Workspace = `viewport - 416px`.

| Viewport | Workspace | 7 × 200px | Overflow? (post-fix) |
|----------|-----------|-----------|---------------------|
| 1024px | 608px | 1400px | Yes — scrollWidth > clientWidth |
| 1440px | 1024px | 1400px | Yes — still overflows |

Use **default Playwright viewport (1280×720)** — workspace ≈ 864px, still < 1400px. Standard and requires no `test.use()` override.

### 3.5 Single-Row Assertion

To distinguish "columns scroll horizontally" from "columns wrap to multiple rows," the test should verify all `[data-column]` elements share the same `offsetTop`. This proves they're in one row — complementary to the scrollWidth assertion.

## 4. Recommendation

**Confidence: 0.90** — Straightforward application of established patterns. All selectors, measurement APIs, and mocking strategies are proven in the existing test suite.

**Approach:** Create `e2e/board-scroll-1593.spec.ts` with:
1. Standard API mocking (`/api/board` with 7 statuses, `/api/tasks` with 1+ task per status)
2. Test 1: Assert `scrollWidth > clientWidth` on board container (RED: auto-fit wraps)
3. Test 2: Assert each `[data-column]` has `width >= 200` and all share the same `offsetTop` (RED: wrapping puts columns at different top positions)

Challenge: SKIPPED — trivial task applying established codebase patterns, no external dependencies or architectural decisions involved.

## 5. Follow-up Tasks

None needed — #1593 itself is the test task; #1596 (implementation) already exists as its dependent.
