# Architect Stance — Cockpit Visual Redesign

## Architectural Stance

The approach is structurally sound with one significant correction, two prerequisite additions, and a theme-contract resolution.

**Correction: Use `@tailwindcss/vite`, not `@tailwindcss/postcss`.**
The Vite config explicitly uses LightningCSS with `css.lightningcss.exclude: Features.LightDark` — this prevents LightningCSS from lowering `light-dark()` calls, which PDS v4 depends on. Adding PostCSS would replace LightningCSS as the CSS processor, potentially breaking this preservation. Tailwind v4 ships `@tailwindcss/vite` — a dedicated Vite plugin that coexists with LightningCSS. Tailwind's engine handles `@theme`/`@import`/utility generation; LightningCSS handles final transforms and minification. The `light-dark()` exclusion remains in effect. No PostCSS config file needed.

Stylelint config must also be updated to allow Tailwind at-rules (`@theme`, `@import "tailwindcss"`). Pipeline reconfiguration is minimal but not zero.

**Prerequisite 1: Complete token provenance map before migration.**
The draft framing implied "one app-specific token (`--signal-claimed`)." That's wrong. Shell.css defines semantic aliases, Card.css has additional semantic-looking vars, and some referenced variables (`--pds-border-subtle`, `--pds-text-subtle`) are defined nowhere. Four-way classification required:
- (a) Has `--p-*` equivalent → migrate to `--p-*` or Tailwind utility
- (b) App-semantic with no PDS equivalent → move to `--app-*` in `custom-tokens.css`
- (c) Broken/undefined (never resolved to a value) → delete, provide proper replacement
- (d) Dead (defined but unreferenced) → delete

This inventory is a prerequisite for the migration task's acceptance criteria.

**Prerequisite 2: Bootstrap readiness contract must be corrected.**
`REQUIRED_PDS_ELEMENTS` in main.tsx lists 4 elements (`p-button`, `p-icon`, `p-tabs`, `p-tabs-item`). The actual PDS surface includes banners, checkboxes, selects, textareas, spinners, and sheets. The readiness list is already false. Foundation task must update it to match the actual PDS custom-element surface used in the codebase.

**Theme contract is settled, not open.**
Research flagged theme coexistence as an open question (ORQ-4). It's resolved:
- `useTheme` hook sets `.scheme-dark`/`.scheme-light` classes — PDS reads these directly
- `useTheme` also sets `data-theme` attribute — only consumed by `tokens.css` manual overrides
- After `tokens.css` deletion, `data-theme` becomes vestigial but harmless
- PDS `light-dark()` resolves via browser `color-scheme` property (set by PDS `color-scheme.css`)
- `theme-bootstrap.js` prevents FOUC — preserved as-is
- Theme switching works without changes because the hook already provides what PDS needs
- Architectural tests need updating to reflect the new token source, not new theme mechanics

## Structural Reasoning

### 1. Decomposition Order (Dependencies)

```
Tier 0   Foundation (additive, safe)
   │      Import global-styles/index.css, update REQUIRED_PDS_ELEMENTS
   ▼
Tier 0.5 Tooling (additive, safe)
   │      Install @tailwindcss/vite, update Stylelint config
   ▼
Tier 1   Token Migration (breaking, atomic)
   │      Delete tokens.css, migrate ~50 refs, create custom-tokens.css,
   │      update architectural tests, update main.tsx imports
   ▼
   ├── [HUMAN CHECKPOINT: visual re-audit]
   ▼
Tier 2a  Component Migration — simple swaps (parallel)
   │      Buttons → PButton, Headings → PHeading, etc.
   │
Tier 2b  Component Migration — complex integrations (serial)
   │      Shell tabs, FilterPanel controls, overlay architecture
   │
Tier 3   Layout (parallel with Tier 2)
   │      Scope determined by post-Tier-1 re-audit
   ▼
Tier 4   Polish (depends on all above)
          Typography, spacing, dark-mode contrast
```

**Why Tailwind before migration:** Not for churn savings (most existing `--pds-*` refs are in selector-driven CSS and stay as `var(--p-*)`). For authoring pattern: new CSS written in Tiers 2-4 should use utilities (`bg-surface`, `gap-md`) from the start, not `var(--p-color-background-base)` that gets migrated later.

**Why migration is one atomic task:** An unmigrated `--pds-*` reference resolves to nothing after `tokens.css` deletion. You cannot split "delete tokens" and "migrate references" across tasks. One task: delete + migrate + custom-tokens + test updates + import changes.

### 2. Vite Integration Architecture

