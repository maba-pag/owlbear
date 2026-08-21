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

async function normalizeSeedLifecycleStatuses(page: Page): Promise<void> {
  await page.route('**/api/work-items', async (route) => {
    const response = await route.fetch()
    const payload = await response.json() as { operating: { statuses: Array<Record<string, unknown>> } }
    const statuses = payload.operating.statuses.map((status) => {
      if (status.change_id === 'work-e2e') {
        return { ...status, admission: 'admitted', stage: 'design', actionable_runtime: true, diagnostic_code: null, diagnostic_detail: null }
      }
      if (status.change_id === 'publication-e2e') {
        return { ...status, admission: 'admitted', stage: 'completed', actionable_runtime: true, diagnostic_code: null, diagnostic_detail: null }
      }
      return status
    })
    await route.fulfill({ response, body: JSON.stringify({ ...payload, operating: { ...payload.operating, statuses } }) })
  })
}

test.describe('assembled Delivery portfolio', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page }) => {
    await normalizeSeedLifecycleStatuses(page)
  })

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
    await expect(table).toContainText('Ready for finalization')
    await expect(table).toContainText('Waiting on OUT-002')
    await expect(table).toContainText('Complete')
    await expect(table).not.toContainText('Reviewed')

    const summary = page.getByLabel('Delivery portfolio status')
    await expect(summary).toContainText('3Changes')
    await expect(summary).toContainText('2Design')
    await expect(summary).toContainText('1Delivery')
    await expect(summary).toContainText('2Ready')
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
    await expect(guidance).toContainText('No session action needed.')
    await expect(guidance).toContainText('Continue Design with:')
    await expect(guidance.getByText('/design design-operations-roadmap', { exact: true })).toBeVisible()
    const tableBox = await table.boundingBox()
    const guidanceBox = await guidance.boundingBox()
    expect(tableBox).not.toBeNull()
    expect(guidanceBox).not.toBeNull()
    expect(guidanceBox!.y).toBeGreaterThanOrEqual(tableBox!.y + tableBox!.height)

    const publicationRow = page.getByLabel('Change publication for Publication release')
    await expect(publicationRow).toContainText('Publication')
    await expect(publicationRow).toContainText('Change: Publication release')
    await expect(publicationRow).toContainText('Ready for finalization')
    await expect(publicationRow.locator('dt')).toHaveText(['Work', 'Progress', 'Status'])
    await expect(publicationRow.locator('dd')).toHaveCount(3)

    const normalOutcome = (await visibleRows(page)).filter({ hasText: 'Publish operator guide' }).locator('td').first()
    await expect(normalOutcome).toHaveCSS('border-left-width', '4px')
    await expect(normalOutcome).toHaveCSS('border-top-width', '1px')
    await expect(normalOutcome).toHaveCSS('border-top-left-radius', '8px')
    const interventionOutcome = (await visibleRows(page)).filter({ hasText: 'Choose release mode' }).locator('td').first()
    await expect(interventionOutcome).toHaveCSS('border-left-width', '4px')
    await expect(publicationRow).toHaveCSS('border-left-width', '4px')

    const publicationTrigger = publicationRow.getByRole('link', { name: 'Publication', exact: true })
    const publicationStatusBox = await publicationRow.getByText('Ready for finalization', { exact: true }).last().boundingBox()
    expect(publicationStatusBox).not.toBeNull()
    const publicationHitTarget = await page.evaluate(({ x, y }) => {
      const element = document.elementFromPoint(x, y)
      const link = element?.closest('a')
      return {
        cursor: element ? getComputedStyle(element).cursor : null,
        href: link?.getAttribute('href') ?? null,
      }
    }, {
      x: publicationStatusBox!.x + publicationStatusBox!.width / 2,
      y: publicationStatusBox!.y + publicationStatusBox!.height / 2,
    })
    expect(publicationHitTarget.cursor).toBe('pointer')
    expect(publicationHitTarget.href).toBe('/delivery/publication-e2e/publication')
    await page.mouse.click(
      publicationStatusBox!.x + publicationStatusBox!.width / 2,
      publicationStatusBox!.y + publicationStatusBox!.height / 2,
    )
    await expect(page.getByTestId('work-item-detail').getByRole('heading', { name: 'Publication', exact: true })).toBeVisible()
    const publicationFlyoutBox = await flyoutPanelBox(page)
    expect(publicationFlyoutBox).not.toBeNull()
    await page.mouse.click(publicationFlyoutBox!.x / 2, publicationFlyoutBox!.y + publicationFlyoutBox!.height / 2)
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(publicationTrigger).toBeFocused()
    await expect.poll(() => publicationTrigger.evaluate((element) => element.matches(':focus-visible'))).toBe(false)

    await publicationTrigger.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('work-item-detail').getByRole('heading', { name: 'Publication', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Dismiss flyout' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(publicationTrigger).toBeFocused()
    await expect.poll(() => publicationTrigger.evaluate((element) => element.matches(':focus-visible'))).toBe(true)

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
    await guidance.scrollIntoViewIfNeeded()
    const guidanceCommand = guidance.getByRole('button', { name: `Copy command ${designCommand}` })
    for (const commandButton of [designCommandButton, guidanceCommand]) {
      const visualContract = await commandButton.evaluate((button) => {
        const code = button.querySelector('code')
        const icon = button.querySelector('p-icon')
        if (!code || !icon) return null
        const buttonStyle = getComputedStyle(button)
        const codeBox = code.getBoundingClientRect()
        const iconBox = icon.getBoundingClientRect()
        return {
          fontSize: buttonStyle.fontSize,
          color: buttonStyle.color,
          iconName: (icon as HTMLElement & { name?: string }).name,
          centerDelta: Math.abs((iconBox.top + iconBox.height / 2) - (codeBox.top + codeBox.height / 2)),
          codeInsideButton: button.contains(code),
        }
      })
      expect(visualContract).not.toBeNull()
      expect(visualContract!.fontSize).toBe('13px')
      expect(visualContract!.color).toBe('rgba(17, 17, 19, 0.6)')
      expect(visualContract!.iconName).toBe('ai-code')
      expect(visualContract!.centerDelta).toBeLessThanOrEqual(1)
      expect(visualContract!.codeInsideButton).toBe(true)
    }
    const guidanceSpacing = await guidanceCommand.evaluate((button) => {
      const wrapper = button.parentElement
      const item = button.closest('li')
      if (!wrapper || !item) return null
      const prose = [...item.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim())
      if (!prose) return null
      const proseRange = document.createRange()
      proseRange.selectNodeContents(prose)
      return wrapper.getBoundingClientRect().left - proseRange.getBoundingClientRect().right
    })
    expect(guidanceSpacing).not.toBeNull()
    expect(guidanceSpacing!).toBeCloseTo(8, 0)
    const guidanceItems = guidance.locator('li')
    const guidanceLayout = await guidanceItems.evaluateAll((items) => {
      const list = items[0]?.parentElement
      const boxes = items.map((item) => item.getBoundingClientRect())
      return {
        display: list ? getComputedStyle(list).display : null,
        adjacentGap: boxes.length > 1 ? boxes[1].left - boxes[0].right : null,
      }
    })
    expect(guidanceLayout.display).toBe('flex')
    expect(guidanceLayout.adjacentGap).not.toBeNull()
    expect(guidanceLayout.adjacentGap!).toBeGreaterThanOrEqual(32)
    expect(guidanceLayout.adjacentGap!).toBeLessThanOrEqual(64)
    await page.screenshot({ path: testInfo.outputPath('delivery-command-alignment.png') })
    await designCommandButton.locator('code').click()
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(designCommand)
    await expect(page).toHaveURL(/\/delivery$/)
    await guidanceCommand.locator('code').click()
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(designCommand)
    await expect(page).toHaveURL(/\/delivery$/)
    const designTrigger = designSection.getByRole('link', { name: 'Design Operations Roadmap' })
    await designTrigger.click()
    const designDetail = page.getByTestId('design-work-detail')
    await expect(designDetail).toContainText('Coordinate the next focused Delivery change.')
    const detailCommand = designDetail.getByRole('button', { name: `Copy command ${designCommand}` })
    await expect(detailCommand).toBeVisible()
    const detailCommandLayout = await detailCommand.evaluate((button) => {
      const label = button.previousElementSibling
      if (!label) return null
      const labelBox = label.getBoundingClientRect()
      const buttonBox = button.getBoundingClientRect()
      return {
        centerDelta: Math.abs((labelBox.top + labelBox.height / 2) - (buttonBox.top + buttonBox.height / 2)),
        gap: buttonBox.left - labelBox.right,
      }
    })
    expect(detailCommandLayout).not.toBeNull()
    expect(detailCommandLayout!.centerDelta).toBeLessThanOrEqual(1)
    expect(detailCommandLayout!.gap).toBeGreaterThanOrEqual(8)
    await page.reload()
    await expect(designDetail.locator('h1').first()).toHaveText('Design Operations Roadmap')
    await page.getByRole('button', { name: 'Dismiss flyout' }).click()
    await expect(designDetail).not.toBeVisible()
    await expect(page).toHaveURL(/\/delivery$/)

    const filterToggle = page.getByTestId('work-filters-toggle')
    await expect(filterToggle).toHaveAttribute('aria-controls', 'work-filters-panel')
    await filterToggle.click()
    await expect(filterToggle).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByTestId('work-filters-panel')).toBeVisible()
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

    inspected = await inspect(page, 'Publication')
    await expect(inspected.detail).toContainText('Ready for finalization')
    await expect(inspected.detail).toContainText('Finalize the reviewed Change')
    await expect(inspected.detail).not.toContainText(/merge now/i)
    await page.screenshot({ path: testInfo.outputPath('delivery-wide-publication-detail.png'), fullPage: true })
    await returnToPortfolio(page, inspected.trigger)

    inspected = await inspect(page, 'Build operator controls')
    await expect(inspected.detail).toContainText('Build OUT-002')
    await returnToPortfolio(page, inspected.trigger)

    inspected = await inspect(page, 'Finalize release')
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
    const guidance = page.getByLabel('Session suggestions')
    await expect(guidance.locator('li')).toHaveCount(3)
    await expect(page.getByTestId('work-portfolio-table')).toBeVisible()
    await expectNoHorizontalOverflow(page)

    const designCommand = '/design design-operations-roadmap'
    const compactCommand = guidance.getByRole('button', { name: `Copy command ${designCommand}` })
    const compactCommandLayout = await compactCommand.evaluate((button) => {
      const code = button.querySelector('code')
      const icon = button.querySelector('p-icon') as (HTMLElement & { name?: string }) | null
      if (!code || !icon) return null
      const buttonBox = button.getBoundingClientRect()
      const codeBox = code.getBoundingClientRect()
      const iconBox = icon.getBoundingClientRect()
      return {
        iconName: icon.name,
        firstLineDelta: Math.abs(iconBox.top - codeBox.top),
        overflow: button.scrollWidth - button.clientWidth,
        contained: codeBox.right <= buttonBox.right,
      }
    })
    expect(compactCommandLayout).not.toBeNull()
    expect(compactCommandLayout!.iconName).toBe('ai-code')
    expect(compactCommandLayout!.firstLineDelta).toBeLessThanOrEqual(1)
    expect(compactCommandLayout!.overflow).toBe(0)
    expect(compactCommandLayout!.contained).toBe(true)

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
    const publicationRow = page.getByLabel('Change publication for Publication release')
    for (const field of ['Progress', 'Status']) {
      await expect(publicationRow.getByText(field, { exact: true })).toBeVisible()
    }
    await expect(publicationRow).toHaveAttribute('aria-label', 'Change publication for Publication release')
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
    await expect(page.getByRole('button', { name: 'Current delivery', exact: true })).toBeFocused()
    const historyResponse = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed')
    await page.getByRole('button', { name: 'Completed history' }).click()
    expect((await historyResponse).status()).toBe(200)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    await expect(page.getByText('Alpha delivery', { exact: true })).toBeVisible()
    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    await receiptRecord.getByRole('button', { name: 'Inspect' }).click()
    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    await expect(completionDetail).toContainText('Finalized Change head')
    await expect(completionDetail).toContainText('Accepted merge commit')
    await expect(completionDetail).toContainText('#42')
    await expectNoHorizontalOverflow(page)
    await page.screenshot({ path: testInfo.outputPath('delivery-completed-history.png'), fullPage: true })

    await page.setViewportSize({ width: 390, height: 844 })
    await expect(completionDetail).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await page.screenshot({ path: testInfo.outputPath('delivery-completed-history-mobile.png'), fullPage: true })
  })

  test('closing detail does not leave a history entry that reopens it', async ({ page }) => {
    await page.goto('/delivery')

    const inspected = await inspect(page, 'Build operator controls')
    await page.getByRole('button', { name: 'Dismiss flyout' }).click()
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(page).toHaveURL(/\/delivery$/)

    await page.goBack()
    await expect(page).toHaveURL(/\/delivery$/)
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(inspected.trigger).toBeVisible()
  })

  test('browser Back from detail restores the originating trigger focus', async ({ page }) => {
    await page.goto('/delivery')

    const inspected = await inspect(page, 'Build operator controls')
    await page.goBack()
    await expect(page).toHaveURL(/\/delivery$/)
    await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
    await expect(inspected.trigger).toBeFocused()
  })

  test('refreshes current delivery immediately after returning from completed history', async ({ page }) => {
    let refreshPortfolio = false
    await page.route('**/api/work-items', async (route) => {
      const response = await route.fetch()
      if (!refreshPortfolio) {
        await route.fulfill({ response })
        return
      }
      const payload = await response.json() as { groups: Array<Record<string, unknown>> }
      const [firstGroup, ...remainingGroups] = payload.groups
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          groups: firstGroup
            ? [{ ...firstGroup, title: 'Refreshed portfolio' }, ...remainingGroups]
            : payload.groups,
        }),
      })
    })

    try {
      await page.goto('/delivery')
      await expect(page.getByText('Work portfolio E2E', { exact: true })).toBeVisible()
      await page.getByRole('button', { name: 'Completed history' }).click()
      await expect(page.getByTestId('completed-history-workspace')).toBeVisible()

      refreshPortfolio = true
      await page.getByRole('button', { name: 'Current delivery' }).click()
      await expect(page.getByText('Refreshed portfolio', { exact: true })).toBeVisible({ timeout: 1_000 })
    } finally {
      await page.unroute('**/api/work-items')
    }
  })

  test('completed history detail dismisses on Escape and restores record focus', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 760 })
    await page.goto('/delivery')

    const historyResponse = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed')
    await page.getByRole('button', { name: 'Completed history' }).click()
    expect((await historyResponse).status()).toBe(200)
    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    await expect(receiptRecord).toBeVisible()
    const trigger = receiptRecord.getByRole('button', { name: 'Inspect' })
    await trigger.click()

    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    await completionDetail.getByRole('button', { name: 'Close' }).focus()
    await page.keyboard.press('Escape')
    await expect(completionDetail).not.toBeVisible()
    await expect(trigger).toBeFocused()
  })

  test('browser Back from completed history detail restores record focus', async ({ page }) => {
    await page.goto('/delivery')
    await page.getByRole('button', { name: 'Completed history' }).click()

    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    const trigger = receiptRecord.getByRole('button', { name: 'Inspect' })
    await trigger.click()

    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/)

    await page.goBack()
    await expect(completionDetail).not.toBeVisible()
    await expect(trigger).toBeFocused()
    await expect(page.getByTestId('completed-history-workspace')).toBeVisible()
  })

  test('completed history detail survives reload and restores workspace focus', async ({ page }) => {
    await page.goto('/delivery')
    await page.getByRole('button', { name: 'Completed history' }).click()

    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    await receiptRecord.getByRole('button', { name: 'Inspect' }).click()

    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/)

    await page.reload()
    await expect(page).toHaveURL(/\/delivery\/history\/[^/]+\/[^/]+$/)
    await expect(completionDetail).toContainText('Finalized Change head')

    await completionDetail.getByRole('button', { name: 'Close' }).click()
    await expect(completionDetail).not.toBeVisible()
    await expect(page.getByTestId('completed-history-workspace')).toBeFocused()
  })

  test('completed history detail closes with its Close button and restores record focus', async ({ page }) => {
    await page.goto('/delivery')
    await page.getByRole('button', { name: 'Completed history' }).click()

    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    const trigger = receiptRecord.getByRole('button', { name: 'Inspect' })
    await trigger.click()

    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    await completionDetail.getByRole('button', { name: 'Close' }).click()
    await expect(completionDetail).not.toBeVisible()
    await expect(trigger).toBeFocused()
  })

  test('completed history detail closes from the backdrop and restores record focus', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 760 })
    await page.goto('/delivery')
    await page.getByRole('button', { name: 'Completed history' }).click()

    const receiptRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })
    const trigger = receiptRecord.getByRole('button', { name: 'Inspect' })
    await trigger.click()

    const completionDetail = page.getByTestId('completed-change-detail')
    await expect(completionDetail).toContainText('Completion receipt')
    const backdropPoint = await page.locator('p-flyout').last().evaluate((element) => {
      const dialog = element.shadowRoot?.querySelector('dialog')
      if (!dialog) return null
      const box = dialog.getBoundingClientRect()
      return { x: box.left + 16, y: box.top + box.height / 2 }
    })
    expect(backdropPoint).not.toBeNull()
    await page.mouse.click(backdropPoint!.x, backdropPoint!.y)
    await expect(completionDetail).not.toBeVisible()
    await expect(trigger).toBeFocused()
  })

  test('completed history restores focus when a pending search replaces the open detail trigger', async ({ page }) => {
    let releaseSearch: (() => void) | undefined
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve
    })
    await page.route('**/api/work-items/completed/search**', async (route) => {
      await searchBlocked
      await route.continue()
    })

    try {
      await page.goto('/delivery')
      await page.getByRole('button', { name: 'Completed history' }).click()
      await expect(page.getByTestId('completed-change-record')).toHaveCount(2)

      const searchInput = page.locator('p-input-search[name="completed-history-search"]').locator('input')
      await searchInput.fill('Beta')
      await expect(page.getByTestId('completed-history-stale-status')).toBeVisible()

      const legacyRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Alpha delivery' })
      const trigger = legacyRecord.getByRole('button', { name: 'Inspect' })
      await trigger.click()
      await expect(page.getByTestId('completed-change-detail')).toContainText('Legacy package')

      releaseSearch?.()
      await expect(page.getByTestId('completed-change-record')).toHaveCount(1)
      await expect(page.getByTestId('completed-change-record').filter({ hasText: 'Beta search' })).toBeVisible()
      await expect(page.getByTestId('completed-change-detail')).not.toBeVisible()
      await expect(page.getByTestId('completed-history-workspace')).toBeFocused()
    } finally {
      releaseSearch?.()
      await page.unroute('**/api/work-items/completed/search**')
    }
  })

  test('completed history focuses its workspace when detail closes during a pending search', async ({ page }) => {
    let releaseSearch: (() => void) | undefined
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve
    })
    await page.route('**/api/work-items/completed/search**', async (route) => {
      await searchBlocked
      await route.continue()
    })

    try {
      await page.goto('/delivery')
      await page.getByRole('button', { name: 'Completed history' }).click()
      await expect(page.getByTestId('completed-change-record')).toHaveCount(2)

      const searchInput = page.locator('p-input-search[name="completed-history-search"]').locator('input')
      await searchInput.fill('Beta')
      await expect(page.getByTestId('completed-history-stale-status')).toBeVisible()

      const legacyRecord = page.getByTestId('completed-change-record').filter({ hasText: 'Alpha delivery' })
      await legacyRecord.getByRole('button', { name: 'Inspect' }).click()
      const completionDetail = page.getByTestId('completed-change-detail')
      await expect(completionDetail).toContainText('Legacy package')

      await completionDetail.getByRole('button', { name: 'Close' }).click()
      await expect(completionDetail).not.toBeVisible()
      await expect(page.getByTestId('completed-history-workspace')).toBeFocused()

      releaseSearch?.()
      await expect(page.getByTestId('completed-change-record')).toHaveCount(1)
      await expect(page.getByTestId('completed-history-workspace')).toBeFocused()
    } finally {
      releaseSearch?.()
      await page.unroute('**/api/work-items/completed/search**')
    }
  })

  test('completed history search remains editable while results are pending', async ({ page }) => {
    let releaseSearch: (() => void) | undefined
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve
    })
    await page.route('**/api/work-items/completed/search**', async (route) => {
      await searchBlocked
      await route.continue()
    })

    try {
      await page.goto('/delivery')
      await page.getByRole('button', { name: 'Completed history' }).click()
      await expect(page.getByTestId('completed-change-record')).toHaveCount(2)

      const search = page.locator('p-input-search[name="completed-history-search"]')
      const input = search.locator('input')
      await input.fill('Beta')
      await expect(page.getByTestId('completed-history-stale-status')).toBeVisible()
      await expect(page.getByTestId('completed-history-results')).toHaveAttribute('aria-busy', 'true')

      await input.fill('Alpha')
      await expect(input).toHaveValue('Alpha')
      releaseSearch?.()

      await expect(page.getByTestId('completed-change-record')).toHaveCount(1)
      await expect(page.getByText('Alpha delivery', { exact: true })).toBeVisible()
      await expect(page.getByText('Beta search', { exact: true })).not.toBeVisible()
    } finally {
      releaseSearch?.()
      await page.unroute('**/api/work-items/completed/search**')
    }
  })

  test('automatically removed Work Item routes to history and restores view focus', async ({ page }) => {
    let removeSelectedChange = false
    await page.route('**/api/work-items', async (route) => {
      const response = await route.fetch()
      if (!removeSelectedChange) {
        await route.fulfill({ response })
        return
      }
      const payload = await response.json() as { groups: Array<{ change_id: string }> }
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          groups: payload.groups.filter((group) => group.change_id !== 'work-e2e'),
        }),
      })
    })

    try {
      await page.goto('/delivery')
      await inspect(page, 'Build operator controls')
      const historyView = page.getByRole('button', { name: 'Completed history' })
      removeSelectedChange = true
      await page.waitForResponse((response) =>
        response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items')
      await expect(page.getByTestId('completed-history-workspace')).toBeVisible()
      await expect(historyView).toBeFocused()
    } finally {
      await page.unroute('**/api/work-items')
    }
  })

  test('automatically closes removed Design detail and restores current view focus', async ({ page }) => {
    let removeDesign = false
    await page.route('**/api/work-items', async (route) => {
      const response = await route.fetch()
      if (!removeDesign) {
        await route.fulfill({ response })
        return
      }
      const payload = await response.json() as { operating: { statuses: Array<{ change_id: string }> } }
      await route.fulfill({
        response,
        body: JSON.stringify({
          ...payload,
          operating: {
            ...payload.operating,
            statuses: payload.operating.statuses.filter((status) => status.change_id !== 'design-operations-roadmap'),
          },
        }),
      })
    })

    try {
      await page.goto('/delivery')
      const designTrigger = page.getByTestId('design-work-section').getByRole('link', { name: 'Design Operations Roadmap' })
      await designTrigger.click()
      await expect(page.getByTestId('design-work-detail')).toBeVisible()

      removeDesign = true
      await page.waitForResponse((response) =>
        response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items')
      await expect(page.getByTestId('design-work-detail')).not.toBeVisible()
      await expect(page.getByRole('button', { name: 'Current delivery' })).toBeFocused()
    } finally {
      await page.unroute('**/api/work-items')
    }
  })

  test('unknown paths render the global Not Found view', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto('/delivery/work-e2e')

    await expect(page.getByTestId('not-found-view')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('cockpit-not-found.png'), fullPage: true })
  })
})
