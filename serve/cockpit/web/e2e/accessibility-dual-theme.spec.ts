import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] as const
const digest = 'a'.repeat(64)

const memories = [
  {
    id: 'memory-dualtheme-001', title: 'Morning operator cadence', content: 'Review memory and ideas before moving work.',
    categories: ['process'], confidence: 0.92, state: 'pending', scope_agents: ['builder'], source_agent: 'auditor',
    created_at: '2026-05-15T08:00:00+00:00', updated_at: '2026-05-16T08:00:00+00:00', approved_at: null,
  },
]

async function seed(page: Page) {
  // Playwright matches routes in reverse registration order, so the catch-all must be registered first.
  await page.route('**/api/**', (route) => route.fulfill({ status: 200, json: {} }))
  await page.route('**/api/changes', (route) => route.fulfill({ json: {
    changes: [{ change_id: 'change', state: 'loaded', delivery_digest: digest, diagnostics: [] }],
  } }))
  await page.route('**/api/events', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' }))
  await page.route('**/api/ideas', (route) => route.fulfill({ json: { content: '# Morning shape\n\n- [ ] Refine cockpit surfaces' } }))
  await page.route('**/api/memories', (route) => route.fulfill({ json: { entries: memories, parse_errors: 0 } }))
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>) {
  return violations.map((item) => `[${item.impact ?? 'unknown'} ${item.id}] ${item.help}`).join('\n')
}

for (const theme of ['light', 'dark'] as const) {
  test.describe(`preserved workflows: ${theme}`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((value) => localStorage.setItem('owlbear-theme', value), theme)
      await seed(page)
    })

    test(`Memory remains accessible under ${theme}`, async ({ page }) => {
      await page.goto('/memory?change=change')
      await expect(page.locator('html')).toHaveClass(new RegExp(`scheme-${theme}`))
      await expect(page.getByTestId('memory-entry').first()).toBeVisible()
      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })

    test(`Ideas remains accessible under ${theme}`, async ({ page }) => {
      await page.goto('/ideas?change=change')
      await expect(page.locator('html')).toHaveClass(new RegExp(`scheme-${theme}`))
      await expect(page.getByTestId('ideas-preview-toggle')).toBeVisible()
      await page.getByTestId('ideas-preview-toggle').click()
      await expect(page.locator('textarea[aria-label="Ideas draft"]')).toBeVisible()
      const results = await new AxeBuilder({ page }).withTags([...WCAG_TAGS]).analyze()
      expect(results.violations, formatViolations(results.violations)).toEqual([])
    })
  })
}
