---
id: 956
title: Setup Playwright E2E infrastructure in cockpit web
status: archived
priority: nice-to-have
created: 2026-04-18T13:49:17.508633+00:00
updated: 2026-04-18T16:03:30.450778+00:00
tags:
- cockpit
- frontend
- phase-2
- type:infra
parent:
depends_on:
- 955
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Install Playwright and create the E2E test infrastructure for the cockpit frontend.

## Context

Research in `.owlbear/research/955-e2e-kanban-board-tests.md` recommends Playwright Test (standalone) for E2E tests that require a real browser: DnD highlights, card density, scroll.

## Acceptance Criteria

- [ ] `@playwright/test` added as devDependency in `serve/cockpit/web/package.json`
- [ ] `playwright.config.ts` created with: chromium only, `webServer` pointing to `vite preview`, headless by default
- [ ] `e2e/` directory created under `serve/cockpit/web/`
- [ ] `"test:e2e": "playwright test"` script added to package.json
- [ ] Existing `npm test` (vitest/jsdom) is unaffected
- [ ] `.gitignore` updated for Playwright artifacts (`test-results/`, `playwright-report/`)
- [ ] One smoke test (`e2e/smoke.spec.ts`) verifies the dev server loads the app shell
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/956-playwright-e2e-infrastructure.md
- Sources: 8 studied, 5 high-relevance (≥0.90)
- Recommendation: Standard Playwright Test setup with `webServer` using `npm run build && npm run preview` on port 4173, chromium only, `e2e/` test dir (confidence: 0.90)
- Follow-up tasks created: none — #956 AC covers full scope
- Decision requests: none
- Tier: T1 — autonomous (standard infra scaffolding, no architectural decisions)
- Challenge: skipped (validation research, no alternative recommendation)
[[2026-04-18]]

## Architecture Review

### AC Refinements (binding for builder)

The original AC has three specification gaps identified by the challenger. The builder MUST follow these refined versions:

**AC2 (refined):** `playwright.config.ts` created with: chromium-only project, `webServer.command` set to `npm run build && npm run preview` (NOT bare `vite preview`), `webServer.url` and `use.baseURL` set to `http://localhost:4173`, `reuseExistingServer: !process.env.CI`, `testDir: 'e2e'`, headless by default

**AC6 (clarified):** `serve/cockpit/web/.gitignore` updated to include `test-results/` and `playwright-report/` (the package-level gitignore, not root)

**AC7 (refined):** One smoke test (`e2e/smoke.spec.ts`) navigates to `/` on the preview server and asserts the app shell element is visible

**AC8 (new):** Browser binaries bootstrapped — either a `postinstall` script running `npx playwright install chromium` in package.json, or a clearly documented manual step in a comment at the top of `playwright.config.ts`. `@playwright/test` does NOT auto-install browsers.

### Pass-through tag needed

Task produces no testable Python code (all TypeScript/npm). Requires a pass-through tag for the test-writer. Recommend adding `type:config` — orchestrator or next agent should add this tag via `edit_task`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: E2E test infrastructure setup |
| Interface clarity | PASS (after refinement) | AC2/AC7 tightened; AC8 added for browser install |
| Dependency correctness | PASS | #955 (research) is resolved/archived; research doc exists |
| Module layering | PASS | Frontend package, no cross-module concerns |
| TDD compliance | PASS | Infra/config task — pass-through via `type:config` tag |
| KISS/YAGNI | PASS | Minimal: one browser, one config, one smoke test |
| Premise challenge | PASS | E2E infra needed per #955 research recommendation |
| Pattern consistency | PASS | Standard Playwright Test setup; npm per cockpit conventions |
| Security surface | PASS | Dev tooling only, no production code |
| Single domain | PASS | Cockpit frontend testing infrastructure |

### Known Limitations (not blockers)

1. **PDS CDN dependency:** PDS web components (`p-icon`, `p-tabs`) load from CDN in real browsers. The smoke test checks app shell only, so no immediate issue. Future E2E tests exercising PDS components may need CDN mocking or offline fallback — track as separate concern.
2. **Backend dependency:** `KanbanBoard.tsx` fetches `/api/board` and `/api/tasks` on mount. Once wired into routes, E2E tests will need either FastAPI backend running or Playwright network mocking. Not #956 scope.
3. **CI integration:** No CI step for E2E tests exists yet. Out of scope — separate follow-up.
4. **tsconfig scope:** `tsconfig.json` includes only `src/` — `playwright.config.ts` and `e2e/` won't be type-checked by `tsc -b`. Standard Playwright behavior (uses own transpiler). Editor IntelliSense still works.

