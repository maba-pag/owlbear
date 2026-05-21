import { test, expect, type Locator, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

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

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] as const

async function stubApis(page: Page): Promise<{ puts: string[] }> {
  const state = {
    content: '# Morning shape\n\n- [ ] Review inbox\n- [x] Keep the board moving',
    puts: [] as string[],
  }

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
  await page.route('/api/memories', (route) => route.fulfill({ json: { entries: [] } }))
  await page.route('/api/decisions/pending', (route) => route.fulfill({ json: { count: 0, items: [] } }))
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))
  await page.route('/api/ideas', async (route) => {
    if (route.request().method() === 'PUT') {
      const payload = route.request().postDataJSON() as { content?: string }
      state.content = payload.content ?? ''
      state.puts.push(state.content)
      await route.fulfill({ status: 204, body: '' })
      return
    }

    await route.fulfill({ json: { content: state.content } })
  })

  return state
}

async function openIdeas(page: Page): Promise<void> {
  await page.goto('/ideas')
  await expect(page.locator('[data-region="ideas-workspace"]')).toBeVisible({ timeout: 8_000 })
  await expect(page.locator('textarea[aria-label="Ideas draft"]')).toBeVisible({ timeout: 8_000 })
}

async function expectPButtonDisabled(locator: Locator): Promise<void> {
  await expect(locator).toHaveJSProperty('disabled', true)
  await expect(locator).toHaveAttribute('aria-disabled', 'true')
}

async function expectPButtonEnabled(locator: Locator): Promise<void> {
  await expect(locator).toHaveJSProperty('disabled', false)
  await expect(locator).not.toHaveAttribute('aria-disabled', 'true')
}

function formatViolations(
  violations: Array<{
    id: string
    impact?: string | null
    help: string
    nodes: Array<{ html: string }>
  }>,
): string {
  if (violations.length === 0) return 'no violations'
  return violations
    .map(
      (violation) =>
        `[${violation.impact ?? 'unknown'} - ${violation.id}] ${violation.help}\n  ${violation.nodes
          .map((node) => node.html)
          .join('\n  ')}`,
    )
    .join('\n\n')
}

for (const theme of ['light', 'dark'] as const) {
  test.describe(`Ideas workspace (${theme})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((selectedTheme) => {
        window.localStorage.setItem('owlbear-theme', selectedTheme)
      }, theme)
    })

    test('loads, edits, saves, previews, and passes WCAG checks', async ({ page }) => {
      const state = await stubApis(page)
      await openIdeas(page)

      await expect(page.getByRole('heading', { name: 'Ideas' })).toBeVisible()
      const saveButton = page.locator('[data-testid="ideas-save"]')
      await expectPButtonDisabled(saveButton)
      await page.locator('textarea[aria-label="Ideas draft"]').fill('# Polished morning\n\nA calm cockpit surface.')
      await expect(page.locator('[data-testid="ideas-dirty"]')).toBeVisible()
      await expectPButtonEnabled(saveButton)

      await saveButton.click()
      await expect(page.locator('[data-testid="ideas-dirty"]')).toHaveCount(0)
      expect(state.puts).toEqual(['# Polished morning\n\nA calm cockpit surface.'])

      await page.locator('[data-testid="ideas-preview-toggle"]').click()
      await expect(page.locator('[data-testid="ideas-preview"] h1')).toHaveText('Polished morning')

      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })
  })
}
