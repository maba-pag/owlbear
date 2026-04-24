/**
 * Playwright E2E tests for #957: kanban board DnD highlights, card density, vertical scroll.
 *
 * Expected to FAIL in RED phase:
 *   - DnD: no dragover event handlers → data-drag-over attribute never set (confidence: 0.99)
 *   - Card density: no explicit height constraints → cards outside 48-56px range (confidence: 0.85)
 *   - Column height: maxHeight:100vh equals viewport height → bounded-constraint assertion fails (confidence: 1.0)
 *
 * API mocking: page.route() for /api/board and /api/tasks — no backend required.
 * Fixture: 50 tasks in 'backlog' (overflow), 3 in 'todo' (DnD valid target), 2 in 'done' (invalid).
 *
 * DnD pattern: double mouse.move() required for dragover events (Playwright docs).
 * Precondition assertion in beforeEach: [data-column] visible before each test.
 */
import { test, expect } from '@playwright/test'

// ─── Fixture data ─────────────────────────────────────────────────────────────

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

function makeTasks() {
  const tasks = []

  // 50 tasks in backlog — sufficient volume for scroll overflow testing
  for (let i = 1; i <= 50; i++) {
    tasks.push({
      id: i,
      title: `Backlog Task ${i}`,
      status: 'backlog',
      priority: 'important',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    })
  }

  // 3 tasks in todo — DnD valid target (backlog → todo is a valid transition)
  for (let i = 51; i <= 53; i++) {
    tasks.push({
      id: i,
      title: `Todo Task ${i}`,
      status: 'todo',
      priority: 'nice-to-have',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    })
  }

  // 2 tasks in done — DnD invalid target (backlog → done is NOT a valid transition)
  for (let i = 54; i <= 55; i++) {
    tasks.push({
      id: i,
      title: `Done Task ${i}`,
      status: 'done',
      priority: 'someday',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
    })
  }

  return tasks
}

