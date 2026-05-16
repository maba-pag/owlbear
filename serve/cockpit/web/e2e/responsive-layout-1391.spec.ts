/**
 * RED-phase Playwright E2E tests for #1391: Cockpit responsive dashboard layout.
 *
 * BUILDER INSTRUCTION (#1392): This file MUST be committed as a tracked artifact:
 *   cp .owlbear/scratch/1391-e2e-v2.spec.ts serve/cockpit/web/e2e/responsive-layout-1391.spec.ts
 *   git add serve/cockpit/web/e2e/responsive-layout-1391.spec.ts
 * Verify the E2E tests also FAIL before implementing the fix.
 *
 * Improved over v1 (1391-e2e.spec.ts) per reviewer RF1–RF4:
 *   RF1: Added 1440px viewport coverage (AC1 complete).
 *   RF2: Added board-scroller internal overflow test and task-detail/sidecar reachability.
 *   RF3: Added all-7-columns simultaneously visible test at 1024px and 1440px.
 *   RF4: Surface coverage (AC4) expanded with status-bar, nav-rail, all states at mobile.
 *
 * Expected to FAIL against the current implementation:
 *   Shell.css grid: fixed 56px 1fr 360px with zero @media queries.
 *   At 320px → workspace=0px; sidecar extends to 416px → off-screen.
 *   At 768px → workspace=352px, sidecar=360px → sidecar wider than board.
 *   Board columns container has overflowX:auto → internal horizontal scroll at 320px/768px.
 *   All surfaces inside workspace (columns, cards, states, affordances) → invisible at 320px.
 *
 * Tests at 1024px and 1440px that PASS with the current fixed grid are noted inline.
 * The failing tests at 320px/768px are the primary RED evidence.
 *
 * API mocking: all routes stubbed via page.route() — no real backend required.
 * Viewport: overridden per describe block via test.use({ viewport: ... }).
 */
import { test, expect, type Page } from '@playwright/test'

// ─── Constants ─────────────────────────────────────────────────────────────────

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['critical', 'needed', 'important', 'nice-to-have', 'someday']

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: PRIORITIES,
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  } as Record<string, string[]>,
}

function makePopulatedTasks() {
  return STATUSES.map((status, i) => ({
    id: i + 1,
    title: `Task in ${status}`,
    status,
    priority: PRIORITIES[i % PRIORITIES.length],
    updated: '2026-05-10T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  }))
}

/** One task in backlog only — remaining columns show empty-column state. */
const TASKS_EMPTY_COLUMNS = [
  {
    id: 1,
    title: 'Backlog Task',
    status: 'backlog',
    priority: 'important',
    updated: '2026-05-10T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  },
]

const POPULATED_TASKS = makePopulatedTasks()

// ─── API stub helpers ──────────────────────────────────────────────────────────

async function stubApis(page: Page, tasks: object[] = POPULATED_TASKS): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: '',
    }),
  )
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks, mtime: 1_713_456_000 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
}

async function stubApiError(page: Page): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: '',
    }),
  )
  await page.route('/api/tasks', (route) =>
    route.fulfill({ status: 500, json: { detail: 'error' } }),
  )
  await page.route('/api/board', (route) =>
    route.fulfill({ status: 500, json: { detail: 'error' } }),
  )
}

async function stubApiNeverResolves(page: Page): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: '',
    }),
  )
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: [], mtime: 0 } }),
  )
  await page.route('/api/board', (_route) => {
    /* intentionally never responds — keeps app in loading state */
  })
}

// ─── AC1: Viewport usability at 320px, 768px, 1024px, 1440px ──────────────────

