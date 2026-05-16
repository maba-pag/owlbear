# Brief — Cockpit Visual Redesign

## Summary

Refactor the cockpit frontend from its current 10/100 visual state to a PDS v4-native application by installing the missing foundation, adopting the PDS-recommended Tailwind integration, migrating the shadow token namespace, replacing raw HTML elements with PDS React components, and applying layout/polish fixes. Four batches execute continuously without inter-batch checkpoints.

## Problem

The cockpit's visual deficit is one defect expressed everywhere: the PDS foundation was never installed. A hand-rolled `tokens.css` with non-standard `--pds-*` prefix partially duplicates PDS but misses key systems. Two variables resolve to nothing. Only 14/73 PDS React components are used. Raw HTML elements, inline styles, and manual dark-mode overrides fill the gap. The board wraps instead of scrolling. The sidecar has zero padding. Cards show minimal metadata.

A comprehensive audit catalogues 73+ findings across 16 sections (`.owlbear/research/cockpit-visual-audit-comprehensive.md`).

## Approach

### Batch 0 — Foundation

Install the PDS design system foundation that all subsequent work depends on.

| Task | Detail |
|------|--------|
| Import `global-styles/index.css` | Replace single `color-scheme.css` import in `main.tsx` with the full bundle (variables, font-face, normalize, color-scheme) |
| Relax CSP for PDS fonts | Add `font-src 'self' https://cdn.ui.porsche.com` to the CSP meta tag in the Vite HTML plugin (D6) |
| Install `@tailwindcss/vite` | Add `@tailwindcss/vite ^4` as Vite plugin (NOT PostCSS — preserves LightningCSS). Import PDS Tailwind theme from `@porsche-design-system/components-react/tailwindcss/index.css`. Pin `tailwindcss ^4` + `@tailwindcss/vite ^4`. |
| Configure Stylelint | Update Stylelint config for Tailwind v4 `@theme` / `@utility` at-rules |
| Board horizontal scroll | Change grid template from `auto-fit` wrapping to fixed-column layout with `overflow-x: auto`. The container already has overflow set; the grid's `minmax(200px, 1fr)` causes wrapping. |

**Acceptance criteria:**

*global-styles import:*
- `--p-color-canvas`, `--p-spacing-md`, `--p-font-family` resolve to non-empty values in any component's computed styles
- `document.fonts.check('1em "Porsche Next"')` returns true (font loaded, not system fallback)
- No console warnings from PDS provider about missing stylesheets

*CSP relaxation:*
- Network tab shows successful font file loads from `cdn.ui.porsche.com` (HTTP 200, not blocked)
- CSP meta tag contains `font-src 'self' https://cdn.ui.porsche.com`

*Tailwind install:*
- `bg-canvas`, `text-contrast-high`, `gap-md`, `rounded-sm` compile without error in `vite build`
- `@theme` block from PDS export is processable by `@tailwindcss/vite` (build succeeds)
- No PostCSS config exists; LightningCSS remains the CSS transformer
- `package.json` shows `tailwindcss ^4` and `@tailwindcss/vite ^4`

*Stylelint:*
- `npm run lint:css` passes with zero violations on `@theme`, `@utility`, `@apply` at-rules

*Board scroll:*
- With 6+ columns, board container scrolls horizontally (Playwright assertion: `scrollWidth > clientWidth`)
- Columns maintain fixed minimum width instead of shrinking to fit viewport

*Cross-cutting:*
- All existing Vitest suites pass (`npm test`)
- All existing Playwright e2e suites pass (`npm run test:e2e`)
- `light-dark()` CSS functions are preserved in output (not compiled away by Tailwind)

### Batch 1 — Token Migration + Layout

Atomic token migration plus structural layout work.

| Task | Detail |
|------|--------|
| Token provenance map | Four-way classify every `--pds-*` reference: direct PDS equivalent, Tailwind utility replacement, custom-token (keep), dead reference (delete) |
| Delete `tokens.css` + migrate | Single atomic task: delete file, update all `--pds-*` → `--p-*` or Tailwind utility, create `custom-tokens.css` for any truly custom values. All dark-mode manual overrides removed. **Includes updating/retiring all tests that assert `tokens.css` structure or `--pds-*` variable names** (TokenArchitecture, BoardVisualDesign, PdsColorSchemeBridge, PdsMigration, ShellSecondaryCSS test files). |
| Formatting utilities | `utils/format.ts` with null-safe formatters. Canonical/display value partition enforced — formatted values never feed mutation APIs (C8). Config-driven enum vocabularies (C7). |
| Extend `computeSignal` | Add "unknown" state for malformed/missing inputs |
| Shell layout | Sticky header, sidebar responsive collapse, CSS grid structure via Tailwind utilities |
| Sidecar structure | Internal padding, section dividers, typography hierarchy |

**Acceptance criteria:**