### Challenge Results

- Challenger: **reconsider** (confidence: 0.60)
- Key concerns: AC2 broken on literal reading (no build step), AC7 misleading "dev server", missing browser install AC, PDS CDN runtime dependency
- Architect response: **accepted** C1/C2/C3 — refined AC2, AC7, added AC8. **Noted** C4 (PDS CDN) as known limitation. **Dismissed** C5 (outDir fragility — sequential `&&` execution is sufficient).

### Verdict: APPROVE (with refinements)

### Action Taken: Advanced to `todo` with binding AC refinements in this note. Builder must follow refined AC2, AC6, AC7, and new AC8 above. Pass-through tag `type:config` needed — not yet applied (no `edit_task` available)

[[2026-04-18]]

## Test-Writer Notes

- Non-impl pass-through: all AC items are TypeScript/npm artifacts (`playwright.config.ts`, `e2e/smoke.spec.ts`, `package.json` script, `.gitignore`). No Python interfaces exist.
- Tag `type:infra` is a config/infra tag; Step 2a heuristic confirms no testable Python code.
- Architect noted `type:config` pass-through tag was needed but not yet applied — treated as equivalent.
- Passing through to builder.
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/package.json` — added `@playwright/test ^1.59.1` devDep, `test:e2e` script
- `serve/cockpit/web/package-lock.json` — updated by npm install
- `serve/cockpit/web/playwright.config.ts` — new: chromium-only, webServer `npm run build && npm run preview`, url/baseURL `http://localhost:4173`, `reuseExistingServer: !process.env.CI`, `testDir: 'e2e'`, headless default, AC8 browser-install comment
- `serve/cockpit/web/e2e/smoke.spec.ts` — new: navigates `/`, asserts `[data-region="workspace"]` visible
- `serve/cockpit/web/.gitignore` — added `test-results/`, `playwright-report/`
- `serve/cockpit/web/vite.config.ts` — added `include: ['src/**/*.{test,spec}.{ts,tsx}']` to prevent vitest picking up e2e/ tests

### Test results

- `npm test` (vitest): **59 passed, 4 test files** — unaffected ✓
- No Python changes; no pytest run needed

### Lint

- No Python files changed; ruff N/A for TypeScript

### AC evidence

- AC1 ✓ `@playwright/test` in devDependencies
- AC2 ✓ playwright.config.ts: chromium, webServer with build+preview, port 4173, reuseExistingServer
- AC3 ✓ `e2e/` directory created
- AC4 ✓ `test:e2e` script added
- AC5 ✓ `npm test` still passes 59 tests
- AC6 ✓ .gitignore updated with test-results/ and playwright-report/
- AC7 ✓ smoke.spec.ts navigates `/` and asserts workspace element visible
- AC8 ✓ Browser install documented in playwright.config.ts comment

### Fix applied

- Vitest was picking up `e2e/smoke.spec.ts` — added `include` pattern to vite.config.ts to scope vitest to `src/` only (1 extra file, directly related to AC5)
[[2026-04-18]]

## Review Evidence

### Tests

- Quality-runner: `npm test` (vitest) — **59 passed, 0 failed**, exit 0
- No Python tests (TypeScript/npm infra task)

### Lint

- N/A — no Python files changed; ruff not applicable

### Coverage

- N/A — config/infra task; no coverage module

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `@playwright/test` devDep | `package.json`: `"@playwright/test": "^1.59.1"` in devDependencies | PASS |
| AC2 (refined): config | chromium project, `npm run build && npm run preview`, url/baseURL `http://localhost:4173`, `reuseExistingServer: !process.env['CI']`, `testDir: 'e2e'`, `headless: true` | PASS |
| AC3: `e2e/` directory | `e2e/smoke.spec.ts` exists | PASS |
| AC4: `test:e2e` script | `package.json` scripts: `"test:e2e": "playwright test"` | PASS |
| AC5: `npm test` unaffected | Quality-runner confirmed 59 passed, 0 failed | PASS |
| AC6 (clarified): package `.gitignore` | `serve/cockpit/web/.gitignore` contains `test-results/`, `playwright-report/` | PASS |
| AC7 (refined): smoke test | `smoke.spec.ts` navigates `/`, asserts `[data-region="workspace"]` visible via `toBeVisible()` | PASS |
| AC8 (new): browser install doc | Top-of-file comment in `playwright.config.ts`: `// Run once after install: npx playwright install chromium` | PASS |

