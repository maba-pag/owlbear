import { expect, test, type Page } from '@playwright/test'

const changeDetail = {
  change_id: 'replace-delivery-pipeline',
  delivery_digest: 'b'.repeat(64),
  intent: 'Replace the delivery pipeline with exact native authority.',
  design: 'Compose immutable receipts, typed jobs, and exact proof boundaries.',
  decisions: {
    decisions: [
      { id: 'DEC-001', status: 'accepted', title: 'Use native authority', rationale: 'One source of truth.' },
      { id: 'DEC-002', status: 'superseded', title: 'Use legacy tasks', rationale: 'Retired.' },
    ],
  },
  graph: {
    state: 'admitted',
    authority: { intent: 'intent.md', design: 'design.md', decisions: 'decisions.yaml', research: ['research.md'] },
    admission: { receipt: 'admission-bf5edd', limits: ['No generic mutation'] },
  },
}

async function seedNativeRoutes(page: Page) {
  await page.route('**/api/changes', (route) =>
    route.fulfill({
      json: {
        changes: [
          {
            change_id: 'replace-delivery-pipeline',
            state: 'loaded',
            delivery_digest: 'b'.repeat(64),
            diagnostics: [],
          },
          {
            change_id: 'invalid-change',
            state: 'invalid',
            delivery_digest: null,
            diagnostics: [{ code: 'ERR_CHANGE_INVALID', detail: 'Invalid authority fixture', target: null }],
          },
        ],
      },
    }),
  )
  await page.route('**/api/changes/replace-delivery-pipeline', (route) => route.fulfill({ json: changeDetail }))
  await page.route('**/api/events', (route) =>
    route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' }),
  )
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: peer shell has bounded keyboard-accessible geometry`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await seedNativeRoutes(page)
    await page.goto('/?change=replace-delivery-pipeline')

    await expect(page.getByTestId('native-shell')).toBeVisible()
    await expect(page.getByText('Specification', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('Delivery', { exact: true })).toBeVisible()
    await expect(page.getByText('Use native authority')).toBeVisible()
    await expect(page.getByText('Use legacy tasks')).toHaveCount(0)
    await expect(page.getByText('admission-bf5edd')).toBeVisible()

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(0)

    const boxes = await page.locator('header, nav[aria-label="Product phases"], main').evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect()
        return { left: box.left, top: box.top, right: box.right, bottom: box.bottom }
      }),
    )
    for (const box of boxes) {
      expect(box.left).toBeGreaterThanOrEqual(0)
      expect(box.right).toBeLessThanOrEqual(viewport.width + 1)
      expect(box.bottom).toBeGreaterThan(box.top)
    }

    await page.keyboard.press('Tab')
    let selectorReached = false
    for (let index = 0; index < 12; index += 1) {
      const focusedId = await page.evaluate(() => document.activeElement?.id ?? '')
      if (focusedId === 'change-selector') {
        selectorReached = true
        break
      }
      await page.keyboard.press('Tab')
    }
    expect(selectorReached).toBe(true)

    await page.screenshot({ path: `test-results/native-shell-${viewport.name}.png`, fullPage: true })
  })
}

test('invalid change remains URL-selected with icon and text in both phases', async ({ page }) => {
  await seedNativeRoutes(page)
  await page.goto('/?change=invalid-change')

  const invalid = page.getByTestId('invalid-change')
  await expect(invalid).toContainText('Invalid authority')
  await expect(invalid.locator('p-icon')).toHaveCount(1)
  await page.getByText('Delivery', { exact: true }).click()
  await expect(page).toHaveURL(/\/delivery\?change=invalid-change/)
  await expect(page.getByText('Invalid authority prevents delivery.')).toBeVisible()
  await expect(page.locator('[role="status"] p-icon')).toHaveCount(1)
})
