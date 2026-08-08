import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Locator, type Page } from '@playwright/test'

async function visibleRows(page: Page): Promise<Locator> {
  return page.locator('[data-work-item]').filter({ visible: true })
}

async function inspect(page: Page, title: string): Promise<{ detail: Locator; trigger: Locator }> {
  const row = (await visibleRows(page)).filter({ hasText: title })
  const trigger = row.getByRole('link', { name: new RegExp(`^${title}`) })
  await trigger.click()
  const detail = page.getByTestId('work-item-detail')
  await expect(detail.getByRole('heading', { name: title })).toBeVisible()
  await expect(page).toHaveURL(/\/delivery\/[^/]+\/[^/]+$/)
  return { detail, trigger }
}

async function closeInspector(page: Page, trigger: Locator): Promise<void> {
  const splitClose = page.getByRole('button', { name: 'Close inspector' })
  if (await splitClose.isVisible()) {
    await splitClose.click()
  } else {
    await page.getByRole('button', { name: 'Dismiss flyout' }).click()
  }
  await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
  await expect(page).toHaveURL(/\/delivery$/)
  await expect(trigger).toBeFocused()
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

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    tables: [...document.querySelectorAll<HTMLElement>('[data-testid="work-table-scroll"]')]
      .filter((table) => table.getBoundingClientRect().height > 0)
      .map((table) => table.scrollWidth - table.clientWidth),
  }))
  expect(overflow.document).toBeLessThanOrEqual(0)
  expect(overflow.tables.every((value) => value <= 1)).toBe(true)
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>): string {
  return violations.map((item) => `[${item.impact ?? 'unknown'} ${item.id}] ${item.help}`).join('\n')
}

