import { expect, test, type Page, type TestInfo } from '@playwright/test'

const PRIMARY_CHANGE = 'replace-delivery-pipeline'
const SCALE_CHANGE = 'scale-proof'
const ASSEMBLED_TIMEOUT_MS = 90_000

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
] as const

async function expectAssembledPage(
  page: Page,
  testId: string,
  viewport: { width: number; height: number },
) {
  const route = page.getByTestId(testId)
  await expect(route).toBeVisible()
  await expect.poll(async () => (await page.locator('body').innerText()).trim().length).toBeGreaterThan(80)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

  const bounds = await route.boundingBox()
  expect(bounds).not.toBeNull()
  expect(bounds!.x).toBeGreaterThanOrEqual(0)
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width + 1)
  expect(bounds!.height).toBeGreaterThan(40)

  const verticalLayout = await page.locator('header, main').evaluateAll((elements) => {
    const [header, main] = elements.map((element) => element.getBoundingClientRect())
    return header && main ? { headerBottom: header.bottom, mainTop: main.top } : null
  })
  if (verticalLayout) {
    expect(verticalLayout.mainTop).toBeGreaterThanOrEqual(verticalLayout.headerBottom - 1)
  }
}

async function screenshot(page: Page, testInfo: TestInfo, name: string) {
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true })
}

async function selectActionResponse(page: Page, requestId: string) {
  const resolver = page.getByTestId('native-request-resolver')
  const response = resolver.locator(`p-textarea[name="request-response-${requestId}"]`)
  await response.evaluate((element) => {
    ;(element as HTMLElement & { value: string }).value = 'signature=proof'
    element.dispatchEvent(new CustomEvent('change', { detail: { value: 'signature=proof' }, bubbles: true }))
  })
  await resolver.getByRole('button', { name: 'Complete request' }).click()
  await expect(resolver.locator('div[role="status"]')).toContainText('Resumed linked jobs')
}

test.describe.configure({ mode: 'serial' })

