# Frontend Scaffold Feasibility — Vite + React 19 + TS + Porsche DS

> **Owning task:** #925 — P2-01: Frontend scaffold (Vite + React 19 + TS + Porsche DS)
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Can the specified stack (React 19 + Vite + TypeScript + Porsche DS React wrapper) be scaffolded at `serve/cockpit/web/` with Vitest component testing? What are the setup specifics, gotchas, and token extraction approach?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS React wrapper npm | npmjs.com/package/@porsche-design-system/components-react | Peer deps, exports map, version (0.95) |
| S2 | PDS React getting-started | designsystem.porsche.com/v3/developing/react/getting-started | Vite integration, partials plugin, Tailwind theme (0.95) |
| S3 | PDS React testing docs | designsystem.porsche.com/v3/developing/react/testing | jsdom polyfill, componentsReady, shadow DOM queries (0.90) |
| S4 | PDS License (GitHub) | github.com/porsche-design-system/.../LICENSE.md | Dual license: Apache 2.0 source + custom assets (0.85) |
| S5 | PDS Theme styles docs | designsystem.porsche.com/v3/styles/theme | Token exports: JS, SCSS, Tailwind CSS theme (0.80) |
| S6 | Vite guide | vite.dev/guide | `react-ts` template, Node 20.19+ required (0.70) |
| S7 | Vitest guide | vitest.dev/guide | Reads vite.config by default, jsdom env (0.70) |
| S8 | PDS package.json | unpkg.com/@porsche-design-system/components-react@3.34.0/package.json | Full peer deps and exports map (0.90) |

## 3. Analysis

### 3.1 Compatibility Verification

| Concern | Finding | Status |
|---------|---------|--------|
| React 19 peer dep | PDS 3.34.0: `"react": ">=19.0.0 <20.0.0"` | **Confirmed** |
| Vite support | PDS docs use Vite 7 + `react-ts` template | **Confirmed** |
| TypeScript | PDS ships `.d.ts` types; `esm/public-api.d.ts` | **Confirmed** |
| Vitest compat | PDS jsdom-polyfill works in any jsdom env (Jest or Vitest) | **Confirmed** |
| Single dependency | PDS React wraps `@porsche-design-system/components-js` (1 dep) | **Confirmed** |

### 3.2 License Assessment

PDS uses a **dual license**:
- **Source code** (components, JS/TS): Apache 2.0 — unrestricted
- **Design assets** (fonts, icons, Porsche marque): Custom restrictive license

External apps are permitted if "dissimilar and visually distinct from Porsche products." A kanban cockpit is clearly dissimilar. The restriction on modifying/redistributing design assets applies to the fonts/icons/marque, not the component logic. **Risk: LOW** for OwlBear's use case.

### 3.3 Token Strategy

| Option | Approach | Pros | Cons | Score |
|--------|----------|------|------|-------|
| **A. CSS custom props file** | Create `tokens.css` mapping PDS values to `--pds-*` vars | Framework-agnostic, works with PDS or Radix fallback, matches AC | Manual sync on PDS version bumps | **0.80** |
| B. PDS SCSS imports | `@use '...components-react/styles'` | Official PDS path, auto-synced | Adds SCSS to Vite pipeline | 0.70 |
| C. PDS Tailwind theme | `@import '...components-react/tailwindcss'` | PDS-recommended, utility-first | Adds Tailwind upfront (it's the D14 fallback, not primary) | 0.60 |
| D. JS token imports | `import { themeLight* } from '.../styles'` | Type-safe, tree-shakeable | Inline styles, verbose | 0.55 |

**Recommendation: Option A.** The AC explicitly asks for `tokens.css`. Create CSS custom properties from PDS JS token exports. This is DS-agnostic — if the D14 fallback triggers (Radix + Tailwind), the same `tokens.css` still works. PDS JS exports provide exact hex/rgb values at build time.

### 3.4 Testing Setup Specifics

| Item | Approach |
|------|----------|
| Test runner | Vitest (reads vite.config by default) |
| DOM environment | jsdom via `environment: 'jsdom'` in vitest config |
| PDS polyfill | `import '@porsche-design-system/components-react/jsdom-polyfill'` in setup file |
| CDN suppression | `skipPorscheDesignSystemCDNRequestsDuringTests()` in setup |
| Provider wrapper | Custom `renderWithProvider()` helper wrapping `PorscheDesignSystemProvider` |
| Component readiness | `await componentsReady()` after render in async tests |
| Shadow DOM queries | PDS `/testing` export: `getByRoleShadowed`, `getByTextShadowed` |
| Dialog/Internals mocks | `vi.fn()` mocks for `HTMLDialogElement` and `attachInternals` (Vitest, not Jest) |

### 3.5 Build Configuration

| Config | Value | Notes |
|--------|-------|-------|
| Vite `build.outDir` | `../dist` (relative from `web/`) | Outputs to `serve/cockpit/dist/` per AC |
| PDS partials plugin | `transformIndexHtml` in vite.config.ts | Preloads fonts, icons, component chunks |
| TypeScript | `strict: true` in tsconfig.json | Per AC |
| CDN | PDS loads fonts/icons from CDN at runtime | Cockpit needs internet on first load |

### 3.6 Directory Naming

Architect voice doc uses `frontend/`; task AC uses `web/`. **Task AC takes precedence** — use `serve/cockpit/web/`.

## 4. Recommendation

**Proceed with scaffold as specified.** Confidence: **0.85**.

All stack components are confirmed compatible. PDS 3.34.0 explicitly targets React 19 + Vite. Token extraction via Option A satisfies the AC. Testing setup requires PDS-specific jsdom polyfill and provider wrapper, both well-documented.

Challenge: N/A — this is a compatibility verification, not an architectural choice. The Brief (D14) already made the stack decision; research confirms feasibility.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #925 itself proceeds to backlog with implementation specifics documented above. Key implementation notes for the builder:

1. Start from `npm create vite@latest -- --template react-ts`
2. PDS testing docs use `jest.fn()` — replace with `vi.fn()` for Vitest
3. PDS `getByRoleShadowed` etc. from `/testing` export for shadow DOM
4. `tokens.css` should map PDS JS token values to CSS custom properties
5. Vite partials plugin prevents FOUC/FOUT — include from day 1
