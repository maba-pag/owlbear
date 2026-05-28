import { test, expect, type Page } from '@playwright/test'

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

const BASE_TASK = {
  id: 1,
  title: 'Trigger mutation error banner',
  status: 'backlog',
  priority: 'important',
  updated: '2026-05-12T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

type MoveMode = 'error' | 'success'

async function stubApis(page: Page, getMoveMode: () => MoveMode): Promise<void> {
  // Catch-all must be first because Playwright route matching is LIFO.
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
  await page.route('/api/tasks', (route) =>
    route.fulfill({ json: { tasks: [BASE_TASK], mtime: 1_713_456_000 } }),
  )
  await page.route(/\/api\/tasks\/\d+$/, (route) => route.fulfill({ json: BASE_TASK }))
  await page.route('/api/sessions', (route) => route.fulfill({ json: { sessions: [] } }))
  await page.route('/api/tasks/scan', (route) => route.fulfill({ json: [] }))

  await page.route(/\/api\/tasks\/\d+\/move\/?(?:\?.*)?$/, async (route) => {
    if (getMoveMode() === 'error') {
      await route.fulfill({ status: 500, json: { detail: 'simulated move failure' } })
      return
    }

    await route.fulfill({
      status: 200,
      json: {
        ...BASE_TASK,
        status: 'todo',
      },
    })
  })
}

async function triggerMoveToTodo(page: Page) {
  const taskCard = page.locator('[data-testid="task-card"][data-id="1"]').first()
  await taskCard.waitFor({ state: 'visible', timeout: 8_000 })
  await taskCard.focus()
  await page.keyboard.press('Shift+F10')

  const contextMenu = page.locator('[data-testid="context-menu"]')
  await contextMenu.waitFor({ state: 'visible', timeout: 5_000 })

  const moveResponse = page.waitForResponse(
    (response) =>
      /\/api\/tasks\/\d+\/move\/?(?:\?.*)?$/.test(response.url()) &&
      response.request().method() === 'POST',
  )

  await page.click('[data-testid="transition-item"][data-status="todo"]')
  return moveResponse
}

async function expectMoveFailedBannerVisible(page: Page): Promise<void> {
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const banner = document.querySelector('p-banner') as
          | (HTMLElement & { heading?: string; open?: boolean })
          | null
        return {
          heading: banner?.heading ?? banner?.getAttribute('heading') ?? '',
          open: banner?.open ?? banner?.hasAttribute('open') ?? false,
        }
      }),
    )
    .toMatchObject({ open: true })

  await expect
    .poll(async () =>
      page.evaluate(() => {
        const banner = document.querySelector('p-banner') as
          | (HTMLElement & { heading?: string; open?: boolean })
          | null
        return banner?.heading ?? banner?.getAttribute('heading') ?? ''
      }),
    )
    .toContain('Move failed')
}

async function dismissBanner(page: Page): Promise<void> {
  const shadowDismiss = page.locator('p-banner [popover] .dismiss').first()
  if ((await shadowDismiss.count()) > 0) {
    await shadowDismiss.click()
    return
  }

  await page.evaluate(() => {
    const banner = document.querySelector('p-banner')
    const dismiss = banner?.shadowRoot?.querySelector<HTMLButtonElement>('.dismiss')
    dismiss?.click()
  })
}

test.describe('mutation error banner', () => {
  test('shows PBanner after /move returns 500', async ({ page }) => {
    const moveMode: MoveMode = 'error'
    await stubApis(page, () => moveMode)

    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })

    const moveResponse = await triggerMoveToTodo(page)
    expect(moveResponse.status()).toBe(500)
    await expectMoveFailedBannerVisible(page)
  })

  test('dismisses PBanner after mutation error', async ({ page }) => {
    const moveMode: MoveMode = 'error'
    await stubApis(page, () => moveMode)

    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })

    const moveResponse = await triggerMoveToTodo(page)
    expect(moveResponse.status()).toBe(500)
    await expectMoveFailedBannerVisible(page)

    await dismissBanner(page)
    await expect
      .poll(async () =>
        page.evaluate(() => {
          const banner = document.querySelector('p-banner') as
            | (HTMLElement & { heading?: string; open?: boolean })
            | null
          return {
            heading: banner?.heading ?? banner?.getAttribute('heading') ?? '',
            open: banner?.open ?? banner?.hasAttribute('open') ?? false,
          }
        }),
      )
      .toMatchObject({
        heading: '',
        open: false,
      })
  })

  test('clears banner after retry succeeds', async ({ page }) => {
    let moveMode: MoveMode = 'error'
    await stubApis(page, () => moveMode)

    await page.goto('/')
    await page.locator('[data-region="workspace"]').waitFor({ state: 'visible', timeout: 8_000 })

    const failedMoveResponse = await triggerMoveToTodo(page)
    expect(failedMoveResponse.status()).toBe(500)
    await expectMoveFailedBannerVisible(page)

    moveMode = 'success'
    const successfulMoveResponse = await triggerMoveToTodo(page)
    expect(successfulMoveResponse.status()).toBe(200)

    await expect
      .poll(async () =>
        page.evaluate(() => {
          const banner = document.querySelector('p-banner') as
            | (HTMLElement & { heading?: string; open?: boolean })
            | null
          return {
            heading: banner?.heading ?? banner?.getAttribute('heading') ?? '',
            open: banner?.open ?? banner?.hasAttribute('open') ?? false,
          }
        }),
      )
      .toMatchObject({
        heading: '',
        open: false,
      })
  })
})
