---
id: 1555
title: Bridge PDS v4 color-scheme with data-theme toggle
status: backlog
priority: important
created: 2026-05-14T05:57:42.186424+00:00
updated: 2026-05-14T09:06:43.912182+00:00
tags:
  - phase-4
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1553
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

PDS v4 web components do NOT respond to `data-theme` attribute — they use CSS `color-scheme` property via `.scheme-*` utility classes. Our Cockpit currently only sets `data-theme` on `<html>`, leaving PDS components permanently in light mode during dark theme.

Research ref: #1553

## Objectives

1. Import PDS v4 `color-scheme.css` so `.scheme-*` utility classes and `light-dark()` polyfill are available
2. Add lightningcss `LightDark` feature exclusion in `vite.config.ts` (Vite 8's built-in lightningcss breaks PDS `light-dark()` polyfill)
3. Update `theme-bootstrap.js` to also add `.scheme-dark`/`.scheme-light` class on `<html>` alongside `data-theme`
4. Update `useTheme.ts` to add/remove `.scheme-dark`/`.scheme-light` class when theme changes (keep `data-theme` for non-PDS styling)
5. Verify PDS components switch correctly between light and dark

## Acceptance Criteria

- [ ] AC-1: `main.tsx` imports `@porsche-design-system/components-react/global-styles/color-scheme.css` (provides `.scheme-*` utility classes and `light-dark()` polyfill). Verification: static import present in source.
- [ ] AC-2: `vite.config.ts` includes `css.lightningcss.exclude` with `Features.LightDark` (prevents lightningcss from rewriting PDS `light-dark()` polyfill). Verification: config assertion in unit test or static inspection.
- [ ] AC-3: `theme-bootstrap.js` sets `.scheme-dark` or `.scheme-light` class on `document.documentElement` alongside `data-theme` at page load (matching resolved theme value). Verification: unit test asserting classList after bootstrap execution.
- [ ] AC-4: All 3 `dataset.theme` mutation sites in `useTheme.ts` (line ~58 effect, line ~72 media-change handler, `applyTheme()` at line ~26) also toggle `.scheme-dark`/`.scheme-light` class on `document.documentElement`; the previous `.scheme-*` class is always removed before the new one is added (no class accumulation after repeated toggles). Verification: unit tests per mutation site asserting classList state.
- [ ] AC-5: Playwright e2e test confirms at least one PDS shadow-DOM component (e.g. `p-button`) renders with dark-mode color values when `.scheme-dark` is active on `<html>`. Verification: e2e assertion on computed style or screenshot comparison.
- [ ] AC-6: Existing theme tests (`theme_1537.test.tsx`, `ThemeBootstrap_1545.test.ts`) continue to pass without modification. Verification: test suite green.
- [ ] AC-7: No app-authored `color-scheme` CSS property declarations exist outside the imported PDS vendor stylesheet (prevents specificity conflicts with `.scheme-*` classes). Verification: grep/lint assertion across `src/**/*.css`.

Proof bundle: behavioral

## Research

- Research doc: `.owlbear/research/1555-pds-color-scheme-bridge.md`
- Sources: 7 studied, 6 high-relevance (see `.owlbear/sources/overview.md`)
- Key finding: Import only `color-scheme.css` (not full `index.css`) — minimal, no reset conflicts
- Critical finding: Vite 8 bundles lightningcss which has a broken `light-dark()` polyfill; must add `css.lightningcss.exclude: Features.LightDark` to `vite.config.ts`
- Implementation: 4 files need changes: `color-scheme.css` import in `main.tsx`, class toggle in `theme-bootstrap.js` and `useTheme.ts` (3 sites), lightningcss exclusion in `vite.config.ts`
- Recommendation: Option B (import `color-scheme.css` only) — confidence: 0.90
- Tier: T1 (integration fix, config tweak)
2026-05-14T07:21:51+00:00
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Bridge PDS color-scheme with existing data-theme toggle — one concern |
| Interface clarity | PASS | AC specifies exact file, import path, mutation sites, and verification method per line |
| Dependency correctness | PASS | #1553 archived/completed ✓; added #1555 as dep to consolidation task #1554 |
| Module layering | N/A | Frontend — no import direction concerns for CSS/theme utilities |
| TDD compliance | PASS | Proof bundle `behavioral` — test-writer will produce failing tests for all mutation sites |
| KISS/YAGNI | PASS | Minimal scope: 4 files, exact CSS import, no new abstractions |
| Premise challenge | PASS | Research #1553 proved PDS v4 doesn't respond to `data-theme`; bridge is required |
| Pattern consistency | PASS | Extends existing `theme-bootstrap.js` IIFE + `useTheme.ts` hook pattern |
| Security surface | N/A | No new system boundaries; CSS class toggling only |
| Single domain | PASS | Cockpit frontend theming — all 4 files serve same domain |

### Challenge Results

- Challenger: reconsider (confidence 0.61)
- Findings addressed:
  - AC-6 vagueness → REFINED: replaced "visual verification or snapshot" with Playwright e2e assertion on computed style (now AC-5)
  - AC-8 self-conflict → REFINED: scoped to "app-authored" declarations only, excluding vendor stylesheet (now AC-7)
  - AC-1 missing path → REFINED: added exact import path `@porsche-design-system/components-react/global-styles/color-scheme.css`
  - AC-4/5 overlap → MERGED: combined toggle + no-accumulation into single AC-4 with explicit mutation-site enumeration
  - Consolidation gap → FIXED: added #1555 as dependency to #1554
- Dismissed: "multiple domains" claim — bootstrap JS, React hook, CSS import, Vite config are all cockpit frontend theming domain (different files ≠ different domains)
- Architect response: accepted refinements, rebutted domain split

### Proof-Bundle Validation

- Planner assignment: (none assigned)
- Final bundle: behavioral
- Rationale: 4 files with testable DOM class-toggle behavior, 3 mutation sites in useTheme.ts, clear pass/fail criteria suitable for TDD
- Test-writer: PROCEED

### Architecture Notes

- PDS shadow DOM components inherit `color-scheme` from ancestors — no per-component CSS overrides needed
- lightningcss 1.32.0 (bundled with Vite 8.0.12) confirmed in package-lock.json — `Features.LightDark` exclusion is mandatory
- `applyTheme()` is an exported function tested separately — AC-4 explicitly covers it as one of the 3 mutation sites
- Consolidation task #1554 now depends on #1555 to ensure bridge is tested in integration context

### Verdict: APPROVE
### Action Taken: Refined AC (8 lines → 7 precise lines with verification methods), assigned proof bundle `behavioral`, added dep #1555 → #1554, advanced to todo
2026-05-14T07:33:43+00:00
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts`

**E2E scratch spec:** `.owlbear/scratch/1555-pds-scheme-dark.spec.ts` (builder: copy to `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts` and verify fails)

**Classes:**
- `TestFromAC_MainTsxColorSchemeImport_1555` — AC-1 (2 tests)
- `TestFromAC_ViteConfigLightDark_1555` — AC-2 (2 tests)
- `TestFromAC_BootstrapSchemeClass_1555` — AC-3 (7 tests)
- `TestFromAC_ApplyThemeSchemeClass_1555` — AC-4 site 1: `applyTheme()` (3 tests)
- `TestFromAC_UseThemeEffectSchemeClass_1555` — AC-4 site 2: hook effect (5 tests)
- `TestFromAC_MediaChangeSchemeClass_1555` — AC-4 site 3: media-change handler (3 tests)
- `TestFromAC_NoAppColorSchemeProp_1555` — AC-7 (2 tests, constraint guards — pass in RED intentionally, annotated in code)
- **E2E (scratch):** `TestFromAC_PdsSchemeClassE2E_1555` — AC-5 (2 tests, Playwright)

**Tests per category (unit):**
- Happy: 10
- Edge: 2
- Boundary: 3
- Constraint guards: 2

**Total unit tests: 24 — 21 FAIL, 2 PASS (AC-7 constraint guards — pre-annotated)**

**Evidence:** quality-runner vitest exit 1, ESLint exit 0, 21 failures confirmed, 2 constraint-guard passes annotated.

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-1 | 2 fail |
| AC-2 | 2 fail |
| AC-3 | 7 fail |
| AC-4 (site 1: applyTheme) | 3 fail |
| AC-4 (site 2: hook effect) | 5 fail |
| AC-4 (site 3: media handler) | 3 fail |
| AC-5 | 2 e2e tests in scratch (Playwright — not runnable in unit context) |
| AC-6 | builder obligation, no new tests |
| AC-7 | 2 constraint guards (pass in RED — annotated) |

**Builder instructions for AC-5:**
```
cp .owlbear/scratch/1555-pds-scheme-dark.spec.ts serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
git add serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
npm run test:e2e -- pds-scheme-dark-1555
```
2026-05-14T07:55:14+00:00
builder crashed once (asked question instead of completing); releasing claim before retry
2026-05-14T08:00:14+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/main.tsx
  - serve/cockpit/web/vite.config.ts
  - serve/cockpit/web/public/theme-bootstrap.js
  - serve/cockpit/web/src/hooks/useTheme.ts
  - serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
- Fixes applied:
  - AC-1: Added static import of PDS color-scheme stylesheet in main entry.
  - AC-2: Added lightningcss `Features.LightDark` exclusion in Vite config; added alias path for the React global-style import to the package CSS file.
  - AC-3: Updated bootstrap script to set `data-theme` and mutually-exclusive `.scheme-dark`/`.scheme-light` on `<html>`.
  - AC-4: Centralized theme DOM mutation in `setDocumentTheme()` and applied it at all three mutation sites (`applyTheme`, main effect, media-change handler), always removing previous scheme class before add.
  - AC-5: Added Playwright proof spec in tracked e2e path and verified pass.
- Test results (quality-runner):
  - `PdsColorSchemeBridge_1555.test.ts`: 23 passed, 0 failed.
  - Existing tests (AC-6): `theme_1537.test.tsx` + `ThemeBootstrap_1545.test.ts`: 39 passed, 0 failed.
  - E2E (AC-5): `pds-scheme-dark-1555.spec.ts`: 2 passed, 0 failed.
- Lint status (quality-runner):
  - Scoped lint rerun clean: true (eslint exit 0) on `serve/cockpit/web/src`, `serve/cockpit/web/public/theme-bootstrap.js`, and task test path.
  - Initial warning-only `ignored-file` signal on `vite.config.ts` was resolved by scoped lint path selection (no code changes required).
- AC-7 verification:
  - Source scan for `color-scheme:` under `serve/cockpit/web/src/**/*.css` found only media-query usage (`src/tokens.css` prefers-color-scheme), no app-authored `color-scheme` property declarations.
- Commit:
  - `99c15e2a` — `feat: bridge pds color-scheme toggle (#1555, builder)`
2026-05-14T08:11:43+00:00
## Review Evidence
- Verdict: FAIL
- Route: todo
- Summary: AC-1/2/3/4/7 map cleanly to code and targeted tests; AC-6 builder evidence is internally consistent; AC-5 remains unproven because the E2E spec never asserts rendered dark-mode color values or a screenshot comparison.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/main.tsx:4` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:115,123` | PASS |
| AC-2 | `serve/cockpit/web/vite.config.ts:83` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:137,143` | PASS |
| AC-3 | `serve/cockpit/web/public/theme-bootstrap.js:12-14` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:165,181,219` | PASS |
| AC-4 | `serve/cockpit/web/src/hooks/useTheme.ts:22-24,33,63,75` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:243,259,283,301,314,345,357,371` | PASS |
| AC-5 | `serve/cockpit/web/src/Shell.tsx:153,166` shows a PDS button is rendered on the default route | `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:83,100,116,123,126,132` only checks `.scheme-dark` presence and `shadowRoot !== null`; task AC at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:42` requires computed style or screenshot proof | FAIL |
| AC-6 | Builder evidence in `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:167` reports existing theme suites green | `theme_1537.test.tsx` + `ThemeBootstrap_1545.test.ts`: 39 passed, 0 failed | PASS |
| AC-7 | Source scan under `serve/cockpit/web/src/**/*.css` found only `serve/cockpit/web/src/tokens.css:83` (`prefers-color-scheme` media query, not a `color-scheme:` declaration) | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:396,414` | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-5 | The new Playwright proof is structurally green but behaviorally weak: it never asserts computed dark-mode color values or a screenshot diff, so a light-rendering PDS component could still pass. | `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:42`; `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:83,100,116,123,126,132`; `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:174,187` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Replace the AC-5 structural E2E with falsifiable dark-style proof on a rendered PDS shadow-DOM component using computed style or screenshot comparison, then rerun the scoped Playwright proof. | `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts` | AC-5; Blocking finding #1 |

## Observations
- Challenger cross-check agreed with `FAIL -> todo` and found no separate source-code defect in `main.tsx`, `vite.config.ts`, `theme-bootstrap.js`, or `useTheme.ts`.
- Editor diagnostics on the changed files were clean.
- I could not independently run the git dirty-tree contamination check because terminal/git commands are unavailable in this tool surface; that did not affect the blocking AC-5 proof gap.
2026-05-14T08:19:49+00:00
## Test-Writer Notes (Retry)

**Required Follow-up addressed:** AC-5 — replaced structural `.scheme-dark`/`shadowRoot` checks with falsifiable computed-style proof.

**Scratch spec:** `.owlbear/scratch/1555-pds-scheme-dark-v2.spec.ts`

**Class:** `TestFromAC_PdsSchemeClassE2E_1555` (2 tests, both computed-style assertions)

**Tests written:**

| # | Name | What it proves | Falsifiable because |
|---|------|----------------|---------------------|
| 1 | AC-5: computed color-scheme on `<html>` is dark when `.scheme-dark` class is active | `color-scheme.css` is imported AND `.scheme-dark` sets the CSS property (not just the class name) | FAILS if `color-scheme.css` is missing → no `.scheme-dark { color-scheme: dark }` rule → `getComputedStyle(html).colorScheme` falls back to `'normal'` or `'light dark'` |
| 2 | AC-5: p-button shadow DOM inner button has distinct computed text color in dark vs light | PDS shadow DOM rendering actually changes with the color scheme | FAILS if `light-dark()` in PDS shadow styles resolves identically in both modes → `darkColor === lightColor` |

**Tests per category:** happy 2, edge 0, error 0, boundary 0 — E2E proof tests, not unit-test categories.

**Total: 2 new E2E tests (replacing 2 weak structural tests)**

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-5 | 2 new computed-style E2E tests (scratch) |

**Note: path guard prevents test-writer from writing to `e2e/`.** Scratch file is gitignored. Builder must:
```
cp .owlbear/scratch/1555-pds-scheme-dark-v2.spec.ts serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
git add serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts
cd serve/cockpit/web && npm run test:e2e -- pds-scheme-dark-1555
```
- If **both tests PASS** → implementation is complete; advance directly to `review`.
- If **any test FAILS** → fix the implementation gap causing the failure, then advance to `review`.
2026-05-14T08:22:16+00:00
## Builder Notes
- Action taken: applied test-writer retry spec to `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts` and executed scoped quality proof via quality-runner.
- Quality-runner result:
  - Playwright: `1 passed, 1 failed` (exit 1)
  - ESLint: clean (exit 0)
- Blocking mismatch (test assumption, not implementation):
  - In AC-5 test 2, `page.addInitScript(() => localStorage.setItem('owlbear-theme', 'dark'))` is registered before the scenario (`serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:149-151`).
  - The test later sets localStorage to light and calls `page.reload()` (`serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:175`).
  - Playwright init scripts run on each document navigation/reload, so reload re-applies dark and invalidates the intended dark-vs-light comparison in the same test.
  - Observed failure: dark and light computed colors are both `rgb(255, 255, 255)`.
- Verdict basis: AC-5 retry proof is currently non-falsifiable for the intended two-theme comparison because the test setup forces the same theme state across both measurements.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Rewrite AC-5 test 2 to avoid init-script theme reapplication across reload boundaries (e.g., separate dark/light navigations without persistent dark init script on the light capture), then rerun scoped Playwright proof. | `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts` | `:149-151` + `:175` and failing output (`darkColor === lightColor`) |
2026-05-14T08:32:11+00:00
## Test-Writer Notes (Retry v4)

**Action:** Fixed AC-5 E2E test — direct-to-review advance (test-proof gap only, no implementation defect).

**File:** `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts`

**Root cause of v2/v3 failures:**
- v2: `page.reload()` triggered `addInitScript` re-run, re-applying dark override on the "light" capture.
- v3: new page with no init script still resolved to dark because macOS OS is in dark mode → `prefersDark()` returns `true` → auto theme resolves to dark.
- Fix (v4): light-mode page gets its own `addInitScript(() => localStorage.setItem('owlbear-theme', 'light'))` — explicitly forces light regardless of OS preference. addInitScript is page-scoped so the dark page's script doesn't bleed over.

**Tests per category:** 2 E2E tests (computed-style assertions), both PASS against current implementation.

**Evidence:** quality-runner Playwright: 2 passed, 0 failed (exit 0); ESLint: clean (exit 0).

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-5 | 2 computed-style E2E tests — falsifiable, both PASS against current impl |

**Step 1b.1 apply:** reviewer Required Follow-up = test-proof gap only, no implementation fix needed. All tests green → builder skip → advance directly to review.
2026-05-14T08:48:43+00:00
## Review Evidence
- Verdict: PASS
- Route: docs
- PASS confirmation: PASS #1555 to docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.

| AC | Code Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/main.tsx:4` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:115-129` | PASS |
| AC-2 | `serve/cockpit/web/vite.config.ts:4,82-83` | Static inspection matches the AC exactly; unit proof at `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:137-147` is consistent with the live config | PASS |
| AC-3 | `serve/cockpit/web/public/theme-bootstrap.js:12-14` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:165-227` | PASS |
| AC-4 | `serve/cockpit/web/src/hooks/useTheme.ts:22-25,33,63,75` | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:243-383` | PASS |
| AC-5 | `serve/cockpit/web/src/main.tsx:4`; `serve/cockpit/web/public/theme-bootstrap.js:12-14`; `serve/cockpit/web/src/hooks/useTheme.ts:22-25,33,63,75` | Prior follow-up required computed-style or screenshot proof at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:201`. The final retry supplies computed-style proof on a PDS shadow button at `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:123-134,174-227`, and the task evidence reports `Playwright: 2 passed, 0 failed` at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:269-271` | PASS |
| AC-6 | Builder evidence for unchanged suites is at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:167`; the builder-scoped file list remains limited to task files at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:153-158` | `theme_1537.test.tsx` + `ThemeBootstrap_1545.test.ts`: `39 passed, 0 failed` at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:167` | PASS |
| AC-7 | Adjacent CSS still uses only `prefers-color-scheme` at `serve/cockpit/web/src/tokens.css:83`; no app-authored `color-scheme` property declaration was introduced in the scoped source surface | `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:396-419` | PASS |

- Safety and security check: no new input handling, auth boundary, secret usage, or unsafe path/shell/storage surface was introduced beyond existing localStorage theme resolution; no blocking safety issue found.

## Observations
- AC-5 Test 1 at `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:123-134` is weaker than Test 2 because it accepts any computed `colorScheme` containing `dark`. That is non-blocking here because the prior review explicitly accepted computed-style comparison as the remedy at `.owlbear/kanban/tasks/1555-bridge-pds-v4-color-scheme-with-data-theme-toggle.md:201`, and Test 2 at `serve/cockpit/web/e2e/pds-scheme-dark-1555.spec.ts:174-227` plus the AC-3/AC-4 class-toggle proof closes that requirement.
- AC-2's automated proof at `serve/cockpit/web/src/__tests__/PdsColorSchemeBridge_1555.test.ts:137-147` is syntactic rather than structural. That is non-blocking because AC-2 explicitly allows static inspection and the live config at `serve/cockpit/web/vite.config.ts:82-83` matches the contract exactly.
- Challenger and code-reader both surfaced the matcher-strength nuances above; neither surfaced a source-code defect or blocking safety issue in `main.tsx`, `vite.config.ts`, `theme-bootstrap.js`, `useTheme.ts`, or the final E2E spec.
2026-05-14T08:51:51+00:00
## Docs Gate

**Verdict:** PASS — no docs impact requiring updates.

### Checklist

| Item | Status | Evidence |
|---|---|---|
| README Verification | PASS — no-impact | `serve/cockpit/README.md` documents API, backend, and launch surface only; theme bridging (CSS import `color-scheme.css`, class toggling in `theme-bootstrap.js`/`useTheme.ts`, lightningcss exclusion in `vite.config.ts`) is a pure frontend behavioral change not documented in this README; no symbols/commands/flags removed; Stack row (Vite ^8.0.10, PDS React ^4.0.0), launch commands, configuration variables, mutation routes, and dependency table all remain accurate |
| External Attribution | PASS | `.owlbear/sources/overview.md` updated with 6 high-relevance sources for #1555 (PDS v4 Theme docs, Color Scheme Stylesheet docs, PDS GitHub Issue #4257, and 3 additional) |
| Research Doc | PASS | `.owlbear/research/1555-pds-color-scheme-bridge.md` exists; linked from task body under Research section |
| Deletion Detection | N/A | No source files deleted; 5 files modified or added only |

**Files updated:** none (no-impact verified)
**Scratch cleanup:** no `.owlbear/scratch/1555-*` files found
2026-05-14T09:06:43+00:00
## Audit

### Regression Detection
- quality-runner mode full: Python 4601 passed / 213 failed (all pre-existing, unrelated domains); Frontend vitest 1751 passed / 3 failed (2 regressions attributed to this task)
- Regression verdict: FAIL
- Attributed regressions: `vite_config.test.ts` and `vite_config_pds_1513.test.ts` both fail with `TypeError: The URL must be of scheme file` at vite.config.ts:9. Root cause: #1555 commit 99c15e2a added module-level `fileURLToPath(new URL('./node_modules/...', import.meta.url))` which breaks in Vitest test environment where `import.meta.url` does not resolve to a file:// URL. These tests were authored by #1513/#1397, last passing before #1555's commit.
- Non-attributed failures: ResponsiveLayout_1391 (Shell.css last modified by #1549/#1542), KanbanBoard.filter-e2e (unrelated), all Python failures (engine_accessor, cockpit_view, etc. unrelated domains)

### Intent Verification
- Scope alignment: PASS (changed files: main.tsx, vite.config.ts, theme-bootstrap.js, useTheme.ts, e2e spec, all cockpit frontend theming)
- Purpose match: PASS (bridge PDS color-scheme with data-theme toggle, implementation addresses stated purpose)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines were specific with exact file paths, import paths, 3 mutation sites enumerated, and verification methods per line. Minor gap: no explicit mention of maintaining existing vite config test compatibility, though that is builder/reviewer responsibility.

### Commit Integrity
- Upstream commit presence: PASS (builder: 99c15e2a, test-writer fix: 7e26851e, both on dev)
- Kanban commit packaging: deferred (rejection, not archival)

### Deduction Breakdown
- Regression failures (vite_config.test.ts + vite_config_pds_1513.test.ts broken by module-level URL resolution in #1555's vite.config.ts changes): -.10

### Confidence: .90
### Action: reject to backlog

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Fix module-level `fileURLToPath(new URL(..., import.meta.url))` in vite.config.ts to be test-environment-safe (Vitest import.meta.url does not use file:// scheme); verify vite_config.test.ts and vite_config_pds_1513.test.ts pass after fix | serve/cockpit/web/vite.config.ts | TypeError at vite.config.ts:9; tests authored by #1513/#1397 |