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

/**
 * Stage headings scroll with their column, so no board content may intersect a heading box and no
 * visible content may be covered by another element at its first visible row.
 */
async function expectNoStageHeadingOcclusion(page: Page): Promise<void> {
  const defects = await page.evaluate(() => {
    const surface = document.querySelector('[data-testid="work-scroll-surface"]')
    if (!surface) return ['missing scroll surface']
    const port = surface.getBoundingClientRect()
    const label = (node: Element) => `${node.textContent?.trim().slice(0, 48) ?? ''}`
    const headings = [...document.querySelectorAll('[data-stage-heading]')]
    const contents = [...document.querySelectorAll('[data-work-item], [data-stage-empty]')]
    const visible = (rect: DOMRect) => rect.height > 0 && rect.bottom > port.top + 1 && rect.top < port.bottom - 1
    const found: string[] = []

    for (const heading of headings) {
      const headingRect = heading.getBoundingClientRect()
      if (!visible(headingRect)) continue
      for (const node of contents) {
        const rect = node.getBoundingClientRect()
        if (!visible(rect)) continue
        const intersects = rect.left < headingRect.right - 1 && rect.right > headingRect.left + 1
          && rect.top < headingRect.bottom - 1 && rect.bottom > headingRect.top + 1
        if (intersects) found.push(`content "${label(node)}" overlaps heading "${label(heading)}"`)
      }
    }

    for (const node of contents) {
      const rect = node.getBoundingClientRect()
      if (!visible(rect)) continue
      const probeY = Math.max(rect.top, port.top) + 3
      const probeX = rect.left + Math.min(rect.width / 2, 40)
      if (probeY >= Math.min(rect.bottom, port.bottom) - 1) continue
      const topmost = document.elementFromPoint(probeX, probeY)
      if (topmost && !node.contains(topmost) && !topmost.contains(node)) {
        found.push(`content "${label(node)}" is occluded by "${label(topmost)}"`)
      }
    }
    return found
  })
  expect(defects, defects.join('\n')).toEqual([])
}

async function inspect(page: Page, title: string): Promise<Locator> {
  const card = page.locator('[data-work-item]').filter({ hasText: title })
  await card.getByText('View details', { exact: true }).click()
  const detail = page.getByTestId('work-item-detail')
  await expect(detail.getByRole('heading', { name: title })).toBeVisible()
  return detail
}

