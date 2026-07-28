import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { expect, test, type Page, type TestInfo } from '@playwright/test'

const CHANGE_ID = 'proof-013-native-delivery'
const ASSEMBLED_TIMEOUT_MS = 90_000
const PROOF_OUTPUT = resolve(process.cwd(), '../../../.owlbear/scratch/proof-013-cockpit.json')

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
] as const

type Rect = { top: number; right: number; bottom: number; left: number }
type JsonRecord = Record<string, unknown>
const viewportProofs: JsonRecord[] = []

function overlaps(first: Rect, second: Rect): boolean {
  return first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top
}

async function expectReleasePage(
  page: Page,
  testId: string,
  viewport: { width: number; height: number },
): Promise<JsonRecord> {
  const route = page.getByTestId(testId)
  await expect(route).toBeVisible()
  await expect.poll(async () => (await page.locator('body').innerText()).trim().length).toBeGreaterThan(80)

  const geometry = await page.evaluate((routeTestId) => {
    const rect = (element: Element | null) => {
      if (!element) return null
      const value = element.getBoundingClientRect()
      return { top: value.top, right: value.right, bottom: value.bottom, left: value.left }
    }
    const route = document.querySelector(`[data-testid="${routeTestId}"]`)
    const routeHeader = route?.querySelector('header') ?? null
    const primaryContent = route?.querySelector('section, ol, [aria-label="Native receipts"]') ?? null
    const navigation = document.querySelector('nav[aria-label="Product phases"]')
    const controls = [...(routeHeader?.querySelectorAll('button, a, p-button, p-select') ?? [])]
      .map((element) => rect(element))
      .filter((value): value is Rect => value !== null && value.right > value.left && value.bottom > value.top)
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      shellHeader: rect(document.querySelector('[data-testid="native-shell"] > header')),
      route: rect(route),
      routeHeader: rect(routeHeader),
      primaryContent: rect(primaryContent),
      navigation: rect(navigation),
      navigationItems: [...(navigation?.querySelectorAll('a, p-link') ?? [])]
        .map((element) => rect(element))
        .filter((value): value is Rect => value !== null && value.right > value.left && value.bottom > value.top),
      controls,
    }
  }, testId)

  expect(geometry.documentWidth).toBeLessThanOrEqual(geometry.viewportWidth)
  expect(geometry.route).not.toBeNull()
  expect(geometry.route!.left).toBeGreaterThanOrEqual(0)
  expect(geometry.route!.right).toBeLessThanOrEqual(viewport.width + 1)
  expect(geometry.route!.bottom - geometry.route!.top).toBeGreaterThan(40)
  if (geometry.shellHeader && geometry.routeHeader) expect(overlaps(geometry.shellHeader, geometry.routeHeader)).toBe(false)
  if (geometry.routeHeader && geometry.primaryContent) expect(overlaps(geometry.routeHeader, geometry.primaryContent)).toBe(false)
  for (let index = 0; index < geometry.navigationItems.length; index += 1) {
    for (let candidate = index + 1; candidate < geometry.navigationItems.length; candidate += 1) {
      expect(overlaps(geometry.navigationItems[index], geometry.navigationItems[candidate])).toBe(false)
    }
  }
  for (let index = 0; index < geometry.controls.length; index += 1) {
    for (let candidate = index + 1; candidate < geometry.controls.length; candidate += 1) {
      expect(overlaps(geometry.controls[index], geometry.controls[candidate])).toBe(false)
    }
  }
  return geometry
}

async function screenshot(page: Page, testInfo: TestInfo, name: string): Promise<string> {
  const path = testInfo.outputPath(`${name}.png`)
  await page.screenshot({ path, fullPage: true })
  return path
}

async function json(page: Page, path: string): Promise<JsonRecord> {
  const response = await page.request.get(path)
  expect(response.ok(), `${response.status()} ${path}`).toBe(true)
  return response.json() as Promise<JsonRecord>
}

async function selectActionResponse(page: Page, requestId: string) {
  const resolver = page.getByTestId('native-request-resolver')
  const response = resolver.locator(`p-textarea[name="request-response-${requestId}"]`)
  await response.evaluate((element) => {
    ;(element as HTMLElement & { value: string }).value = 'browser=real-fastapi-built-spa'
    element.dispatchEvent(new CustomEvent('change', {
      detail: { value: 'browser=real-fastapi-built-spa' },
      bubbles: true,
    }))
  })
  await resolver.getByRole('button', { name: 'Complete request' }).click()
  await expect(resolver.locator('div[role="status"]')).toContainText('Resumed linked jobs')
}

