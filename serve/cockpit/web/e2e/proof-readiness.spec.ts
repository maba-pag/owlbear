import { test, expect, type Page } from '@playwright/test'
import { getWorkspaceReadinessSnapshot, waitForWorkspaceReady } from './support/workspace-readiness'

const BOARD = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['critical', 'needed', 'important', 'nice-to-have', 'someday'],
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

const MEMORY_ENTRIES = [
  {
    id: 'memory-proof-001',
    title: 'Morning operator cadence',
    content: 'Use stable route evidence before turning screenshots into Cockpit UX tasks.',
    categories: ['process', 'proof'],
    confidence: 0.92,
    state: 'pending',
    scope_agents: ['builder'],
    source_agent: 'auditor',
    created_at: '2026-05-24T08:00:00+00:00',
    updated_at: '2026-05-24T08:00:00+00:00',
    approved_at: null,
  },
]

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
  await page.route('/api/board', (route) => route.fulfill({ json: BOARD }))
  await page.route('/api/tasks', (route) => route.fulfill({ json: { tasks: [], mtime: 1_716_000_000 } }))
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/health', (route) => route.fulfill({ json: {
    status: 'healthy',
    modules: Object.fromEntries(['tasks', 'requests', 'memory', 'ideas'].map((name) => [name, {
      status: 'healthy', findings: [], repairable_count: 0, checked_paths: [name],
    }])),
  } }))
  await page.route('/api/memories', (route) =>
    route.fulfill({ json: { entries: MEMORY_ENTRIES, parse_errors: 0 } }),
  )
  await page.route('/api/ideas', (route) =>
    route.fulfill({
      json: {
        content: '# Morning shape\n\n- [x] Review stable proof\n- [ ] File only real UX findings',
      },
    }),
  )
}

test.describe('Cockpit proof readiness', () => {
  test.use({ viewport: { width: 1024, height: 768 } })

  test.beforeEach(async ({ page }) => {
    await stubApis(page)
  })

  test('memory route waits for final content, opacity, and transform before proof capture', async ({ page }) => {
    await page.goto('/memories')
    await waitForWorkspaceReady(page, { routeContentSelector: '[data-testid="memory-entry"]' })

    await expect(page.locator('[data-testid="memory-entry"]').first()).toContainText('Morning operator cadence')

    const readiness = await getWorkspaceReadinessSnapshot(page, {
      routeContentSelector: '[data-testid="memory-entry"]',
    })

    expect(readiness.panelCount).toBe(1)
    expect(readiness.panelOpacity).toBe(1)
    expect(readiness.panelTranslateY).toBe(0)
    expect(readiness.transformSettled).toBe(true)
    expect(readiness.routeLoadingVisible).toBe(false)
    expect(readiness.routeContentVisible).toBe(true)
    expect(readiness.stableAcrossFrames).toBe(true)
    expect(readiness.ready).toBe(true)
  })

  test('ideas route waits for rendered note content, opacity, and transform before proof capture', async ({ page }) => {
    await page.goto('/ideas')
    await waitForWorkspaceReady(page, { routeContentSelector: '[data-region="ideas-workspace"]' })

    await expect(page.locator('[data-testid="ideas-preview"]')).toContainText('Morning shape')

    const readiness = await getWorkspaceReadinessSnapshot(page, {
      routeContentSelector: '[data-region="ideas-workspace"]',
    })

    expect(readiness.panelCount).toBe(1)
    expect(readiness.panelOpacity).toBe(1)
    expect(readiness.panelTranslateY).toBe(0)
    expect(readiness.transformSettled).toBe(true)
    expect(readiness.routeLoadingVisible).toBe(false)
    expect(readiness.routeContentVisible).toBe(true)
    expect(readiness.stableAcrossFrames).toBe(true)
    expect(readiness.ready).toBe(true)
  })
})
