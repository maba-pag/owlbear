import { expect, test } from '@playwright/test'
import { execFile } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { promisify } from 'node:util'

const failedEntryId = '11111111-1111-4111-8111-111111111111'
const runFile = promisify(execFile)

test.describe('assembled Memory purge', () => {
  test('previews, cancels, and executes project-wide tombstone cleanup through production HTTP', async ({ page }) => {
    await page.goto('/memories')
    await expect(page.getByTestId('memory-tab')).toBeVisible()
    await expect(page.getByTestId('memory-purge-open-button')).toHaveText('Purge deleted (3)')
    await expect(page.getByText('Eligible deleted')).toHaveCount(0)
    await page.locator('p-multi-select[name="state-filter"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('change', { detail: { value: ['approved'] }, bubbles: true }))
    })
    await expect(page.getByTestId('memory-purge-open-button')).toHaveText('Purge deleted (3)')

    await page.getByTestId('memory-purge-open-button').click()
    const purgeDialog = page.getByTestId('memory-purge-dialog')
    await expect(purgeDialog).toBeVisible()
    await purgeDialog.locator('p-button').filter({ hasText: 'Cancel' }).dispatchEvent('click')
    await expect(page.getByTestId('memory-purge-open-button')).toHaveText('Purge deleted (3)')

    await page.getByTestId('memory-purge-open-button').click()
    await page.locator('p-input-number[name="memory-purge-threshold"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('input', { detail: { value: '1' }, bubbles: true }))
    })
    await purgeDialog.locator('p-button').filter({ hasText: 'Preview' }).dispatchEvent('click')
    const positivePreview = page.getByTestId('memory-purge-preview')
    await expect(positivePreview.locator('div').filter({ has: page.getByText('Eligible') }).locator('dd')).toHaveText('2')
    await expect(positivePreview.locator('div').filter({ has: page.getByText('Too recent') }).locator('dd')).toHaveText('1')
    const fixture = JSON.parse(await readFile('test-results/memory-purge-fixture.json', 'utf8')) as {
      memoryDir: string
    }
    const failedEntryPath = join(fixture.memoryDir, `${failedEntryId}.md`)
    await runFile('chflags', ['uchg', failedEntryPath])
    await purgeDialog.locator('p-button').filter({ hasText: 'Purge' }).dispatchEvent('click')

    await expect(page.getByTestId('memory-purge-receipt')).toContainText('Purged 1; skipped 1; failed 1')
    await runFile('chflags', ['nouchg', failedEntryPath])
    await page.locator('p-multi-select[name="state-filter"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('change', { detail: { value: ['deleted'] }, bubbles: true }))
    })
    await expect(page.getByTestId('memory-purge-open-button')).toHaveText('Purge deleted (2)')
    await expect(page.getByText('Eligible deleted')).toBeVisible()
    await expect(page.getByText('Recent deleted')).toBeVisible()
    await expect(page.getByText('Exact cutoff deleted')).toHaveCount(0)

    await page.getByTestId('memory-purge-open-button').click()
    await page.locator('p-input-number[name="memory-purge-threshold"]').evaluate((element) => {
      element.dispatchEvent(new CustomEvent('input', { detail: { value: '0' }, bubbles: true }))
    })
    await purgeDialog.locator('p-button').filter({ hasText: 'Preview' }).dispatchEvent('click')
    const zeroDayPreview = page.getByTestId('memory-purge-preview')
    await expect(zeroDayPreview.locator('div').filter({ has: page.getByText('Eligible') }).locator('dd')).toHaveText('2')
    await expect(zeroDayPreview.locator('div').filter({ has: page.getByText('Too recent') }).locator('dd')).toHaveText('0')
    await purgeDialog.locator('p-button').filter({ hasText: 'Purge' }).dispatchEvent('click')

    await expect(page.getByTestId('memory-purge-receipt')).toContainText('Purged 2; skipped 0; failed 0')
    await expect(page.getByTestId('memory-purge-open-button')).toHaveText('Purge deleted (0)')
    await expect(page.getByText('Eligible deleted')).toHaveCount(0)
    await expect(page.getByText('Recent deleted')).toHaveCount(0)
    await expect(page.getByText('Exact cutoff deleted')).toHaveCount(0)
  })
})
