# Card Component CSS: Signal Border, Hover, Focus, Selected States

> **Owning task:** #1546 — P3-02: impl — card component CSS: signal border, hover, focus, selected states
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Card.css exists (pre-migration state) with signal selectors, hover/focus, and selected styles. However, it uses legacy `--pds-theme-light-*` token references that break dark mode, violates AC-3 (fixed height, missing overflow-wrap), and lacks AC-4 (drag state). What changes are needed for AC compliance?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `src/components/Card.css` | Codebase | 1.0 — current CSS with legacy tokens |
| S2 | `src/components/Card.tsx` | Codebase | 1.0 — JSX already has data-signal, needs drag state |
| S3 | `src/tokens.css` | Codebase | 1.0 — agnostic tokens migrated by #1543 |
| S4 | `.owlbear/research/1538-card-css-test-approach.md` | Codebase | 0.9 — test strategy, purple gap analysis |
| S5 | MDN: Kanban board with drag and drop | Web | 0.9 — `opacity: 0.2` on dragged element via ID/class |
| S6 | `src/__tests__/Card.css.test.ts` | Codebase | 1.0 — test expectations for signal/selected/hover/focus |
| S7 | Board Visual Design brief (#1534) | Brief | 1.0 — signal model, card spec D7/D10/D14 |
| S8 | Penpot: Design tokens and CSS variables guide | Web | 0.7 — `:root` token architecture pattern validation |

## 3. Analysis

### 3.1 Legacy Token Shadowing (Critical)

Card.css lines 5–11 re-declare `--pds-notification-warning`, `--pds-notification-error`, etc. within `.card` scope, mapping them to legacy `--pds-theme-light-*` names. Since #1543 migrated tokens.css to agnostic names with dark overrides, these local re-declarations **shadow the global tokens with light-only values**, completely breaking dark mode for card styling.

**Fix:** Remove all local token re-declarations. The signal selectors already reference `var(--pds-notification-warning)` etc. — they'll resolve correctly against the global tokens once shadowing is removed. Also change `var(--pds-theme-light-contrast-medium)` in the base border to `var(--pds-contrast-medium)`.

### 3.2 `--pds-signal-claimed` Token Placement

| Option | Location | Dark mode | Consistency |
|--------|----------|-----------|-------------|
| A: Keep in Card.css (current) | Local to `.card` | Same hue both themes | ❌ Inconsistent with token system |
| B: Move to tokens.css | Global, with dark override | Can lighten for dark bg | ✅ Centralized |

**Recommendation (B, confidence: .82):** Move to tokens.css `:root` with a dark override. Light: `hsl(270 58% 46%)`, Dark: `hsl(270 80% 70%)` (lighter for dark background contrast). Consistent with how all other semantic colors are managed.

### 3.3 AC-3 Compliance: Height and Text Overflow

| Current | Required | Change |
|---------|----------|--------|
| `max-height: 56px` | No fixed height constraint (D7) | Remove `max-height` |
| No overflow-wrap | `overflow-wrap: break-word` | Add to `.card` or title span |
| `background: transparent` | Transparent background | ✅ Already correct |

`overflow-wrap: break-word` should go on the `.card` container (not the span), ensuring long unbroken strings (task IDs, URLs) wrap instead of overflowing.

### 3.4 AC-4: Drag State

MDN kanban tutorial (S5) applies `opacity: 0.2` via CSS selector on the original element during drag. Brief says `opacity: 0.5`. Implementation approach:

1. Add `useState<boolean>(false)` for `isDragging` in Card.tsx
2. Set `true` in `onDragStart`, `false` in `onDragEnd`
3. Render `data-dragging={isDragging ? 'true' : undefined}`
4. CSS: `.card[data-dragging="true"] { opacity: 0.5; }`

This is the simplest React-compatible approach. No external library needed.

### 3.5 `--card-priority-border` Redundancy

Signal selectors set both `--card-priority-border` AND `border-left-color` directly. The CSS variable is unused elsewhere. Simplify: remove `--card-priority-border`, set only `border-left-color` in each selector. Base rule becomes `border-left: 4px solid var(--pds-contrast-medium)` (ready/default state).

### 3.6 Test Coverage Gaps

| AC | Test coverage | Notes |
|----|--------------|-------|
| AC-1 (signal borders) | ✅ Card.css.test.ts + Card.signal.test.tsx | |
| AC-2 (hover/focus/selected) | ✅ Card.css.test.ts | |
| AC-3 (overflow-wrap, no height) | ❌ No test | Builder should add or note gap |
| AC-4 (drag opacity) | ❌ No test | Builder should add or note gap |

Test file `Card.css.test.ts` uses its own AC numbering (AC-2/3/4) that doesn't match task #1546's ACs. The builder should be aware task AC-3 and AC-4 are untested.

## 4. Recommendation

**Approach: Clean up existing Card.css** (confidence: .90)

The implementation is straightforward CSS cleanup + 2 additions (drag state, overflow-wrap). No architecture decisions needed. All dependencies are complete (#1538 tests, #1543 tokens, #1544 signal model).

Key changes for the builder:
1. Remove 7 legacy token re-declarations (lines 5–11 of Card.css)
2. Fix base border fallback: `--pds-theme-light-contrast-medium` → `--pds-contrast-medium`
3. Move `--pds-signal-claimed` to tokens.css with dark override
4. Remove `max-height: 56px`, add `overflow-wrap: break-word`
5. Remove `--card-priority-border` intermediate variable
6. Add `[data-dragging="true"] { opacity: 0.5 }` CSS + `data-dragging` attribute in Card.tsx

Challenge: skipped (trivial CSS implementation, no trade-off between competing approaches).

## 5. Follow-up Tasks

None needed beyond the existing #1546 implementation task — all findings are implementation guidance for the builder.