```
┌─ vite.config.ts ─────────────────────────────┐
│ plugins: [                                    │
│   react(),                                    │
│   babel({ presets: [reactCompilerPreset()] }),│
│   tailwindcss(),          ← NEW              │
│   pdsVersionCheckPlugin(),                    │
│   cspPlugin(),                                │
│ ]                                             │
│ css.lightningcss.exclude: Features.LightDark  │  ← PRESERVED
└───────────────────────────────────────────────┘
```

Tailwind's Vite plugin processes CSS through its own engine (Oxide). LightningCSS handles final transforms. Both coexist — no conflict because they operate at different pipeline stages. The critical `Features.LightDark` exclusion stays intact at the LightningCSS layer.

### 3. `custom-tokens.css` Structure

```css
/*
 * App-specific tokens — values with NO PDS equivalent.
 *
 * Rules:
 * 1. --app-* prefix only (never --p-* or --pds-*)
 * 2. Reference --p-* variables as values where possible
 * 3. Use light-dark() for theme (no manual [data-theme] overrides)
 * 4. If this file exceeds ~5 entries, audit for PDS equivalents
 */
:root {
  --app-signal-claimed: light-dark(hsl(270 58% 46%), hsl(270 80% 70%));
  /* additional app-semantic tokens TBD by provenance map */
}
```

The count and names of additional entries depend on the token provenance map. The structural contract is: `--app-*` prefix, `light-dark()` for theme, reference `--p-*` values where possible, and a hard cap on growth.

### 4. Component Migration Axes

Not all component swaps are equal. The decomposition axis is **behavioral complexity**:

**Simple swaps (task-per-component-type):** Raw `<button>` → `PButton`, raw headings → `PHeading`/`PText`, raw `<select>` → `PSelect` — where the element is purely presentational with standard event handling.

**Complex integrations (task-per-integration):** Shell tabs (custom `tabChange` event wiring, raw `p-tabs`/`p-sheet`), FilterPanel (manual update/input/change listeners, raw `p-checkbox`), overlays (hand-rolled fixed-position overlays → PDS overlay components). Each carries behavioral risk and test harness dependencies (jsdom shims, property-vs-attribute assertions).

**Overlay track (distinct from component swaps):** Hand-rolled modals, popovers, context menus, and dialogs form a separate architectural concern. These share positioning, z-index, and dismiss-behavior patterns that should be migrated cohesively, not per-file.

Full component inventory with complexity classification is a prerequisite for task planning.

## Key Trade-offs

1. **Tailwind adds tooling complexity for authoring convenience.** D4 resolves this — PDS recommends Tailwind, we follow PDS. The cost is a build dependency; the gain is a utility vocabulary coherent with the design system.

2. **Atomic token migration is high-risk but unavoidable.** ~50 references across 7 files in one commit. Mitigation: complete provenance map beforehand (no surprises), human checkpoint immediately after.

3. **Foundation-first means temporary visual oddity.** After Tier 0, PDS variables exist alongside `tokens.css` variables. Both resolve. The visual state may be inconsistent (PDS components inherit different values than custom CSS). This is brief and resolved by Tier 1.

4. **Component inventory delays execution but prevents the old failure mode.** The previous brief failed by underestimating the integration surface. Spending one task on inventory before starting swaps is insurance.

## Warnings

1. **Do NOT add PostCSS.** `@tailwindcss/vite` is the correct integration. PostCSS replaces LightningCSS and risks breaking `light-dark()` preservation.

2. **Do NOT create a mapping layer between `--pds-*` and `--p-*`.** The migration is find-replace, not abstraction. Mapping layers are how tokens.css happened.

3. **Do NOT scope tokens.css deletion and reference migration as separate tasks.** They are atomic. An unmigrated reference is a broken reference.

4. **Do NOT defer bootstrap readiness.** The `REQUIRED_PDS_ELEMENTS` list is already wrong. Fix it as part of foundation work.

5. **Do NOT assume all component swaps are simple.** Test harness dependencies (jsdom shims, `attachInternals`, property assertions) make some swaps integration tasks. Inventory before decomposition.

## Confidence

**0.78**

High confidence in: Vite integration path (`@tailwindcss/vite` over PostCSS), theme contract resolution, decomposition order and dependency chain, token migration atomicity requirement, `custom-tokens.css` structural contract.

Moderate confidence in: Component migration granularity (inventory-dependent, can't fully assess without it), exact scope of Tier 3 layout work (depends on post-foundation re-audit), `@tailwindcss/vite` + LightningCSS `light-dark()` coexistence (needs smoke test — clean fallback exists if it fails).
