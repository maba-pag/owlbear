---
id: 925
title: 'P2-01: Frontend scaffold (Vite + React 19 + TS + Porsche DS)'
status: archived
priority: medium
created: 2026-04-17T19:57:10.963361+00:00
updated: 2026-04-18T11:32:53.468007+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
- type:config
parent: 920
depends_on:
- 921
- 922
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Set up the frontend build toolchain at `serve/cockpit/web/` with React 19, Vite, TypeScript, and Porsche DS React wrapper (D14).

## Acceptance Criteria

- [ ] `serve/cockpit/web/package.json` with React 19, Vite, TypeScript, `@porsche-design-system/components-react`; `engines` field requires Node >=20.19
- [ ] Vitest configured with `environment: 'jsdom'`; test setup file imports PDS jsdom-polyfill (`@porsche-design-system/components-react/jsdom-polyfill`) and calls `skipPorscheDesignSystemCDNRequestsDuringTests()`
- [ ] `vite.config.ts` outputs built bundle to `serve/cockpit/dist/` and includes PDS partials plugin (`transformIndexHtml`) for font/icon preloading
- [ ] `tsconfig.json` with `strict: true`
- [ ] Minimal `App.tsx` renders a PDS `<PHeading>` with visible text; `npm test` confirms it appears in the DOM
- [ ] `tokens.css` exports PDS design-token values as CSS custom properties (e.g. `--pds-theme-light-primary`); placeholder values acceptable if PDS tokens require runtime
- [ ] `npm run build` produces working bundle; `npm run dev` starts dev server; `npm test` runs Vitest suite
- [ ] `serve/cockpit/web/.gitignore` covers `node_modules/`, `dist/`; root `.gitignore` gets a `node_modules/` entry (first Node.js code in repo)
- [ ] `.nvmrc` pins Node version (>=20.19, per Vite requirement)
- [ ] If PDS React wrapper proves problematic at setup, document in task body and flag D14 fallback

## Files

- `serve/cockpit/web/package.json`
- `serve/cockpit/web/vite.config.ts`
- `serve/cockpit/web/tsconfig.json`
- `serve/cockpit/web/vitest.setup.ts`
- `serve/cockpit/web/index.html`
- `serve/cockpit/web/.nvmrc`
- `serve/cockpit/web/.gitignore`
- `serve/cockpit/web/src/App.tsx`
- `serve/cockpit/web/src/tokens.css`
- `.gitignore` (root — add `node_modules/` entry)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/925-frontend-scaffold.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Proceed with scaffold as specified — all stack components confirmed compatible (confidence: 0.85)
- Key findings: PDS 3.34.0 requires React >=19.0.0; dual license (Apache 2.0 source + restrictive assets, LOW risk for OwlBear); tokens.css via CSS custom properties from PDS JS exports (Option A, score 0.80); Vitest needs PDS jsdom-polyfill + componentsReady + vi.fn() mocks (not jest.fn()); Vite partials plugin prevents FOUC/FOUT
- Follow-up tasks created: none (task itself proceeds)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Frontend build toolchain only — no backend, no business logic |
| Interface clarity | PASS (after refinement) | AC refined: specific PDS component, Node version, test setup file contents, partials plugin |
| Dependency correctness | PASS | #921 (benchmark) and #922 (layout mockup) both archived/done |
| Module layering | PASS | Greenfield at `serve/cockpit/web/` — no existing modules to conflict. `serve/cockpit/` without `pyproject.toml` is benign; uv skips directories without one |
| TDD compliance | PASS | Tagged `type:config` for test-writer pass-through — produces no testable Python code (JS/TS only). Vitest smoke test is the scaffold's own verification |
| KISS/YAGNI | PASS | Minimal scaffold: Vite template + PDS integration + tokens + one smoke test |
| Premise challenge | PASS | Brief D14 decided the stack; research confirmed feasibility at 0.85 confidence |
| Pattern consistency | PASS | First frontend package; follows `serve/` package convention. Root `.gitignore` updated for first Node.js code in monorepo |
| Security surface | PASS | No system boundary exposed. XSS hardening is Phase 2 surface work (later tasks) |
| Single domain | PASS | Frontend build toolchain domain only |

### AC Refinements Applied

