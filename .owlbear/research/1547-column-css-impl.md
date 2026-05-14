# Column Component CSS Implementation

> **Owning task:** #1547 — P3-04: impl — column component CSS: fixed header, scroll body, empty text fallback
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1547 implements PDS token-based visual styling for the Column component. Dependencies #1539 (test — structural separation, overflow, empty text) and #1543 (impl — token architecture) are both archived/completed. The HTML structure is ready; this task adds the CSS visual treatment.

**Question:** What CSS changes are needed, what tokens to use, and are there cross-task risks?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Codebase: Column.tsx | serve/cockpit/web/src/components/Column.tsx | 1.0 — current component |
| Codebase: Column.css | serve/cockpit/web/src/components/Column.css | 1.0 — file to modify |
| Codebase: tokens.css | serve/cockpit/web/src/tokens.css | 1.0 — available PDS tokens |
| Codebase: Card.css | serve/cockpit/web/src/components/Card.css | 0.8 — peer component pattern |
| Codebase: KanbanBoard.css | serve/cockpit/web/src/KanbanBoard.css | 0.8 — context menu token usage |
| Brief: board visual design | .owlbear/briefs/draft-board-visual-design/brief.md | 1.0 — column spec |
| SO #21515042 | stackoverflow.com/questions/21515042 | 0.9 — flexbox scrolling patterns |
| PDS v4 SCSS Intro | designsystem.porsche.com/v4/scss/introduction/ | 0.7 — PDS design tokens |

## 3. Analysis

### 3.1 Current State vs Target

| Aspect | Current Column.css | Target (ACs) | Action |
|--------|-------------------|--------------|--------|
| Background | none | `--pds-background-surface` | Add to `.column` |
| Border-radius | none | `--pds-radius-md` (6px) | Add to `.column` |
| Border | none | subtle (low-contrast) | Add `1px solid var(--pds-contrast-low)` |
| Min-width | `min-width: 0` | 200px | Change to `min-width: 200px` |
| Layout | implicit block | flex column (fixed header) | Add `display: flex; flex-direction: column` |
| Header | unstyled | fixed outside scroll area | Add `flex-shrink: 0` + padding |
| Body scroll | `overflow-y: auto` | same + contained by flex | Add `flex: 1; min-height: 0` |
| Empty state | centered | centered (done) | No change needed |
| Drag-over | no rule | visible highlight | Add `[data-drag-over="true"]` rule |

### 3.2 Fixed-Header Scrolling Pattern

The column needs `display: flex; flex-direction: column` so header stays fixed while body scrolls. Per SO #21515042 (364 votes), the critical CSS is:

- Parent: `display: flex; flex-direction: column`
- Header: `flex-shrink: 0` (prevents compression)
- Body: `flex: 1; overflow-y: auto; min-height: 0`

The `min-height: 0` overrides flexbox's automatic minimum size, allowing the body to shrink below its content height and activate scrolling. Without it, overflow-y never triggers.

### 3.3 Token Mapping Recommendations

| AC Term | Token | Value (light) | Value (dark) |
|---------|-------|---------------|-------------|
| "background-surface" | `--pds-background-surface` | hsl(240 10% 95%) | hsl(240 2% 10%) |
| "border-radius-md" | `--pds-radius-md` | 6px | 6px |
| "subtle border" | `--pds-contrast-low` | hsla(240 5.3% 14.9% / 0.5) | hsla(240 12.5% 96.9% / 0.45) |
| "drop-target highlight" | `--pds-state-hover` | hsla(240 5% 70% / 0.148) | hsla(240 2% 43% / 0.228) |

All tokens are theme-responsive via `[data-theme="dark"]` + media fallback from #1543.

### 3.4 Cross-Task Dependencies

| Concern | Owner | Risk |
|---------|-------|------|
| Board grid `minmax(200px, 1fr)` | #1550 (Shell + secondary CSS) | Low — column `min-width` is intrinsic; grid enforces it |
| Board `overflow-x: auto` for horizontal scroll | #1550 | Low — column works without it, scroll just won't activate |
| Column height constraints (for body scroll) | Board layout (#1550) | Medium — scroll needs constrained parent height |

### 3.5 Scope Clarification: AC-4 vs "Out" DnD

The scope says "Out: DnD column highlighting (minimal)." AC-4 requires a minimal drop-target highlight. These are consistent: extensive DnD animation/styling is out; the minimal `[data-drag-over="true"]` CSS rule IS the in-scope treatment. The `data-drag-over` attribute is already wired in Column.tsx.

## 4. Recommendation

**Proceed with CSS-only Column.css expansion** using agnostic PDS tokens. No JSX changes needed.

Confidence: 0.75

Challenge: reconsider (0.67 confidence in original) — challenger raised valid concerns about cross-task layout coupling, proof gaps for AC-1/AC-4, and AC ambiguity. Researcher response: accepted as advisory notes for architect review. The CSS approach is sound; cross-task coupling is documented but doesn't block this task's CSS work. Proof gaps are expected for an impl task — architect/test-writer decide coverage.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1547 is correctly scoped. The architect review will evaluate whether AC-1 and AC-4 need additional test coverage beyond #1539's existing suite.
