# Research Notes — Cockpit Visual Redesign

## Verified Findings

### VF-1: PDS v4.1.0 ships a complete CSS variable system

`@porsche-design-system/components-react` v4.1.0 provides `global-styles/index.css` which bundles:
- `variables.css` — all `--p-*` CSS custom properties
- `font-face.css` — Porsche Next font declarations (12 language variants)
- `normalize.css` — HTML/body baseline reset
- `color-scheme.css` — light/dark framework

**CSS variable categories available in `--p-*` namespace:**
- Colors (`--p-color-*`): 40+ tokens (canvas, surface, frosted, contrast levels, primary, notification states)
- Typography (`--p-typescale-*`): 2xs through 5xl (fluid/clamp-based)
- Font (`--p-font-*`): porsche-next, weights (normal/semibold/bold), leading
- Spacing (`--p-spacing-*`): fluid (xs–2xl) + static (2xs–2xl) = 14 values
- Radius (`--p-radius-*`): xs through full (2px–32px)
- Shadows (`--p-shadow-*`): sm, md, lg
- Effects: blur, easing curves, duration tokens

These are a **complete superset** of what `tokens.css` manually defines. PDS uses native CSS `light-dark()` for theme support — no manual `[data-theme="dark"]` overrides needed.

### VF-2: The current import is minimal — only `color-scheme.css`

`main.tsx` imports `@porsche-design-system/components-react/global-styles/color-scheme.css` (the optional framework file). The two **required** files (`variables.css`, `font-face.css`) and the recommended `normalize.css` are not imported.

Replacing the single color-scheme import with `global-styles/index.css` would load all four files in one import.

### VF-3: Tailwind is NOT installed and NOT required

- Zero Tailwind packages in `package.json` (dependencies or devDependencies)
- No `tailwind.config.*` or `postcss.config.*` exists
- Vite uses default LightningCSS, no PostCSS chain configured
- PDS Tailwind export exists at `@porsche-design-system/components-react/tailwindcss/index.css` but it's purely a token-remapping layer for Tailwind v4 `@theme` syntax — it maps PDS `--p-*` variables to Tailwind utility classes (e.g., `bg-canvas`, `text-contrast-high`)
- **It does not add any capability that PDS CSS variables in plain CSS do not already provide**

### VF-4: tokens.css creates a parallel shadow namespace

`tokens.css` defines 30+ `--pds-*` variables that partially overlap with PDS's `--p-*` namespace but use different names, different values, and miss key systems (typography scale, fluid spacing, font weights, transitions). Two variables (`--pds-border-subtle`, `--pds-text-subtle`) are defined nowhere. `Shell.css` adds two more semantic aliases (`--pds-border-default`, `--pds-text-default`).

The `--pds-*` namespace does not conflict with PDS's `--p-*` namespace (different names), so importing the full PDS stylesheet alongside tokens.css would not break things — but it would make the custom tokens redundant.

### VF-5: PDS light-dark() eliminates manual theme overrides

PDS v4 uses CSS native `light-dark()` in all variable definitions. The current `tokens.css` approach manually duplicates every variable in three places:
1. `:root` (light defaults)
2. `[data-theme="dark"]` (manual toggle)
3. `@media (prefers-color-scheme: dark) :root:not([data-theme])` (OS fallback)

Switching to PDS variables eliminates all three blocks. Theme switching would use PDS's built-in mechanism (the `PorscheDesignSystemProvider` already wraps the app).

## Candidate Implications

### CI-1: Root-cause-first hypothesis is strongly supported

Deleting `tokens.css` and importing `global-styles/index.css` would:
- Unify all CSS variables under the `--p-*` namespace
- Load Porsche Next font (currently missing — system fallback fonts render)
- Apply CSS normalize (currently missing — browser defaults leak)
- Give PDS components correct variable inheritance for first time
- Eliminate 90+ lines of manual dark-mode overrides

**Expected impact:** Every existing PDS component (14 used) immediately inherits correct styling. The visual score likely jumps significantly with zero other changes. The extent (challenger estimate: 40-60%) can only be verified by doing it.

### CI-2: Tailwind integration is PDS-recommended and should be adopted

The audit resolved "PDS + Tailwind" as the styling architecture. Research confirms the PDS Tailwind export exists at `@porsche-design-system/components-react/tailwindcss/index.css` and uses Tailwind v4 `@theme` syntax to remap all PDS `--p-*` variables as Tailwind utility classes.

While Tailwind is technically not *required* for token access, PDS provides this integration path for a reason — it gives layout utility classes (`flex`, `gap-md`, `bg-surface`, etc.) that are coherent with the design system. The previous brief failed by taking shortcuts around PDS recommendations. Phase 2 should plan Tailwind installation as part of the foundation work, following PDS docs.

**Note:** Early challengers argued Tailwind is "unearned." This was overridden by user directive (D4) — questioning PDS recommendations is the pattern that produced the 10/100 failure.

### CI-3: Component migration scope depends on post-foundation audit

After the PDS foundation is installed, the remaining visual debt depends on how much self-resolves. Component migration (raw `<button>` → `PButton`, etc.) will still be needed but the urgency and priority of each replacement may change. Phase 2 should plan for a re-audit checkpoint after foundation lands.

### CI-4: Builder visual feedback is a process risk, not a scope risk

First-principles challenger raised: builder agents write CSS blind. This is a real risk that no brief can solve. The mitigation is process-level: smaller batches with human visual review between each. Phase 2 should consider this in decomposition — no single task should change more than one visual surface.

## Open Research Questions

### ORQ-1: What happens to existing PDS components when tokens.css is removed?

The 14 used PDS components (PButton, PText, PTabs, etc.) currently render with tokens.css values. After removal, they'll inherit PDS's own `--p-*` values. Will this produce visual regressions on surfaces that currently look acceptable (e.g., columns, which the audit called "one of the better surfaces")? Needs testing.

### ORQ-2: Does PDS `PorscheDesignSystemProvider` handle theme switching without tokens.css?

The provider already wraps the app. Does it provide a theme-switching mechanism that works with `light-dark()`, or does the current `useTheme` hook + `data-theme` attribute approach need to be preserved?

### ORQ-3: What's the migration path for `--pds-*` references?

After tokens.css is deleted, all `--pds-*` variable references in CSS files become undefined. These need to be migrated to `--p-*` equivalents. How many references exist and what's the mapping? (Partial answer: grep shows ~50 references across Shell.css, Card.css, Column.css, FilterPanel.css, SessionRows.css, ErrorBoundary.tsx.)

### ORQ-4: How does PDS `light-dark()` interact with the existing `useTheme` hook?

The current theme system uses a `useTheme` hook that sets `data-theme` attribute. PDS v4 uses `color-scheme` CSS property via `light-dark()`. Can these coexist, or does the theme toggle mechanism need to change?