*Token provenance map:*
- Document exists classifying every `--pds-*` usage into: PDS equivalent, Tailwind utility, custom-keep, or dead-delete
- All ~50 `--pds-*` references accounted for (Shell.css, Card.css, Column.css, FilterPanel.css, SessionRows.css, ErrorBoundary.tsx)

*Token migration (atomic):*
- `grep -r '\-\-pds-' serve/cockpit/web/src/` returns zero matches (CSS and TSX)
- `tokens.css` no longer exists in the repository
- `custom-tokens.css` exists only if provenance map identified truly custom values (not PDS equivalents)
- All `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)` manual override blocks removed from authored CSS
- All 14 existing PDS components render correctly in both light and dark themes (Playwright screenshot comparison)
- Tests formerly asserting `--pds-*` names updated to assert `--p-*` equivalents or retired with documented rationale
- Light/dark toggle via `useTheme` hook still functions (`.scheme-dark`/`.scheme-light` classes trigger PDS `light-dark()` cascade)

*Formatting utilities:*
- `utils/format.ts` exports null-safe formatters for: relative time, priority label, status label, signal description
- Unit tests prove: `format*(null)` returns defined fallback, `format*(undefined)` returns defined fallback
- No formatter output appears in any `fetch()` / mutation call path (static analysis or test assertion)
- Enum values sourced from board API config response, not hardcoded arrays

*computeSignal:*
- `computeSignal(null)` and `computeSignal({})` return `"unknown"` state
- Existing 5-state behavior unchanged for valid inputs (unit tests)

*Shell layout:*
- Header remains visible at scroll position > viewport height (Playwright: `isVisible()` after scroll)
- Sidebar collapses to icon-only state at viewport width < 1024px
- Shell uses CSS Grid or Flexbox via Tailwind utilities (no inline `style` for layout)

*Sidecar structure:*
- Sidecar content has `--p-spacing-md` or greater padding on all sides
- At least 3 visually distinct sections with PDS typography scale differentiation (heading sizes differ)
- Section dividers visible between content blocks

### Batch 2 — Component Migration

Replace raw HTML with PDS React components. Informed by complexity inventory.

| Task | Detail |
|------|--------|
| Component complexity inventory | Classify all remaining raw elements: simple swap vs. complex integration. Planning artifact that unblocks parallel work. |
| Simple swaps | `<button>` → `PButton`, `<h1-h6>` → `PHeading`/`PText`, `<select>` → `PSelect`, `<ul>` → `PTag`/`PText` list, raw web-components → React wrappers. **Preserve intentional native controls** where tests assert specific DOM contracts (e.g., sidecar collapse button, theme toggle). |
| Card visual treatment | Status chip (`PTag`), priority color indicator, signal icon, tag pills, metadata density increase |
| Sidecar information architecture | Section ordering, action prominence, content layout, accordion structure |
| Filter panel controls | PDS form components for filter inputs, horizontal bar or collapsible layout |
| Complex integrations | Shell tabs (if not PDS `PTabs` already), overlays: custom modals → `PModal`, context menus |

**Acceptance criteria:**

*Component inventory:*
- Document classifying every raw interactive/display element as: simple swap, complex integration, or intentional native (with rationale)
- Produces dependency graph showing which swaps can proceed in parallel

*Simple swaps:*
- `grep -r '<select' serve/cockpit/web/src/` returns zero matches outside test files
- All `<p-button>`, `<p-icon>`, etc. web-component elements replaced with React wrapper equivalents (`PButton`, `PIcon`)
- Raw `<button>` elements remain ONLY where documented as intentional native (e.g., sidecar collapse, theme toggle) — list maintained in inventory doc
- Raw `<h1>`–`<h6>` replaced with `PHeading` or `PText` where semantically appropriate

*Card visual treatment:*
- Each card renders: title, status chip (PTag with color variant), priority indicator (icon or color), signal icon, tag pills, relative timestamp
- Card metadata visible without expanding/hovering (scannable at board level)
- Priority and status use PDS color tokens (not hardcoded hex)

*Sidecar information architecture:*
- Sections ordered by usage frequency (actions prominent, metadata lower)
- Accordion or collapsible sections for low-frequency content
- Section headings use PDS typography scale (visually distinct hierarchy)

*Filter panel:*
- All filter inputs use PDS form components (`PSelect`, `PTextFieldWrapper`, `PCheckboxWrapper` as appropriate)
- Filter panel has coherent layout (horizontal bar or collapsible sidebar — decided at task time)

*Complex integrations:*
- All custom modal implementations replaced with `PModal` (ConfirmDialog, ResolveModal, ArchivalModal)
- Focus trapping and focus return behavior preserved post-migration (Playwright keyboard test)
- Overlay dismiss on backdrop click and Escape key functional

*Cross-cutting:*
- Inline `style={{}}` count ≤ 3 (justified exceptions documented)
- All existing Vitest + Playwright suites pass
- No accessibility regressions (existing ARIA attributes preserved)