test.describe('TestFromAC_ViewportUsability', () => {
  test.describe('at 320px viewport', () => {
    test.use({ viewport: { width: 320, height: 800 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
    })

    // RED: grid 56+0+360=416px → workspace width=0px → not visible
    test('workspace region has positive rendered width at 320px', async ({ page }) => {
      await expect(
        page.locator('[data-region="workspace"]'),
        'workspace must have non-zero rendered width at 320px',
      ).toBeVisible()
    })

    // RED: total grid=416px > viewport=320px → horizontal overflow at document level
    test('shell produces no horizontal overflow at document level at 320px', async ({ page }) => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      )
      expect(overflow, 'shell must not overflow horizontally at 320px').toBe(false)
    })
  })

  test.describe('at 768px viewport', () => {
    test.use({ viewport: { width: 768, height: 1024 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
    })

    // RED: workspace=352px, sidecar=360px → sidecar wider than board workspace
    test('workspace region is wider than sidecar region at 768px', async ({ page }) => {
      const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()
      const sidecarBox = await page.locator('[data-region="sidecar"]').boundingBox()
      expect(workspaceBox, 'workspace bounding box must exist at 768px').not.toBeNull()
      expect(sidecarBox, 'sidecar bounding box must exist at 768px').not.toBeNull()
      expect(
        workspaceBox!.width,
        `workspace (${workspaceBox!.width}px) must be wider than sidecar (${sidecarBox!.width}px) at 768px`,
      ).toBeGreaterThan(sidecarBox!.width)
    })

    // RED: 352/768=45.8% < 50%
    test('workspace region occupies more than 50% of viewport width at 768px', async ({ page }) => {
      const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()
      expect(workspaceBox, 'workspace bounding box must exist at 768px').not.toBeNull()
      const pct = workspaceBox!.width / page.viewportSize()!.width
      expect(
        pct,
        `workspace (${(pct * 100).toFixed(1)}%) must exceed 50% at 768px`,
      ).toBeGreaterThan(0.5)
    })

    // AC1: 56+1fr+360 fills viewport at 768px (1fr=352px) -> no document overflow.
    test('shell produces no horizontal overflow at document level at 768px', async ({ page }) => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      )
      expect(overflow, 'shell must not overflow horizontally at 768px').toBe(false)
    })
  })

  // 1024px: workspace=608px (59.4%) — documents AC1 coverage; workspace proportion PASSES.
  test.describe('at 1024px viewport', () => {
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
    })

    test('workspace region occupies more than 50% of viewport width at 1024px', async ({
      page,
    }) => {
      const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()
      expect(workspaceBox).not.toBeNull()
      const pct = workspaceBox!.width / page.viewportSize()!.width
      expect(
        pct,
        `workspace (${(pct * 100).toFixed(1)}%) must exceed 50% at 1024px`,
      ).toBeGreaterThan(0.5)
    })

    // AC1: 56+1fr+360 fills viewport at 1024px (1fr=608px) -> no document overflow.
    test('shell produces no horizontal overflow at document level at 1024px', async ({ page }) => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      )
      expect(overflow, 'shell must not overflow horizontally at 1024px').toBe(false)
    })
  })

  // 1440px: workspace=1024px (71.1%) — documents AC1 full-viewport coverage.
  test.describe('at 1440px viewport', () => {
    test.use({ viewport: { width: 1440, height: 900 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
    })

    test('workspace region occupies more than 50% of viewport width at 1440px', async ({
      page,
    }) => {
      const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()
      expect(workspaceBox).not.toBeNull()
      const pct = workspaceBox!.width / page.viewportSize()!.width
      expect(
        pct,
        `workspace (${(pct * 100).toFixed(1)}%) must exceed 50% at 1440px`,
      ).toBeGreaterThan(0.5)
    })

    // AC1: 56+1fr+360 fills viewport at 1440px (1fr=1024px) -> no document overflow.
    test('shell produces no horizontal overflow at document level at 1440px', async ({ page }) => {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      )
      expect(overflow, 'shell must not overflow horizontally at 1440px').toBe(false)
    })
  })
})

// ─── AC2: Mobile reachability — board, board-scroller, sidecar/task-detail ─────
// At 320px: workspace=0px → board invisible; sidecar at 416px → off-screen.
// Board column container (overflowX: auto) has 0px clientWidth → internal overflow.
// All tests FAIL against current fixed grid.

