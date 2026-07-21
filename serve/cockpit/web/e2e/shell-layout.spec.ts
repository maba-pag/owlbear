/**
 * Playwright coverage for the current Cockpit PCanvas shell layout.
 *
 * The old custom CSS grid sidecar contract is retired. These tests guard the
 * present top-level shape: PCanvas owns layout, the right sidecar is absent,
 * the left workspace rail is compact, and task detail opens in a modal.
 */
import { test, expect, type Page } from '@playwright/test'

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

const TASK = {
  id: 1,
  title: 'PCanvas layout task',
  status: 'todo',
  priority: 'important',
  updated: '2026-05-16T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  dep_status: null,
}

const TASK_DETAIL = {
  ...TASK,
  body: '## Context\n\nTask detail renders in a modal.',
  created: '2026-05-16T00:00:00+00:00',
  claimed_at: null,
  parent: null,
  depends_on: [] as number[],
}

async function stubApis(page: Page): Promise<void> {
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
  await page.route('/health', (route) => route.fulfill({ json: {
    status: 'healthy',
    modules: Object.fromEntries(['tasks', 'requests', 'memory', 'ideas'].map((name) => [name, {
      status: 'healthy', findings: [], repairable_count: 0, checked_paths: [name],
    }])),
  } }))
  await page.route('/api/tasks/1', (route) => route.fulfill({ json: TASK_DETAIL }))
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: [TASK], mtime: 1_747_353_600 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/memories', (route) => route.fulfill({ json: { entries: [] } }))
  await page.route('/api/ideas', (route) => route.fulfill({ json: { content: '# Direct load' } }))
}

