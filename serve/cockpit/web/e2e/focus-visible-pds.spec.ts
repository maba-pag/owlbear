/**
 * Browser focus-visible contract for the current Cockpit shell.
 *
 * Keyboard focus is product-relevant, so this keeps representative live controls
 * covered without preserving retired DecisionViewport or sidecar anatomy.
 */
import { test, expect, type Locator, type Page } from '@playwright/test'

const PDS_FOCUS_COLOR = 'rgb(26, 68, 234)'

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
  title: 'Focus ring test task',
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
  body: '## Context\n\nFocus visible proof task.',
  created: '2026-05-16T00:00:00+00:00',
  claimed_at: null,
  parent: null,
  depends_on: [] as number[],
}

const SESSIONS = {
  sessions: [
    {
      task_id: 1,
      state: 'released',
      agent: 'builder',
      started_at: '2026-05-16T09:00:00+00:00',
      duration: 120,
      outcome: 'success',
    },
  ],
}

const WORKSPACE_HEALTH = {
  status: 'healthy',
  modules: {
    tasks: { status: 'healthy', findings: [], repairable_count: 0, checked_paths: ['tasks'] },
    requests: { status: 'healthy', findings: [], repairable_count: 0, checked_paths: ['requests'] },
    memory: { status: 'healthy', findings: [], repairable_count: 0, checked_paths: ['memory'] },
    ideas: { status: 'healthy', findings: [], repairable_count: 0, checked_paths: ['ideas'] },
  },
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
  await page.route(/\/api\/sessions(\?.*)?$/, (route) => route.fulfill({ json: SESSIONS }))
  await page.route('/health', (route) => route.fulfill({ json: WORKSPACE_HEALTH }))
  await page.route('/api/tasks/1', (route) => route.fulfill({ json: TASK_DETAIL }))
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: [TASK], mtime: 1_713_456_000 } }),
  )
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/memories', (route) => route.fulfill({ json: { entries: [] } }))
}

async function tabUntilFocused(page: Page, locator: Locator, maxTabs = 50): Promise<void> {
  for (let i = 0; i < maxTabs; i++) {
    if (await locator.evaluate((element) => document.activeElement === element)) {
      return
    }
    await page.keyboard.press('Tab')
  }
}

async function expectPDSFocus(locator: Locator): Promise<void> {
  const focus = await locator.evaluate((element) => {
    const style = getComputedStyle(element)
    return {
      outlineStyle: style.outlineStyle,
      outlineColor: style.outlineColor,
      outlineOffset: style.outlineOffset,
    }
  })

  expect(focus.outlineStyle).toBe('solid')
  expect(focus.outlineColor).toBe(PDS_FOCUS_COLOR)
  expect(focus.outlineOffset).toBe('2px')
}

async function expectVisibleFocus(locator: Locator): Promise<void> {
  const focus = await locator.evaluate((element) => {
    const style = getComputedStyle(element)
    return {
      matchesFocusVisible: element.matches(':focus-visible'),
      outlineStyle: style.outlineStyle,
      outlineColor: style.outlineColor,
      outlineOffset: style.outlineOffset,
    }
  })

  expect(focus.matchesFocusVisible).toBe(true)
  expect(focus.outlineStyle).toBe('solid')
  expect(focus.outlineColor).not.toBe('rgba(0, 0, 0, 0)')
  expect(focus.outlineOffset).toBe('2px')
}

test.describe('focus-visible styling on live controls', () => {
  test.use({ viewport: { width: 1280, height: 800 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })
  })

  test('workspace status button receives PDS focus via Tab', async ({ page }) => {
    const workspaceStatus = page.locator('[data-testid="workspace-status"]')
    await workspaceStatus.waitFor({ state: 'visible' })
    await tabUntilFocused(page, workspaceStatus)
    await expect(workspaceStatus).toBeFocused()
    await expectVisibleFocus(workspaceStatus)
  })

  test('workspace nav button receives PDS focus via Tab', async ({ page }) => {
    const decisionsNav = page.locator('[data-surface="decisions"]')
    await tabUntilFocused(page, decisionsNav)
    await expect(decisionsNav).toBeFocused()
    await expectVisibleFocus(decisionsNav)
  })

  test('task card role button receives PDS focus via Tab', async ({ page }) => {
    const card = page.locator('[data-testid="task-card"]').first()
    await tabUntilFocused(page, card)
    await expect(card).toBeFocused()
    await expectPDSFocus(card)
  })

  test('task history session row receives PDS focus via Tab inside detail modal', async ({ page }) => {
    await page.locator('[data-testid="task-card"]').first().click()
    await expect(page.locator('[data-testid="task-detail-modal"]')).toBeVisible()
    await page.locator('[data-testid="history-tab"]').click()

    const sessionRow = page.locator('[data-testid="history-session-row"]').first()
    await expect(sessionRow).toBeVisible()
    await tabUntilFocused(page, sessionRow)
    await expect(sessionRow).toBeFocused()
    await expectPDSFocus(sessionRow)
  })
})
