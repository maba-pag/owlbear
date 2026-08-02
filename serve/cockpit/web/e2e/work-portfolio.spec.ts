import { expect, test, type Page } from '@playwright/test'

const stages = ['design', 'planning', 'implementation', 'assembly'] as const
const attention = ['user', 'agent', 'waiting', 'none'] as const

function workItems() {
  return Array.from({ length: 16 }, (_, index) => ({
    work_item_id: `OUT-${String(index + 1).padStart(3, '0')}`,
    change_id: `change-${(index % 2) + 1}`,
    scope: 'outcome',
    title: `Outcome ${index + 1}`,
    promise: `Deliver observable outcome ${index + 1}`,
    stage: stages[index % stages.length],
    attention: attention[index % attention.length],
    dependency_ready: true,
    commitment_ids: [`COM-${index + 1}`],
    dependency_ids: [],
    replacement_ids: [],
    task_count: 4,
    reviewed_task_count: index % 5,
    next_action: 'Continue delivery',
  }))
}

async function seed(page: Page) {
  const items = workItems()
  await page.route('**/api/work-items', (route) => route.fulfill({
    json: { items, attention_counts: { user: 4, agent: 4, waiting: 4, none: 4 } },
  }))
  await page.route(/\/api\/work-items\/OUT-\d{3}\?change_id=.*/, (route) => {
    const url = new URL(route.request().url())
    const workItemId = url.pathname.split('/').at(-1)!
    const item = items.find((candidate) => candidate.work_item_id === workItemId)!
    return route.fulfill({ json: {
      card: item,
      authority_identity: 'a'.repeat(64),
      commitments: [{
        commitment_id: item.commitment_ids[0],
        commitment_class: 'protected-request',
        provenance: 'user request',
        statement: `Preserve ${item.title}`,
      }],
      acceptance: [`Observe ${item.title}`],
      task_progress: [{ scope_id: 'PLAN-001', task_count: 4, reviewed_task_count: item.reviewed_task_count }],
      correction_history: [],
      semantic_updates: [],
      completion_summary: null,
      trace_links: { activity: '/trace', evidence: '/trace', requests: '/requests' },
    } })
  })
  await page.route(/\/api\/work-items\/OUT-\d{3}\/requests\?change_id=.*/, (route) => route.fulfill({
    json: { requests: [] },
  }))
  await page.route(/\/api\/work-items\/OUT-\d{3}\/trace\?change_id=.*/, (route) => route.fulfill({
    json: { activity: [{ kind: 'reviewed' }], evidence: [{ kind: 'receipt' }] },
  }))
}

interface Rectangle {
  left: number
  right: number
  top: number
  bottom: number
}

function overlap(first: Rectangle, second: Rectangle): boolean {
  return first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top
}

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`${viewport.name}: work portfolio remains bounded and detail is reachable`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport)
    await seed(page)
    await page.goto('/work')

    await expect(page).toHaveURL(/\/work$/)
    await expect(page.getByTestId('work-shown-count')).toHaveText('Showing 16 of 16')
    for (const label of ['Design', 'Planning', 'Implementation', 'Assembly']) {
      await expect(page.getByText(label, { exact: true })).toBeVisible()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

    const visibleCards = page.locator('[data-work-item]').filter({ visible: true })
    const cardBoxes = await visibleCards.evaluateAll((nodes) => nodes.slice(0, 8).map((node) => {
      const rectangle = node.getBoundingClientRect()
      return { left: rectangle.left, right: rectangle.right, top: rectangle.top, bottom: rectangle.bottom }
    }))
    for (let first = 0; first < cardBoxes.length; first += 1) {
      for (let second = first + 1; second < cardBoxes.length; second += 1) {
        expect(overlap(cardBoxes[first], cardBoxes[second])).toBe(false)
      }
    }

    const firstCard = visibleCards.first()
    const inspect = firstCard.getByText('Inspect', { exact: true })
    await expect(inspect).toBeVisible()
    const cardBox = await firstCard.boundingBox()
    const actionBox = await inspect.boundingBox()
    expect(cardBox).not.toBeNull()
    expect(actionBox).not.toBeNull()
    expect(actionBox!.x).toBeGreaterThanOrEqual(cardBox!.x)
    expect(actionBox!.x + actionBox!.width).toBeLessThanOrEqual(cardBox!.x + cardBox!.width + 1)
    await page.screenshot({ path: testInfo.outputPath(`work-${viewport.name}-portfolio.png`) })
    await inspect.click()

    const detail = page.getByTestId('work-item-detail')
    await expect(detail).toBeVisible()
    await expect(detail.getByRole('heading', { name: 'Specification' })).toBeVisible()
    await expect(detail.getByRole('heading', { name: 'Requests' })).toBeVisible()
    await expect(page.getByTestId('work-technical-trace')).toHaveCount(0)
    await detail.getByText('Show technical trace').click()
    await expect(page.getByRole('heading', { name: 'Activity' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Evidence' })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)

    await page.evaluate(() => window.scrollTo(0, 0))
    await detail.evaluate((element) => element.scrollTo(0, 0))
    await page.screenshot({ path: testInfo.outputPath(`work-${viewport.name}-detail.png`) })
  })
}
