import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Locator, type Page } from '@playwright/test'

interface Rectangle {
  left: number
  right: number
  top: number
  bottom: number
}

function overlap(first: Rectangle, second: Rectangle): boolean {
  return first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top
}

async function expectNoOverlap(locator: Locator): Promise<void> {
  const rectangles = await locator.evaluateAll((nodes) => nodes.map((node) => {
    const rectangle = node.getBoundingClientRect()
    return { left: rectangle.left, right: rectangle.right, top: rectangle.top, bottom: rectangle.bottom }
  }))
  for (let first = 0; first < rectangles.length; first += 1) {
    for (let second = first + 1; second < rectangles.length; second += 1) {
      expect(overlap(rectangles[first], rectangles[second])).toBe(false)
    }
  }
}

async function inspect(page: Page, title: string): Promise<Locator> {
  const card = page.locator('[data-work-item]').filter({ hasText: title })
  await card.getByText('Inspect', { exact: true }).click()
  const detail = page.getByTestId('work-item-detail')
  await expect(detail.getByRole('heading', { name: title })).toBeVisible()
  return detail
}

async function selectValue(locator: Locator, value: string): Promise<void> {
  await locator.evaluate((element, selected) => {
    ;(element as HTMLElement & { value: string }).value = selected
    element.dispatchEvent(new CustomEvent('change', { detail: { value: selected }, bubbles: true }))
  }, value)
}

async function inputValue(locator: Locator, value: string): Promise<void> {
  await locator.evaluate((element, input) => {
    ;(element as HTMLElement & { value: string }).value = input
    element.dispatchEvent(new CustomEvent('input', { detail: { value: input }, bubbles: true }))
  }, value)
}

async function openHistoryWithKeyboard(page: Page): Promise<void> {
  const currentTab = page.getByRole('tab', { name: 'Current' })
  await currentTab.focus()
  await currentTab.press('ArrowRight')
  await expect(page.getByTestId('completed-history-workspace')).toBeVisible()
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>): string {
  return violations.map((item) => `[${item.impact ?? 'unknown'} ${item.id}] ${item.help}`).join('\n')
}

