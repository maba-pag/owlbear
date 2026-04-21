/**
 * Playwright benchmark tests for #959: 700-task board performance
 *
 * Tests mount time, scroll behaviour, and re-render cost against the
 * RAIL-model thresholds specified in the AC. All tests mock /api/board and
 * /api/tasks via page.route() — no real backend required.
 *
 * AC thresholds (from AC + research §3):
 *   - Mount time:   <500ms  (uniform 100/col and skewed 400/150/30)
 *   - Scroll:       column with 100+ tasks must have overflow-y auto/scroll;
 *                   <5% dropped frames (≤1 longtask per 30 rAF frames)
 *   - Re-render:    <100ms for state change (task move) with 700 cards present
 *
 * Fixture: SEED=42 deterministic LCG — mirrors KanbanBoard_959.test.tsx.
 *
 * RED-phase notes:
 *   - Tests that wait for [data-testid="kanban-board"] fail until the builder
 *     adds that testid to the board root div.
 *   - Scroll tests fail until the builder adds overflow-y + height constraints
 *     to column divs (required for independent column scrolling per AC).
 */
import { test, expect } from '@playwright/test'

// ─── SEED=42 deterministic LCG ────────────────────────────────────────────────
// Matches the implementation in KanbanBoard_959.test.tsx exactly.

function lcg(seed: number): () => number {
  let s = seed & 0xffffffff
  return (): number => {
    s = Math.imul(s, 1664525) + 1013904223
    s = s & 0xffffffff
    return (s >>> 0) / 0x100000000
  }
}

const STATUSES = ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']
const PRIORITIES = ['someday', 'nice-to-have', 'important', 'needed', 'critical']

interface TaskFixture {
  id: number
  title: string
  status: string
  priority: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
}

/** Uniform: 100 tasks per column × 7 columns = 700 */
function generateUniformTasks(seed = 42): TaskFixture[] {
  const rand = lcg(seed)
  return Array.from({ length: 700 }, (_, i) => {
    const r1 = rand()
    const r2 = rand()
    const r3 = rand()
    const blocked = r1 < 0.1
    return {
      id: i + 1,
      title: `Task ${i + 1}`,
      status: STATUSES[i % STATUSES.length],
      priority: PRIORITIES[Math.floor(r2 * PRIORITIES.length)],
      tags: [],
      blocked,
      block_reason: blocked ? `Blocked ${i + 1}` : null,
      claimed: r3 < 0.15,
    }
  })
}

/** Skewed: 400 backlog / 150 done / 30 each in remaining 5 statuses = 700 */
function generateSkewedTasks(seed = 42): TaskFixture[] {
  const rand = lcg(seed)
  const distribution: [string, number][] = [
    ['backlog', 400],
    ['done', 150],
    ['research', 30],
    ['todo', 30],
    ['in-progress', 30],
    ['review', 30],
    ['docs', 30],
  ]
  const tasks: TaskFixture[] = []
  let id = 1
  for (const [status, count] of distribution) {
    for (let j = 0; j < count; j++) {
      const r1 = rand()
      const r2 = rand()
      const r3 = rand()
      const blocked = r1 < 0.1
      tasks.push({
        id: id++,
        title: `Task ${id}`,
        status,
        priority: PRIORITIES[Math.floor(r2 * PRIORITIES.length)],
        tags: [],
        blocked,
        block_reason: blocked ? `Blocked ${id}` : null,
        claimed: r3 < 0.15,
      })
    }
  }
  return tasks
}

