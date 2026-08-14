import { act, render } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type {
  AcceptanceReconciliationResponse,
  WorkItemPortfolioResponse,
} from '../api/workItems'
import { useAcceptanceReconciliation } from '../hooks/useWorkItems'

function portfolio(changeIds: string[], lifecycle: 'awaiting-merge' | 'acceptance' = 'awaiting-merge'): WorkItemPortfolioResponse {
  const groups = changeIds.map((changeId) => ({
    change_id: changeId,
    title: `Change ${changeId}`,
    snapshot_version: 'a'.repeat(64),
    lifecycle,
    outcome_total: 0,
    outcome_completed: 0,
    items: [{
      item_key: 'publication',
      work_item_id: changeId,
      change_id: changeId,
      scope: 'change-publication' as const,
      title: 'Change publication',
      stage: null,
      needs: 'you' as const,
      needs_headline: 'Merge pull request in GitHub',
      next_actor: 'you' as const,
      next_step: 'Merge pull request in GitHub',
      activity: { state: 'idle' as const, worker_role: null, started_at: null, task_id: null },
      progress: { kind: 'publication' as const, label: 'Awaiting merge in GitHub', done: null, total: null },
      action: { kind: 'observe-acceptance' as const, label: 'Check GitHub acceptance', command: null },
    }],
  }))
  return {
    groups,
    totals: {
      total: groups.length,
      complete: 0,
      needs: { you: groups.length, dependency: 0, none: 0 },
      activity: { idle: groups.length, ready: 0, working: 0 },
    },
    operating: {
      unfinished_change_count: groups.length,
      completed_change_count: 0,
      draft_design_change_ids: [],
      design_required_change_ids: [],
      claimed: [],
      queued_for_orchestration: [],
      interventions: [],
      dependency_waits: [],
      guidance: [],
    },
  }
}

function outcome(changeId: string, status: AcceptanceReconciliationResponse['outcomes'][number]['status']) {
  return { change_id: changeId, status, code: null, detail: null, completion_id: null }
}

function Harness({ portfolioData, onChanged }: { portfolioData: WorkItemPortfolioResponse; onChanged: () => void }) {
  useAcceptanceReconciliation(portfolioData, onChanged)
  return null
}

let visible = true
let responses: AcceptanceReconciliationResponse[]
let requests: Array<{ body: unknown }>

async function settle() {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds)
  })
}

function setVisibility(value: 'visible' | 'hidden') {
  visible = value === 'visible'
  document.dispatchEvent(new Event('visibilitychange'))
}

beforeEach(() => {
  visible = true
  responses = [{ outcomes: [outcome('change-a', 'waiting')] }]
  requests = []
  vi.useFakeTimers()
  vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visible ? 'visible' : 'hidden')
  vi.stubGlobal('fetch', vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    requests.push({ body: typeof init?.body === 'string' ? JSON.parse(init.body) : null })
    const payload = responses.shift() ?? { outcomes: [outcome('change-a', 'waiting')] }
    return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

it('stays silent while hidden and reconciles immediately on visible activation', async () => {
  setVisibility('hidden')
  render(<Harness portfolioData={portfolio(['change-a'])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(0)

  setVisibility('visible')
  await settle()
  expect(requests).toHaveLength(1)
  expect(requests[0].body).toEqual({ change_ids: ['change-a'] })
})

it('keeps the provider poll stable across equivalent portfolio replacements', async () => {
  const { rerender } = render(<Harness portfolioData={portfolio(['change-b', 'change-a'])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(1)

  rerender(<Harness portfolioData={portfolio(['change-a', 'change-b'])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(1)

  await advance(30_000)
  expect(requests).toHaveLength(2)
  expect(requests[1].body).toEqual({ change_ids: ['change-a', 'change-b'] })
})

it('serializes visibility-triggered polls while one provider request is in flight', async () => {
  let release: ((response: Response) => void) | undefined
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => { release = resolve })))
  render(<Harness portfolioData={portfolio(['change-a'])} onChanged={vi.fn()} />)
  await settle()
  expect(release).toBeDefined()

  document.dispatchEvent(new Event('visibilitychange'))
  await settle()
  expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1)

  release?.(new Response(JSON.stringify({ outcomes: [outcome('change-a', 'waiting')] }), { status: 200 }))
  await settle()
})

it('backs off locally after provider-unavailable outcomes', async () => {
  const onChanged = vi.fn()
  responses = [
    { outcomes: [outcome('change-a', 'provider-unavailable')] },
    { outcomes: [outcome('change-a', 'waiting')] },
  ]
  render(<Harness portfolioData={portfolio(['change-a'])} onChanged={onChanged} />)
  await settle()
  expect(requests).toHaveLength(1)
  expect(onChanged).toHaveBeenCalledTimes(1)

  await advance(30_000)
  expect(requests).toHaveLength(1)
  await advance(30_000)
  expect(requests).toHaveLength(2)
  expect(onChanged).toHaveBeenCalledTimes(1)
})

it('reconciles immediately when a resumed Change re-enters the observed set', async () => {
  const { rerender } = render(<Harness portfolioData={portfolio([])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(0)

  rerender(<Harness portfolioData={portfolio(['change-a'])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(1)

  rerender(<Harness portfolioData={portfolio([])} onChanged={vi.fn()} />)
  await settle()
  rerender(<Harness portfolioData={portfolio(['change-a'])} onChanged={vi.fn()} />)
  await settle()
  expect(requests).toHaveLength(2)
})

it('does not poll Changes whose acceptance was already observed', async () => {
  render(<Harness portfolioData={portfolio(['change-a'], 'acceptance')} onChanged={vi.fn()} />)
  await settle()

  expect(requests).toHaveLength(0)
})
