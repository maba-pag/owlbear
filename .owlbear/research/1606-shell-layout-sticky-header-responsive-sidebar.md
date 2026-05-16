# Shell Layout — Sticky Header + Responsive Sidebar

> **Owning task:** #1606 — P1-09: Shell layout — sticky header + responsive sidebar
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1606 requires three changes to the cockpit shell: (1) make the header sticky so it remains visible when content scrolls past viewport height, (2) collapse the sidebar to icon-only at viewport < 1024px, and (3) express the layout structure via Tailwind CSS Grid/Flexbox utilities instead of a standalone Shell.css file.

The test-writing task (#1601) was archived/deprecated with `archival_refs: [1606]`, so this implementation task absorbs test responsibility.

**Key ambiguity:** "Sidebar" in the AC could mean the left nav-rail or the right sidecar. Analysis below resolves this.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PDS v4 component introduction | designsystem.porsche.com/v4/components/introduction/ | 0.7 — `p-canvas` (🧪) has sidebar slots but is experimental |
| PDS v4 Tailwind Grid docs | designsystem.porsche.com/v4/tailwindcss/grid/examples/ | 0.5 — "Porsche Grid" is for content pages, not app shells |
| Tailwind CSS v4 position docs | tailwindcss.com/docs/position | 0.9 — `sticky top-0` utility for header |
| Tailwind CSS v4 grid-template-columns | tailwindcss.com/docs/grid-template-columns | 0.9 — `grid-cols-[...]` arbitrary value syntax |
| Current Shell.tsx (440 lines) | serve/cockpit/web/src/Shell.tsx | 1.0 — existing implementation |
| Current Shell.css (217 lines) | serve/cockpit/web/src/Shell.css | 1.0 — current CSS Grid layout with named areas |
| Responsive layout E2E tests (670 lines) | serve/cockpit/web/e2e/responsive-layout-1391.spec.ts | 0.9 — extensive viewport tests at 320/768/1024/1440px |
| Shell unit tests (168 lines) | serve/cockpit/web/src/__tests__/Shell.test.tsx | 0.8 — region existence tests |

## 3. Analysis

### 3.1 "Sidebar" Ambiguity Resolution

The shell has two side panels: nav-rail (left, 56px) and sidecar (right, 360px).

| Evidence | Points to |
|----------|-----------|
| "Icon-only state" — classic nav sidebar pattern | Nav-rail |
| Nav-rail is ALREADY icon-only at all viewports | Neither (already satisfied) |
| Brief says "sidebar responsive collapse", sidecar has collapse toggle | Sidecar |
| AC scope excludes "sidecar structure" but includes shell layout | Sidecar collapse = layout concern |
| 768–1023px breakpoint narrows sidecar to 240px but doesn't collapse | Sidecar |

**Conclusion:** "Sidebar" = sidecar (right panel). The nav-rail is already icon-only. The AC means: at < 1024px the sidecar auto-collapses to a minimal icon-only strip (~48px), showing just the collapse toggle. At ≥ 1024px it shows at full width (360px). This is a CSS Grid column change, not a sidecar-internal restructuring.

### 3.2 Sticky Header

| Aspect | Finding |
|--------|---------|
| Current state | Header is `grid-area: status-bar` in `grid-template-rows: auto 1fr`. Shell has `height: 100vh` — page itself doesn't scroll. |
| Effective stickiness | Already visually fixed because the shell fills the viewport and only workspace scrolls internally. |
| AC test approach | Playwright `isVisible()` after scroll — scroll must target workspace element, not document body. |
| Recommended change | Add `sticky top-0 z-10` to header as belt-and-suspenders: ensures stickiness even if shell layout changes or content overflows 100vh. |
| Risk | Minimal — sticky within a grid row is well-supported in modern browsers. z-index ensures header stays above scrollable siblings. |

### 3.3 Tailwind Migration Strategy

| Option | Description | Confidence | Risk |
|--------|-------------|------------|------|
| **A: Full Tailwind (no Shell.css)** | Express everything as className utilities including grid areas via arbitrary values `[grid-area:status-bar]` | 0.60 | Complex class strings; `grid-template-areas` requires repetitive arbitrary syntax; harder to read |
| **B: Hybrid (thin Shell.css + Tailwind)** | Keep `grid-template-areas` definitions in ~30 lines of CSS; use Tailwind for columns, rows, sizing, positioning, overflow, flexbox | 0.85 | Minor: still some CSS file dependency |
| **C: p-canvas component** | Replace Shell.tsx grid with PDS `p-canvas` experimental component | 0.30 | 🧪 experimental; would require full Shell.tsx rewrite; sidebar slots may not match current data-region contracts |

**Trade-off matrix:**

| Criterion | A: Full TW | B: Hybrid | C: p-canvas |
|-----------|-----------|-----------|-------------|
| AC3 compliance (Tailwind utilities for layout) | ✅ Full | ✅ Partial (areas in CSS, layout in TW) | ⚠️ PDS component, not TW |
| Readability | ⚠️ Long class strings | ✅ Clean separation | ✅ Semantic slots |
| Test regression risk | ⚠️ Medium | ✅ Low (same DOM structure) | ❌ High (different DOM) |
| PDS alignment | ⚠️ Generic TW only | ✅ PDS tokens + TW | ✅ Full PDS |
| KISS/YAGNI | ✅ Single source | ✅ Minimal CSS | ❌ Experimental dependency |
| Existing E2E compatibility | ✅ Same selectors | ✅ Same selectors | ❌ Different DOM structure |

### 3.4 Implementation Approach (Option B)

**Shell.css reduction plan:** ~217 lines → ~40 lines

Keep in CSS: `grid-template-areas` definitions (4 breakpoints), semantic color aliases (`--pds-border-default`, `--pds-text-default`), and the `.icon-button` utility class.

Move to Tailwind classes in JSX: `display: grid`, `grid-template-columns`, `grid-template-rows`, `height`, `min-width`, `background`, `color`, `font-family`, `overflow`, `padding`, `gap`, `flex-direction`, `align-items`, `border`, `position: sticky`, `z-index`, responsive variants.

**Tailwind class mapping (desktop baseline):**

| Element | CSS property | Tailwind class |
|---------|-------------|----------------|
| `.shell` | `display: grid` | `grid` |
| `.shell` | `grid-template-columns: 56px 1fr 360px` | `grid-cols-[56px_1fr_360px]` |
| `.shell` | `grid-template-rows: auto 1fr` | `grid-rows-[auto_1fr]` |
| `.shell` | `height: 100vh` | `h-screen` |
| `.shell__status-bar` | `display: flex; align-items: center; gap: 8px` | `flex items-center gap-2` |
| `.shell__status-bar` | sticky header | `sticky top-0 z-10` |
| `.shell__workspace` | `overflow: auto; min-width: 0` | `overflow-auto min-w-0` |
| `.shell__sidecar` | `overflow: hidden; min-width: 0` | `overflow-hidden min-w-0` |

**Responsive sidebar collapse (< 1024px):**

```
lg:grid-cols-[56px_1fr_360px]  /* ≥ 1024px: full sidecar */
md:grid-cols-[56px_1fr_48px]   /* 768–1023px: icon-only sidecar */
grid-cols-[1fr]                /* < 768px: stacked mobile */
```

At < 1024px, the sidecar column becomes 48px (icon-width) and `data-sidecar-collapsed` is set automatically via a media query effect, hiding content and showing only the collapse toggle icon.

## 4. Recommendation

**Option B: Hybrid (thin Shell.css + Tailwind utilities)** — confidence: 0.85

Challenge: SKIPPED — straightforward implementation research with no contested trade-offs. The hybrid approach is the clear KISS/YAGNI winner given the existing codebase constraints.

Key reasons:
1. AC3 says "no inline `style={{}}`" — Tailwind className satisfies this while CSS `grid-template-areas` remain in a thin file
2. 670+ lines of E2E tests depend on the current DOM structure and `data-region` selectors — Option B preserves them
3. `p-canvas` is experimental (🧪) and would require rewriting Shell.tsx and all E2E tests
4. The PDS "Porsche Grid" (`grid-template` utility) is for full-viewport content pages, not application shells

## 5. Follow-up Tasks

Task #1606 itself is the implementation task — no additional follow-up tasks needed. The research findings inform the builder directly:

1. **Sticky header:** Add `sticky top-0 z-10` + ensure Playwright test scrolls the workspace element (not document body)
2. **Responsive sidebar:** CSS Grid column change at `< 1024px` breakpoint, auto-set `data-sidecar-collapsed`
3. **Tailwind migration:** Reduce Shell.css to ~40 lines (areas + aliases), move layout utilities to className
4. **Test responsibility:** #1601 was archived into #1606 — builder must ensure AC tests pass