| Original AC | Refinement | Rationale |
|------------|------------|-----------|
| AC1: package.json with deps | Added `engines` field with Node >=20.19 | Research §3.5 (S6): Vite requires Node 20.19+; challenger C5 |
| AC2: Vitest configured | Specified jsdom env, PDS jsdom-polyfill import, CDN suppression in setup file | Research §3.4; removed `renderWithProvider` per challenger C3 (belongs in later test task) |
| AC3: Vite config outputs bundle | Added PDS partials plugin (`transformIndexHtml`) | Research §3.5: prevents FOUC/FOUT |
| AC5: Renders PDS component | Specified `<PHeading>` with visible text + `npm test` assertion | Challenger C4: original was vague |
| AC7: npm scripts | Added `npm test` to script list | Vitest suite should be runnable from day 1 |
| AC8: .gitignore | Split: local `.gitignore` + root `node_modules/` entry | Challenger C2: first Node.js code in all-Python repo |
| NEW: .nvmrc | Pin Node version | Challenger C5: prevent silent breakage on older Node |

### Files Added to Scope

- `vitest.setup.ts` — PDS jsdom polyfill + CDN suppression
- `index.html` — Vite requires entry point at web root
- `.nvmrc` — Node version pinning
- `serve/cockpit/web/.gitignore` — local gitignore
- `.gitignore` (root) — `node_modules/` entry

### Challenge Results

- Challenger: `reconsider` (confidence 0.55)
- Key challenges addressed:
  - C1 (uv workspace race): Verified — uv skips dirs without `pyproject.toml`; no ordering issue
  - C2 (root `.gitignore`): Added AC for `node_modules/` in root `.gitignore`
  - C3 (scope creep `renderWithProvider`): Removed from AC2 refinement — belongs in test task
  - C4 (AC5 incomplete): Specified `<PHeading>` + `npm test` assertion
  - C5 (Node version): Added `.nvmrc` + `engines` AC
  - C6 (`type:config` tag): Added per w-arch-review directive; explicit pass-through is more reliable than heuristic fallback
- Architect response: accepted C2–C5, rebutted C1 (benign), rebutted C6 (directive is explicit)

### Builder Guidance

1. Start from `npm create vite@latest -- --template react-ts`
2. PDS testing docs use `jest.fn()` — replace with `vi.fn()` for Vitest
3. PDS `getByRoleShadowed` etc. from `/testing` export for shadow DOM queries
4. `tokens.css` should map PDS JS token values (`themeLight*` exports) to CSS custom properties
5. PDS partials plugin prevents FOUC/FOUT — include from day 1
6. Research doc at `.owlbear/research/925-frontend-scaffold.md` has full setup specifics

### Verdict: APPROVE (after refinement)

### Action Taken: Refined AC for precision (9 items → 10), added `type:config` tag for pipeline pass-through, added 5 missing files to scope, advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Non-implementation task (tagged `type:config`, `type:build`) — no Python tests applicable.
- All deliverables are frontend files: `package.json`, `vite.config.ts`, `tsconfig.json`, `vitest.setup.ts`, `index.html`, `App.tsx`, `tokens.css`, `.nvmrc`, `.gitignore` entries.
- Test coverage is provided by Vitest itself (AC5 smoke test: `<PHeading>` visible in DOM via `npm test`).
- Passing through to builder.
[[2026-04-18]]

## Builder Notes

### Files changed (14)

- `serve/cockpit/web/package.json` — React 19, Vite 6, TS, PDS 3.34.0, Vitest 3; engines: node >=20.19
- `serve/cockpit/web/vite.config.ts` — `@vitejs/plugin-react`, PDS partials plugin (try/catch), outDir `../dist`, Vitest jsdom config merged via `/// <reference types="vitest" />`
- `serve/cockpit/web/tsconfig.json` — strict: true, bundler moduleResolution, jsx: react-jsx
- `serve/cockpit/web/vitest.setup.ts` — PDS jsdom-polyfill, `skipPorscheDesignSystemCDNRequestsDuringTests()`, HTMLDialogElement + HTMLElement.attachInternals mocks (vi.fn)
- `serve/cockpit/web/index.html` — Vite entry point
- `serve/cockpit/web/src/main.tsx` — React 19 createRoot entry
- `serve/cockpit/web/src/App.tsx` — `<PorscheDesignSystemProvider>` + `<PHeading>OwlBear Cockpit</PHeading>`
- `serve/cockpit/web/src/App.test.tsx` — smoke tests: p-heading element in DOM, visible text
- `serve/cockpit/web/src/tokens.css` — PDS light theme CSS custom properties (--pds-theme-light-*)
- `serve/cockpit/web/src/vite-env.d.ts` — Vite client types
- `serve/cockpit/web/.nvmrc` — 20.19.0
- `serve/cockpit/web/.gitignore` — node_modules/, dist/, *.local,*.tsbuildinfo
- `.gitignore` (root) — added node_modules/ entry (first Node.js code in repo)
- `serve/cockpit/web/package-lock.json` — generated by npm install

