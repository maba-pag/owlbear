import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Locator, type Page } from '@playwright/test'

async function visibleRows(page: Page): Promise<Locator> {
  return page.locator('[data-work-item]').filter({ visible: true })
}

async function inspect(page: Page, title: string, detailTitle = title): Promise<{ detail: Locator; trigger: Locator }> {
  const row = (await visibleRows(page)).filter({ hasText: title })
  const trigger = row.getByRole('link', { name: new RegExp(`^${title}`) })
  await trigger.click()
  const detail = page.getByTestId('work-item-detail')
  await expect(detail.getByRole('heading', { name: detailTitle })).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Work Item detail' })).toBeVisible()
  await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
  await expect(page).toHaveURL(/\/delivery\/[^/]+\/[^/]+$/)
  return { detail, trigger }
}

async function returnToPortfolio(page: Page, trigger: Locator): Promise<void> {
  await page.getByRole('button', { name: 'Dismiss flyout' }).click()
  await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Work Item detail' })).not.toBeVisible()
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

async function flyoutPanelBox(page: Page): Promise<{ width: number; height: number } | null> {
  return page.locator('p-flyout').last().evaluate((element) => {
    const panel = element.shadowRoot?.querySelector('.flyout')
    if (!panel) return null
    const box = panel.getBoundingClientRect()
    return { width: box.width, height: box.height }
  })
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>): string {
  return violations.map((item) => `[${item.impact ?? 'unknown'} ${item.id}] ${item.help}`).join('\n')
}

test.describe('assembled Delivery portfolio', () => {
  test.describe.configure({ mode: 'serial' })

  test('wide workspace explains operating state and provides routed detail', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/work')
    await expect(page).toHaveURL(/\/delivery$/)

    const table = page.getByTestId('work-portfolio-table')
    await expect(table).toBeVisible()
    await expect(await visibleRows(page)).toHaveCount(8)
    await expect(table).toContainText('Work portfolio E2E')
    for (const column of ['Work', 'Pipeline', 'Current state']) {
      await expect(table.getByRole('columnheader', { name: column })).toHaveCount(2)
      await expect(table.getByRole('columnheader', { name: column }).first()).toBeVisible()
    }
    await expect(table).toContainText('Decision required')
    await expect(table).toContainText('Integration repairer working')
    await expect(table).toContainText('Waiting on OUT-002')
    await expect(table).toContainText('Done')
    await expect(table).not.toContainText('Reviewed')

    const summary = page.getByLabel('Delivery portfolio status')
    await expect(summary).toContainText('2unfinished Changes')
    await expect(summary).toContainText('1being worked on')
    await expect(summary).toContainText('2need you')

    const guidance = page.getByLabel('Recommended next steps')
    await expect(guidance).toContainText('Review 2 interventions')
    await expect(guidance).toContainText('Let the current /orchestrate session continue')
    await expect(guidance).not.toContainText('Start /orchestrate')

    const integrationRow = (await visibleRows(page)).filter({ hasText: 'Integration' })
    await expect(integrationRow).toContainText('Integration')
    await expect(integrationRow).toContainText('Change')

    await page.getByTestId('work-filters-toggle').click()
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), 'dependency')
    await expect(page.getByTestId('work-shown-count')).toContainText('1 of 8')
    await expect(await visibleRows(page)).toHaveCount(1)
    await page.getByTestId('work-filters-reset').click()
    await expect(await visibleRows(page)).toHaveCount(8)
    await page.getByTestId('work-filters-toggle').click()

    const returnedRow = (await visibleRows(page)).filter({ hasText: 'Plan release notes' })
    const returnedTrigger = returnedRow.getByRole('link', { name: /^Plan release notes/ })
    const progressCell = returnedRow.locator('td').nth(1)
    const progressBox = await progressCell.boundingBox()
    expect(progressBox).not.toBeNull()
    await page.mouse.click(progressBox!.x + progressBox!.width / 2, progressBox!.y + progressBox!.height / 2)
    const returnedDetail = page.getByTestId('work-item-detail')
    await expect(returnedDetail.getByRole('heading', { name: 'Plan release notes' })).toBeVisible()
    await expect(returnedDetail).toContainText('Returned to Design — re-admission required')
    await expect(returnedDetail).toContainText('Evidence: request:release-notes-authority')
    await expect(returnedDetail).toContainText('Source boundary: design:release-notes-v2')
    await returnToPortfolio(page, returnedTrigger)

    const requestRow = (await visibleRows(page)).filter({ hasText: 'Choose release mode' })
    const requestTrigger = requestRow.getByRole('link', { name: /^Choose release mode/ })
    await requestRow.getByRole('link', { name: 'Answer request' }).click()
    let inspected = { detail: page.getByTestId('work-item-detail'), trigger: requestTrigger }
    await expect(inspected.detail.getByRole('heading', { name: 'Choose release mode' })).toBeVisible()
    await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
    await expect(inspected.detail).toContainText('Resolve the bounded release decision.')
    await expect(inspected.detail).toContainText('Observe Choose release mode.')
    await expectNoHorizontalOverflow(page)
    await selectValue(inspected.detail.locator('p-select[name="request-request-release-mode-option"]'), 'safe')
    const answerResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().includes('/requests/request-release-mode/answer'))
    await inspected.detail.getByText('Submit answer', { exact: true }).click()
    expect((await answerResponse).status()).toBe(200)
    await expect(inspected.detail).toContainText('Safe rollout')
    await returnToPortfolio(page, inspected.trigger)

    inspected = await inspect(page, 'Integration')
    await expect(inspected.detail).toContainText('Repair in progress')
    await expect(inspected.detail).toContainText('A reviewed Integration repair is currently in progress.')
    await expect(inspected.detail).toContainText('Conflicting files')
    await expect(inspected.detail).toContainText('product.txt')
    await expect(inspected.detail).not.toContainText('Admit the independently reviewed repair.')
    await expect(inspected.detail).not.toContainText('Complete')
    await page.screenshot({ path: testInfo.outputPath('delivery-wide-repair-detail.png'), fullPage: true })
    await returnToPortfolio(page, inspected.trigger)

    inspected = await inspect(page, 'Build operator controls')
    await expect(inspected.detail).toContainText('Build OUT-002')
    await returnToPortfolio(page, inspected.trigger)

    inspected = await inspect(page, 'Assemble release')
    const parentScrollHeight = await page.getByTestId('work-scroll-surface').evaluate((element) => element.scrollHeight)
    await inspected.detail.getByText('Administrative actions', { exact: true }).click()
    await expect.poll(() => page.getByTestId('work-scroll-surface').evaluate((element) => element.scrollHeight))
      .toBe(parentScrollHeight)
    const nestedScrollers = await inspected.detail.locator('*').evaluateAll((elements) => elements.filter((element) => {
      const style = getComputedStyle(element)
      return ['auto', 'scroll'].includes(style.overflowY) && element.scrollHeight > element.clientHeight
    }).length)
    expect(nestedScrollers).toBe(0)
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
    await returnToPortfolio(page, inspected.trigger)

    await expectNoHorizontalOverflow(page)
    const accessibility = await new AxeBuilder({ page }).analyze()
    const blocking = accessibility.violations.filter((violation) =>
      violation.impact === 'serious' || violation.impact === 'critical')
    expect(blocking, formatViolations(blocking)).toEqual([])
    await page.screenshot({ path: testInfo.outputPath('delivery-wide-table.png'), fullPage: true })
  })

  test('compact workspace uses a fullscreen flyout and restores row focus', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/delivery')

    await expect(await visibleRows(page)).toHaveCount(8)
    await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
    await expectNoHorizontalOverflow(page)

    const inspected = await inspect(page, 'Build operator controls')
    await expect(page.getByRole('button', { name: 'Dismiss flyout' })).toBeVisible()
    await expect(inspected.detail).toContainText('Build OUT-002')
    const flyoutBox = await flyoutPanelBox(page)
    expect(flyoutBox).not.toBeNull()
    expect(flyoutBox!.width).toBeGreaterThan(380)
    await page.screenshot({ path: testInfo.outputPath('delivery-compact-flyout.png') })
    await returnToPortfolio(page, inspected.trigger)

    await expectNoHorizontalOverflow(page)
  })

  test('mobile rows preserve field semantics without overflow', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/delivery')

    const rows = await visibleRows(page)
    await expect(rows).toHaveCount(8)
    const integrationRow = rows.filter({ hasText: 'Integration' })
    for (const field of ['Pipeline', 'Current state']) {
      await expect(integrationRow.getByText(field, { exact: true })).toBeVisible()
    }
    await expect(integrationRow).toHaveAttribute('aria-label', 'Change Integration for Repair release')
    await expectNoHorizontalOverflow(page)
    const accessibility = await new AxeBuilder({ page }).analyze()
    const blocking = accessibility.violations.filter((violation) =>
      violation.impact === 'serious' || violation.impact === 'critical')
    expect(blocking, formatViolations(blocking)).toEqual([])
    await page.screenshot({ path: testInfo.outputPath('delivery-mobile-rows.png'), fullPage: true })
  })

  test('intermediate workspace uses a fullscreen detail sheet', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 800 })
    await page.goto('/delivery')

    const inspected = await inspect(page, 'Build operator controls')
    await expect(inspected.detail).toContainText('Build OUT-002')
    const flyoutBox = await flyoutPanelBox(page)
    expect(flyoutBox).not.toBeNull()
    expect(flyoutBox!.width).toBeGreaterThanOrEqual(1023)
  })

  test('wide detail flyout preserves overview context without horizontal scrolling', async ({ page }) => {
    await page.setViewportSize({ width: 1408, height: 800 })
    await page.goto('/delivery')

    const inspected = await inspect(page, 'Build operator controls')
    await expect(inspected.detail).toContainText('Build OUT-002')
    const [surfaceBox, flyoutBox] = await Promise.all([
      page.getByTestId('work-scroll-surface').boundingBox(),
      flyoutPanelBox(page),
    ])
    expect(surfaceBox).not.toBeNull()
    expect(flyoutBox).not.toBeNull()
    expect(flyoutBox!.width).toBeGreaterThan(surfaceBox!.width * 0.55)
    expect(flyoutBox!.width).toBeLessThan(surfaceBox!.width * 0.75)
    await expectNoHorizontalOverflow(page)
  })

  test('routed detail survives reload and completed history remains reachable', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 760 })
    await page.goto('/delivery/work-e2e/outcome%3AOUT-005')

    const detail = page.getByTestId('work-item-detail')
    await expect(detail.getByRole('heading', { name: 'Publish operator guide' })).toBeVisible()
    await expect(detail).toContainText('Delivery task evidence')
    await page.reload()
    await expect(detail.getByRole('heading', { name: 'Publish operator guide' })).toBeVisible()
    await expect(page.getByTestId('desktop-product-navigation').getByLabel('Delivery')).toHaveAttribute('aria-current', 'page')

    await page.getByRole('button', { name: 'Dismiss flyout' }).click()
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
