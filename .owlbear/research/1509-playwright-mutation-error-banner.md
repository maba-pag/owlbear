# Playwright E2E Test: Mutation Error Banner

> **Owning task:** #1509 — Cockpit: Playwright E2E test for mutation error banner
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

Task #1509 (child of #1494) requests a Playwright E2E test for the PDS PBanner
mutation error banner. The Vitest unit test coverage is comprehensive (56 tests
across 3 files, all passing — see research from #1500). The only gap is E2E
validation of the banner in a real browser with PDS web components rendering
their shadow DOM.

**Question:** What selectors, mock patterns, and shadow DOM interaction
strategies should the E2E test use?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | PDS `banner.tsx` source (GitHub) — shadow DOM structure, `dismiss` event | 0.95 |
| S2 | PDS `banner.e2e.ts` (GitHub) — close button selector, event testing | 0.95 |
| S3 | PDS default-dom snapshot `p-banner.txt` — rendered shadow DOM tree | 1.00 |
| S4 | `accessibility-1395.spec.ts` — LIFO route-stub pattern (`stubApis`) | 1.00 |
| S5 | `kanban-board.spec.ts` — route mock, fixture data, board assertions | 0.95 |
| S6 | `bench_959.spec.ts` — context-menu trigger + transition click flow | 0.90 |
| S7 | `Shell.tsx` — PBanner wiring (`bannerError`, `onDismiss`) | 1.00 |
| S8 | `KanbanBoard.tsx` — `handleTransitionClick`, `onMutationError` call | 1.00 |

## 3. Analysis

### 3a. PDS Shadow DOM Structure (from S3)

```text
<p-banner>
  #shadow-root
    <div popover="manual" aria-hidden="true|false" role="status">
      <div class="notification">
        <slot></slot>
        <p-button class="dismiss hydrated">Close banner</p-button>
      </div>
    </div>
```

### 3b. Selector Strategy

| Element | Selector | Source |
|---------|----------|-------|
| Banner host | `page.locator('p-banner')` | S1 |
| Banner popover | `page.locator('p-banner [popover]')` | S2, S3 |
| Dismiss button | `page.locator('p-banner [popover] .dismiss')` | S2, S3 |
| Banner open check | `getAttribute('open')` or `[popover]` visibility | S2 |
| Context menu | `[data-testid="context-menu"]` | S6 |
| Transition item | `[data-testid="transition-item"][data-status="..."]` | S6 |

Playwright auto-pierces shadow DOM with `.locator()` — no `page.evaluate()`
fallback needed. Confirmed by PDS's own E2E tests (S2).

### 3c. Dismiss Mechanisms

| Method | How | Source |
|--------|-----|--------|
| Click dismiss button | `page.locator('p-banner [popover] .dismiss').click()` | S2 |
| Escape key | `page.keyboard.press('Escape')` | S2 |

Both fire the `dismiss` CustomEvent on the host, which React binds to
`onDismiss={() => setBannerError(null)}` (S7).

### 3d. API Mock Pattern

From S4 (`accessibility-1395.spec.ts`), the proven pattern registers
catch-all first (LIFO):

```ts
await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
// Then specific routes override for /api/board, /api/tasks, etc.
// Finally, /api/tasks/*/move mocked to 500 for error scenario.
```

### 3e. Error Trigger Flow

From S8 (`KanbanBoard.tsx:196-230`):

1. Right-click task card → context menu appears
2. Click transition item → calls `handleTransitionClick`
3. `moveTask()` calls `POST /api/tasks/{id}/move`
4. On 500 error → `onMutationError('Move failed', message, 'error')`
5. Shell sets `bannerError` → PBanner renders with `open=true`

### 3f. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| PDS shadow DOM selector breaks on upgrade | Low | Use PDS's own selector pattern (`.dismiss` class) — stable across v3 |
| Banner render timing | Low | Use `waitFor({ state: 'visible' })` on the popover |
| Context menu positioning | Low | Already proven in bench_959.spec.ts |
| Route mock ordering | Medium | LIFO pattern documented; catch-all first |

## 4. Recommendation (confidence: 0.90)

**T1 — Autonomous.** This is a straightforward E2E test following established
patterns from the existing test suite. No architectural decisions needed.

Implementation: single file `e2e/mutation-error-banner.spec.ts` with 3 tests
matching the AC. Use `stubApis()` helper pattern from accessibility spec, add
move-specific route override for error/success scenarios.

Challenge: skipped — trivial testing task with clear patterns, no trade-offs.

## 5. Follow-up Tasks

1. **Build `e2e/mutation-error-banner.spec.ts`** — already captured as #1509
   itself (task is ready to advance to backlog for architecture review).