for (const viewport of VIEWPORTS) {
  test(`${viewport.name}: assembled native Cockpit journey`, async ({ page }, testInfo) => {
    test.setTimeout(ASSEMBLED_TIMEOUT_MS)
    await page.setViewportSize(viewport)
    const apiFailures: string[] = []
    const pageErrors: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error.message))
    page.on('response', (response) => {
      if (response.url().includes('/api/') && response.status() >= 400) {
        apiFailures.push(`${response.status()} ${response.url()}`)
      }
    })

    await page.goto(`/?change=${PRIMARY_CHANGE}&node=DN-011`)
    await expectAssembledPage(page, 'specification-page', viewport)
    await expect(page.getByRole('heading', { name: 'Authority metadata' })).toBeVisible()
    await expect(page.getByText('admission-6c95c70c81a1')).toBeVisible()
    const graph = page.getByTestId('delivery-graph-outline')
    await expect(graph).toBeVisible()
    await expect(graph.getByTestId('node-detail')).toContainText('DN-011')
    await expect(graph.getByRole('heading', { name: 'Packet plan' })).toBeVisible()

    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur())
    let selectorReached = false
    for (let index = 0; index < 14; index += 1) {
      await page.keyboard.press('Tab')
      if (await page.evaluate(() => document.activeElement?.id === 'change-selector')) {
        selectorReached = true
        break
      }
    }
    expect(selectorReached).toBe(true)

    const nodeList = graph.getByRole('listbox', { name: 'Delivery nodes' })
    await nodeList.focus()
    await page.keyboard.press('ArrowDown')
    await expect(page).toHaveURL(/node=DN-012/)
    await screenshot(page, testInfo, `PROOF-012-${viewport.name}-specification`)

    await page.getByRole('link', { name: 'Delivery' }).click()
    await expectAssembledPage(page, 'delivery-page', viewport)
    const board = page.getByTestId('delivery-job-board')
    await expect(board).toBeVisible()
    await expect.poll(() => board.locator('[data-job-id]').count()).toBeGreaterThanOrEqual(4)
    await expect(board.getByRole('heading', { name: 'plan', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'build', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'accept', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'audit', exact: true })).toBeVisible()
    const firstJob = board.locator('[data-job-id]').first()
    await firstJob.getByRole('button', { name: 'Inspect' }).click()
    await expect(page.getByTestId('selected-job-detail')).toBeVisible()

    await page.getByRole('link', { name: 'Requests' }).click()
    await expectAssembledPage(page, 'requests-page', viewport)
    const requestId = `request-${viewport.name}`
    await page.locator(`[data-request-id="${requestId}"]`).click()
    await expect(page.getByTestId('request-detail')).toContainText(`Provide ${viewport.name} proof signature`)
    await selectActionResponse(page, requestId)
    await screenshot(page, testInfo, `PROOF-012-${viewport.name}-request-resolved`)
    await page.reload()
    expect(pageErrors).toEqual([])
    await expectAssembledPage(page, 'requests-page', viewport)
    await page.getByRole('button', { name: 'Resolved' }).click()
    await expect(page.locator(`[data-request-id="${requestId}"]`)).toBeVisible()

    await page.getByRole('link', { name: 'Activity' }).click()
    await expectAssembledPage(page, 'activity-page', viewport)
    await expect(page.getByRole('list', { name: 'Native activity' }).locator('[data-activity-id]').first()).toBeVisible()
    await page.getByRole('button', { name: 'Full history' }).click()
    await expect(page.getByText('finding-proof')).toBeVisible()

    await page.getByRole('link', { name: 'Evidence' }).click()
    await expectAssembledPage(page, 'evidence-page', viewport)
    await page.getByRole('button', { name: 'Full history' }).click()
    await expect(page.locator('[data-receipt-id="build-proof"]')).toBeVisible()
    const supersession = page.locator('[data-receipt-id="supersession-proof"]')
    await expect(supersession).toBeVisible()
    await supersession.getByRole('button', { name: 'Inspect supersession chain' }).click()
    await expect(page.getByTestId('supersession-chain')).toContainText('invalidation-proof')
    await expect(page.getByTestId('supersession-chain')).toContainText('finding-proof')
    await screenshot(page, testInfo, `PROOF-012-${viewport.name}-evidence-chain`)

    await page.getByRole('link', { name: 'Legacy' }).click()
    await expectAssembledPage(page, 'legacy-page', viewport)
    await expect(page.locator('[aria-labelledby="legacy-tasks-heading"] li').first()).toBeVisible()
    await expect(page.locator('[aria-labelledby="legacy-requests-heading"] li').first()).toBeVisible()
    await expect(page.locator('[aria-labelledby="legacy-activity-heading"] li').first()).toBeVisible()

    await page.getByRole('link', { name: 'Memory' }).click()
    await expectAssembledPage(page, 'memory-tab', viewport)
    await expect(page.getByTestId('memory-entry-title')).toHaveText('Native proof memory')

    await page.getByRole('link', { name: 'Ideas' }).click()
    await expect(page.getByTestId('ideas-editor-shell')).toBeVisible()
    await expect(page.getByTestId('ideas-preview')).toContainText('Native proof ideas')
    await expect(page.getByTestId('ideas-preview')).toContainText('Preserve Ideas continuity')
    await screenshot(page, testInfo, `PROOF-012-${viewport.name}-preserved-workspaces`)

    await page.goto(`/?change=${SCALE_CHANGE}&node=DN-300`)
    await expectAssembledPage(page, 'specification-page', viewport)
    const scaleGraph = page.getByTestId('delivery-graph-outline')
    await expect(scaleGraph.getByText('300 of 300 nodes')).toBeVisible({ timeout: 30_000 })
    await expect(scaleGraph.getByTestId('node-detail')).toContainText('DN-300')
    await expect(scaleGraph.getByTestId('node-detail')).toContainText('DN-300-PK-001')
    const mountedRows = scaleGraph.locator('[data-node-id]')
    await expect(scaleGraph.locator('[data-node-id="DN-300"]')).toBeVisible()
    expect(await mountedRows.count()).toBeLessThan(100)
    await screenshot(page, testInfo, `PROOF-012-${viewport.name}-scale-300`)

    expect(apiFailures).toEqual([])
  })
}