const BOARD = {
  statuses: STATUSES.map((name) => ({ name })),
  priorities: [...PRIORITIES],
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

// ─── Pre-generated fixtures (SEED=42) ─────────────────────────────────────────

const UNIFORM = generateUniformTasks(42)
const SKEWED = generateSkewedTasks(42)

// ─── Benchmark tests ──────────────────────────────────────────────────────────

test.describe('TestFromAC_Board700Performance', () => {
  // ─── AC: mount time <500ms — uniform distribution ──────────────────────────

  test('mount time <500ms — uniform 100 tasks/column (SEED=42)', async ({ page }) => {
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      await route.fulfill({ json: { tasks: UNIFORM, mtime: 1713456000 } })
    })

    const t0 = Date.now()
    await page.goto('/')
    // Board root testid required: builder must add data-testid="kanban-board"
    await page.waitForSelector('[data-testid="kanban-board"]', { timeout: 5000 })
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="task-card"]').length >= 700,
    )
    const elapsed = Date.now() - t0

    expect(elapsed).toBeLessThan(500)
  })

  // ─── AC: mount time <500ms — skewed distribution ───────────────────────────

  test('mount time <500ms — skewed (400 backlog / 150 done / 30 each remaining, SEED=42)', async ({
    page,
  }) => {
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      await route.fulfill({ json: { tasks: SKEWED, mtime: 1713456000 } })
    })

    const t0 = Date.now()
    await page.goto('/')
    // Board root testid required: builder must add data-testid="kanban-board"
    await page.waitForSelector('[data-testid="kanban-board"]', { timeout: 5000 })
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="task-card"]').length >= 700,
    )
    const elapsed = Date.now() - t0

    expect(elapsed).toBeLessThan(500)
  })

  // ─── AC: scroll 100+ card column — column must be independently scrollable ─
  // Requires overflow-y: auto (or scroll) + a height constraint on the column
  // div. Currently [data-column] has no overflow CSS — this test is RED.

  test('100+ card column has overflow-y auto or scroll', async ({ page }) => {
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      await route.fulfill({ json: { tasks: SKEWED, mtime: 1713456000 } })
    })

    await page.goto('/')
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="task-card"]').length >= 700,
    )

    // The backlog column has 400 tasks and must be independently scrollable.
    const overflowY = await page.evaluate(() => {
      const col = document.querySelector('[data-column="backlog"]')
      if (!col) return 'not-found'
      return window.getComputedStyle(col).overflowY
    })

    expect(overflowY, '[data-column="backlog"] must have overflow-y: auto or scroll').toMatch(
      /^(auto|scroll)$/,
    )
  })

  // ─── AC: scroll 100+ card column — <5% frame drops ────────────────────────
  // Uses PerformanceObserver(longtask) to count >50ms blocks during 30 rAF
  // frames of programmatic scroll. Also asserts scrollTop changes to confirm
  // the column is actually scrollable (fails if overflow-y is missing).

  test('scroll 400-card backlog column: scrollTop changes and <5% long tasks', async ({
    page,
  }) => {
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      await route.fulfill({ json: { tasks: SKEWED, mtime: 1713456000 } })
    })

    await page.goto('/')
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="task-card"]').length >= 700,
    )

    const result = await page.evaluate(() => {
      return new Promise<{ longTasks: number; finalScrollTop: number }>((resolve) => {
        const col = document.querySelector('[data-column="backlog"]') as HTMLElement | null
        if (!col) {
          resolve({ longTasks: -1, finalScrollTop: -1 })
          return
        }

        const longTaskEntries: PerformanceEntry[] = []
        const observer = new PerformanceObserver((list) => {
          longTaskEntries.push(...list.getEntries())
        })
        observer.observe({ entryTypes: ['longtask'] })

        // Scroll 667px per frame over 30 rAF frames ≈ 20,000px total
        let frame = 0
        function scrollStep(): void {
          col!.scrollTop += 667
          frame++
          if (frame < 30) {
            requestAnimationFrame(scrollStep)
          } else {
            // One extra frame to allow longtask observer to flush
            requestAnimationFrame(() => {
              observer.disconnect()
              resolve({ longTasks: longTaskEntries.length, finalScrollTop: col!.scrollTop })
            })
          }
        }
        requestAnimationFrame(scrollStep)
      })
    })

    // Column not found — structural failure
    expect(result.longTasks, 'backlog column element not found').not.toBe(-1)

    // scrollTop must have changed — proves overflow-y is set correctly
    expect(
      result.finalScrollTop,
      'scrollTop did not change — column needs overflow-y: auto and a height constraint',
    ).toBeGreaterThan(0)

    // <5% of 30 frames = at most 1 long task (>50ms block during scroll)
    expect(result.longTasks, 'too many long tasks during scroll').toBeLessThanOrEqual(1)
  })

  // ─── AC: re-render <100ms after state change with 700 cards ───────────────
  // Moves task-1 (research → backlog) and measures time from clicking the
  // transition to when task-1 appears in the backlog column. Timing is
  // measured inside the browser via performance.now() + MutationObserver.

  test('re-render after task move <100ms with 700 cards present', async ({ page }) => {
    let tasksRequestCount = 0
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      tasksRequestCount++
      if (tasksRequestCount === 1) {
        // Initial load
        await route.fulfill({ json: { tasks: UNIFORM, mtime: 1713456000 } })
      } else {
        // After move: task-1 (initially 'research') moved to 'backlog'
        const updated = UNIFORM.map((t) => (t.id === 1 ? { ...t, status: 'backlog' } : t))
        await route.fulfill({ json: { tasks: updated, mtime: 1713456001 } })
      }
    })
    await page.route('/api/tasks/1/move', async (route) => {
      await route.fulfill({ json: { ok: true }, status: 200 })
    })

    await page.goto('/')
    // Board root testid required: builder must add data-testid="kanban-board"
    await page.waitForSelector('[data-testid="kanban-board"]', { timeout: 5000 })
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="task-card"]').length >= 700,
    )

    // Inject a MutationObserver that records the time from __startMove() call
    // to when task-1 appears inside [data-column="backlog"].
    await page.evaluate(() => {
      ;(window as unknown as Record<string, unknown>)['__reRenderMs'] = null
      ;(window as unknown as Record<string, unknown>)['__startMove'] = (): void => {
        const start = performance.now()
        const observer = new MutationObserver(() => {
          if (document.querySelector('[data-column="backlog"] [data-id="1"]')) {
            ;(window as unknown as Record<string, unknown>)['__reRenderMs'] =
              performance.now() - start
            observer.disconnect()
          }
        })
        observer.observe(document.body, { childList: true, subtree: true })
      }
    })

    // Open context menu on task-1 (status: 'research'; transitions: ['backlog'])
    const taskCard = page.locator('[data-id="1"]').first()
    await taskCard.click({ button: 'right' })
    await page.waitForSelector('[data-testid="context-menu"]', { timeout: 5000 })

    // Start timing, then immediately click the transition
    await page.evaluate(() => {
      ;(window as unknown as Record<string, () => void>)['__startMove']()
    })
    await page.click('[data-testid="transition-item"][data-status="backlog"]')

    // Wait for MutationObserver to record the DOM update
    await page.waitForFunction(
      () => (window as unknown as Record<string, unknown>)['__reRenderMs'] !== null,
      { timeout: 5000 },
    )

    const renderMs = await page.evaluate(
      () => (window as unknown as Record<string, number>)['__reRenderMs'],
    )
    expect(renderMs, 're-render time after task move').toBeLessThan(100)
  })
})