test.describe('TestFromAC_MobileReachability', () => {
  test.use({ viewport: { width: 320, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
  })

  // RED: board columns inside workspace=0px → non-zero width → not visible
  test('board column list has non-zero rendered area at 320px (board is reachable)', async ({
    page,
  }) => {
    const col = page.locator('[data-column]').first()
    await col.waitFor({ state: 'attached', timeout: 5_000 })
    await expect(col, 'board column must be visible at 320px').toBeVisible()
  })

  // RED: scrollWidth=416px > clientWidth=320px → requires document horizontal scrolling
  test('board content reachable without document-level horizontal scrolling at 320px', async ({
    page,
  }) => {
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    expect(overflow, 'board must be reachable without document horizontal scrolling at 320px').toBe(
      false,
    )
  })

  // RF2: board column container (KanbanBoard line ~291, overflowX: auto).
  // At 320px workspace=0px → container clientWidth=0 but column content makes scrollWidth>0 → overflow.
  // Proves the hidden horizontal-scroll-only failure inside the board scroller specifically.
  test('board column container does not require internal horizontal scrolling at 320px', async ({
    page,
  }) => {
    const col = page.locator('[data-column]').first()
    await col.waitFor({ state: 'attached', timeout: 5_000 })
    const result = await page.evaluate(() => {
      const firstCol = document.querySelector('[data-column]')
      if (!firstCol) return { overflow: true, scrollWidth: 0, clientWidth: 0 }
      const container = firstCol.parentElement
      if (!container) return { overflow: true, scrollWidth: 0, clientWidth: 0 }
      return {
        overflow: container.scrollWidth > container.clientWidth,
        scrollWidth: container.scrollWidth,
        clientWidth: container.clientWidth,
      }
    })
    expect(
      result.overflow,
      `board column container (clientWidth=${result.clientWidth}px, scrollWidth=${result.scrollWidth}px) must not require internal horizontal scrolling at 320px`,
    ).toBe(false)
  })

  // RED: sidecar x=56, width=360 → right edge=416px > 320px viewport → off-screen
  test('sidecar region is within viewport bounds at 320px (no horizontal scroll required)', async ({
    page,
  }) => {
    const sidecarBox = await page.locator('[data-region="sidecar"]').boundingBox()
    expect(sidecarBox, 'sidecar bounding box must exist at 320px').not.toBeNull()
    const viewportWidth = page.viewportSize()!.width
    expect(
      sidecarBox!.x + sidecarBox!.width,
      `sidecar right edge (${(sidecarBox!.x + sidecarBox!.width).toFixed(0)}px) must be within viewport (${viewportWidth}px) at 320px`,
    ).toBeLessThanOrEqual(viewportWidth)
  })

  // AC-1 (cycle-4 addition): last-column reachability via board-container scrollIntoView.
  // Proves the board container (scrollable parent of [data-column]) can bring the last column
  // into the viewport without introducing document-level horizontal overflow.
  test('last board column reachable via board-container scrollIntoView at 320px without document horizontal overflow', async ({
    page,
  }) => {
    const lastCol = page.locator('[data-column]').last()
    await lastCol.waitFor({ state: 'attached', timeout: 5_000 })
    // Scroll last column into view using the board container as the scroll surface.
    await page.evaluate(() => {
      const cols = Array.from(document.querySelectorAll('[data-column]'))
      if (cols.length === 0) return
      const lastColumn = cols[cols.length - 1] as HTMLElement
      lastColumn.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'nearest' })
    })
    await expect(
      lastCol,
      'last board column must be in viewport after board-container scrollIntoView at 320px',
    ).toBeInViewport()
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    expect(
      overflow,
      'document must not have horizontal overflow after last-column scrollIntoView at 320px',
    ).toBe(false)
  })

  // RF2: task-detail surface (Shell.tsx: detail-placeholder when no task selected) lives
  // inside sidecar. At 320px sidecar is off-screen → task-detail not reachable.
  // Proves the sidecar/task-detail surface is a hidden horizontal-scroll-only failure.
  test('task-detail surface (sidecar detail-placeholder) reachable without horizontal scrolling at 320px', async ({
    page,
  }) => {
    const detailBox = await page.locator('[data-testid="detail-placeholder"]').boundingBox()
    expect(detailBox, 'detail-placeholder bounding box must exist at 320px').not.toBeNull()
    const viewportWidth = page.viewportSize()!.width
    expect(
      detailBox!.x + detailBox!.width,
      `detail-placeholder right edge (${(detailBox!.x + detailBox!.width).toFixed(0)}px) must be within viewport (${viewportWidth}px)`,
    ).toBeLessThanOrEqual(viewportWidth)
  })
})

