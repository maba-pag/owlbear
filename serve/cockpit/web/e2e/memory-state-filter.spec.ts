import { test, expect, type Page } from '@playwright/test'

const MEMORY_ENTRIES = [
  {
    id: 'memory-pending',
    title: 'Pending Memory',
    content: 'Pending content',
    categories: ['process'],
    confidence: 0.91,
    state: 'pending',
    scope_agents: ['builder'],
    source_agent: 'builder',
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    approved_at: null,
  },
  {
    id: 'memory-curated',
    title: 'Curated Memory',
    content: 'Curated content',
    categories: ['pitfall'],
    confidence: 0.82,
    state: 'curated',
    scope_agents: ['reviewer'],
    source_agent: 'reviewer',
    created_at: '2026-05-20T11:00:00Z',
    updated_at: '2026-05-20T11:00:00Z',
    approved_at: null,
  },
  {
    id: 'memory-approved',
    title: 'Approved Memory',
    content: 'Approved content',
    categories: ['preference'],
    confidence: 0.73,
    state: 'approved',
    scope_agents: ['architect'],
    source_agent: 'architect',
    created_at: '2026-05-20T12:00:00Z',
    updated_at: '2026-05-20T12:00:00Z',
    approved_at: '2026-05-20T12:30:00Z',
  },
  {
    id: 'memory-deleted',
    title: 'Deleted Memory',
    content: 'Deleted content',
    categories: ['obsolete'],
    confidence: 0.64,
    state: 'deleted',
    scope_agents: ['auditor'],
    source_agent: 'auditor',
    created_at: '2026-05-20T13:00:00Z',
    updated_at: '2026-05-20T13:00:00Z',
    approved_at: null,
  },
] as const

async function stubApis(page: Page): Promise<void> {
  await page.route('/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('/api/events', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
      body: '',
    }),
  )
  await page.route('/api/board', (route) =>
    route.fulfill({
      json: {
        statuses: [{ name: 'todo' }],
        priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
        valid_transitions: { todo: [] },
      },
    }),
  )
  await page.route('/api/tasks', (route) => route.fulfill({ json: { tasks: [], mtime: 1 } }))
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
  await page.route('/api/memories', (route) =>
    route.fulfill({ json: { entries: MEMORY_ENTRIES, parse_errors: 0 } }),
  )
}

test.describe('Memory state filter', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('state multi-select change event controls visible rows and shown count', async ({ page }) => {
    await stubApis(page)
    await page.goto('/memories')

    const titles = page.getByTestId('memory-entry-title')
    await expect(titles).toHaveText(['Pending Memory', 'Curated Memory', 'Approved Memory'])
    await expect(page.getByTestId('workspace-header-metric')).toHaveText(/3\s*of\s*4\s*shown/)

    await page.locator('p-multi-select[name="state-filter"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('change', { detail: { value: ['deleted'] }, bubbles: true }))
    })

    await expect(titles).toHaveText(['Deleted Memory'])
    await expect(page.getByTestId('workspace-header-metric')).toHaveText(/1\s*of\s*4\s*shown/)
  })
})
