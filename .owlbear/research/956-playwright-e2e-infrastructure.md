# Playwright E2E Infrastructure Setup — Research

> **Owning task:** #956 — Setup Playwright E2E infrastructure in cockpit web
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #955 research recommended Playwright Test (standalone) for E2E kanban board tests requiring a real browser (DnD highlights, card density, scroll). Task #956 adds the infrastructure: install, config, directory, smoke test. The research question is whether the proposed approach is feasible and what the exact configuration should be.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | Playwright `webServer` docs (playwright.dev/docs/test-webserver) | 0.95 |
| S2 | Playwright config reference (playwright.dev/docs/test-configuration) | 0.90 |
| S3 | Vite preview options — port 4173 default (vite.dev/config/preview-options) | 0.90 |
| S4 | `.owlbear/research/955-e2e-kanban-board-tests.md` — prior recommendation | 0.95 |
| S5 | `serve/cockpit/web/package.json` — current deps, scripts, no E2E infra | 0.90 |
| S6 | `serve/cockpit/web/vite.config.ts` — build output `../dist`, PDS partials, vitest config | 0.90 |
| S7 | `serve/cockpit/web/tsconfig.json` — include: `["src", "vite.config.ts", "vitest.setup.ts"]` | 0.85 |
| S8 | `serve/cockpit/web/.gitignore` — `node_modules/`, `dist/`, `*.local`, `*.tsbuildinfo` | 0.85 |

## 3. Analysis

### 3.1 Configuration Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| webServer command | `vite preview` (stale build) vs `npm run build && npm run preview` | `npm run build && npm run preview` | Ensures fresh build before every E2E run; `build` finishes, `preview` stays running [S1] |
| Port | 4173 (vite preview default) vs custom | 4173 (default) | Standard Vite preview port, no config needed [S3] |
| Browser | Chromium only vs multi-browser | Chromium only | Per AC; sufficient for DnD/layout testing; saves ~400MB of browser binaries |
| Test dir | `tests/` vs `e2e/` | `e2e/` | Per AC; avoids collision with vitest's `src/__tests__/` convention |
| tsconfig | Modify existing vs none | None needed | Playwright uses its own TS transpiler; editor IntelliSense works via default resolution |
| Reporter | HTML vs list | HTML (default) | Standard; generates `playwright-report/` (gitignored) |

### 3.2 `webServer` Configuration

Playwright's `webServer` starts a process and waits for a URL to respond before running tests [S1]:

- `command`: `npm run build && npm run preview` — builds production bundle then serves on port 4173
- `url`: `http://localhost:4173` — Playwright polls until 2xx/3xx/4xx
- `reuseExistingServer`: `!process.env.CI` — reuses existing server locally, forces fresh server in CI
- `baseURL`: `http://localhost:4173` — tests use relative paths (`page.goto('/')`)

Vite's build output goes to `../dist` (per `vite.config.ts` [S6]). The `preview` command serves that directory.

### 3.3 Vitest Isolation

Current vitest runs via `npm test` → `vitest run` [S5]. Playwright runs via `npx playwright test` [S2]. No overlap:

| Concern | Status |
|---------|--------|
| Test runner conflict | None — separate executables |
| Config conflict | None — `vite.config.ts` (vitest) vs `playwright.config.ts` (Playwright) |
| Test discovery | None — vitest finds `src/__tests__/*.test.tsx`, Playwright finds `e2e/*.spec.ts` |
| Dependencies | None — `@playwright/test` is a standalone package |

### 3.4 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Port 4173 occupied | Low | `reuseExistingServer` handles dev case; CI starts clean. If persistent, add `--strictPort` |
| Browser binary not installed | Medium | Document `npx playwright install chromium` in setup; could add `postinstall` script |
| Build failure breaks E2E silently | Low | `&&` chaining fails the command if build fails; Playwright reports webServer timeout |
| `../dist` path assumption | Low | Both `vite.config.ts` and Playwright config reference same build output implicitly |

## 4. Recommendation

**Proceed with standard Playwright Test setup** as specified in the AC.

Confidence: **0.90**

The implementation is straightforward, well-documented by Playwright, and fully compatible with the existing Vite + React + vitest stack. No architectural decisions or trade-offs — this is standard infra scaffolding.

Challenge: SKIPPED — info/validation research, no alternative recommendation to challenge. The framework choice was already decided in #955 research.

### Exact File Changes

1. `package.json`: add `@playwright/test` devDep, add `"test:e2e": "playwright test"` script
2. `playwright.config.ts`: chromium project, `webServer` with build+preview, `testDir: 'e2e'`
3. `e2e/smoke.spec.ts`: navigate to `/`, assert app shell element visible
4. `.gitignore`: append `test-results/` and `playwright-report/`

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #956 itself covers the full scope. The subsequent DnD/density/scroll E2E tests are a separate concern (tracked via #955 follow-ups).
