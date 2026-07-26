import { expect, test, type Page } from '@playwright/test'

function job(kind: 'plan' | 'build' | 'accept' | 'audit', id: number) {
  return {
    job_id: id,
    token: `token-${id}`,
    kind,
    priority: id,
    change_id: 'change',
    delivery_digest: 'a'.repeat(64),
    target_node_id: `DN-${String(id).padStart(3, '0')}`,
    title: `${kind} job ${id}`,
    outcome: `Immutable ${kind} purpose`,
    acceptance: ['AC-1'],
    modules: ['MOD-001'],
    interfaces: ['IF-003'],
    proof: 'PROOF-003',
    dependency_ready: kind !== 'build',
    claim_id: null,
    disposition: 'pending',
    requests: kind === 'build' ? [{ request: { request_id: 'request-1' }, resolution: null }] : [],
    block_id: kind === 'build' ? 'block-1' : null,
    attempt: null,
    finding: kind === 'build' ? { finding_id: 'finding-1', created_at: '2026-07-26T10:00:00Z' } : null,
    receipt: kind === 'accept' ? { receipt_id: 'receipt-1', kind: 'accept', issued_at: '2026-07-26T10:00:00Z' } : null,
    validity: { code: 'CURRENT', detail: 'current' },
  }
}

const jobs = ['plan', 'build', 'accept', 'audit'].map((kind, index) => job(kind as 'plan' | 'build' | 'accept' | 'audit', index + 1))

async function seed(page: Page) {
  await page.route('**/api/changes', (route) => route.fulfill({ json: { changes: [{ change_id: 'change', state: 'loaded', delivery_digest: 'a'.repeat(64), diagnostics: [] }] } }))
  await page.route('**/api/changes/change/jobs?**', (route) => route.fulfill({ json: { items: jobs, next_cursor: null } }))
  await page.route('**/api/changes/change', (route) => route.fulfill({ json: {
    change_id: 'change', delivery_digest: 'a'.repeat(64), intent: 'Intent', design: 'Design', decisions: { decisions: [] },
    graph: { state: 'admitted', authority: { intent: 'intent.md', design: 'design.md', decisions: 'decisions.yaml', research: [] }, admission: { receipt: 'admission', limits: [] } },
  } }))
  await page.route('**/api/events', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' }))
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: immutable Delivery groups remain bounded and navigable`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await seed(page)
    await page.goto('/delivery?change=change')

    const board = page.getByTestId('delivery-job-board')
    await expect(board).toBeVisible()
    for (const kind of ['plan', 'build', 'accept', 'audit']) {
      await expect(board.getByText(kind, { exact: true })).toBeVisible()
    }
    await expect(board.getByText('Waiting')).toBeVisible()
    await expect(board.getByText('finding-1')).toBeVisible()
    await expect(board.getByText('block-1')).toBeVisible()
    await expect(board.getByText('pending').first()).toBeVisible()
    await expect(board.getByText('receipt-1')).toBeVisible()
    await expect(page.locator('[draggable="true"]')).toHaveCount(0)
    await expect(page.getByText('Move', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Edit fields', { exact: true })).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

    const box = await board.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1)

    await board.locator('[data-job-id="2"]').getByText('Inspect').click()
    await expect(page).toHaveURL(/job=2/)
  })
}

test('priority conflict retains card, submitted intent, and current authority', async ({ page }) => {
  await seed(page)
  let priorityCalls = 0
  await page.route('**/api/changes/change/jobs/2/priority', (route) => route.fulfill({
    ...(priorityCalls++ === 0
      ? {
          status: 409,
          json: {
            detail: {
              code: 'ERR_JOB_ADMIN_OCC_STALE',
              detail: 'job OCC token is stale',
              current_delivery_digest: 'b'.repeat(64),
              current: { job: { ...jobs[1], priority: 8, delivery_digest: 'b'.repeat(64) }, token: 'token-current' },
            },
          },
        }
      : { status: 200, json: { job: { job: jobs[1], token: 'token-new' } } }),
  }))
  await page.goto('/delivery?change=change')

  const card = page.locator('[data-job-id="2"]')
  await card.getByText('Prioritize').click()

  await expect(card).toBeVisible()
  await expect(card).toContainText('ERR_JOB_ADMIN_OCC_STALE')
  await expect(card).toContainText('Submitted: priority 2')
  await expect(card).toContainText('Current token: token-current')
  await expect(card).toContainText(`Current digest: ${'b'.repeat(64)}`)
  await expect(card).toContainText('Current job: priority 8, pending, unclaimed')
  await expect(card.getByText('Retry')).toBeVisible()
  await card.getByText('Retry').click()
  await expect.poll(() => priorityCalls).toBe(2)
})