async function dismissOutcomeDetail(page: Page): Promise<void> {
  const flyout = page.locator('#work-item-flyout')
  const motionHidden = flyout.evaluate((element) => new Promise<void>((resolve) => {
    element.addEventListener('motionHiddenEnd', () => resolve(), { once: true })
  }))
  await page.getByRole('button', { name: 'Dismiss flyout' }).click()
  await motionHidden
  await expect(page.getByTestId('work-item-detail')).not.toBeVisible()
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

async function openCompletedHistory(page: Page): Promise<void> {
  const completedChanges = page.getByRole('button', { name: 'Completed history' })
  await expect(completedChanges).toBeVisible()
  await completedChanges.focus()
  await expect(completedChanges).toBeFocused()
  await completedChanges.click()
  await expect(page.getByTestId('completed-history-workspace')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Completed changes' })).toBeVisible()
}

/** Both Delivery views share one content-header row, so switching must not resize it. */
async function viewHeaderHeight(page: Page, heading: string): Promise<number> {
  const box = await page.getByRole('heading', { name: heading }).locator('xpath=../..').boundingBox()
  return box!.height
}

async function expectCenteredDesktopNavigation(page: Page): Promise<void> {
  const navRail = page.getByTestId('desktop-product-navigation')
  await expect(navRail).toBeVisible()
  const railBox = await navRail.boundingBox()
  expect(railBox).not.toBeNull()
  expect(railBox!.width).toBe(64)

  const identity = navRail.getByTestId('rail-identity')
  await expect(identity).toHaveAccessibleName('OwlBear Cockpit')
  const identityBox = await identity.boundingBox()
  expect(identityBox).not.toBeNull()
  expect(identityBox!.width).toBeLessThanOrEqual(railBox!.width)

  const navigationItems = navRail.getByRole('link')
  await expect(navigationItems).toHaveCount(3)
  for (const navigationItem of await navigationItems.all()) {
    const itemBox = await navigationItem.boundingBox()
    const iconBox = await navigationItem.locator('p-icon').boundingBox()
    expect(itemBox).not.toBeNull()
    expect(iconBox).not.toBeNull()
    expect(itemBox!.width).toBe(40)
    expect(itemBox!.height).toBe(40)
    const railCenter = railBox!.x + railBox!.width / 2
    const iconCenter = iconBox!.x + iconBox!.width / 2
    expect(Math.abs(iconCenter - railCenter)).toBeLessThanOrEqual(0.5)
  }
}

function formatViolations(violations: Array<{ id: string; impact?: string | null; help: string }>): string {
  return violations.map((item) => `[${item.impact ?? 'unknown'} ${item.id}] ${item.help}`).join('\n')
}

test.describe('assembled Work portfolio', () => {
  test.describe.configure({ mode: 'serial' })

  test('desktop runs bounded controls and completed semantic history', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/work')
    await expect(page).toHaveURL(/\/delivery$/)

    await expect(page.getByTestId('cockpit-shell')).toBeVisible()
    await expectCenteredDesktopNavigation(page)
    await expect(page.locator('[data-work-item]')).toHaveCount(6)
    for (const label of ['Design', 'Planning', 'Implementation', 'Assembly', 'Done']) {
      await expect(page.getByText(label, { exact: true })).toBeVisible()
    }
    const summary = page.getByLabel('Delivery portfolio status')
    await expect(summary).toContainText('6work items')
    await expect(summary).toContainText('1need you')
    await expect(summary).toContainText('3with agents')
    await expect(summary).toContainText('1waiting')
    await expect(summary).toContainText('1no action needed')
    await expect(summary).not.toContainText('outcome')
    await expect(page.getByRole('heading', { name: 'Delivery stages' })).toBeVisible()
    await expect(page.getByTestId('work-shown-count')).toBeEmpty()
    await expect(page.getByTestId('work-portfolio-board')).toContainText('Waiting on dependencies')
    await expect(page.getByTestId('work-portfolio-board')).toContainText('No action needed')
    await expect(page.getByTestId('work-filters-panel')).toHaveCount(0)
    await page.getByTestId('work-filters-toggle').click()
    await expect(page.getByTestId('work-filters-panel')).toBeVisible()
    await page.getByTestId('work-filters-toggle').click()
    await expect(page.getByTestId('work-filters-panel')).toHaveCount(0)

    const workspaceStatus = page.getByTestId('workspace-status').first()
    await expect(workspaceStatus).toBeVisible()
    await workspaceStatus.click()
    const statusPanel = page.getByTestId('workspace-status-panel')
    await expect(statusPanel).toBeVisible()
    await expect(page.getByTestId('workspace-status-module-memory')).toBeVisible()
    await expect(page.getByTestId('workspace-status-module-ideas')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('workspace-status-panel.png') })
    await page.keyboard.press('Escape')
    await expect(statusPanel).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await expectNoOverlap(page.locator('[data-work-item]').filter({ visible: true }))
    await page.screenshot({ path: testInfo.outputPath('work-desktop-current.png') })
    await page.getByTestId('work-filters-toggle').click()
    await expect(page.getByTestId('work-filters-panel')).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('work-desktop-filters-open.png') })
    await selectValue(page.locator('p-select[name="work-attention-filter"]'), 'agent')
    await expect(page.getByTestId('work-shown-count')).toContainText('3 of 6')
    await page.getByTestId('work-filters-reset').click()
    await expect(page.getByTestId('work-shown-count')).toBeEmpty()
    await page.getByTestId('work-filters-toggle').click()
    const currentHeaderHeight = await viewHeaderHeight(page, 'Delivery stages')

    let detail = await inspect(page, 'Choose release mode')
    await selectValue(detail.locator('p-select[name="request-request-release-mode-option"]'), 'safe')
    const answerResponse = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().includes('/requests/request-release-mode/answer'))
    await detail.getByText('Submit answer', { exact: true }).click()
    expect((await answerResponse).status()).toBe(200)
    await expect(detail.getByRole('region', { name: 'Requests' }).locator('article p')).toHaveText('Safe rollout')
    await dismissOutcomeDetail(page)

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
    await dismissOutcomeDetail(page)

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
    await dismissOutcomeDetail(page)

    const listResponsePromise = page.waitForResponse((response) =>
      response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/work-items/completed')
    await openCompletedHistory(page)
    expect((await listResponsePromise).status()).toBe(200)
    expect(Math.abs(await viewHeaderHeight(page, 'Completed changes') - currentHeaderHeight)).toBeLessThanOrEqual(1)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    await page.screenshot({ path: testInfo.outputPath('work-desktop-history-list.png'), fullPage: true })
    // Without an open detail the record rules must reach the view-header rule, not stop short of it.
    const headerRule = (await page.getByRole('heading', { name: 'Completed changes' }).locator('xpath=../..').boundingBox())!
    const recordBox = (await page.getByTestId('completed-change-record').first().boundingBox())!
    expect(Math.abs(recordBox.x - headerRule.x)).toBeLessThanOrEqual(1)
    expect(Math.abs(recordBox.width - headerRule.width)).toBeLessThanOrEqual(1)
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

    // Last, because it leaves the rail dot in its non-healthy state for the rest of the page life.
    await page.route('**/health/memory', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'attention',
        findings: [{ path: 'store/memory/entry.md', code: 'missing-scope', detail: 'scope is absent' }],
        repairable_count: 0,
        checked_paths: ['store/memory/entry.md'],
      }),
    }))
    await page.getByTestId('workspace-status').first().click()
    await expect(page.getByTestId('workspace-status-module-memory')).toContainText('Needs attention')
    await expect(page.getByTestId('workspace-status').first()).toHaveAttribute('data-status', 'attention')
    await page.screenshot({ path: testInfo.outputPath('workspace-status-panel-attention.png') })
  })

  test('compact desktop keeps current and completed work reachable without overlap', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1100, height: 800 })
    await page.goto('/delivery')

    await expectCenteredDesktopNavigation(page)
    await expect(page.locator('[data-work-item]')).toHaveCount(6)
    const metrics = page.getByTestId('workspace-header-summary').getByTestId('workspace-header-metric')
    await expect(metrics).toHaveCount(5)
    await expect(metrics.last()).toContainText('no action needed')
    const metricBoxes = await metrics.evaluateAll((nodes) => nodes.map((node) => ({
      top: Math.round(node.getBoundingClientRect().top),
      clipped: node.scrollWidth > node.clientWidth,
    })))
    expect(new Set(metricBoxes.map((box) => box.top)).size, 'header metrics must stay on one line').toBe(1)
    expect(metricBoxes.filter((box) => box.clipped)).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await expectNoOverlap(page.locator('[data-work-item]').filter({ visible: true }))
    await page.screenshot({ path: testInfo.outputPath('work-compact-desktop-current.png') })
    const detail = await inspect(page, 'Build operator controls')
    await expect(detail.getByText('Recover confirmed-lost claim', { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('work-compact-desktop-detail.png'), fullPage: true })

    await dismissOutcomeDetail(page)
    await openCompletedHistory(page)
    await expect(page.getByTestId('completed-change-record')).toHaveCount(2)
    await expectNoOverlap(page.getByTestId('completed-change-record'))
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('work-compact-desktop-history.png'), fullPage: true })  })

  test('short desktop scrolls stage headings with their columns without slicing content', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 640 })
    await page.goto('/delivery')
    await expect(page.locator('[data-work-item]')).toHaveCount(6)

    const surface = page.getByTestId('work-scroll-surface')
    await surface.evaluate((node) => node.scrollBy(0, 140))
    await expect.poll(() => surface.evaluate((node) => node.scrollTop)).toBeGreaterThan(0)

    const surfaceBox = (await surface.boundingBox())!
    const selectorBox = (await page.getByTestId('work-view-selector').boundingBox())!
    expect(selectorBox.y + selectorBox.height).toBeLessThanOrEqual(surfaceBox.y + 0.5)

    await expectNoStageHeadingOcclusion(page)
    await page.screenshot({ path: testInfo.outputPath('work-short-desktop-scrolled.png') })

    // Sweep every intermediate offset: slicing only appears while content passes a heading band.
    const maxScroll = await surface.evaluate((node) => node.scrollHeight - node.clientHeight)
    for (let offset = 0; offset <= maxScroll; offset += 20) {
      await surface.evaluate((node, top) => node.scrollTo(0, top), offset)
      await expectNoStageHeadingOcclusion(page)
    }

    await surface.evaluate((node, top) => node.scrollTo(0, top), Math.round(maxScroll / 2))
    await page.screenshot({ path: testInfo.outputPath('work-short-desktop-scrolled-mid.png') })
  })
})
