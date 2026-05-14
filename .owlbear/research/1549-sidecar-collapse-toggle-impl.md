# Sidecar Collapse Toggle — Implementation Approach

> **Owning task:** #1549 — P3-08: impl — sidecar collapse toggle
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1549 adds visual collapse/expand behavior to the sidecar panel. The ARIA toggle button and React state already exist in Shell.tsx (delivered by #1541 tests + preliminary green). What's missing: (a) CSS transition for smooth animation (AC-2), (b) visual hide/show of the sidecar content (AC-1 visual), (c) proper toggle button styling.

**Key questions:** Which CSS technique animates the sidecar collapse? How does the grid respond? How should the toggle button be styled?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | CSS-Tricks: Animating CSS Grid | https://css-tricks.com/animating-css-grid-how-to-examples/ | 1.0 |
| S2 | CanIUse: grid-template-columns animation | https://caniuse.com/mdn-css_properties_grid-template-columns_animation | 0.95 |
| S3 | CodePen: CSS Grid sidebar expand | https://codepen.io/mrdanielschwarz/pen/BaPjKrP | 0.90 |
| S4 | Codidact: CSS grid animated cells | https://software.codidact.com/posts/287970 | 0.80 |
| S5 | Shell.tsx + Shell.css (codebase) | local | 1.0 |
| S6 | #1541 research doc | `.owlbear/research/1541-sidecar-collapse-toggle-test-approach.md` | 1.0 |
| S7 | Brief: draft-board-visual-design | `.owlbear/briefs/draft-board-visual-design/brief.md` | 1.0 |

## 3. Analysis

### 3.1 CSS Collapse Technique — Options

| Option | Technique | Pros | Cons |
|--------|-----------|------|------|
| A — Grid column transition | `transition` on `.shell`, change `grid-template-columns` from `56px 1fr 360px` → `56px 1fr 0fr` | Smooth, native, workspace auto-expands, single CSS property | Must use `0fr` not `0` (unit required); content needs overflow:hidden during animation |
| B — Width + transform | `width: 0; transform: translateX(100%)` on sidecar | Works without grid animation support | Workspace doesn't auto-expand; sidecar leaves gap or needs absolute positioning |
| C — Conditional render | `{!collapsed && <aside>}` in JSX | Simplest React code | No animation possible; unmounts sidecar (loses tab state, scroll) |
| D — display:none toggle | Add/remove `.hidden` class | Zero layout cost when hidden | No transition possible; same unmount-like UX problems |

**Recommendation: Option A** (confidence: 0.90). Grid column animation is supported in all major browsers at 93%+ global coverage (S2). The CSS-Tricks article (S1) demonstrates this exact sidebar collapse pattern. The `0fr` → `360px` transition is the canonical approach. The existing grid layout in Shell.css makes this a ~10-line CSS change.

### 3.2 Implementation Detail — Option A

**CSS changes (Shell.css):**

```css
.shell {
  /* Add transition to existing grid rule */
  transition: grid-template-columns 250ms ease;
}

/* Collapsed state — driven by data attribute on .shell */
.shell[data-sidecar-collapsed] {
  grid-template-columns: 56px 1fr 0fr;
}

.shell__sidecar {
  overflow: hidden;  /* Prevent content spill during transition */
}
```

**JSX changes (Shell.tsx):**
- Add `data-sidecar-collapsed={isSidecarCollapsed || undefined}` to `.shell` div
- Content div already has `aria-hidden` from #1541 green pass

**Why `data-sidecar-collapsed` on `.shell` not on `.shell__sidecar`?** The `grid-template-columns` property is on the grid container (`.shell`), not the grid item. The state attribute must be on the same element that owns the transition.

**Pitfall (S1):** `grid-template-columns` must transition between values with the same number of tracks. `0fr` works; removing the track doesn't. The `0fr` value collapses the column to zero width while keeping the grid structure intact.

### 3.3 Responsive Breakpoints

| Breakpoint | Desktop grid | Collapsed grid | Notes |
|------------|-------------|----------------|-------|
| ≥1024px | `56px 1fr 360px` | `56px 1fr 0fr` | Standard collapse |
| 768–1023px | `56px 1fr 240px` | `56px 1fr 0fr` | Same pattern, narrower sidecar |
| ≤767px | Single column stack | Toggle hides sidecar row | Could use `grid-template-rows` transition or `display:none` |

Mobile (≤767px) is **out of scope** per AC. The task says "Out: responsive breakpoints." Desktop and tablet get the grid transition; mobile behavior is unchanged.

### 3.4 Toggle Button Styling

Current toggle is an unstyled `<button>` with text. Options:

| Option | Component | Pros | Cons |
|--------|-----------|------|------|
| A — Inline SVG chevron | Native `<button>` + `<svg>` | Zero deps, matches nav-rail pattern | Manual styling needed |
| B — PDS PButton | `<PButton variant="ghost" icon="arrow-right">` | PDS consistent | PButton may be heavy for a toggle; icon name availability unclear |
| C — CSS-only chevron | `<button>` + `::after` pseudo-element | Minimal DOM | Less accessible if text is removed |

**Recommendation: Option A** (confidence: 0.80). The nav-rail already uses a native `<button>` + inline SVG (Shell.tsx L143-163). Same pattern: a small icon button, no PDS component overhead. The chevron rotates 180° when collapsed via CSS transform.

### 3.5 State Persistence (AC-3)

Already implemented. `useState(false)` in Shell.tsx preserves collapsed state across re-renders. No localStorage persistence needed per AC — "component local state" is explicit. Tests in SidecarCollapse_1541.test.tsx already verify this via `rerender()`.

## 4. Recommendation

**Approach (confidence: 0.88):** Animate sidecar collapse via `grid-template-columns` transition on `.shell`. Drive state via `data-sidecar-collapsed` attribute. Style toggle as a small icon button with chevron SVG. Content hidden via `overflow: hidden` + `0fr` grid column (content already has `aria-hidden` from #1541).

Challenge: FALLBACK — implementation is a direct application of the established CSS Grid animation pattern (S1, S3) to existing layout. Low architectural risk, no new dependencies.

**Tier: T1** — CSS + minor JSX change, no architecture impact.

## 5. Follow-Up Tasks

No new follow-up tasks needed. Task #1549 itself is the implementation task, already scoped with AC. Dependencies #1541 (tests) and #1543 (token architecture) cover prerequisites.