async function collectProof(page: Page, viewport: string, geometry: JsonRecord[], screenshots: string[]) {
  const prefix = `/api/changes/${CHANGE_ID}`
  const change = await json(page, prefix)
  const graph = await json(page, `${prefix}/graph`)
  const jobs = await json(page, `${prefix}/jobs?candidate_revision=HEAD&limit=100`)
  const receipts = await json(page, `${prefix}/receipts?limit=100`)
  const findings = await json(page, `${prefix}/findings?limit=100`)
  const activity = await json(page, `${prefix}/activity?limit=100`)
  const workHealth = await json(page, `${prefix}/health/work?limit=100`)
  const changeHealth = await json(page, `${prefix}/health/change?limit=100`)
  const legacy = await json(page, '/api/legacy?limit=100')
  const invalidation = await json(page, `${prefix}/invalidations/supersession-accept-001`)
  const receiptItems = receipts.items as JsonRecord[]
  const audit = receiptItems.find((item) => item.receipt_id === 'audit-proof-013')!
  const auditPayload = audit.payload as JsonRecord
  const graphRecord = graph.graph as JsonRecord
  const planReceipts = receiptItems.filter((item) => item.kind === 'plan')
  return {
    schema_version: 1,
    proof: 'PROOF-013',
    boundary: 'Built Cockpit SPA and real FastAPI backend over the completed fresh-consumer native workflow',
    commands: [
      'python setup/init.py (invoked by the assembled workflow)',
      'uv run pytest serve/mcp-kanban/tests/test_complete_native_delivery.py -q --tb=short -n 0',
      'npm run build',
      'npm run test:e2e:native-release',
    ],
    viewport,
    change_id: CHANGE_ID,
    delivery_digest: change.delivery_digest,
    tested_git_revision: auditPayload.code_revision,
    node_plan_digests: Object.fromEntries(planReceipts.map((receipt) => {
      const payload = receipt.payload as JsonRecord
      return [payload.target_node_id, payload.node_plan_digest]
    })),
    graph_nodes: (graphRecord.nodes as JsonRecord[]).map((node) => node.id),
    receipt_ids: receiptItems.map((item) => item.receipt_id),
    admission_receipt: (graphRecord.admission as JsonRecord).receipt,
    plan_receipts: planReceipts.map((item) => item.receipt_id),
    build_receipts: receiptItems.filter((item) => item.kind === 'build').map((item) => item.receipt_id),
    accept_receipts: receiptItems.filter((item) => item.kind === 'accept').map((item) => item.receipt_id),
    audit_receipt: audit.receipt_id,
    audit_impact_closure: audit.impact_closure,
    finding_ids: (findings.items as JsonRecord[]).map((item) => item.finding_id),
    supersession_receipt_id: invalidation.supersession_receipt_id,
    invalidation_id: invalidation.invalidation_id,
    affected_receipt_ids: invalidation.affected_receipt_ids,
    corrective_job_ids: invalidation.corrective_job_ids,
    current_job_receipts: (jobs.items as JsonRecord[])
      .filter((item) => item.receipt)
      .map((item) => {
        const receipt = item.receipt as JsonRecord
        const validity = item.validity as JsonRecord | null
        return { receipt_id: receipt.receipt_id, kind: receipt.kind, validity: validity?.code ?? 'HISTORICAL' }
      }),
    activity_identities: (activity.items as JsonRecord[]).map((item) => item.identity),
    work_health: workHealth,
    change_health: changeHealth,
    legacy_inventory: legacy,
    active_legacy_surfaces: [],
    allowed_replacements: ['temporary consumer repository', 'two pending browser-attestation requests'],
    setup_finalize_invoked: false,
    dn_015_invoked: false,
    api_transport: 'real-fastapi',
    frontend_artifact: 'built-spa',
    geometry,
    screenshots,
  }
}

test.describe.configure({ mode: 'serial' })

