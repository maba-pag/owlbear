# Architectural Stance — Board Visual Design CSS Architecture

## Position Summary

The proposed CSS architecture is structurally sound with five corrections. The token rename, per-component CSS extraction, data-attribute state model, and flexbox column layout are all defensible. The theme toggle mechanism needs a synchronous bootstrap script, and the token architecture must expand beyond colors.

---

## Structural Reasoning

### 1. Token Architecture: Agnostic Alias Layer (Justified)

**Rename `--pds-theme-light-*` → `--pds-*` (e.g., `--pds-background-base`).**

This IS an alias layer — the research notes correctly identify it as such. It's justified because:
- Names encoding "light" are semantically wrong when overridden for dark mode
- The rename happens once; every future consumer gets correct names
- The extraction is happening anyway (inline styles → CSS), so touching the references is unavoidable

**Token coverage must expand.** Current `tokens.css` has 17 color/state properties. The brief requires:
- **Shadow tokens** (sm, md, lg) — cards, context menu, column surfaces
- **Border-radius tokens** (xs through 4xl) — cards, columns, context menu, empty states
- **Spacing static tokens** (xs through 2xl) — padding, gaps, margins
- Typography references (PDS font family/weight/size)

Non-color tokens are theme-independent — they go in `:root` once, no dark overrides needed.

**Token generation:** PDS v4.1.0 exports individual light-suffixed and dark-suffixed tokens (`colorSurfaceLight`, `colorSurfaceDark`), NOT a `themeLight`/`themeDark` pair object for dark values. The generation script maps both variant sets to agnostic names:

```css
:root {
  --pds-background-base: /* from colorBackgroundBaseLight */;
  --pds-shadow-sm: /* from shadowSmall — theme-independent */;
  --pds-border-radius-md: /* from borderRadiusMedium — theme-independent */;
}
[data-theme="dark"] {
  --pds-background-base: /* from colorBackgroundBaseDark */;
  /* shadows, radii, spacing: no overrides needed */
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --pds-background-base: /* from colorBackgroundBaseDark */;
  }
}
```

**Scope impact:** ~20 direct references in Shell.css + inline styles (migrating anyway) + test files that assert on var names. Mechanical find-and-replace, broader than initially estimated but not architecturally complex.

### 2. Per-Component CSS with styles.ts Absorption

**6 component CSS files:** Card.css, Column.css, KanbanBoard.css, FilterPanel.css, DetailTab.css, ActivityTab.css. Plus existing Shell.css and tokens.css.

**`utils/styles.ts` must be absorbed.** The `rowStyleForState()` helper produces inline CSSProperties for blocked/rejected/stuck row states. This is a symptom of no CSS infrastructure. The helper's logic becomes CSS selectors (`[data-state="blocked"]`) in the consuming component CSS files. The helper file is then deleted.

**FilterPanel.css will be thin** — FilterPanel is mostly PDS web components (`PMultiSelect`, `PSelect`). Its CSS file handles layout only (flex container, gap, alignment). A thin file is correct; merging it elsewhere creates coupling.

**PDS web component boundary:** PDS React components are Web Component wrappers. Their internal styling is CSS-var driven and responds to the token layer automatically. No custom CSS reaches inside their shadow DOM.

### 3. State Model: Data Attributes for Dynamic State, BEM for Structure

**Structural classes (BEM):**
- `.card`, `.card__title`, `.column`, `.column__header`, `.column__body`
- `.board`, `.board__columns`, `.board__filter-bar`
- `.context-menu`, `.context-menu__item`

**Dynamic state via data attributes:**
- `data-priority="critical|needed|important|nice-to-have|someday"` — card priority color
- `data-selected="true"` — card selection highlight
- `data-drag-over="true"` — column drag target (already exists)
- `data-state="blocked|rejected|stuck"` — row health state (replaces styles.ts)
- `data-column` — column status identity (already exists)

**Existing ARIA attributes double as selectors** where appropriate (e.g., `aria-expanded` for filter panel, `aria-pressed` for activity filter). No need to duplicate with custom data attributes.

**Context menu position stays inline.** `position: fixed; top: Ypx; left: Xpx` is runtime-computed from click coordinates — this cannot be CSS-only. CSS handles all visual treatment (background, shadow, border-radius, padding).

**Specificity:** Data-attribute selectors and class selectors share identical specificity (0,1,0). Per-component CSS files eliminate cross-component specificity conflicts. No `!important`, no deep nesting needed.

### 4. Theme Toggle: Synchronous Bootstrap + Runtime Listener

**Three-layer mechanism:**

1. **Synchronous inline script in `index.html`** (before any CSS paints):
   ```html
   <script>
     (function() {
       var saved = localStorage.getItem('theme');
       if (saved === 'dark' || saved === 'light') {
         document.documentElement.setAttribute('data-theme', saved);
       } else if (matchMedia('(prefers-color-scheme: dark)').matches) {
         document.documentElement.setAttribute('data-theme', 'dark');
       }
     })();
   </script>
   ```
   Eliminates flash-of-wrong-theme (FOWT). Runs before React mount or stylesheet evaluation.