test.describe('assembled Delivery portfolio', () => {
  test.describe.configure({ mode: 'serial' })

  test('wide workspace uses grouped table, routed split inspector, and bounded controls', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/work')
    await expect(page).toHaveURL(/\/delivery$/)

    const table = page.getByTestId('work-portfolio-table')
    await expect(table).toBeVisible()
    await expect(await visibleRows(page)).toHaveCount(8)
    await expect(table).toContainText('Work portfolio E2E')
    await expect(table).toContainText('1 of 6 Outcomes complete')
    for (const column of ['Needs', 'Work item', 'Stage', 'Progress', 'Activity', 'Action']) {
      await expect(table.getByRole('columnheader', { name: column })).toHaveCount(2)
      await expect(table.getByRole('columnheader', { name: column }).first()).toBeVisible()
    }
    await expect(table).toContainText('Decision required')
    await expect(table).toContainText('Integration repairer working')
    await expect(table).toContainText('Waiting on OUT-002')
    await expect(table).toContainText('Complete')
    await expect(table).not.toContainText('Reviewed')

    const summary = page.getByLabel('Delivery portfolio status')
    await expect(summary).toContainText('8work items')
    await expect(summary).toContainText('2need you')
    await expect(summary).toContainText('1dependency')
    await expect(summary).toContainText('0need repair')
    await expect(summary).toContainText('1active')
    await expect(summary).toContainText('2ready')
    await expect(summary).toContainText('2complete')

    const integrationRow = (await visibleRows(page)).filter({ hasText: 'Integration' })
    await expect(integrationRow.locator('td').nth(2)).toHaveText('—')

    await page.getByTestId('work-filters-toggle').click()
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), 'dependency')
    await expect(page.getByTestId('work-shown-count')).toContainText('1 of 8')
    await expect(await visibleRows(page)).toHaveCount(1)
    await page.getByTestId('work-filters-reset').click()
    await expect(await visibleRows(page)).toHaveCount(8)
    await page.getByTestId('work-filters-toggle').click()

    const returnedRow = (await visibleRows(page)).filter({ hasText: 'Plan release notes' })
    const returnedTrigger = returnedRow.getByRole('link', { name: /^Plan release notes/ })
    const progressCell = returnedRow.locator('td').nth(3)
    const progressBox = await progressCell.boundingBox()
    expect(progressBox).not.toBeNull()
    await page.mouse.click(progressBox!.x + progressBox!.width / 2, progressBox!.y + progressBox!.height / 2)
    const returnedDetail = page.getByTestId('work-item-detail')
    await expect(returnedDetail.getByRole('heading', { name: 'Plan release notes' })).toBeVisible()
    await expect(returnedDetail).toContainText('Returned to Design — re-admission required')
    await expect(returnedDetail).toContainText('Evidence: request:release-notes-authority')
    await expect(returnedDetail).toContainText('Source boundary: design:release-notes-v2')
    await closeInspector(page, returnedTrigger)

    const requestRow = (await visibleRows(page)).filter({ hasText: 'Choose release mode' })
    const requestTrigger = requestRow.getByRole('link', { name: /^Choose release mode/ })
    await requestRow.getByRole('link', { name: 'Answer request' }).click()
    let inspected = { detail: page.getByTestId('work-item-detail'), trigger: requestTrigger }
    await expect(inspected.detail.getByRole('heading', { name: 'Choose release mode' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Close inspector' })).toBeVisible()
    await expect(inspected.detail).toContainText('Promise: Resolve the bounded release decision.')
    await expect(inspected.detail).toContainText('Observe Choose release mode.')
    await expectNoHorizontalOverflow(page)
    await selectValue(inspected.detail.locator('p-select[name="request-request-release-mode-option"]'), 'safe')
    const answerResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().includes('/requests/request-release-mode/answer'))
    await inspected.detail.getByText('Submit answer', { exact: true }).click()
    expect((await answerResponse).status()).toBe(200)
    await expect(inspected.detail).toContainText('Safe rollout')
    await closeInspector(page, inspected.trigger)

    inspected = await inspect(page, 'Integration')
    await expect(inspected.detail).toContainText('Repair in progress')
    await expect(inspected.detail).toContainText('A reviewed Integration repair is currently in progress.')
    await expect(inspected.detail).toContainText('Conflicting files')
    await expect(inspected.detail).toContainText('product.txt')
    await expect(inspected.detail).not.toContainText('Admit the independently reviewed repair.')
    await expect(inspected.detail).not.toContainText('Complete')
    await page.screenshot({ path: testInfo.outputPath('delivery-wide-repair-inspector.png'), fullPage: true })
    await closeInspector(page, inspected.trigger)

    inspected = await inspect(page, 'Build operator controls')
    await expect(inspected.detail).toContainText('Build OUT-002')
    await closeInspector(page, inspected.trigger)

    inspected = await inspect(page, 'Assemble release')
    await inspected.detail.getByText('Administrative actions', { exact: true }).click()
    await selectValue(inspected.detail.locator('p-select[name="backward-stage"]'), 'planning')
    await inputValue(inspected.detail.locator('p-input-text[name="backward-reason"]'), 'Authority changed')
    const previewResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/move-backward/preview'))
    await inspected.detail.getByText('Review backward move', { exact: true }).click()
    expect((await previewResponse).status()).toBe(200)
    const modal = page.locator('p-modal').filter({ hasText: 'The following Outcomes will be reset:' })
    await expect(modal).toContainText('OUT-003')
    const moveResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/outcomes/OUT-003/move-backward'))
    await modal.getByText('Confirm backward move', { exact: true }).click()
    expect((await moveResponse).status()).toBe(200)
    await expect(inspected.detail).toContainText('Moved backward. Reset: OUT-003.')
    await closeInspector(page, inspected.trigger)

    await expectNoHorizontalOverflow(page)
    const accessibility = await new AxeBuilder({ page }).analyze()
    const blocking = accessibility.violations.filter((violation) =>
      violation.impact === 'serious' || violation.impact === 'critical')
    expect(blocking, formatViolations(blocking)).toEqual([])
    await page.screenshot({ path: testInfo.outputPath('delivery-wide-table.png'), fullPage: true })
  })

  test('compact workspace uses a fully dismissed flyout and restores row focus', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 960, height: 800 })
    await page.goto('/delivery')

    await expect(await visibleRows(page)).toHaveCount(8)
    await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
    await expectNoHorizontalOverflow(page)

    const inspected = await inspect(page, 'Build operator controls')
    await expect(page.getByRole('button', { name: 'Close inspector' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Dismiss flyout' })).toBeVisible()
    await expect(inspected.detail).toContainText('Build OUT-002')
    await page.screenshot({ path: testInfo.outputPath('delivery-compact-flyout.png') })
    await closeInspector(page, inspected.trigger)

    await expect(page.locator('p-flyout').filter({ has: page.getByTestId('work-item-detail') })).toHaveCount(0)
    await expectNoHorizontalOverflow(page)
  })

  test('mobile rows preserve field semantics without overflow', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/delivery')

    const rows = await visibleRows(page)
    await expect(rows).toHaveCount(8)
    const integrationRow = rows.filter({ hasText: 'Integration' })
    for (const field of ['Needs', 'Work item', 'Stage', 'Progress', 'Activity', 'Action']) {
      await expect(integrationRow.getByText(field, { exact: true })).toBeVisible()
    }
    await expect(integrationRow).toHaveAttribute('aria-label', 'Integration work item')
    await expectNoHorizontalOverflow(page)
    const accessibility = await new AxeBuilder({ page }).analyze()
    const blocking = accessibility.violations.filter((violation) =>
      violation.impact === 'serious' || violation.impact === 'critical')
    expect(blocking, formatViolations(blocking)).toEqual([])
    await page.screenshot({ path: testInfo.outputPath('delivery-mobile-rows.png'), fullPage: true })
  })

  test('split threshold preserves all table columns without horizontal scrolling', async ({ page }) => {
    await page.setViewportSize({ width: 1408, height: 800 })
    await page.goto('/delivery')

    const inspected = await inspect(page, 'Build operator controls')
    await expect(page.getByRole('button', { name: 'Close inspector' })).toBeVisible()
    await expect(inspected.detail).toContainText('Build OUT-002')
    await expectNoHorizontalOverflow(page)
  })

  test('routed inspector survives reload and completed history remains reachable', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 760 })
    await page.goto('/delivery/work-e2e/outcome%3AOUT-005')

    const detail = page.getByTestId('work-item-detail')
    await expect(detail.getByRole('heading', { name: 'Publish operator guide' })).toBeVisible()
    await expect(detail).toContainText('Task evidence')
    await page.reload()
    await expect(detail.getByRole('heading', { name: 'Publish operator guide' })).toBeVisible()
    await expect(page.getByTestId('desktop-product-navigation').getByLabel('Delivery')).toHaveAttribute('aria-current', 'page')

    await page.getByRole('button', { name: 'Close inspector' }).click()
    const historyResponse = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed')
    await page.getByRole('button', { name: 'Completed history' }).click()
    expect((await historyResponse).status()).toBe(200)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    await expect(page.getByText('Alpha delivery', { exact: true })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('delivery-completed-history.png'), fullPage: true })
  })

  test('unknown paths render the global Not Found view', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto('/delivery/work-e2e')

    await expect(page.getByTestId('not-found-view')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('cockpit-not-found.png'), fullPage: true })
  })
})