for (const viewport of VIEWPORTS) {
  test(`${viewport.name}: completed native release journey`, async ({ page }, testInfo) => {
    test.setTimeout(ASSEMBLED_TIMEOUT_MS)
    await page.setViewportSize(viewport)
    const apiFailures: string[] = []
    const pageErrors: string[] = []
    const geometry: JsonRecord[] = []
    const screenshots: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error.message))
    page.on('response', (response) => {
      if (response.url().includes('/api/') && response.status() >= 400) apiFailures.push(`${response.status()} ${response.url()}`)
    })

    await page.goto(`/?change=${CHANGE_ID}&node=DN-001`)
    geometry.push(await expectReleasePage(page, 'specification-page', viewport))
    await expect(page.getByRole('heading', { name: 'Authority metadata' })).toBeVisible()
    await expect(page.getByText('receipts/admission-')).toBeVisible()
    const graph = page.getByTestId('delivery-graph-outline')
    await expect(graph.getByTestId('node-detail')).toContainText('DN-001')
    await expect(graph.getByTestId('node-detail')).toContainText('DN-001-PK-001')
    screenshots.push(await screenshot(page, testInfo, `PROOF-013-${viewport.name}-specification`))

    await page.getByRole('link', { name: 'Delivery' }).click()
    geometry.push(await expectReleasePage(page, 'delivery-page', viewport))
    const board = page.getByTestId('delivery-job-board')
    await expect.poll(() => board.locator('[data-job-id]').count()).toBeGreaterThanOrEqual(2)
    await expect(board.getByRole('heading', { name: 'plan', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'build', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'accept', exact: true })).toBeVisible()
    await expect(board.getByRole('heading', { name: 'audit', exact: true })).toBeVisible()
    await board.locator('[data-job-id]').first().getByRole('button', { name: 'Inspect' }).click()
    await expect(page.getByTestId('selected-job-detail')).toBeVisible()

    await page.getByRole('link', { name: 'Requests' }).click()
    geometry.push(await expectReleasePage(page, 'requests-page', viewport))
    const requestId = `request-${viewport.name}`
    await page.locator(`[data-request-id="${requestId}"]`).click()
    await expect(page.getByTestId('request-detail')).toContainText(`Provide ${viewport.name} release attestation`)
    await selectActionResponse(page, requestId)
    screenshots.push(await screenshot(page, testInfo, `PROOF-013-${viewport.name}-request-resolved`))

    await page.getByRole('link', { name: 'Evidence' }).click()
    geometry.push(await expectReleasePage(page, 'evidence-page', viewport))
    await expect(page.locator('[data-receipt-id="accept-dn-001"]')).toBeVisible()
    await expect(page.locator('[data-receipt-id="audit-proof-013"]')).toBeVisible()
    await page.getByRole('button', { name: 'Full history' }).click()
    await expect(page.locator('[data-receipt-id="audit-proof-013"]')).toBeVisible()
    await expect(page.locator('[data-receipt-id="build-dn-001-4"]')).toBeVisible()
    const supersession = page.locator('[data-receipt-id="supersession-accept-001"]')
    await expect(supersession).toBeVisible()
    await supersession.getByRole('button', { name: 'Inspect supersession chain' }).click()
    await expect(page.getByTestId('supersession-chain')).toContainText('invalidation-accept-001')
    await expect(page.getByTestId('supersession-chain')).toContainText('finding-accept-001')
    screenshots.push(await screenshot(page, testInfo, `PROOF-013-${viewport.name}-evidence-chain`))

    await page.getByRole('link', { name: 'Activity' }).click()
    geometry.push(await expectReleasePage(page, 'activity-page', viewport))
    await page.getByRole('button', { name: 'Full history' }).click()
    await expect(page.getByText('finding-accept-001')).toBeVisible()
    await expect(page.getByText('audit-proof-013')).toBeVisible()

    await page.getByRole('link', { name: 'Legacy' }).click()
    geometry.push(await expectReleasePage(page, 'legacy-page', viewport))
    await expect(page.locator('[aria-labelledby="legacy-tasks-heading"] li')).toHaveCount(0)
    await expect(page.locator('[aria-labelledby="legacy-requests-heading"] li')).toHaveCount(0)
    await expect(page.locator('[aria-labelledby="legacy-activity-heading"] li')).toHaveCount(0)
    screenshots.push(await screenshot(page, testInfo, `PROOF-013-${viewport.name}-legacy-empty`))

    const proof = await collectProof(page, viewport.name, geometry, screenshots)
    expect((proof.work_health as JsonRecord).findings).toEqual([])
    expect((proof.change_health as JsonRecord).findings).toEqual([])
    expect(proof.legacy_inventory).toEqual({
      tasks: [], requests: [], activity: [], truncated: { tasks: false, requests: false, activity: false },
    })
    expect(proof.receipt_ids).toEqual(expect.arrayContaining([
      'plan-dn-001', 'build-dn-001-4', 'supersession-accept-001', 'build-dn-001-6',
      'accept-dn-001', 'accept-dn-002', 'accept-dn-014', 'audit-proof-013',
    ]))
    expect(proof.finding_ids).toContain('finding-accept-001')
    expect(proof.audit_impact_closure).toEqual(expect.objectContaining({ paths: ['/'] }))
    expect(apiFailures).toEqual([])
    expect(pageErrors).toEqual([])

    const output = testInfo.outputPath(`PROOF-013-${viewport.name}.json`)
    await writeFile(output, `${JSON.stringify(proof, null, 2)}\n`, 'utf8')
    await testInfo.attach(`PROOF-013-${viewport.name}`, { path: output, contentType: 'application/json' })
    viewportProofs.push(proof)
    if (viewport.name === 'mobile') {
      await mkdir(resolve(PROOF_OUTPUT, '..'), { recursive: true })
      await writeFile(PROOF_OUTPUT, `${JSON.stringify({ ...proof, viewport_runs: viewportProofs }, null, 2)}\n`, 'utf8')
    }
  })
}
