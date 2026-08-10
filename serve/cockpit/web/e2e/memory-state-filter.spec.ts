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

const SCOPE_ENTRIES = [
  {
    id: 'memory-unscoped', title: 'Unscoped Memory', content: 'Unscoped content', categories: ['process'], confidence: 0.91, score: 0.91,
    state: 'pending', scope_agents: [], source_agent: 'builder', created_at: '2026-05-20T10:00:00Z', updated_at: '2026-05-20T10:00:00Z', approved_at: null,
  },
  {
    id: 'memory-all', title: 'All Agents Memory', content: 'All agents content', categories: ['pitfall'], confidence: 0.82, score: 0.82,
    state: 'curated', scope_agents: ['*'], source_agent: 'builder', created_at: '2026-05-20T11:00:00Z', updated_at: '2026-05-20T11:00:00Z', approved_at: null,
  },
  {
    id: 'memory-all-builder', title: 'All Builder Memory', content: 'Wildcard builder content', categories: ['process'], confidence: 0.73, score: 0.73,
    state: 'approved', scope_agents: ['*', 'builder'], source_agent: 'builder', created_at: '2026-05-20T12:00:00Z', updated_at: '2026-05-20T12:00:00Z', approved_at: '2026-05-20T12:30:00Z',
  },
  {
    id: 'memory-builder', title: 'Builder Memory', content: 'Builder content', categories: ['process'], confidence: 0.64, score: 0.64,
    state: 'pending', scope_agents: ['builder'], source_agent: 'builder', created_at: '2026-05-20T13:00:00Z', updated_at: '2026-05-20T13:00:00Z', approved_at: null,
  },
  {
    id: 'memory-pair', title: 'Named Pair Memory', content: 'Builder reviewer content', categories: ['preference'], confidence: 0.55, score: 0.55,
    state: 'curated', scope_agents: ['builder', 'reviewer'], source_agent: 'reviewer', created_at: '2026-05-20T14:00:00Z', updated_at: '2026-05-20T14:00:00Z', approved_at: null,
  },
  {
    id: 'memory-mode-all', title: 'Mode All Memory', content: 'Collision-safe content', categories: ['process'], confidence: 0.46, score: 0.46,
    state: 'approved', scope_agents: ['mode:all'], source_agent: 'builder', created_at: '2026-05-20T15:00:00Z', updated_at: '2026-05-20T15:00:00Z', approved_at: '2026-05-20T15:30:00Z',
  },
] as const

async function stubApis(page: Page, entries = MEMORY_ENTRIES): Promise<void> {
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
  await page.route('/health', (route) => route.fulfill({ json: {
    status: 'healthy',
    modules: Object.fromEntries(['tasks', 'requests', 'memory', 'ideas'].map((name) => [name, {
      status: 'healthy', findings: [], repairable_count: 0, checked_paths: [name],
    }])),
  } }))
  await page.route('/api/memories', (route) =>
    route.fulfill({ json: { entries, parse_errors: 0 } }),
  )
}

async function selectAgent(page: Page, value: string): Promise<void> {
  await page.locator('p-select[name="agent-filter"]').evaluate((element, selectedValue) => {
    element.dispatchEvent(new CustomEvent('change', { detail: { value: selectedValue }, bubbles: true }))
  }, value)
}

test.describe('Memory state filter', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('state multi-select change event controls visible rows and shown count', async ({ page }) => {
    await stubApis(page)
    await page.goto('/memory')

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

test.describe('Memory scope filter', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('agent modes preserve scope semantics, composition, labels, and shown count', async ({ page }) => {
    await stubApis(page, SCOPE_ENTRIES)
    await page.goto('/memory')

    const titles = page.getByTestId('memory-entry-title')
    const agentOptions = page.locator('p-select[name="agent-filter"] p-select-option')
    await expect(agentOptions).toHaveText(['Any agent', 'All agents', 'Unscoped', 'builder', 'mode:all', 'reviewer'])
    await expect(titles).toHaveText([
      'Unscoped Memory', 'All Agents Memory', 'All Builder Memory', 'Builder Memory', 'Named Pair Memory', 'Mode All Memory',
    ])
    await expect(page.getByTestId('workspace-header-metric')).toHaveText(/6\s*entries/)

    await selectAgent(page, 'mode:all')
    await expect(titles).toHaveText(['All Agents Memory', 'All Builder Memory'])
    await expect(page.getByTestId('workspace-header-metric')).toHaveText(/2\s*of\s*6\s*shown/)

    await selectAgent(page, 'mode:unscoped')
    await expect(titles).toHaveText(['Unscoped Memory'])

    await selectAgent(page, 'agent:builder')
    await expect(titles).toHaveText(['All Agents Memory', 'All Builder Memory', 'Builder Memory', 'Named Pair Memory'])

    await page.locator('p-multi-select[name="category-filter"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('change', { detail: { value: ['process'] }, bubbles: true }))
    })
    await expect(titles).toHaveText(['All Builder Memory', 'Builder Memory'])

    await page.locator('p-input-search[name="memory-search"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('input', { detail: { value: 'missing' }, bubbles: true }))
    })
    await expect(page.getByTestId('clear-filters')).toBeVisible()
    await page.getByTestId('clear-filters').click()
    await expect(titles).toHaveText([
      'Unscoped Memory', 'All Agents Memory', 'All Builder Memory', 'Builder Memory', 'Named Pair Memory', 'Mode All Memory',
    ])
    await expect(page.getByTestId('workspace-header-metric')).toHaveText(/6\s*entries/)

    await selectAgent(page, 'agent:mode%3Aall')
    await expect(titles).toHaveText(['All Agents Memory', 'All Builder Memory', 'Mode All Memory'])
    await expect(page.getByTestId('memory-entry-agents').nth(0)).toHaveText('All agents')
    await expect(page.getByTestId('memory-entry-agents').nth(2)).toHaveText('mode:all')

    await selectAgent(page, 'mode:unscoped')
    await page.locator('p-accordion').first().evaluate((element) => {
      element.dispatchEvent(new CustomEvent('update', { detail: { open: true }, bubbles: true }))
    })
    await expect(page.getByTestId('memory-accordion-detail').getByText('Unscoped', { exact: true })).toBeVisible()
  })
})
