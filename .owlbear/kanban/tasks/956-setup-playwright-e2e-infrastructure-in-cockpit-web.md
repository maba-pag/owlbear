---
id: 956
title: Setup Playwright E2E infrastructure in cockpit web
status: research
priority: nice-to-have
created: 2026-04-18T13:49:17.508633+00:00
updated: 2026-04-18T13:49:17.508633+00:00
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