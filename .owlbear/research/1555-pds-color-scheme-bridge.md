# PDS v4 color-scheme Bridge Implementation

> **Owning task:** #1555 — Bridge PDS v4 color-scheme with data-theme toggle
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

PDS v4 components use CSS `color-scheme` property via `.scheme-*` utility classes. Our Cockpit sets `data-theme` on `<html>` only — PDS components never switch theme. How do we bridge `data-theme` to `color-scheme` with minimal risk?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | PDS v4 Theme docs (designsystem.porsche.com/v4/must-know/theme/) | 1.0 |
| 2 | PDS v4 Color Scheme Stylesheet docs (designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/) | 1.0 |
| 3 | `@porsche-design-system/components-react` package exports (local, package.json `"style"` field) | 0.9 |
| 4 | PDS `global-styles/color-scheme.css` (local file inspection) | 1.0 |
| 5 | PDS `global-styles/index.css` (local file inspection) | 0.8 |
| 6 | Cockpit `theme-bootstrap.js`, `useTheme.ts`, `tokens.css`, `vite.config.ts` (local) | 1.0 |
| 7 | PDS GitHub Issue #4257 — lightningcss `light-dark()` bug | 0.9 |

## 3. Analysis

### Finding 1: Import Strategy

| Option | Contents | Risk |
|--------|----------|------|
| A: `@import 'components-react'` (full global styles) | `index.css`: html/body reset, `--p-color-*` via `light-dark()`, `:root { color-scheme: light }` | Font/reset conflict with our styles; 318 lines; sets `color-scheme: light` on `:root` |
| B: `@import 'components-react/color-scheme.css'` (minimal) | `.scheme-*` utility classes + `@supports not light-dark()` polyfill only | No conflicts; ~120 lines; exactly what we need |

**Finding:** Option B is sufficient and KISS. PDS shadow DOM components inherit `color-scheme` from ancestors — they don't need `--p-color-*` host-level variables. The `.scheme-dark { color-scheme: dark }` class triggers `light-dark()` resolution in shadow DOM CSS.

### Finding 2: Lightning CSS Exclusion (Critical)

Vite 8.0.12 bundles `lightningcss ^1.32.0` as a direct dependency (default CSS transformer). PDS docs explicitly warn: lightningcss has a broken `light-dark()` polyfill that conflicts with the PDS polyfill. **Must** add to `vite.config.ts`:

```ts
import { Features } from 'lightningcss'
// in defineConfig:
css: { lightningcss: { exclude: Features.LightDark } }
```

Without this, lightningcss rewrites `light-dark()` calls incorrectly, breaking PDS component theming.

### Finding 3: Bridge Implementation Pattern

**`theme-bootstrap.js`** (sync, pre-render):
```js
// After: document.documentElement.dataset.theme = resolved
document.documentElement.classList.remove('scheme-dark', 'scheme-light')
document.documentElement.classList.add(resolved === 'dark' ? 'scheme-dark' : 'scheme-light')
```

**`useTheme.ts`** — same pattern at each `dataset.theme = resolved` site (3 locations: effect, media change handler, `applyTheme()`).

### Finding 4: Specificity/Ordering

- `color-scheme.css` defines `.scheme-dark { color-scheme: dark }` (specificity `0,1,0`)
- If `index.css` were imported, `:root { color-scheme: light }` also has `0,1,0` — order-dependent
- With Option B only, no conflict — `.scheme-dark`/`.scheme-light` are the sole `color-scheme` declarations

### Finding 5: Testing Strategy

Existing suites (`ThemeBootstrap_1545.test.ts`, `theme_1537.test.tsx`) verify `data-theme` behavior. New tests should assert:
- `theme-bootstrap.js` adds correct `.scheme-*` class on `<html>`
- `useTheme` toggles `.scheme-*` class (removes old, adds new)
- No class accumulation after multiple toggles
- CSS import exists (static analysis)

## 4. Recommendation

**Option B: Import only `color-scheme.css` + add lightningcss exclusion** (confidence: 0.90)

| Criterion | Option A (full import) | Option B (color-scheme only) |
|-----------|----------------------|------------------------------|
| Sufficiency | Over-provides (reset, fonts, variables) | Exactly sufficient |
| Risk | Font reset conflicts; specificity issues | None identified |
| KISS | No — 318 lines of mostly-unused CSS | Yes — minimal addition |
| PDS docs support | Documented as valid subset import | Documented separately at `/stylesheets/color-scheme/` |
| lightningcss fix needed | Yes | Yes |

Challenge: skipped (T1 — integration fix, no architecture decision involved)

## 5. Follow-up Tasks

1. **Implementation task** — Import `color-scheme.css`, update `theme-bootstrap.js` and `useTheme.ts` to toggle `.scheme-*` class, add lightningcss exclusion to `vite.config.ts`. Single atomic task.
2. **Vite config lightningcss exclusion** — can be bundled into the same task since it's a prerequisite.
