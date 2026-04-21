import { test, expect } from '@playwright/test'

test('app shell loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('[data-region="workspace"]')).toBeVisible()
})
