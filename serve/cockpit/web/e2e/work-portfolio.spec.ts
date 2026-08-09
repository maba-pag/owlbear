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
  await expect(detail.getByRole('heading', { name: detailTitle, exact: true })).toBeVisible()
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

async function flyoutPanelBox(page: Page): Promise<{ x: number; y: number; width: number; height: number } | null> {
  return page.locator('p-flyout').last().evaluate((element) => {
    const panel = element.shadowRoot?.querySelector('.flyout')
    if (!panel) return null
    const box = panel.getBoundingClientRect()
    return { x: box.x, y: box.y, width: box.width, height: box.height }
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
    for (const column of ['Work', 'Progress', 'Status']) {
      await expect(table.getByRole('columnheader', { name: column })).toHaveCount(2)
      await expect(table.getByRole('columnheader', { name: column }).first()).toBeVisible()
    }
    await expect(table).toContainText('Decision required')
    await expect(table).toContainText('Integration repairer working')
    await expect(table).toContainText('Waiting on OUT-002')
    await expect(table).toContainText('Done')
    await expect(table).not.toContainText('Reviewed')

    const summary = page.getByLabel('Delivery portfolio status')
    await expect(summary).toContainText('3Changes')
    await expect(summary).toContainText('2Design')
    await expect(summary).toContainText('1Delivery')
    await expect(summary).toContainText('1Running')
    await expect(summary).toContainText('2Needs you')

    const needsYou = summary.getByRole('button', { name: 'Filter to 2 work items: Needs you' })
    await needsYou.click()
    await expect(needsYou).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('work-filter-chip-needs')).toBeVisible()
    await needsYou.click()
    await expect(needsYou).toHaveAttribute('aria-pressed', 'false')
    await expect(page.getByTestId('work-filter-chip-needs')).not.toBeVisible()
    await expect(await visibleRows(page)).toHaveCount(8)

    const guidance = page.getByLabel('Session suggestions')
    await expect(guidance).toContainText('Review 2 items that need you')
    await expect(guidance).toContainText('/orchestrate is already working')
    await expect(guidance.getByText('/orchestrate', { exact: true })).toHaveCSS('font-family', /mono/i)
    await expect(guidance.getByText('/design design-operations-roadmap', { exact: true })).toBeVisible()
    const tableBox = await table.boundingBox()
    const guidanceBox = await guidance.boundingBox()
    expect(tableBox).not.toBeNull()
    expect(guidanceBox).not.toBeNull()
    expect(guidanceBox!.y).toBeGreaterThanOrEqual(tableBox!.y + tableBox!.height)

    const integrationRow = (await visibleRows(page)).filter({ hasText: 'Integration' })
    await expect(integrationRow).toContainText('Integration')
    await expect(integrationRow).toContainText('Change: Repair release')
    await expect(integrationRow).toContainText('Repair in progress')
    await expect(integrationRow).toContainText('Integration repairer working')
    await expect(integrationRow).not.toContainText('Manual option:')
    await expect(integrationRow.locator('dt')).toHaveText(['Work', 'Progress', 'Status'])
    await expect(integrationRow.locator('dd')).toHaveCount(3)

    const normalOutcome = (await visibleRows(page)).filter({ hasText: 'Publish operator guide' }).locator('td').first()
    await expect(normalOutcome).toHaveCSS('border-left-width', '4px')
    await expect(normalOutcome).toHaveCSS('border-top-width', '1px')
    await expect(normalOutcome).toHaveCSS('border-top-left-radius', '8px')
    const interventionOutcome = (await visibleRows(page)).filter({ hasText: 'Choose release mode' }).locator('td').first()
    await expect(interventionOutcome).toHaveCSS('border-left-width', '4px')
    await expect(integrationRow).toHaveCSS('border-left-width', '4px')

    const integrationTrigger = integrationRow.getByRole('link', { name: 'Integration', exact: true })
    const integrationStatusBox = await integrationRow.getByText('Integration repairer working', { exact: true }).boundingBox()
    expect(integrationStatusBox).not.toBeNull()
    const integrationHitTarget = await page.evaluate(({ x, y }) => {
      const element = document.elementFromPoint(x, y)
      const link = element?.closest('a')
      return {
        cursor: element ? getComputedStyle(element).cursor : null,
        href: link?.getAttribute('href') ?? null,
      }
    }, {
      x: integrationStatusBox!.x + integrationStatusBox!.width / 2,
      y: integrationStatusBox!.y + integrationStatusBox!.height / 2,
    })
    expect(integrationHitTarget.cursor).toBe('pointer')
    expect(integrationHitTarget.href).toBe('/delivery/repair-e2e/integration')
    await page.mouse.click(
      integrationStatusBox!.x + integrationStatusBox!.width / 2,
      integrationStatusBox!.y + integrationStatusBox!.height / 2,
    )
    await expect(page.getByTestId('work-item-detail').getByRole('heading', { name: 'Integration', exact: true })).toBeVisible()
    const integrationFlyoutBox = await flyoutPanelBox(page)
    expect(integrationFlyoutBox).not.toBeNull()
    await page.mouse.click(integrationFlyoutBox!.x / 2, integrationFlyoutBox!.y + integrationFlyoutBox!.height / 2)
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(integrationTrigger).toBeFocused()
    await expect.poll(() => integrationTrigger.evaluate((element) => element.matches(':focus-visible'))).toBe(false)

    await integrationTrigger.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('work-item-detail').getByRole('heading', { name: 'Integration', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Dismiss flyout' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(integrationTrigger).toBeFocused()
    await expect.poll(() => integrationTrigger.evaluate((element) => element.matches(':focus-visible'))).toBe(true)

    const designSection = page.getByTestId('design-work-section')
    await expect(designSection).toContainText('Design Operations Roadmap')
    await expect(designSection).toContainText('Not admitted to Delivery')
    await expect(designSection.getByRole('heading', { name: 'Design work' })).toHaveCSS('border-bottom-width', '1px')
    const designRow = designSection.locator('[data-design-work]')
    await expect(designRow).toHaveCSS('border-left-width', '4px')
    await expect(designRow).toHaveCSS('border-top-left-radius', '8px')
    await expect(designRow.locator('dt')).toHaveText(['Work', 'Progress', 'Status'])
    await expect(designRow.locator('dd')).toHaveCount(3)
    const firstChange = table.locator(':scope > section').first()
    const [changeHeadingBox, changeLabelsBox, changeRowBox, designBox, designHeadingBox, designLabelsBox, designRowBox] = await Promise.all([
      firstChange.getByRole('heading').first().boundingBox(),
      firstChange.locator('thead').boundingBox(),
      firstChange.locator('tbody tr').first().boundingBox(),
      designSection.boundingBox(),
      designSection.getByRole('heading', { name: 'Design work' }).boundingBox(),
      designSection.locator(':scope > div[aria-hidden="true"]').boundingBox(),
      designRow.boundingBox(),
    ])
    expect(changeHeadingBox).not.toBeNull()
    expect(changeLabelsBox).not.toBeNull()
    expect(changeRowBox).not.toBeNull()
    expect(designBox).not.toBeNull()
    expect(designHeadingBox).not.toBeNull()
    expect(designLabelsBox).not.toBeNull()
    expect(designRowBox).not.toBeNull()
    expect(changeLabelsBox!.y - (changeHeadingBox!.y + changeHeadingBox!.height)).toBeCloseTo(8, 0)
    expect(changeRowBox!.y - (changeLabelsBox!.y + changeLabelsBox!.height)).toBeCloseTo(8, 0)
    expect(designLabelsBox!.y - (designHeadingBox!.y + designHeadingBox!.height)).toBeCloseTo(8, 0)
    expect(designRowBox!.y - (designLabelsBox!.y + designLabelsBox!.height)).toBeCloseTo(8, 0)
    expect(designBox!.y - (tableBox!.y + tableBox!.height)).toBeCloseTo(32, 0)
    expect(guidanceBox!.y - (designBox!.y + designBox!.height)).toBeCloseTo(32, 0)
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
    const designCommand = '/design design-operations-roadmap'
    const designCommandButton = designRow.getByRole('button', { name: `Copy command ${designCommand}` })
    const [blockCommandIconBox, blockCommandTextBox] = await Promise.all([
      designCommandButton.locator('p-icon').boundingBox(),
      designCommandButton.locator('code').boundingBox(),
    ])
    expect(blockCommandIconBox).not.toBeNull()
    expect(blockCommandTextBox).not.toBeNull()
    expect(blockCommandIconBox!.y + blockCommandIconBox!.height / 2).toBeCloseTo(
      blockCommandTextBox!.y + blockCommandTextBox!.height / 2,
      0,
    )
    await guidance.scrollIntoViewIfNeeded()
    const guidanceCommand = guidance.getByRole('button', { name: `Copy command ${designCommand}` })
    const proseAlignment = await guidanceCommand.evaluate((button) => {
      const item = button.closest('li')
      const code = button.parentElement?.previousElementSibling
      if (!item || !code) return null
      const textNode = [...item.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim())
      if (!textNode) return null
      const textRange = document.createRange()
      textRange.selectNodeContents(textNode)
      const proseBox = textRange.getBoundingClientRect()
      const codeBox = code.getBoundingClientRect()
      const punctuation = item.querySelector('[data-command-suffix]')
      const punctuationBox = punctuation?.getBoundingClientRect() ?? null
      const punctuationButtonBox = punctuation?.previousElementSibling?.getBoundingClientRect() ?? null
      return {
        centerDelta: Math.abs((proseBox.top + proseBox.height / 2) - (codeBox.top + codeBox.height / 2)),
        copyTargetLargeEnough: punctuationButtonBox
          ? punctuationButtonBox.width >= 24 && punctuationButtonBox.height >= 24
          : false,
        suffixAdjacent: punctuationBox && punctuationButtonBox
          ? Math.abs(punctuationBox.left - punctuationButtonBox.right) <= 1
          : false,
      }
    })
    expect(proseAlignment).not.toBeNull()
    expect(proseAlignment!.centerDelta).toBeLessThanOrEqual(1)
    expect(proseAlignment!.copyTargetLargeEnough).toBe(true)
    expect(proseAlignment!.suffixAdjacent).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('delivery-command-alignment.png') })
    await designCommandButton.click()
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(designCommand)
    await expect(page).toHaveURL(/\/delivery$/)
    await expect(guidance.getByRole('button', { name: `Copy command ${designCommand}` })).toBeVisible()
    const designTrigger = designSection.getByRole('link', { name: 'Design Operations Roadmap' })
    await designTrigger.click()
    const designDetail = page.getByTestId('design-work-detail')
    await expect(designDetail).toContainText('Coordinate the next focused Delivery change.')
    await expect(designDetail.getByText('/design design-operations-roadmap', { exact: true })).toBeVisible()
    await page.reload()
    await expect(designDetail.locator('h1').first()).toHaveText('Design Operations Roadmap')
    await page.getByRole('button', { name: 'Dismiss flyout' }).click()
    await expect(designDetail).not.toBeVisible()
    await expect(page).toHaveURL(/\/delivery$/)

    await page.getByTestId('work-filters-toggle').click()
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), 'you')
    await expect(page.getByTestId('work-shown-count')).toContainText('3 of 9')
    await expect(page.getByTestId('design-work-section')).toBeVisible()
    await selectValue(page.locator('p-select[name="work-needs-filter"]'), 'dependency')
    await expect(page.getByTestId('work-shown-count')).toContainText('1 of 9')
    await expect(page.getByTestId('design-work-section')).not.toBeVisible()
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
    await expect(returnedDetail).toContainText('Returned to Design')
    await expect(returnedDetail).toContainText('Evidence: request:release-notes-authority')
    await expect(returnedDetail).toContainText('Source boundary: design:release-notes-v2')
    await returnToPortfolio(page, returnedTrigger)

    const requestRow = (await visibleRows(page)).filter({ hasText: 'Choose release mode' })
    const requestTrigger = requestRow.getByRole('link', { name: /^Choose release mode/ })
    const requestAction = requestRow.locator('p-link-pure', { hasText: 'Answer request' })
    await expect(requestAction).toHaveJSProperty('href', '/delivery/work-e2e/outcome%3AOUT-001')
    await requestAction.click()
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
    await expect(page.getByTestId('design-work-section')).toBeVisible()
    await expect(page.getByLabel('Session suggestions').locator('li')).toHaveCount(3)
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
    for (const field of ['Progress', 'Status']) {
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

  test('desktop workspaces keep columns and overview context beside detail', async ({ page }) => {
    for (const width of [1024, 1280]) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto('/delivery')

      const table = page.getByTestId('work-table-scroll').first()
      await expect(table).toBeVisible()
      await expect(table.getByRole('columnheader', { name: 'Work' })).toBeVisible()
      const inspected = await inspect(page, 'Build operator controls')
      await expect(inspected.detail).toContainText('Build OUT-002')
      const flyoutBox = await flyoutPanelBox(page)
      expect(flyoutBox).not.toBeNull()
      expect(flyoutBox!.width).toBeLessThan(width)
      await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
      await expectNoHorizontalOverflow(page)
      await returnToPortfolio(page, inspected.trigger)
    }
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