### Test results

- `npm test`: **2 passed** (App renders PHeading in DOM ✓, PHeading contains visible heading text ✓)
- `npm run build`: **0 errors**, 123 modules transformed → `serve/cockpit/dist/` ✓

### Lint

- No Python code → ruff N/A
- TypeScript: `tsc -b` passes (confirmed via build)

### Builder-discovered fix

- Research doc placed `skipPorscheDesignSystemCDNRequestsDuringTests` in `@porsche-design-system/components-react/testing`; actual export is in main package `@porsche-design-system/components-react`. Fixed in vitest.setup.ts.
- `attachInternals` lives on `HTMLElement`, not `Element` — fixed TypeScript cast.

### Commit

`e694d178` feat: frontend scaffold Vite+React19+TS+PDS at serve/cockpit/web/ (#925, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- Vitest: **2 passed, 0 failed** (run independently via quality-runner)
  - `App > renders PHeading component in DOM` ✓
  - `App > PHeading contains visible heading text` ✓

### Lint: clean

- `tsc -b --noEmit`: no output (all type checks passed)
- No Python code → ruff N/A

### Coverage: N/A (JS/TS scaffold — no Python coverage applicable)

### Build: success

- `npm run build`: 123 modules transformed → `serve/cockpit/dist/index.html`, `dist/assets/index-*.css`, `dist/assets/index-*.js` ✓

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes — conditional skipped (JS/TS task; test-writer confirmed pass-through).

#### Security Review

- No hardcoded secrets, tokens, or API keys
- `pdsPartialsPlugin` `transformIndexHtml`: build-time only, `css` comes from trusted PDS library call (`getInitialStyles()`), not user-controlled input — no XSS risk
- All new dependencies (React 19, Vite 6, PDS 3.34.0, @testing-library/react ^16, vitest ^3) well-maintained, widely-used
- No injection, path traversal, insecure deserialization, or missing boundary validation
- Result: **No issues**

#### Test Integrity

No `TestFromAC_*` classes — conditional skipped.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | `querySelector('p-heading')` verifies custom element presence; `textContent` verifies visible text — both match AC5 exactly |
| Negative/error-path coverage | N/A | Scaffold smoke test; no AC-required error paths |
| Mutation reasoning | ADEQUATE | Remove `<PHeading>` from App.tsx → test 1 fails; remove text → test 2 fails |
| Test independence | STRONG | Each test renders independently |
| Descriptive names | STRONG | "renders PHeading component in DOM", "PHeading contains visible heading text" |

Overall: **ADEQUATE** — appropriate for a scaffold smoke test; assertions match AC5 requirements precisely.

#### Data Safety

N/A — static frontend scaffold, no LLM outputs, no shared mutable state, no runtime persistence.

#### Implementation-Aware Gaps

- `pdsPartialsPlugin` (build-time only): build output confirms it works; no runtime test needed
- `vitest.setup.ts` mock setup (HTMLDialogElement, attachInternals): jsdom compatibility shims, not business logic — no test gap
- `tokens.css` CSS properties: static file, AC6 explicitly permits placeholder values — no gap
- Result: **No untested paths requiring coverage**

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | **CLEAN** |

Builder-discovered fix documented: import path correction for `skipPorscheDesignSystemCDNRequestsDuringTests` (main package, not `/testing` export) + TypeScript cast fix for `attachInternals` on `HTMLElement`. Both legitimate discoveries, well-documented.

### Pass 2 — INFORMATIONAL

- `pdsPartialsPlugin` uses silent `try/catch` fallback — reasonable defensive coding for an optional build enhancement; no correctness impact
- `tokens.css` placeholder values acknowledged in file comments — matches AC6 expectation

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: package.json + React 19 + Vite + TS + PDS + engines >=20.19 | `package.json` lines 3–5, 14–18, 19–24 | — | PASS |
| AC2: Vitest jsdom + PDS jsdom-polyfill + CDN skip in setup file | `vite.config.ts` test block; `vitest.setup.ts` lines 1–5 | — | PASS |
| AC3: vite.config.ts outDir `../dist` + PDS partials plugin transformIndexHtml | `vite.config.ts` build block + `pdsPartialsPlugin()`; build output `../dist/` | — | PASS |
| AC4: tsconfig strict: true | `tsconfig.json` line 14 | — | PASS |
| AC5: App.tsx PHeading + visible text + npm test | `App.tsx`; 2/2 tests pass (quality-runner) | App > renders PHeading, App > PHeading contains visible heading text | PASS |
| AC6: tokens.css CSS custom properties --pds-theme-light-* | `tokens.css` lines 6–end; placeholder values present | — | PASS |
| AC7: npm run build + npm run dev + npm test scripts | `package.json` scripts; build 0 errors; test 2/2 pass | — | PASS |
| AC8: local .gitignore (node_modules/, dist/) + root .gitignore node_modules/ | `serve/cockpit/web/.gitignore` lines 1–2; `.gitignore` line 2 | — | PASS |
| AC9: .nvmrc >= 20.19 | `.nvmrc` contains `20.19.0` | — | PASS |
| AC10: D14 fallback if PDS problematic | PDS integrated successfully; builder-discovered fix documented | — | PASS |

### Confidence: .95

### Verdict: PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | First Node.js/frontend code in repo — added `## 3. Cockpit Frontend` section to `.github/copilot-instructions.md` with stack table (React 19, Vite 6, TS, PDS 3.34.0), test/build commands, Node requirement, and `npm` vs `uv` disambiguation. Commit `014ff860`. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified — all deliverables are JS/TS/config files. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains a complete "Frontend Scaffold Feasibility (Task #925)" section with all 5 sources (PDS npm, getting-started, testing docs, license, theme styles). No update needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/925-frontend-scaffold.md` exists and is linked in task body under `## Research`. |

### Scratch files

No `.owlbear/scratch/925-*` files found — nothing to clean.

### Files Updated

- `.github/copilot-instructions.md` — new `## 3. Cockpit Frontend` section
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: package.json + React 19 + Vite + TS + PDS + engines >=20.19 | File confirmed; engines field present with >=20.19 | PASS |
| AC2: Vitest jsdom + PDS jsdom-polyfill + CDN skip | vitest.setup.ts confirmed: jsdom-polyfill import + skipPorscheDesignSystemCDNRequestsDuringTests() | PASS |
| AC3: vite.config.ts outDir ../dist + PDS partials plugin | File confirmed: outDir '../dist', pdsPartialsPlugin() present | PASS |
| AC4: tsconfig strict: true | tsconfig.json confirmed: strict: true | PASS |
| AC5: App.tsx PHeading + npm test | App.tsx renders PHeading "OwlBear Cockpit"; Vitest 2/2 pass | PASS |
| AC6: tokens.css CSS custom properties | tokens.css confirmed: --pds-theme-light-* properties present | PASS |
| AC7: npm build + dev + test scripts | Build success (123 modules); test 2/2 pass; scripts confirmed in package.json | PASS |
| AC8: .gitignore local + root node_modules/ | serve/cockpit/web/.gitignore + root .gitignore both confirmed | PASS |
| AC9: .nvmrc >= 20.19 | .nvmrc contains 20.19.0 | PASS |
| AC10: D14 fallback if PDS problematic | PDS integrated successfully; builder-discovered fix documented | PASS |

### Test Results

- pytest: 474 passed, 6 failed (all pre-existing in knowledge/MCP packages — outside task scope)
- Vitest: 2 passed, 0 failed
- ruff: clean
- tsc: clean
- npm build: success

### Architect Quality: 5/5

Exemplary. 10 specific AC items (refined from 9). Challenger integration addressed 6 concerns (C1-C6). 5 files added to scope. 6-point builder guidance. Clean implementation path.

### Deduction Breakdown

- Starting: 1.00
- AC lines without evidence: 0 (all 10 PASS) → no deduction
- Lint violations: none → no deduction
- AC quality ≤ 3: N/A (score 5) → no deduction
- Missing reviewer evidence: present and detailed → no deduction
- Full-suite failures in task scope: none → no deduction
- Commit verification: hashes documented (e694d178, 014ff860), all files exist — no terminal to independently verify git log, minor process gap → -0.02

### Confidence: .98

### Action: archive