### Code Notes

- Builder added `include: ['src/**/*.{test,spec}.{ts,tsx}']` to `vite.config.ts` vitest config — necessary for AC5 (prevents vitest from picking up `e2e/smoke.spec.ts`). Minimal, in scope.
- `process.env['CI']` vs `process.env.CI`: equivalent in JS/TS; bracket notation preferred in strict TS.
- `headless: true` is explicit per AC2; Playwright 1.46+ deprecated this in `use:` but `^1.59.1` still honors it. Not a blocker.
- Smoke test assertion (`toBeVisible()` on `[data-region="workspace"]`) is specific and would fail on broken implementation.

### Security

Dev tooling only. No secrets, no injection points, no user input. No concerns.

### Deductions

0 deductions.

### Verdict

Confidence: .95 → **PASS**
Action: → docs
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | New `test:e2e` script + Playwright E2E runner added. Added `E2E test runner` row to Cockpit Frontend table in `.github/copilot-instructions.md` — agents reading docs need to know about `npm run test:e2e` and the `npx playwright install chromium` prerequisite. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. All changes are TypeScript/npm. |
| 3 | External attribution | Yes | Verified | S1–S3 (playwright.dev/docs/test-webserver, playwright.dev/docs/test-configuration, vite.dev/config/preview-options) already added to `.owlbear/sources/overview.md` under `## Playwright E2E Infrastructure (Task #956)` at line 4142. No gaps. |
| 4 | CLI changes | Yes | Updated | Covered by Item 1 — `test:e2e` script documented in copilot-instructions.md. No README CLI section affected. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/956-playwright-e2e-infrastructure.md` exists and is linked from task body. No follow-up tasks were prescribed. |

### Files Updated

- `.github/copilot-instructions.md` — added E2E test runner row to Cockpit Frontend table

### Scratch Files Cleaned

- None found (`956-*` pattern returned no results in `.owlbear/scratch/`)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `@playwright/test` devDep | `package.json`: `"@playwright/test": "^1.59.1"` in devDependencies | PASS |
| AC2 (refined): config | `playwright.config.ts`: chromium project, `npm run build && npm run preview`, url/baseURL `http://localhost:4173`, `reuseExistingServer: !process.env['CI']`, `testDir: 'e2e'`, `headless: true` | PASS |
| AC3: `e2e/` directory | `e2e/smoke.spec.ts` exists | PASS |
| AC4: `test:e2e` script | `package.json` scripts: `"test:e2e": "playwright test"` | PASS |
| AC5: `npm test` unaffected | Reviewer confirmed 59 passed, 0 failed; `vite.config.ts` scopes vitest to `src/` via `include` | PASS |
| AC6 (clarified): package `.gitignore` | `serve/cockpit/web/.gitignore` contains `test-results/`, `playwright-report/` | PASS |
| AC7 (refined): smoke test | `smoke.spec.ts` navigates `/`, asserts `[data-region="workspace"]` toBeVisible() | PASS |
| AC8 (new): browser install doc | Top comment in `playwright.config.ts`: `// Run once after install: npx playwright install chromium` | PASS |

### Test Results

- pytest (full suite): 594 passed, 6 failed, ruff clean
- 6 failures all in mcp-knowledge/knowledge domain (get_stats schema, top_k forwarding, skill doc) -- pre-existing, unrelated to #956
- 0 failures in task scope
- npm test (vitest): 59 passed per reviewer

### Architect Quality: 4/5

Original AC missed build step in webServer command and browser binary install. Challenger caught both; architect accepted and refined AC2, AC7, added AC8. Final AC was specific and verifiable. Minor gap filled during challenge loop -- system worked as designed.

### Deduction Breakdown

- AC lines with no evidence: 0 (8/8 verified)
- Lint violations: 0
- AC quality score: 4/5 (above threshold)
- Missing reviewer evidence: No (detailed, per-AC table)
- Full-suite failures in task scope: 0

### Confidence: .98

### Action: archive

### Notes

- Doc-writer added E2E test runner row to `.github/copilot-instructions.md` -- confirmed
- Builder's vitest `include` fix in vite.config.ts was necessary and minimal (AC5 protection)
- 6 pre-existing test failures in knowledge domain should be tracked separately