// ─── AC3: Desktop layout — all 7 status columns simultaneously visible ─────────
// RF3: all 7 [data-column] elements must be visible without horizontal scrolling
// in the board column container (KanbanBoard line ~291) at 1024px and 1440px.

test.describe('TestFromAC_AllColumnsVisible', () => {
  // 1024px: workspace=608px. After fix: repeat(7, minmax(200px,1fr)) → 7×200px=1400px > 608px → horizontal overflow.
  // RED: updated for #1596 — board-container overflow assertion flipped to expect horizontal scroll.
  test.describe('at 1024px viewport', () => {
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-column]').first().waitFor({ state: 'visible', timeout: 8_000 })
    })

    // AC3 (updated for #1596): board container must overflow horizontally at 1024px after fix.
    // repeat(7, minmax(200px,1fr)) → 7×200px=1400px > 608px workspace → scrollWidth > clientWidth.
    // RED: asserts overflow=true; fails against current auto-fit (wraps, no overflow).
    test('board column container overflows horizontally at 1024px with 7-column fixed layout (AC-3 #1596)', async ({
      page,
    }) => {
      const columnCount = await page.locator('[data-column]').count()
      expect(columnCount, 'all 7 status columns must be rendered at 1024px').toBe(7)

      const result = await page.evaluate(() => {
        const cols = Array.from(document.querySelectorAll('[data-column]'))
        if (cols.length === 0) return { overflow: false, scrollWidth: 0, clientWidth: 0 }
        const container = cols[0].parentElement
        if (!container) return { overflow: false, scrollWidth: 0, clientWidth: 0 }
        return {
          overflow: container.scrollWidth > container.clientWidth,
          scrollWidth: container.scrollWidth,
          clientWidth: container.clientWidth,
        }
      })
      expect(
        result.overflow,
        `board column container (scrollWidth=${result.scrollWidth}px, clientWidth=${result.clientWidth}px) must overflow horizontally at 1024px — 7×200px=1400px exceeds workspace width`,
      ).toBe(true)
    })

    // AC3: workspace must be wider than sidecar so board workspace dominates at desktop.
    test('workspace region is wider than sidecar at 1024px desktop viewport', async ({ page }) => {
      const workspaceBox = await page.locator('[data-region="workspace"]').boundingBox()
      const sidecarBox = await page.locator('[data-region="sidecar"]').boundingBox()
      expect(workspaceBox).not.toBeNull()
      expect(sidecarBox).not.toBeNull()
      expect(
        workspaceBox!.width,
        `workspace (${workspaceBox!.width}px) must exceed sidecar (${sidecarBox!.width}px) at 1024px`,
      ).toBeGreaterThan(sidecarBox!.width)
    })

    // AC-3 (cycle-4 addition): board container must not overflow vertically.
    // With repeat(auto-fit, minmax(200px, 1fr)) at 1024px, columns may wrap to multiple rows.
    // scrollHeight ≤ clientHeight proves all rows fit without vertical scrolling required.
    test('board column container has no vertical overflow at 1024px (scrollHeight ≤ clientHeight)', async ({
      page,
    }) => {
      const result = await page.evaluate(() => {
        const cols = Array.from(document.querySelectorAll('[data-column]'))
        if (cols.length === 0) return { overflow: true, scrollHeight: 0, clientHeight: 0 }
        const container = cols[0].parentElement
        if (!container) return { overflow: true, scrollHeight: 0, clientHeight: 0 }
        return {
          overflow: container.scrollHeight > container.clientHeight,
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight,
        }
      })
      expect(
        result.overflow,
        `board column container (scrollHeight=${result.scrollHeight}px, clientHeight=${result.clientHeight}px) must not require vertical scrolling at 1024px`,
      ).toBe(false)
    })

    // AC3 (2nd loop-breaker): each of the 7 columns must have positive rendered area,
    // not just DOM presence. Proves no column is zero-width or hidden due to grid constraints.
    test('each of the 7 status columns has positive rendered area at 1024px', async ({ page }) => {
      const columns = page.locator('[data-column]')
      const count = await columns.count()
      expect(count, 'all 7 status columns must be rendered at 1024px').toBe(7)
      for (let i = 0; i < count; i++) {
        await expect(
          columns.nth(i),
          `status column ${i + 1} must have positive rendered area (be visible) at 1024px`,
        ).toBeVisible()
      }
    })
  })

  // 1440px: workspace=1024px. After fix: repeat(7, minmax(200px,1fr)) → 7×200px=1400px > 1024px → horizontal overflow.
  // RED: updated for #1596 — board-container overflow assertion flipped to expect horizontal scroll.
  test.describe('at 1440px viewport', () => {
    test.use({ viewport: { width: 1440, height: 900 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-column]').first().waitFor({ state: 'visible', timeout: 8_000 })
    })

    // AC3 (updated for #1596): board container must overflow horizontally at 1440px after fix.
    // repeat(7, minmax(200px,1fr)) → 7×200px=1400px > 1024px workspace → scrollWidth > clientWidth.
    // RED: asserts overflow=true; fails against current auto-fit (wraps, no overflow).
    test('board column container overflows horizontally at 1440px with 7-column fixed layout (AC-3 #1596)', async ({
      page,
    }) => {
      const columnCount = await page.locator('[data-column]').count()
      expect(columnCount, 'all 7 status columns must be rendered at 1440px').toBe(7)

      const result = await page.evaluate(() => {
        const cols = Array.from(document.querySelectorAll('[data-column]'))
        if (cols.length === 0) return { overflow: false, scrollWidth: 0, clientWidth: 0 }
        const container = cols[0].parentElement
        if (!container) return { overflow: false, scrollWidth: 0, clientWidth: 0 }
        return {
          overflow: container.scrollWidth > container.clientWidth,
          scrollWidth: container.scrollWidth,
          clientWidth: container.clientWidth,
        }
      })
      expect(
        result.overflow,
        `board column container (scrollWidth=${result.scrollWidth}px, clientWidth=${result.clientWidth}px) must overflow horizontally at 1440px — 7×200px=1400px exceeds workspace width`,
      ).toBe(true)
    })

    // AC-3 (cycle-4 addition): board container must not overflow vertically at 1440px.
    test('board column container has no vertical overflow at 1440px (scrollHeight ≤ clientHeight)', async ({
      page,
    }) => {
      const result = await page.evaluate(() => {
        const cols = Array.from(document.querySelectorAll('[data-column]'))
        if (cols.length === 0) return { overflow: true, scrollHeight: 0, clientHeight: 0 }
        const container = cols[0].parentElement
        if (!container) return { overflow: true, scrollHeight: 0, clientHeight: 0 }
        return {
          overflow: container.scrollHeight > container.clientHeight,
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight,
        }
      })
      expect(
        result.overflow,
        `board column container (scrollHeight=${result.scrollHeight}px, clientHeight=${result.clientHeight}px) must not require vertical scrolling at 1440px`,
      ).toBe(false)
    })

    // AC3 (2nd loop-breaker): each of the 7 columns must have positive rendered area at 1440px.
    test('each of the 7 status columns has positive rendered area at 1440px', async ({ page }) => {
      const columns = page.locator('[data-column]')
      const count = await columns.count()
      expect(count, 'all 7 status columns must be rendered at 1440px').toBe(7)
      for (let i = 0; i < count; i++) {
        await expect(
          columns.nth(i),
          `status column ${i + 1} must have positive rendered area (be visible) at 1440px`,
        ).toBeVisible()
      }
    })
  })
})