const TASKS = makeTasks()

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('TestFromAC_KanbanBoardDnDDensityScroll', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('/api/board', async (route) => {
      await route.fulfill({ json: BOARD })
    })
    await page.route('/api/tasks', async (route) => {
      await route.fulfill({ json: { tasks: TASKS, mtime: 1713456000 } })
    })
    await page.goto('/')
    // Precondition: board columns visible before testing behaviour
    await page.locator('[data-column]').first().waitFor({ state: 'visible' })
  })

  // ─── AC: DnD highlights — valid target ────────────────────────────────────
  // drag card over a valid transition target → column gets data-drag-over="true"
  // RED: no dragover event handlers → attribute never set → assertion fails

  test('drag backlog card: valid target column (todo) receives data-drag-over="true"', async ({
    page,
  }) => {
    const sourceCard = page.locator('[data-column="backlog"] [data-testid="task-card"]').first()
    const targetCol = page.locator('[data-column="todo"]')

    const sourceBox = await sourceCard.boundingBox()
    expect(sourceBox, 'source card must be visible').not.toBeNull()
    const targetBox = await targetCol.boundingBox()
    expect(targetBox, 'target column must be visible').not.toBeNull()

    const sourceCx = sourceBox!.x + sourceBox!.width / 2
    const sourceCy = sourceBox!.y + sourceBox!.height / 2
    const targetCx = targetBox!.x + targetBox!.width / 2
    const targetCy = targetBox!.y + targetBox!.height / 2

    await page.mouse.move(sourceCx, sourceCy)
    await page.mouse.down()
    // Double-move pattern required for dragover events to fire (Playwright docs)
    await page.mouse.move(targetCx, targetCy)
    await page.mouse.move(targetCx, targetCy)

    // Valid target column must receive data-drag-over="true" during drag
    await expect(targetCol).toHaveAttribute('data-drag-over', 'true')

    await page.mouse.up()
  })

  // ─── AC: DnD highlights — valid highlighted, invalid not highlighted ───────
  // valid transition target gets data-drag-over="true"; invalid target does not
  // RED: fails at first assertion (valid target never gets attribute)

  test('drag backlog card: valid target (todo) highlighted, invalid target (done) not highlighted', async ({
    page,
  }) => {
    const sourceCard = page.locator('[data-column="backlog"] [data-testid="task-card"]').first()
    const validCol = page.locator('[data-column="todo"]')
    const invalidCol = page.locator('[data-column="done"]')

    const sourceBox = await sourceCard.boundingBox()
    expect(sourceBox, 'source card must be visible').not.toBeNull()
    const validBox = await validCol.boundingBox()
    expect(validBox, 'valid target column must be visible').not.toBeNull()
    const invalidBox = await invalidCol.boundingBox()
    expect(invalidBox, 'invalid target column must be visible').not.toBeNull()

    const sourceCx = sourceBox!.x + sourceBox!.width / 2
    const sourceCy = sourceBox!.y + sourceBox!.height / 2

    // Drag over valid target — must receive data-drag-over="true"
    await page.mouse.move(sourceCx, sourceCy)
    await page.mouse.down()
    const validCx = validBox!.x + validBox!.width / 2
    const validCy = validBox!.y + validBox!.height / 2
    await page.mouse.move(validCx, validCy)
    await page.mouse.move(validCx, validCy)
    await expect(validCol).toHaveAttribute('data-drag-over', 'true')

    // Drag over invalid target — must NOT receive data-drag-over="true"
    const invalidCx = invalidBox!.x + invalidBox!.width / 2
    const invalidCy = invalidBox!.y + invalidBox!.height / 2
    await page.mouse.move(invalidCx, invalidCy)
    await page.mouse.move(invalidCx, invalidCy)
    await expect(invalidCol).not.toHaveAttribute('data-drag-over', 'true')

    await page.mouse.up()
  })

  // ─── AC: Card density ─────────────────────────────────────────────────────
  // each [data-testid="task-card"] has rendered height between 48-56px
  // RED: no explicit height/min-height/padding CSS on cards → height outside range → fails

  test('all visible task cards have rendered height between 48-56px', async ({ page }) => {
    const cards = page.locator('[data-testid="task-card"]')
    const count = await cards.count()
    expect(count, 'board must render task cards').toBeGreaterThan(0)

    // Check first 10 cards (sufficient to cover the contract without excessive slowness)
    for (let i = 0; i < Math.min(count, 10); i++) {
      const box = await cards.nth(i).boundingBox()
      expect(box, `card ${i} must have a bounding box`).not.toBeNull()
      expect(
        box!.height,
        `card ${i} height ${box!.height}px must be ≥ 48px`,
      ).toBeGreaterThanOrEqual(48)
      expect(
        box!.height,
        `card ${i} height ${box!.height}px must be ≤ 56px`,
      ).toBeLessThanOrEqual(56)
    }
  })

  // ─── AC: Vertical scroll — column height constraint ───────────────────────
  // column must have a bounded max-height that accounts for shell chrome
  // so it acts as an independent scroll container within the workspace.
  // RED: current implementation uses maxHeight:100vh which equals viewport height —
  //      the column is not constrained below the viewport boundary → assertion fails.
  //
  // Note: horizontal scroll excluded from scope per architecture review — board
  // container already has overflowX:auto which would pass in RED.

  test('backlog column max-height is bounded below viewport height (accounts for shell chrome)', async ({
    page,
  }) => {
    const col = page.locator('[data-column="backlog"]')
    await col.waitFor({ state: 'visible' })

    const viewport = page.viewportSize()
    expect(viewport, 'viewport size must be available').not.toBeNull()

    // Column max-height must be strictly less than full viewport height to account
    // for the shell status bar, ensuring the column is a bounded scroll container
    // within the workspace grid area.
    // Current code: maxHeight:'100vh' = viewport.height → fails this assertion.
    const colMaxHeightPx = await col.evaluate((el) => {
      return parseFloat(window.getComputedStyle(el).maxHeight)
    })

    expect(
      colMaxHeightPx,
      `column max-height (${colMaxHeightPx}px) must be < viewport height` +
        ` (${viewport!.height}px) to account for shell chrome`,
    ).toBeLessThan(viewport!.height)
  })
})