2. **`useTheme` custom hook** (React API for toggle):
   - Reads current `data-theme` attribute on mount
   - Provides `theme` value and `setTheme(mode)` function
   - `setTheme` updates `document.documentElement` attribute + `localStorage`
   - Listens to `matchMedia('(prefers-color-scheme: dark)')` change events
   - When OS theme changes and no manual override is saved, updates `data-theme` to match

3. **CSS cascade** (tokens.css):
   - `:root` — light defaults
   - `[data-theme="dark"]` — dark overrides (manual or script-set)
   - `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` — auto-dark fallback for browsers with JS disabled or before script executes

**No React Context needed.** Theme is a DOM attribute. CSS custom properties propagate through the cascade. Components never re-render on theme change — CSS handles it entirely.

**Toggle UI placement** is a UI/feature decision, not a CSS architecture concern. The architecture provides the contract (`data-theme` attribute + `useTheme` hook). Where the button lives (status bar, nav rail, settings) is decided separately.

### 5. Card Height Removal: Safe As-Is

Removing `minHeight: 48px` and `maxHeight: 56px` (per D7) is safe. Current Card DOM renders:
- Title text (variable length)
- Blocked badge (emoji, conditional)
- Running indicator (emoji, conditional)

There is no body preview, no tag rendering, no description text. Content is inherently bounded. The degenerate case (very long title) produces a taller card — this is acceptable because:
- Columns scroll independently (D8)
- Human-written kanban titles are typically 5-15 words
- A tall card doesn't break sibling column layouts

**Single CSS guard:** `overflow-wrap: break-word` on `.card__title` prevents horizontal overflow from unbroken strings.

### 6. Column Layout: Flexbox with Board-Owned Scroll

**Column structure:**
```
.column (flex-direction: column; height: 100%)
  .column__header (flex: 0 0 auto) — always visible
  .column__body (flex: 1 1 0; overflow-y: auto) — card list scrolls
```

**Scroll hierarchy resolution:** The workspace area (`shell__workspace`) has `overflow: auto`. The board fills it completely. Instead of conditionally changing the parent, the board component owns its own height:
- Board: `height: 100%; display: flex; flex-direction: column`
- Column grid: `flex: 1; min-height: 0` (enables shrink-to-fit)
- Each column: `height: 100%; display: flex; flex-direction: column`
- Card list: `flex: 1; overflow-y: auto; min-height: 0`

This works because CSS Grid + flex with `min-height: 0` propagates the height constraint down to the card-list scroll container without modifying the workspace parent.

**Column minimum width:** The current `minmax(80px, 1fr)` produces unreadable columns below ~180px. Recommend increasing the floor, but this is a UX tuning decision, not a structural concern. The flex-column scroll pattern works at any width.

---

## Key Trade-offs

| Decision | Trade-off | Accepted Because |
|----------|-----------|-----------------|
| Alias layer (token rename) | ~20+ reference renames including tests | Names are wrong; rename happens during extraction anyway |
| Per-component CSS (no shared file) | Possible duplication of common patterns | 6 components is too few for premature consolidation; BEM + tokens provide consistency |
| Data attributes for state | Slightly more verbose than class toggling | Self-documenting, already partially adopted, identical specificity |
| Synchronous bootstrap script | Inline JS in HTML (non-module) | Only reliable FOWT prevention; 6 lines, no framework dependency |
| No React Context for theme | Toggle consumers must use hook directly | Theme is DOM-level, not React state; zero re-renders on change |
| Unbounded card height | Tall cards from long titles | Acceptable: columns scroll independently, titles are human-written |

---

## Warnings

1. **Token generation script must be updated and documented.** The current comment references a `themeLight` extraction one-liner. The new script must extract light-suffixed, dark-suffixed, and non-color tokens from PDS v4.1.0 exports and map them to agnostic names. If this script is wrong, every token is wrong.

2. **Test suite references light-suffixed names.** At least 3 test files assert on `--pds-theme-light-*` var names. The rename is mechanical but the surface is broader than source CSS alone.

3. **PDS web component theming is implicit.** PDS components respond to CSS custom properties set by `PorscheDesignSystemProvider`. Verify that PDS components respect `data-theme` attribute changes, or whether the provider needs explicit theme prop updates. If PDS has its own theme mechanism, the token layer must align.

4. **Context menu position remains JS-coupled.** Visual treatment (shadow, radius, background) moves to CSS, but `top`/`left` coordinates stay as inline styles. This is correct but means the context menu is the one component where inline styles are intentionally preserved.

5. **Shell.css must also be updated.** It references `--pds-theme-light-*` vars directly. The rename scope includes Shell.css — not just the 6 new component CSS files.

---

## Confidence

**0.78** — High confidence on token architecture, per-component CSS, and theme bootstrap pattern. Moderate confidence on scroll hierarchy (nested scroll containers in CSS Grid are fragile and need empirical testing). The two Critic cycles surfaced and resolved five genuine gaps: token generation mechanism, FOWT bootstrap, styles.ts migration, card DOM reality check, and runtime theme listener.
