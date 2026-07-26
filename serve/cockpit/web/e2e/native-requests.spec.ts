import { expect, test, type Page } from '@playwright/test'

const digest = 'a'.repeat(64)
const decision = {
  request: {
    request_id: 'decision-1', kind: 'decision', title: 'Choose storage', summary: 'Select the persistence model', body: 'Compare both approaches.',
    agent: 'builder', created_at: '2026-07-26T10:00:00Z', change_id: 'change', delivery_digest: digest,
    target_node_id: 'DN-011', job_ids: [20],
    options: [
      { option_id: 'local', label: 'Local store', recommended: true, confidence: 0.85, rationale: 'Fast delivery', pros: ['Simple'], cons: ['Single host'], risks: ['Disk loss'] },
      { option_id: 'remote', label: 'Remote store', recommended: false, confidence: 0.7, rationale: 'Shared state', pros: ['Durable'], cons: ['Latency'], risks: ['Outage'] },
    ],
  },
  resolution: null,
}
const action = {
  request: {
    request_id: 'action-1', kind: 'action', title: 'Provide signature', summary: 'Supply signed evidence', body: 'A signature unblocks acceptance.',
    agent: 'builder', created_at: '2026-07-26T10:01:00Z', change_id: 'change', delivery_digest: digest,
    target_node_id: null, job_ids: [21], evidence: ['signature=required'], resume_condition: 'Signature is present',
  },
  resolution: null,
}

async function seed(page: Page) {
  await page.route('**/api/changes', (route) => route.fulfill({ json: { changes: [{ change_id: 'change', state: 'loaded', delivery_digest: digest, diagnostics: [] }] } }))
  await page.route('**/api/changes/change/requests?**', (route) => route.fulfill({ json: { items: [decision, action], next_cursor: null } }))
  await page.route('**/api/changes/change/requests/decision-1', (route) => route.fulfill({ json: decision }))
  await page.route('**/api/changes/change/requests/action-1', (route) => route.fulfill({ json: action }))
  await page.route('**/api/events', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' }))
}

async function choose(page: Page, label: string) {
  await page.getByTestId('native-request-resolver').getByRole('button', { name: new RegExp(label) }).click()
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: complete request context is bounded and Return restores focus`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await seed(page)
    await page.goto('/requests?change=change&request=decision-1')

    const detail = page.getByTestId('request-detail')
    await expect(detail).toBeVisible()
    await expect(detail).toContainText('Pros: Simple')
    await expect(detail).toContainText('Cons: Single host')
    await expect(detail).toContainText('Risks: Disk loss')
    await expect(detail).toContainText('Recommended')
    await expect(detail).toContainText('Confidence 85%')
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

    const box = await detail.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1)

    await detail.getByText('Return', { exact: true }).click()
    await expect(page.locator('[data-request-id="decision-1"]')).toBeFocused()
  })
}

test('request node and job commands navigate to exact native deep links', async ({ page }) => {
  await seed(page)
  await page.goto('/requests?change=change&request=decision-1')
  await page.getByTestId('request-detail').getByText('Open node').click({ noWaitAfter: true })
  await expect(page).toHaveURL('/?change=change&node=DN-011')

  await page.goto('/requests?change=change&request=decision-1')
  await page.getByTestId('request-detail').getByText('Open job #20').click({ noWaitAfter: true })
  await expect(page).toHaveURL('/delivery?change=change&job=20')
})

test('local decision resolution submits digest and renders resumed jobs before refresh', async ({ page }) => {
  await seed(page)
  let submitted: Record<string, unknown> | null = null
  let listCalls = 0
  let resultVisibleAtRefresh = false
  await page.route('**/api/changes/change/requests?**', async (route) => {
    listCalls += 1
    if (listCalls > 1) {
      resultVisibleAtRefresh = await page.getByText('Resumed linked jobs: #20').isVisible()
    }
    await route.fulfill({ json: { items: [decision, action], next_cursor: null } })
  })
  await page.route('**/api/changes/change/requests/decision-1/resolve', async (route) => {
    submitted = await route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({ json: {
      request: { ...decision, resolution: { request_id: 'decision-1', disposition: 'local', resolved_at: '', resolved_by: 'user', selected_option_id: 'local', response: null, rationale: 'Prefer simplicity' } },
      resumed_jobs: [{ job: { job_id: 20 }, token: 'token-20' }],
      resume: { disposition: 'resume-linked-jobs', request_id: 'decision-1', target_node_id: 'DN-011', job_ids: [20] },
      design_reentry: null,
    } })
  })
  await page.goto('/requests?change=change&request=decision-1')
  await choose(page, 'Local store')
  await page.getByTestId('native-request-resolver').getByText('Complete request').click()

  await expect(page.getByText('Resumed linked jobs: #20')).toBeVisible()
  await expect.poll(() => listCalls).toBeGreaterThan(1)
  expect(resultVisibleAtRefresh).toBe(true)
  expect(submitted).toMatchObject({ delivery_digest: digest, selected_option_id: 'local', disposition: 'local' })
})

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: material revision conflict retains authority and Retry renders design re-entry`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await seed(page)
    let calls = 0
    let retryBody: Record<string, unknown> | null = null
    await page.route('**/api/changes/change/requests/action-1/resolve', async (route) => {
      const body = await route.request().postDataJSON() as Record<string, unknown>
      if (calls++ === 0) {
        await route.fulfill({ status: 409, json: { detail: {
          code: 'ERR_CHANGE_REVISION_CONFLICT', detail: 'request changed', current_delivery_digest: 'b'.repeat(64),
        } } })
        return
      }
      retryBody = body
      await route.fulfill({ json: {
        request: action, resumed_jobs: [], resume: null,
        design_reentry: { disposition: 'design-reentry', request_id: 'action-1', change_id: 'change', delivery_digest: 'b'.repeat(64), target_node_id: 'DN-011', job_ids: [21] },
      } })
    })
    await page.goto('/requests?change=change&request=action-1')
    const resolver = page.getByTestId('native-request-resolver')
    const response = resolver.locator('p-textarea')
    await response.evaluate((element) => {
      ;(element as HTMLElement & { value: string }).value = 'signed'
      element.dispatchEvent(new CustomEvent('change', { detail: { value: 'signed' }, bubbles: true }))
    })
    const disposition = resolver.locator('p-select')
    await disposition.evaluate((element) => {
      ;(element as HTMLElement & { value: string }).value = 'material'
      element.dispatchEvent(new CustomEvent('change', { detail: { value: 'material' }, bubbles: true }))
    })
    await resolver.getByText('Complete request').click()

    const conflict = resolver.locator('[role="alert"][tabindex="-1"]')
    await expect(conflict).toBeFocused()
    await expect(conflict).toContainText('ERR_CHANGE_REVISION_CONFLICT')
    await expect(conflict).toContainText('Submitted: signed')
    await expect(conflict).toContainText(`Current digest: ${'b'.repeat(64)}`)
    await expect(conflict).toContainText('Provide signature')
    await conflict.getByText('Retry resolution').click()

    await expect(page.getByText('Design re-entry: DN-011')).toBeVisible()
    expect(retryBody).toMatchObject({ delivery_digest: 'b'.repeat(64), response: 'signed', disposition: 'material' })
  })
}