test.describe('PCanvas shell layout', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  test('PCanvas is the shell root and owns the compact start-sidebar width', async ({ page }) => {
    const shell = page.locator('p-canvas.shell')
    await expect(shell).toBeVisible()
    await expect(shell).toHaveAttribute('data-no-sidecar', '')

    const sidebarWidth = await shell.evaluate((el) =>
      getComputedStyle(el).getPropertyValue('--p-canvas-sidebar-start-width').trim(),
    )
    expect(sidebarWidth).toBe('72px')
  })

  test('header-end status bar stays visible while the board workspace scrolls', async ({ page }) => {
    await page.locator('[data-region="workspace"]').evaluate((el) => {
      const spacer = document.createElement('div')
      spacer.style.height = '2000px'
      el.appendChild(spacer)
      el.scrollTop = 1500
    })

    await expect(page.locator('[data-region="status-bar"]')).toBeVisible()
    await expect(page.getByTestId('app-identity')).toBeVisible()
    await expect(page.getByRole('img', { name: 'Porsche' })).toHaveCount(0)

    const viewport = page.viewportSize()
    const identityBox = await page.getByTestId('app-identity').boundingBox()
    const statusBox = await page.locator('[data-region="status-bar"]').boundingBox()

    expect(viewport).not.toBeNull()
    expect(identityBox).not.toBeNull()
    expect(statusBox).not.toBeNull()
    expect(statusBox!.x + statusBox!.width).toBeGreaterThan(viewport!.width - 96)
    expect(statusBox!.x).toBeGreaterThan(identityBox!.x + identityBox!.width + 300)
  })

  test('workspace status uses a compact transparent target with a visible state light', async ({ page }) => {
    const badge = page.locator('[data-testid="workspace-status"]')
    const light = page.locator('[data-testid="traffic-light"]')
    await expect(badge).toBeVisible()
    await expect(light).toBeVisible()

    const badgeBox = await badge.boundingBox()
    const style = await badge.evaluate((element) => {
      const computed = getComputedStyle(element)
      return {
        backgroundColor: computed.backgroundColor,
        borderTopWidth: computed.borderTopWidth,
      }
    })

    expect(badgeBox).not.toBeNull()
    expect(badgeBox!.width).toBeGreaterThanOrEqual(30)
    expect(badgeBox!.width).toBeLessThanOrEqual(36)
    expect(badgeBox!.height).toBeGreaterThanOrEqual(30)
    expect(badgeBox!.height).toBeLessThanOrEqual(36)
    expect(style).toEqual({ backgroundColor: 'rgba(0, 0, 0, 0)', borderTopWidth: '0px' })
    await expect(light).toHaveAttribute('data-health', 'healthy')
  })

  test('start sidebar contains icon-only workspace navigation', async ({ page }) => {
    const navRail = page.locator('[slot="sidebar-start"][data-region="nav-rail"]')
    await expect(navRail).toBeVisible()
    await expect(navRail.locator('[data-surface="kanban"]')).toHaveAttribute('aria-label', 'Kanban')
    await expect(navRail.locator('[data-surface="kanban"] p-icon')).toBeVisible()
    await expect(navRail.locator('[data-surface="kanban"]')).not.toContainText('Kanban')
  })

  test('start sidebar close event hides the workspace navigation on desktop', async ({ page }) => {
    const navRail = page.locator('[slot="sidebar-start"][data-region="nav-rail"]')
    await expect(navRail).toBeVisible()

    await page.locator('p-canvas.shell').evaluate((element) => {
      element.dispatchEvent(
        new CustomEvent('sidebarStartUpdate', {
          detail: { open: false },
          bubbles: true,
        }),
      )
    })

    await expect(navRail).not.toBeVisible()
    await expect(navRail).toHaveAttribute('aria-hidden', 'true')
    await expect(navRail.locator('[data-surface="kanban"]')).toHaveAttribute('tabindex', '-1')
  })

  test('retired right sidecar and collapse state are absent', async ({ page }) => {
    await expect(page.locator('[data-region="sidecar"]')).toHaveCount(0)
    await expect(page.locator('[slot="sidebar-end"]')).toHaveCount(0)
    await expect(page.locator('[slot="sidebar-end-header"]')).toHaveCount(0)
    await expect(page.locator('[data-testid="sidecar-collapse"]')).toHaveCount(0)
    await expect(page.locator('.shell')).not.toHaveAttribute('data-sidecar-collapsed', /.+/)
  })

  test('task detail opens as a modal without changing shell width', async ({ page }) => {
    const before = await page.locator('[data-region="workspace"]').boundingBox()
    expect(before).not.toBeNull()

    await page.locator('[data-testid="task-card"]').click()
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()
    await expect(page.locator('[data-region="sidecar"]')).toHaveCount(0)

    const after = await page.locator('[data-region="workspace"]').boundingBox()
    expect(after).not.toBeNull()
    expect(Math.abs(after!.width - before!.width)).toBeLessThan(1)
  })
})

test.describe('PCanvas shell at 1280px desktop width', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  test('no sidecar width is reserved at 1280px', async ({ page }) => {
    await expect(page.locator('[data-region="sidecar"]')).toHaveCount(0)
    const workspace = await page.locator('[data-region="workspace"]').boundingBox()
    expect(workspace).not.toBeNull()
    expect(workspace!.width).toBeGreaterThan(1_100)
  })

  test('task detail modal remains inside the viewport at 1280px', async ({ page }) => {
    await page.locator('[data-testid="task-card"]').click()
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()

    const windowBox = await page.locator('[data-region="task-detail-window"]').boundingBox()
    expect(windowBox).not.toBeNull()
    expect(windowBox!.x).toBeGreaterThanOrEqual(0)
    expect(windowBox!.x + windowBox!.width).toBeLessThanOrEqual(1280)
  })
})

test.describe('PCanvas modal containment at desktop floor', () => {
  test.use({ viewport: { width: 1024, height: 900 } })

  test('task detail modal remains inside the 1024px viewport', async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
    await page.locator('[data-testid="task-card"]').click()
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()

    const viewport = page.viewportSize()
    const windowBox = await page.locator('[data-region="task-detail-window"]').boundingBox()
    const editButtonBox = await page.locator('[data-testid="edit-details-button"]').boundingBox()

    expect(viewport).not.toBeNull()
    for (const box of [windowBox, editButtonBox]) {
      expect(box).not.toBeNull()
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width)
      expect(box!.y).toBeGreaterThanOrEqual(0)
      expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height)
    }
  })
})

