# E2E Kanban Board Tests: DnD, Density, Scroll — Research

> **Owning task:** #957 — RED: Playwright E2E tests for kanban board DnD, density, scroll
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #957 writes failing Playwright E2E tests for 3 kanban board behaviours that require a real browser: DnD target highlighting during mid-drag, card density (48-56px height), and horizontal/vertical scroll. Prior research (#955) chose Playwright Test; infrastructure (#956) is deployed.

**Key question:** What are the exact test patterns, API mocking strategy, and RED-phase considerations for these 3 tests?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | Playwright Mouse API (playwright.dev/docs/api/class-mouse) | 0.95 |
| S2 | Playwright Locator.boundingBox() (playwright.dev/docs/api/class-locator#locator-bounding-box) | 0.95 |
| S3 | Playwright DnD + Scrolling docs (playwright.dev/docs/input#drag-and-drop, #scrolling) | 0.95 |
| S4 | `.owlbear/research/955-e2e-kanban-board-tests.md` — framework comparison | 0.95 |
| S5 | `.owlbear/research/956-playwright-e2e-infrastructure.md` — infra config | 0.90 |
| S6 | `serve/cockpit/web/src/KanbanBoard.tsx` — current component (no DnD, no height control) | 0.95 |
| S7 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` — fixture data pattern | 0.90 |
| S8 | `serve/cockpit/web/playwright.config.ts` — live config, chromium only, port 4173 | 0.90 |

## 3. Analysis

### 3.1 API Mocking Strategy

E2E tests run against `vite preview` (port 4173) — no Python backend. Tests must intercept API calls with `page.route()` to provide fixture data.

| Endpoint | Mock response | Source |
|----------|--------------|--------|
| `/api/board` | Board config: 7 statuses, 5 priorities, valid_transitions map | S7 fixtures |
| `/api/tasks` | 4+ tasks across different statuses, priorities, blocked/claimed states | S7 fixtures |

Pattern: `beforeEach` hook calls `page.route('/api/board', ...)` and `page.route('/api/tasks', ...)` before `page.goto('/')`. Same fixture shape as unit tests [S7].

### 3.2 Test Patterns per AC

| AC Item | Playwright API | Selector | Assertion | Will Fail Because |
|---------|---------------|----------|-----------|-------------------|
| DnD highlights | `locator.hover()` → `mouse.down()` → `mouse.move()` → assert → `mouse.up()` [S1,S3] | `[data-testid="task-card"]`, `[data-column="{status}"]` | Column has highlight class/style during mid-drag | No DnD event handlers on component [S6] |
| Card density | `locator.boundingBox()` [S2] | `[data-testid="task-card"]` | `height >= 48 && height <= 56` | No explicit height styling on cards [S6] |
| Scroll (horizontal) | `mouse.wheel(deltaX, 0)` [S1] | Board container (`[style*="overflowX"]` or parent locator) | `scrollLeft > 0` after wheel | 7 columns may not overflow default viewport at preview size |
| Scroll (vertical) | `evaluate(e => e.scrollTop)` [S2] | Column `[data-column="{status}"]` | `scrollTop > 0` after scroll | No `overflow-y` on columns, no max-height constraint [S6] |

### 3.3 DnD Mid-Drag Pattern (Critical)

Playwright docs [S3] note: _"you need at least two mouse moves to trigger [dragover] in all browsers."_ The test sequence must be:

```
1. hover card → mouse.down()
2. mouse.move() to target column center (1st move)
3. mouse.move() to same position (2nd move — triggers dragover)
4. Assert highlight class/attribute on target column
5. mouse.move() to invalid column
6. mouse.move() again (2nd move for dragover)
7. Assert dim/no-highlight on invalid column
8. mouse.up()
```

This will fail cleanly — the component has zero DnD event listeners [S6].

### 3.4 RED Phase Guarantees

| Test | Failure mode | Confidence test fails |
|------|-------------|----------------------|
| DnD highlights | No DnD handlers → no highlight class added → assertion fails | 0.99 |
| Card density | Default div height ≠ constrained 48-56px range → assertion fails | 0.85 |
| Scroll horizontal | No viewport overflow OR no scroll handler → `scrollLeft === 0` | 0.80 |
| Scroll vertical | No `overflow-y`/`max-height` on columns → no scrollable overflow | 0.90 |

**Risk:** Card density test might accidentally pass if PDS styling + default text rendering produces a height in the 48-56px range. Mitigation: assert on multiple cards and ensure the range check is strict enough.

### 3.5 Available Test Selectors

From `KanbanBoard.tsx` [S6]:
- `[data-testid="task-card"]` + `[data-id="{N}"]` + `[data-priority="{p}"]`
- `[data-column="{status}"]` (column wrapper)
- `[data-testid="column-count"]`, `[data-testid="card-title"]`
- `[data-testid="loading-indicator"]`, `[data-testid="error-message"]`

## 4. Recommendation

**Proceed with implementation.** All Playwright APIs are confirmed, infra is in place, fixtures are available, and the component's current state guarantees test failures.

Confidence: **0.90**

The test-writer should use `page.route()` for API mocking, re-use the unit test fixture shape, and follow the double-mouse-move pattern for DnD tests. The only moderate risk is the card density test potentially passing by accident.

Challenge: SKIPPED — validation research on established approach, no alternative recommendation to challenge. Prior #955 research already underwent challenger review (block → revised to Playwright Test).

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #957 itself is the actionable output — it has concrete AC and implementation guidance.
