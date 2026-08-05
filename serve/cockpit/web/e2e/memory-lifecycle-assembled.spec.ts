import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { expect, test, type Locator, type Page } from '@playwright/test'

const ALL_STATES = ['pending', 'curated', 'approved', 'contested', 'disputed', 'stale', 'deleted']
const ORDERED_TITLES = [
  'Approved memory',
  'Pending memory',
  'Curated memory',
  'Contested memory',
  'Disputed memory',
  'Stale memory',
  'Deleted memory',
]
const EXCEPTIONAL_ENTRIES = [
  { id: '22222222-2222-4222-8222-222222222222', state: 'contested', title: 'Contested memory' },
  { id: '33333333-3333-4333-8333-333333333333', state: 'disputed', title: 'Disputed memory' },
  { id: '44444444-4444-4444-8444-444444444444', state: 'stale', title: 'Stale memory' },
]

async function selectAllStates(page: Page): Promise<void> {
  await page.locator('p-multi-select[name="state-filter"]').evaluate((element, states) => {
    element.dispatchEvent(new CustomEvent('change', {
      detail: { value: states },
      bubbles: true,
    }))
  }, ALL_STATES)
}

async function openEntry(page: Page, title: string): Promise<Locator> {
  const entry = page.getByTestId('memory-entry').filter({ hasText: title })
  await entry.locator('p-accordion').evaluate((element) => {
    ;(element as HTMLElement & { open: boolean }).open = true
    element.dispatchEvent(new CustomEvent('update', { detail: { open: true }, bubbles: true }))
  })
  await expect(entry.getByTestId('memory-accordion-detail')).toBeVisible()
  return entry
}

test.describe('assembled Memory lifecycle', () => {
  test.describe.configure({ mode: 'serial' })

  for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'mobile', width: 390, height: 844 }]) {
    test(`${viewport.name} proves lifecycle visibility and human controls`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await page.goto('/memory')
      await expect(page.getByTestId('memory-tab')).toBeVisible()
      await selectAllStates(page)
      await expect(page.getByTestId('memory-entry')).toHaveCount(7)
      await expect(page.getByTestId('memory-entry-title')).toHaveText(ORDERED_TITLES)
      await expect(page.getByTestId('memory-entry-score')).toHaveText(['0.95', '0.88', '0.84', '0.82', '0.71', '0.61', '0.20'])
      for (const score of await page.getByTestId('memory-entry-score').all()) {
        expect(await score.evaluate((element) => (element as HTMLElement & { variant?: string }).variant)).toBe('secondary')
      }

      const approved = await openEntry(page, 'Approved memory')
      await expect(approved.getByTestId('memory-content-panel')).toContainText('Lifecycle fixture content for Approved memory.')
      await expect(approved).toContainText('Editing will require re-approval')

      const contested = await openEntry(page, 'Contested memory')
      await expect(contested.getByTestId('memory-entry-state')).toHaveText('contested')
      const contestedTask = contested.getByText('Contested task', { exact: true }).locator('..')
      await expect(contestedTask).toContainText('1960')
      await expect(contestedTask.getByRole('button')).toHaveCount(0)
      await expect(contested.getByTestId('memory-edit-btn')).toBeVisible()
      await expect(contested.getByTestId('memory-resolve-btn')).toBeVisible()
      await expect(contested).not.toContainText('Unremarkable')
      await expect(contested).not.toContainText("Didn't use")
      await contested.getByTestId('memory-entry-title').scrollIntoViewIfNeeded()
      await page.screenshot({ path: `test-results/memory-lifecycle-${viewport.name}.png`, fullPage: true })
      if (viewport.name === 'mobile') {
        await contested.getByTestId('memory-detail-actions').scrollIntoViewIfNeeded()
        await page.screenshot({ path: 'test-results/memory-lifecycle-mobile-actions.png', fullPage: true })
      } else {
        await contested.screenshot({ path: 'test-results/memory-lifecycle-desktop-detail.png' })
      }

      const deleted = await openEntry(page, 'Deleted memory')
      await expect(deleted.getByTestId('memory-edit-btn')).toHaveCount(0)
      await expect(deleted.getByTestId('memory-resolve-btn')).toHaveCount(0)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    })
  }

  test('real MCP and Cockpit boundaries reject or complete exceptional-state operations', async ({ page }) => {
    const mcpProofPath = resolve(process.cwd(), 'test-results/memory-lifecycle-mcp.json')
    const mcpProof = JSON.parse(await readFile(mcpProofPath, 'utf-8')) as {
      transport: string
      operations: string[]
      responses: Array<{ state: string; is_error: boolean; message: string }>
    }
    expect(mcpProof.transport).toBe('mcp-stdio')
    expect(mcpProof.operations).toEqual(['curate_memory'])
    expect(mcpProof.operations).not.toContain('resolve_memory')
    expect(mcpProof.responses.map((response) => response.state)).toEqual(['contested', 'disputed', 'stale'])
    for (const response of mcpProof.responses) {
      expect(response.is_error).toBe(true)
      expect(response.message).toContain(response.state)
    }

    await page.goto('/memory')
    await selectAllStates(page)

    for (const exceptional of EXCEPTIONAL_ENTRIES) {
      let entry = await openEntry(page, exceptional.title)
      await entry.getByTestId('memory-edit-btn').click()
      const editedTitle = `${exceptional.title} edited`
      await entry.locator('p-input-text[name="edit-title"]').evaluate((element, title) => {
        element.dispatchEvent(new CustomEvent('input', { detail: { value: title }, bubbles: true }))
      }, editedTitle)

      const editResponsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST' && response.url().endsWith(`/api/memories/${exceptional.id}/edit`))
      await entry.getByTestId('memory-edit-save-btn').click()
      const editResponse = await editResponsePromise
      expect(editResponse.status()).toBe(200)
      const editPayload = await editResponse.json() as { entry: { id: string; state: string; title: string } }
      expect(editPayload.entry).toMatchObject({ id: exceptional.id, state: exceptional.state, title: editedTitle })

      entry = page.getByTestId('memory-entry').filter({ hasText: editedTitle })
      await expect(entry.getByTestId('memory-entry-title')).toHaveText(editedTitle)
      const resolveResponsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST' && response.url().endsWith(`/api/memories/${exceptional.id}/resolve`))
      await entry.getByTestId('memory-resolve-btn').click()
      const resolveResponse = await resolveResponsePromise
      expect(resolveResponse.status()).toBe(200)
      const resolvePayload = await resolveResponse.json() as { entry: { id: string; state: string; title: string } }
      expect(resolvePayload.entry).toMatchObject({ id: exceptional.id, state: 'approved', title: editedTitle })
      await expect(entry.getByTestId('memory-entry-state')).toHaveText('approved')
      await expect(entry.getByTestId('memory-resolve-btn')).toHaveCount(0)
    }
  })
})