test.describe('PCanvas shell on direct workspace routes', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('direct Ideas route waits for the shell grid before painting workspace content', async ({ page }) => {
    await stubApis(page)
    await page.goto('/ideas')
    await page.locator('[data-region="ideas-workspace"]').waitFor({ state: 'visible' })

    const workspace = await page.locator('[data-region="workspace"]').boundingBox()
    const ideas = await page.locator('[data-region="ideas-workspace"]').boundingBox()
    const statusBar = await page.locator('[data-region="status-bar"]').boundingBox()
    const editor = await page.locator('[data-testid="ideas-editor-shell"]').boundingBox()
    const statePanel = await page.locator('[data-testid="ideas-state-panel"]').boundingBox()

    expect(workspace).not.toBeNull()
    expect(ideas).not.toBeNull()
    expect(statusBar).not.toBeNull()
    expect(editor).not.toBeNull()
    expect(statePanel).not.toBeNull()
    expect(workspace!.width).toBeGreaterThan(1_000)
    expect(ideas!.width).toBeGreaterThan(1_000)
    expect(statusBar!.x + statusBar!.width).toBeGreaterThan(1_340)
    expect(statusBar!.width).toBeLessThan(180)
    expect(statePanel!.x).toBeGreaterThan(editor!.x + editor!.width)
    expect(Math.abs(statePanel!.y - editor!.y)).toBeLessThan(4)
  })

  test('direct Memory route keeps its restored header metric without a leading separator', async ({ page }) => {
    await stubApis(page)
    await page.goto('/memories')
    await page.locator('[data-testid="memory-tab"]').waitFor({ state: 'visible' })

    const metrics = page.locator('[data-testid="workspace-header-metric"]')
    await expect(metrics).toHaveCount(1)

    const firstMetric = await metrics.nth(0).evaluate((metric) => {
      const value = metric.querySelector('strong')
      return {
        borderLeftWidth: getComputedStyle(metric).borderLeftWidth,
        valueFontSize: value ? getComputedStyle(value).fontSize : null,
      }
    })

    expect(firstMetric.borderLeftWidth).toBe('0px')
    expect(Number.parseFloat(firstMetric.valueFontSize ?? '0')).toBeGreaterThan(20)
  })
})

test.describe('PCanvas shell on direct workspace routes at minimum desktop width', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test('direct Memory route gives filters enough width at 1280px', async ({ page }) => {
    await stubApis(page)
    await page.goto('/memories')
    await page.locator('[data-testid="memory-tab"]').waitFor({ state: 'visible' })

    const panel = await page.locator('[data-testid="memory-filter-panel"]').boundingBox()
    const stateFilter = await page.locator('p-multi-select[name="state-filter"]').boundingBox()
    const categoryFilter = await page.locator('p-multi-select[name="category-filter"]').boundingBox()
    const agentFilter = await page.locator('p-select[name="agent-filter"]').boundingBox()
    const searchFilter = await page.locator('p-input-search[name="memory-search"]').boundingBox()

    expect(panel).not.toBeNull()
    expect(stateFilter).not.toBeNull()
    expect(categoryFilter).not.toBeNull()
    expect(agentFilter).not.toBeNull()
    expect(searchFilter).not.toBeNull()
    expect(panel!.width).toBeGreaterThan(1_100)
    expect(stateFilter!.width).toBeGreaterThan(300)
    expect(categoryFilter!.x).toBeGreaterThan(stateFilter!.x + stateFilter!.width)
    expect(agentFilter!.y).toBeGreaterThan(stateFilter!.y + stateFilter!.height - 2)
    expect(Math.abs(searchFilter!.y - agentFilter!.y)).toBeLessThan(2)
  })
})
