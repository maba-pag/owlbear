# Cockpit: Mutation Error Notification Tests

> **Owning task:** #1500 — Cockpit: Tests for mutation error banner and inline notification
> **Date:** 2026-05-12  **Status:** Complete

## 1. Context and Question

Task #1500 specifies Vitest unit tests and Playwright E2E tests for PDS notification components added by sibling tasks #1498 (PBanner in Shell) and #1499 (PInlineNotification in modals). The question is: what test coverage already exists, what gaps remain, and what implementation approach should the follow-up tasks use?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `Shell.pbanner-1498.test.tsx` — 20 Vitest tests (AC-1,5,6,7,8,9) | 1.00 |
| S2 | `KanbanBoard.pbanner-1498.test.tsx` — 10 Vitest tests (AC-2,6) | 1.00 |
| S3 | `PInlineNotification.modal-1499.test.tsx` — 26 Vitest tests (AC-1–7) | 1.00 |
| S4 | `ArchivalModal.test.tsx` + `ArchivalModal.error-body.test.tsx` — error display | 0.85 |
| S5 | `ResolveModal.test.tsx` — AC6 error rendering | 0.85 |
| S6 | PDS Banner API v3 (designsystem.porsche.com) — open attr, dismiss event | 0.90 |
| S7 | Existing E2E tests (`kanban-board.spec.ts`, `smoke.spec.ts`) — route mock pattern | 0.90 |

## 3. Analysis

### 3a. AC-to-Coverage Map

| AC Item | Test File(s) | Tests | Verdict |
|---------|-------------|-------|---------|
| PBanner appears on move/edit failure, correct state, dismiss | S1 (6 tests) + S2 (6 tests) | 12 | ✅ Covered |
| PBanner auto-clears on next successful mutation | S1 AC-6, AC-7 (3 tests) | 3 | ✅ Covered |
| PBanner survives selectedTaskId change | S1 AC-8 (2 tests) | 2 | ✅ Covered |
| PInlineNotification in ArchivalModal + retry | S3 AC-1,3,4,5,6,7 (14 tests) | 14 | ✅ Covered |
| PInlineNotification in ResolveModal | S3 AC-2,3,4,6 (12 tests) | 12 | ✅ Covered |
| **E2E: Banner on API error, dismiss, clear on retry** | **None** | 0 | ❌ Gap |

**All 5 Vitest AC items are fully covered** (56 passing tests across 3 files). The only gap is the Playwright E2E test.

### 3b. E2E Implementation Approach

| Criterion | Assessment |
|-----------|------------|
| PBanner DOM access | `<p-banner>` custom element; `open` reflected as HTML attr |
| Shadow DOM pierce | Dismiss button inside shadow root; Playwright auto-pierces with `.locator()` |
| API mock pattern | `page.route('/api/tasks/*/move', ...)` — same as kanban-board.spec.ts |
| Trigger mechanism | Context menu → transition click (proven in kanban-board.spec.ts) |
| Banner heading check | `page.locator('p-banner').getAttribute('heading')` |
| Dismiss interaction | Dispatch `dismiss` CustomEvent or click inner close button |
| "Clears on retry" | Second move with success mock; `p-banner` element hidden |

### 3c. E2E Test Plan

| # | Scenario | Steps | Assert |
|---|----------|-------|--------|
| 1 | Banner visible on API error | Mock move → 500; context-menu → click transition | `p-banner` visible, heading="Move failed" |
| 2 | Banner dismissible | Click dismiss on banner from (1) | `p-banner` hidden |
| 3 | Banner clears on retry success | Mock move → 200; repeat transition | No `p-banner[open]` present |

### 3d. E2E Risk: PDS Shadow DOM dismiss button

PDS `<p-banner>` dismiss button is `<p-button-pure>` inside shadow root. Playwright's `.locator()` can auto-pierce shadow DOM, but the exact selector needs verification at build time. Fallback: use `page.evaluate()` to dispatch `dismiss` CustomEvent on the host element.

## 4. Recommendation (confidence: 0.88)

**T1 — Autonomous.** Create a single follow-up task to add the Playwright E2E test file (`e2e/mutation-error-banner.spec.ts`). No new Vitest tests needed — existing coverage from #1498 and #1499 is comprehensive (56 tests, all passing).

Challenge: skipped — trivial testing gap with clear implementation path; no architectural decisions.

## 5. Follow-up Tasks

1. **Playwright E2E: mutation error banner** — Add `e2e/mutation-error-banner.spec.ts` covering banner visibility on API error, dismiss, and clear-on-retry-success (3 test cases). Use context-menu transition trigger, `page.route()` mocking, and shadow DOM piercing for PDS components.
