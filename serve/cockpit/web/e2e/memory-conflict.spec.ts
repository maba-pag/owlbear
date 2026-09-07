import { expect, test, type Page } from '@playwright/test'

const INITIAL_ENTRY = {
  id: 'entry-1',
  title: 'Draft title',
  content: 'Draft content',
  categories: ['process'],
  confidence: 0.9,
  score: 0.9,
  state: 'approved',
  outstanding_count: 0,
  scope_agents: ['builder'],
  source_agent: 'builder',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  approved_at: '2026-01-01T00:00:00Z',
  contested_by_task: null,
}

const CURRENT_ENTRY = {
  ...INITIAL_ENTRY,
  title: 'Server title',
  content: 'Server content',
  updated_at: '2026-01-02T00:00:00Z',
}

async function stubCockpitApis(page: Page): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) => route.fulfill({
    status: 200,
    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
    body: '',
  }))
  await page.route('/api/board', (route) => route.fulfill({
    json: {
      statuses: [{ name: 'todo' }],
      priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
      valid_transitions: { todo: [] },
    },
  }))
  await page.route('/api/tasks', (route) => route.fulfill({ json: { tasks: [], mtime: 1 } }))
  await page.route('/health', (route) => route.fulfill({ json: { status: 'healthy', modules: {} } }))

  let listRequests = 0
  let editRequests = 0
  await page.route('/api/memories', (route) => {
    if (route.request().method() !== 'GET') {
      return route.fulfill({ status: 405, json: { message: 'method not allowed' } })
    }
    listRequests += 1
    return route.fulfill({
      json: {
        entries: [listRequests === 1 ? INITIAL_ENTRY : CURRENT_ENTRY],
        parse_errors: 0,
      },
    })
  })
  await page.route('/api/memories/entry-1/edit', (route) => {
    editRequests += 1
    if (editRequests === 1) {
      return route.fulfill({ status: 409, json: { code: 'MEM_CONFLICT', message: 'Entry revision is stale' } })
    }
    return route.fulfill({ json: { entry: INITIAL_ENTRY } })
  })
}

async function openEntry(page: Page): Promise<ReturnType<Page['getByTestId']>> {
  const entry = page.getByTestId('memory-entry').first()
  await entry.locator('p-accordion').evaluate((element) => {
    ;(element as HTMLElement & { open: boolean }).open = true
    element.dispatchEvent(new CustomEvent('update', { detail: { open: true }, bubbles: true }))
  })
  await expect(entry.getByTestId('memory-accordion-detail')).toBeVisible()
  return entry
}

test.describe('Memory conflict recovery', () => {
  for (const viewport of [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
  ]) {
    test(`${viewport.name} conflict actions are keyboard reachable`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      await stubCockpitApis(page)
      await page.goto('/memory')

      const entry = await openEntry(page)
      await entry.getByTestId('memory-edit-btn').click()
      await entry.getByTestId('memory-edit-save-btn').click()
      await expect(entry.getByTestId('memory-conflict-panel')).toBeVisible()
      await expect(entry.getByTestId('memory-conflict-current-content')).toHaveText('Server content')

      const panel = entry.getByTestId('memory-conflict-panel')
      const reapply = entry.getByTestId('memory-conflict-reapply')
      await expect(panel).toBeFocused()
      await page.keyboard.press('Tab')
      await expect(entry.getByTestId('memory-conflict-reload')).toBeFocused()
      await page.keyboard.press('Tab')
      await expect(reapply).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
      await page.keyboard.press('Enter')
      await expect(entry.getByTestId('memory-conflict-panel')).toHaveCount(0)

      const save = entry.getByTestId('memory-edit-save-btn')
      await expect(save).toBeEnabled()
      await save.click()
      await expect(entry.getByTestId('memory-edit-form')).toHaveCount(0)
    })
  }
})
