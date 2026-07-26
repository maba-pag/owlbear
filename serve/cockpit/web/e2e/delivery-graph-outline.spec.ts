import { expect, test, type Page } from '@playwright/test'
import { createDeliveryGraphFixture } from './support/delivery-graph-fixture'

const graphResponse = createDeliveryGraphFixture(300, 'change-300')

async function seed(page: Page) {
  await page.route('**/api/changes', (route) => route.fulfill({ json: { changes: [{ change_id: 'change-300', state: 'loaded', delivery_digest: 'c'.repeat(64), diagnostics: [] }] } }))
  await page.route('**/api/changes/change-300/graph', (route) => route.fulfill({ json: graphResponse }))
  await page.route('**/api/changes/change-300', (route) => route.fulfill({ json: {
    change_id: 'change-300', delivery_digest: 'c'.repeat(64), intent: 'Intent', design: 'Design', decisions: { decisions: [] },
    graph: { state: 'admitted', authority: { intent: 'intent.md', design: 'design.md', decisions: 'decisions.yaml', research: [] }, admission: { receipt: 'admission', limits: [] } },
  } }))
  await page.route('**/api/events', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' }))
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: virtual outline deep-links DN-275 without page overflow`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await seed(page)
    await page.goto('/?change=change-300&node=DN-275')

    const outline = page.getByTestId('delivery-graph-outline')
    const detail = page.getByTestId('node-detail')
    await expect(outline).toBeVisible()
    await expect(detail).toContainText('DN-275')
    await expect(detail).toContainText('DN-275-PK-001')
    expect(await page.locator('[data-node-id]').count()).toBeLessThan(100)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

    for (const locator of [outline, page.getByRole('listbox', { name: 'Delivery nodes' }), detail]) {
      const box = await locator.boundingBox()
      expect(box).not.toBeNull()
      expect(box!.width).toBeGreaterThan(80)
      expect(box!.height).toBeGreaterThan(40)
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1)
    }

    const proofFilter = page.locator('p-input-text[name="graph-filter-proof"]')
    await proofFilter.evaluate((element, value) => {
      ;(element as HTMLElement & { value: string }).value = String(value)
      element.dispatchEvent(new CustomEvent('change', { detail: { value }, bubbles: true }))
    }, 'PROOF-275')
    await expect(outline).toContainText('1 of 300 nodes')
    await expect(detail).toContainText('DN-275')

    await proofFilter.evaluate((element) => {
      ;(element as HTMLElement & { value: string }).value = 'PROOF-001'
      element.dispatchEvent(new CustomEvent('change', { detail: { value: 'PROOF-001' }, bubbles: true }))
    })
    await expect(detail).toContainText('DN-001')
    await expect(page).toHaveURL(/node=DN-001/)
  })
}