// ─── AC4: Surface coverage — all major surfaces as one coherent experience ─────

// RF3/RF4: Desktop coverage at 1024px.
// status-bar, nav-rail: PASS (always visible in fixed grid areas).
// cards, filter, task-detail: PASS (workspace=608px at 1024px).
test.describe('TestFromAC_SurfaceCoverage', () => {
  test.describe('at 1024px desktop viewport', () => {
    test.use({ viewport: { width: 1024, height: 768 } })

    test.beforeEach(async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-column]').first().waitFor({ state: 'visible', timeout: 8_000 })
    })

    test('status-bar surface is visible at 1024px desktop viewport', async ({ page }) => {
      await expect(page.locator('[data-region="status-bar"]')).toBeVisible()
    })

    test('nav-rail surface is visible at 1024px desktop viewport', async ({ page }) => {
      await expect(page.locator('[data-region="nav-rail"]')).toBeVisible()
    })

    test('task card surface is accessible at 1024px desktop viewport', async ({ page }) => {
      await expect(page.locator('[data-testid="task-card"]').first()).toBeVisible()
    })

    test('filter-toggle affordance is accessible at 1024px desktop viewport', async ({ page }) => {
      await expect(page.locator('[data-testid="filter-toggle"]')).toBeVisible()
    })

    // RF3: task-detail surface (sidecar, detail-placeholder) visible at desktop.
    test('task-detail surface (detail-placeholder) is accessible at 1024px desktop viewport', async ({
      page,
    }) => {
      await expect(page.locator('[data-testid="detail-placeholder"]')).toBeVisible()
    })
  })

  // Mobile surface coverage at 320px.
  // status-bar, nav-rail: PASS (fixed grid areas always visible).
  // All surfaces inside workspace=0px: FAIL.
  test.describe('at 320px mobile viewport', () => {
    test.use({ viewport: { width: 320, height: 800 } })

    // status-bar spans all 3 grid columns → always visible. Documents AC4 coverage.
    test('status-bar surface is visible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      await expect(page.locator('[data-region="status-bar"]')).toBeVisible()
    })

    // nav-rail: fixed 56px column → always visible. Documents AC4 coverage.
    test('nav-rail surface is visible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      await expect(page.locator('[data-region="nav-rail"]')).toBeVisible()
    })

    // RED: board columns inside workspace=0px → invisible
    test('board columns surface is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const col = page.locator('[data-column]').first()
      await col.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(col, 'board column must be visible at 320px').toBeVisible()
    })

    // RED: task cards inside workspace=0px → invisible
    test('task card surface is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const card = page.locator('[data-testid="task-card"]').first()
      await card.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(card, 'task card must be visible at 320px').toBeVisible()
    })

    // RED: empty-column inside workspace=0px → invisible
    test('empty-column state surface is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page, TASKS_EMPTY_COLUMNS)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const empty = page.locator('[data-testid="empty-column"]').first()
      await empty.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(empty, 'empty-column must be visible at 320px').toBeVisible()
    })

    // RED: loading-indicator inside workspace=0px → invisible
    test('loading state surface is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApiNeverResolves(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const indicator = page.locator('[data-testid="loading-indicator"]')
      await indicator.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(indicator, 'loading-indicator must be visible at 320px').toBeVisible()
    })

    // RED: error-message inside workspace=0px → invisible
    test('error state surface is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApiError(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const error = page.locator('[data-testid="error-message"]')
      await error.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(error, 'error-message must be visible at 320px').toBeVisible()
    })

    // RED: filter-toggle inside workspace=0px → invisible
    test('filter-toggle affordance is accessible at 320px mobile viewport', async ({ page }) => {
      await stubApis(page)
      await page.goto('/')
      await page.locator('[data-region="status-bar"]').waitFor({ state: 'attached' })
      const toggle = page.locator('[data-testid="filter-toggle"]')
      await toggle.waitFor({ state: 'attached', timeout: 5_000 })
      await expect(toggle, 'filter-toggle must be visible at 320px').toBeVisible()
    })
  })
})