test.describe('assembled Work portfolio', () => {
  test.describe.configure({ mode: 'serial' })

  test('desktop runs bounded controls and completed semantic history', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/work')

    await expect(page.getByTestId('cockpit-shell')).toBeVisible()
    const navRail = page.getByTestId('desktop-product-navigation')
    await expect(navRail).toBeVisible()
    const railBox = await navRail.boundingBox()
    expect(railBox).not.toBeNull()
    expect(railBox!.width).toBeLessThan(100)
    await expect(navRail.locator('p-link-pure')).toHaveCount(3)
    for (const navigationItem of await navRail.locator('p-link-pure').all()) {
      const itemBox = await navigationItem.boundingBox()
      expect(itemBox).not.toBeNull()
      expect(itemBox!.width).toBeLessThanOrEqual(56)
      expect(itemBox!.height).toBeLessThanOrEqual(56)
    }
    await expect(page.locator('[data-work-item]')).toHaveCount(6)
    for (const label of ['Design', 'Planning', 'Implementation', 'Assembly', 'Completed']) {
      await expect(page.getByText(label, { exact: true })).toBeVisible()
    }
    await expect(page.getByLabel('Attention totals')).toContainText('User 1')
    await expect(page.getByLabel('Attention totals')).toContainText('Waiting 1')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await expectNoOverlap(page.locator('[data-work-item]').filter({ visible: true }))

    let detail = await inspect(page, 'Choose release mode')
    await selectValue(detail.locator('p-select[name="request-request-release-mode-option"]'), 'safe')
    const answerResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().includes('/requests/request-release-mode/answer'))
    await detail.getByText('Submit answer', { exact: true }).click()
    expect((await answerResponse).status()).toBe(200)
    await expect(detail.getByRole('region', { name: 'Requests' }).locator('article p')).toHaveText('Safe rollout')

    detail = await inspect(page, 'Build operator controls')
    await detail.getByText('Recover confirmed-lost claim', { exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Confirm lost claim' })).toBeVisible()
    await page.getByText('Cancel', { exact: true }).click()
    const rejectedRecovery = await page.request.post('/api/changes/work-e2e/outcomes/OUT-002/claims/recover', {
      data: {
        confirmed_lost: false,
        attempt_id: 'attempt-work-e2e',
        claim_id: 'claim-work-e2e',
      },
    })
    expect(rejectedRecovery.status()).toBe(422)
    await expect(detail.getByText('Recover confirmed-lost claim', { exact: true })).toBeVisible()

    detail = await inspect(page, 'Assemble release')
    const retryResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/api/changes/work-e2e/integration/retry'))
    await detail.getByText('Retry Integration', { exact: true }).click()
    expect((await retryResponse).status()).toBe(409)
    await expect(detail.locator('p[role="alert"]')).toContainText('change is not ready for Integration')

    await selectValue(detail.locator('p-select[name="backward-stage"]'), 'planning')
    await inputValue(detail.locator('p-input-text[name="backward-reason"]'), 'Authority changed')
    await detail.getByText('Review backward move', { exact: true }).click()
    const moveResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/api/changes/work-e2e/outcomes/OUT-003/move-backward'))
    await page.getByText('Confirm backward move', { exact: true }).click()
    expect((await moveResponse).status()).toBe(200)
    await expect(detail.locator('p[role="status"]')).toContainText('Moved backward. Reset: OUT-003.')

    const listResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed')
    await openHistoryWithKeyboard(page)
    expect((await listResponsePromise).status()).toBe(200)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    const searchResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed/search')
    await inputValue(page.locator('p-input-search[name="completed-history-search"]'), 'Beta')
    expect((await searchResponsePromise).status()).toBe(200)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(1)
    await expect(page.getByText('Beta search', { exact: true })).toBeVisible()
    const showResponse = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed/completed-beta')
    await page.getByText('Inspect', { exact: true }).click()
    expect((await showResponse).status()).toBe(200)
    await expect(page.getByTestId('completed-change-detail')).toContainText('Beta search | Ship Beta search')

    const accessibility = await new AxeBuilder({ page }).analyze()
    const blocking = accessibility.violations.filter((violation) =>
      violation.impact === 'serious' || violation.impact === 'critical')
    expect(blocking, formatViolations(blocking)).toEqual([])
    await page.screenshot({ path: testInfo.outputPath('work-desktop-history.png'), fullPage: true })
  })

  test('mobile keeps current and completed work reachable without overlap', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/work')

    await expect(page.getByTestId('desktop-product-navigation')).not.toBeVisible()
    const navigationButton = page.getByText('Open navigation', { exact: true })
    await expect(navigationButton).toBeVisible()
    await navigationButton.click()
    const mobileNavigation = page.locator('p-flyout').getByRole('navigation', { name: 'Product areas' })
    await expect(mobileNavigation).toBeVisible()
    for (const label of ['Work', 'Memory', 'Ideas']) {
      await expect(mobileNavigation.getByText(label, { exact: true })).toBeVisible()
    }
    await page.keyboard.press('Escape')
    await expect(mobileNavigation).not.toBeVisible()
    await expect(page.locator('[data-work-item]')).toHaveCount(6)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await expectNoOverlap(page.locator('[data-work-item]').filter({ visible: true }))
    const detail = await inspect(page, 'Build operator controls')
    await expect(detail.getByText('Recover confirmed-lost claim', { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('work-mobile-detail.png'), fullPage: true })

    await detail.getByText('Close detail', { exact: true }).click()
    await openHistoryWithKeyboard(page)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    await expectNoOverlap(page.getByTestId('completed-change-record'))
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('work-mobile-history.png'), fullPage: true })
  })
})