### Batch 3 — Polish + Accessibility

Final quality pass across the entire surface.

| Task | Detail |
|------|--------|
| Success feedback | `PToast` for move/mutation success, inline confirmation for edits |
| Dark mode audit | Border contrast, surface differentiation, ensure all tokens use `light-dark()` correctly |
| Focus-visible rings | PDS focus styling on all interactive elements |
| Motion/transitions | PDS duration/easing tokens for state changes (expand/collapse, route transitions) |

| Accessibility sweep | Keyboard navigation, ARIA labels on custom controls, color contrast verification |

**Acceptance criteria:**

*Success feedback:*
- Task move triggers visible PToast notification (Playwright: toast element appears within 500ms)
- Inline edit save shows confirmation state (visual change on the edited element)
- Error states still display distinct error feedback (no regression)

*Dark mode audit:*
- In `.scheme-dark`, adjacent surface panels have visually distinct borders (contrast ratio ≥ 1.3:1 between surfaces)
- No `border-color` values hardcoded in CSS — all use PDS color tokens
- Screenshot comparison between light and dark shows intentional differentiation (not just inverted)

*Focus-visible:*
- Tab through all interactive elements: each shows visible focus ring (Playwright: `outline` or `box-shadow` computed style is non-none on `:focus-visible`)
- Focus rings use PDS focus tokens (not custom ring styles)

*Motion/transitions:*
- Expand/collapse animations use `--p-transition-duration` and `--p-transition-timing-function` tokens
- No `transition: all` declarations in authored CSS (grep verification)
- Route transitions are smooth (no flash of unstyled content)

*Accessibility sweep:*
- axe-core automated scan via Playwright reports zero violations at WCAG 2.1 AA level
- All interactive elements have accessible names (no empty `aria-label` or missing labels)
- Color contrast meets 4.5:1 for normal text, 3:1 for large text (automated check)
- Keyboard navigation reaches all interactive elements without traps

## Key Constraints

1. **`@tailwindcss/vite` only, never PostCSS** — preserves LightningCSS `light-dark()` processing (C3)
2. **Token migration is atomic** — cannot split delete/migrate/custom-tokens across tasks (C4)
3. **Canonical/display partition** — formatted display values never feed mutation APIs (C8)
4. **Enum vocabularies are config-driven** — statuses and priorities come from board API, not hardcoded arrays (C7)
5. **No new product features** — grouping, search, notes tab, DnD styling have their own briefs. Interaction quality improvements (toast feedback, sticky header) ARE in scope as visual redesign work.
6. **Desktop-only** — no NEW responsive/mobile work (audit decision gate #4). Existing mobile code paths in Shell (viewport detection, `p-sheet` mobile rendering, media queries) are preserved as-is.
7. **PDS documentation governs** — when uncertain, follow PDS v4 docs over custom approaches (D4)
8. **Accessibility is cross-cutting** — existing ARIA attributes, focus management, and keyboard navigation must be preserved or improved in every batch, not deferred to Batch 3. The Batch 3 sweep is verification, not implementation.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `@tailwindcss/vite` + LightningCSS `light-dark()` incompatibility | Low | High — requires re-planning Tailwind integration | Smoke test in Batch 0 first task; fallback: plain CSS with PDS variables only |
| Token migration misses references | Medium | Medium — broken styles in specific views | Grep-based verification in AC; provenance map is exhaustive by design |
| PDS component API changes between install and use | Low | Low — pinned version | Lock `@porsche-design-system/components-react` version in Batch 0 |
| Builder agents write CSS blind | Medium | Medium — visual regressions | Playwright screenshot tests established in Batch 0; builder tasks include screenshot verification |
| 73 findings inflate task count | Medium | Low — some self-resolve | Continuous execution without checkpoint; self-resolved items become no-op tasks |
| Source-inspecting tests break during token migration | High | Medium — CI red until tests updated | Token migration task explicitly includes test updates; provenance map identifies affected test files |
| PDS test-environment shims fragile | Medium | Medium — Vitest failures on PDS component rendering | `vitest.setup.ts` already suppresses CDN/ownerDocument/attachInternals; verify shims survive `global-styles` import |

## Out of Scope

- Backend/API changes
- New features (grouping, search, notes, DnD)
- NEW responsive/mobile layouts (existing mobile paths preserved)
- Performance optimization
- Screenshot regression baseline infrastructure (use Playwright directly)
- Self-hosted fonts (CDN allowed per D6)

## Decisions Trail

- **D4:** Follow PDS v4 recommendations strictly including Tailwind
- **D6:** Relax CSP for Porsche CDN fonts (not self-host)
- **D7:** No inter-batch checkpoint; plan and execute continuously

## Supersedes

`draft-board-visual-design/` — earlier, narrower framing that produced the current 10/100 state.
