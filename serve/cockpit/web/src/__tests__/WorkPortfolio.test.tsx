import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import type {
  ChangeGroupView,
  CompletedChangeRecord,
  PortfolioOperatingView,
  WorkItemCardView,
  WorkItemDetailResponse,
  WorkItemPortfolioResponse,
} from '../api/workItems'
import { PortfolioHeaderSummary } from '../components/PortfolioOperatingSummary'
import WorkPortfolioPage from '../pages/WorkPortfolioPage'

function card(overrides: Partial<WorkItemCardView> = {}): WorkItemCardView {
  return {
    item_key: 'outcome:OUT-001',
    work_item_id: 'OUT-001',
    change_id: 'change-alpha',
    scope: 'outcome',
    title: 'Delivery foundation',
    stage: 'implementation',
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Work in progress',
    activity: { state: 'working', worker_role: 'builder', started_at: '2026-08-08T10:00:00Z', task_id: 'TASK-001' },
    progress: { kind: 'tasks', label: '1 of 2 Delivery tasks reviewed', done: 1, total: 2 },
    action: { kind: 'none', label: null, command: null },
    ...overrides,
  }
}

function group(overrides: Partial<ChangeGroupView> = {}): ChangeGroupView {
  return {
    change_id: 'change-alpha',
    title: 'Portfolio redesign',
    snapshot_version: 'a'.repeat(64),
    lifecycle: 'in-delivery',
    outcome_total: 2,
    outcome_completed: 0,
    items: [
      card(),
      card({
        item_key: 'outcome:OUT-002',
        work_item_id: 'OUT-002',
        title: 'User controls',
        stage: 'planning',
        needs: 'you',
        needs_headline: 'Decision required',
        next_actor: 'you',
        next_step: 'Decision required',
        activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
        progress: { kind: 'plan', label: 'Task plan not published', done: null, total: null },
        action: { kind: 'answer-request', label: 'Answer request', command: null },
      }),
    ],
    ...overrides,
  }
}

function portfolio(groups: ChangeGroupView[] = [group()]): WorkItemPortfolioResponse {
  const items = groups.flatMap((item) => item.items)
  const reference = (item: WorkItemCardView) => ({
    change_id: item.change_id,
    item_key: item.item_key,
    scope: item.scope === 'change-integration' ? 'integration' as const : 'outcome' as const,
  })
  const claimed = items.filter((item) => ['working', 'repairing'].includes(item.activity.state)).map(reference)
  const queued = items.filter((item) => item.activity.state === 'ready' || item.needs === 'repair').map(reference)
  const interventions = items.filter((item) => item.needs === 'you').map(reference)
  const dependencyWaits = items.filter((item) => item.needs === 'dependency').map(reference)
  const guidance: WorkItemPortfolioResponse['operating']['guidance'] = []
  if (interventions.length > 0) guidance.push({ kind: 'intervene', change_ids: [...new Set(interventions.map((item) => item.change_id))], work_count: interventions.length })
  if (claimed.length > 0) guidance.push({ kind: 'work-underway', change_ids: [...new Set(claimed.map((item) => item.change_id))], work_count: claimed.length })
  else if (queued.length > 0) guidance.push({ kind: 'start-orchestration', change_ids: [...new Set(queued.map((item) => item.change_id))], work_count: queued.length })
  else if (dependencyWaits.length > 0) guidance.push({ kind: 'wait', change_ids: [...new Set(dependencyWaits.map((item) => item.change_id))], work_count: dependencyWaits.length })
  if (groups.length === 0) guidance.push({ kind: 'create-change', change_ids: [], work_count: 0 })
  return {
    groups,
    totals: {
      total: items.length,
      complete: items.filter((item) => item.stage === 'completed' && item.scope === 'outcome').length,
      needs: {
        you: items.filter((item) => item.needs === 'you').length,
        dependency: items.filter((item) => item.needs === 'dependency').length,
        repair: items.filter((item) => item.needs === 'repair').length,
        none: items.filter((item) => item.needs === 'none').length,
      },
      activity: {
        idle: items.filter((item) => item.activity.state === 'idle').length,
        ready: items.filter((item) => item.activity.state === 'ready').length,
        working: items.filter((item) => item.activity.state === 'working').length,
        repairing: items.filter((item) => item.activity.state === 'repairing').length,
      },
    },
    operating: {
      unfinished_change_count: groups.length,
      completed_change_count: 0,
      draft_design_change_ids: [],
      design_required_change_ids: [],
      claimed,
      queued_for_orchestration: queued,
      interventions,
      dependency_waits: dependencyWaits,
      guidance,
    },
  }
}

function detail(overrides: Partial<WorkItemDetailResponse['item']> = {}): WorkItemDetailResponse {
  return {
    item: {
      snapshot_version: 'a'.repeat(64),
      change_title: 'Portfolio redesign',
      card: card(),
      promise: 'Make Delivery supervision coherent.',
      acceptance: ['The current state is unambiguous.'],
      commitments: [{
        commitment_id: 'COM-001',
        commitment_class: 'protected-request',
        provenance: 'user request',
        statement: 'Keep user attention explicit.',
      }],
      dependencies: [],
      tasks: [{
        task_id: 'TASK-001',
        title: 'Build the projection',
        result: 'A reviewed grouped snapshot.',
        status: 'reviewed',
        completed_commit: '1'.repeat(40),
        acceptance_observations: ['Projection is observable.'],
        proof_boundaries: ['Focused component test'],
      }],
      block: null,
      requests: [],
      active_claim: null,
      return_context: null,
      operator_moves: [],
      recovery_attention: null,
      integration: null,
      ...overrides,
    },
  }
}

const completed: CompletedChangeRecord = {
  change_id: 'change-alpha',
  completion_id: 'b'.repeat(64),
  completion_path: '.owlbear/completed/change-alpha',
  package_id: 'c'.repeat(64),
  introducing_target_commit: 'd'.repeat(40),
  source_target_commit: 'e'.repeat(40),
  title: 'Portfolio redesign',
  semantic_summary: 'Shipped the grouped Delivery workspace.',
}

let currentPortfolio: WorkItemPortfolioResponse
let currentDetail: WorkItemDetailResponse
let portfolioAfterIntegration: WorkItemPortfolioResponse | null
let portfolioFailure: boolean
let detailFailure: boolean
let requests: Array<{ url: string; method: string; body: unknown }>

function response(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function requestUrl(input: RequestInfo | URL): string {
  return typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
}

function installFetch() {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = requestUrl(input)
    const method = init?.method ?? 'GET'
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : null
    requests.push({ url, method, body })

    if (method === 'GET' && url === '/api/work-items') {
      return portfolioFailure ? response({ detail: 'Temporary polling failure' }, 503) : response(currentPortfolio)
    }
    if (method === 'GET' && url.startsWith('/api/changes/change-alpha/work-items/')) {
      return detailFailure ? response({ detail: 'Delivery runtime is absent: change-alpha' }, 409) : response(currentDetail)
    }
    if (method === 'GET' && url === '/api/design-work/design-draft') {
      return response({
        change_id: 'design-draft',
        package_id: 'd'.repeat(64),
        intent_markdown: '# Design Draft\n\nShape a coherent operator workflow.',
        design_markdown: '# Architecture\n\nKeep authority explicit.',
      })
    }
    if (method === 'GET' && url === '/api/work-items/completed') {
      return response({ records: [completed], next_cursor: null })
    }
    if (method === 'GET' && url.startsWith('/api/work-items/completed/change-alpha')) return response(completed)

    if (method === 'POST' && url.includes('/requests/')) {
      const requestId = url.split('/requests/')[1].split('/')[0]
      currentDetail = detail({
        ...currentDetail.item,
        requests: currentDetail.item.requests.map((item) => item.request_id === requestId
          ? { ...item, resolution: body as { selected_option_id: string | null; response_text: string | null } }
          : item),
      })
      return response({})
    }
    if (method === 'POST' && url.includes('/blocks/')) {
      currentDetail = detail({ ...currentDetail.item, block: null })
      return response({})
    }
    if (method === 'POST' && url.endsWith('/claims/recover')) {
      currentDetail = detail({ ...currentDetail.item, active_claim: null })
      return response({})
    }
    if (method === 'POST' && url.endsWith('/move-backward/preview')) {
      return response({
        outcome_id: 'OUT-001',
        target: (body as { target: string }).target,
        snapshot_version: 'a'.repeat(64),
        invalidated_outcome_ids: ['OUT-001', 'OUT-002'],
      })
    }
    if (method === 'POST' && url.endsWith('/move-backward')) {
      return response({ invalidated_outcome_ids: ['OUT-002'], move: {} })
    }
    if (method === 'POST' && url.endsWith('/integration/retry')) {
      if (portfolioAfterIntegration) currentPortfolio = portfolioAfterIntegration
      return response({})
    }
    return response({ detail: 'Not found' }, 404)
  }))
}

function selectValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string }
  host.value = value
  fireEvent(host, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function inputValue(element: Element, value: string) {
  const host = element as HTMLElement & { value: string }
  host.value = value
  fireEvent(host, new CustomEvent('input', { detail: { value }, bubbles: true }))
}

function renderPage(path = '/delivery') {
  return render(<MemoryRouter initialEntries={[path]}><WorkPortfolioPage /></MemoryRouter>)
}

beforeEach(() => {
  currentPortfolio = portfolio()
  currentDetail = detail()
  portfolioAfterIntegration = null
  portfolioFailure = false
  detailFailure = false
  requests = []
  installFetch()
})

it('summarizes all current Change phases and nonzero operating states', () => {
  const outcome = { change_id: 'delivery-change', item_key: 'outcome:OUT-001', scope: 'outcome' as const }
  const integration = { change_id: 'integration-change', item_key: 'integration', scope: 'integration' as const }
  const operating: PortfolioOperatingView = {
    unfinished_change_count: 3,
    completed_change_count: 8,
    draft_design_change_ids: ['draft-change'],
    design_required_change_ids: ['design-reentry'],
    claimed: [outcome],
    queued_for_orchestration: [integration],
    interventions: [outcome],
    dependency_waits: [integration],
    guidance: [],
  }

  render(<PortfolioHeaderSummary operating={operating} />)

  expect(screen.getAllByTestId('workspace-header-metric').map((metric) => metric.textContent)).toEqual([
    '4current Changes',
    '2in Design',
    '2in Delivery',
    '1work item active',
    '1work item queued',
    '1work item needs you',
    '1work item waiting',
  ])
})

it('presents Change-grouped Outcomes by work, progress, and status', async () => {
  renderPage()

  const table = await screen.findByTestId('work-portfolio-table')
  expect(table).toHaveTextContent('Portfolio redesign')
  expect(table).toHaveTextContent('Work')
  expect(table).toHaveTextContent('Progress')
  expect(table).toHaveTextContent('Status')
  expect(table).toHaveTextContent('Builder working')
  expect(table).toHaveTextContent('Decision required')
  expect(table).toHaveTextContent('Answer request')
  expect(table).toHaveTextContent('Outcome: OUT-001')
  expect(within(table).getAllByText('OUT-001', { selector: 'code' }).length).toBeGreaterThan(0)
  expect(within(table).getAllByText('Portfolio redesign')).toHaveLength(1)
  expect(await screen.findByLabelText('Delivery portfolio status')).toHaveTextContent('1work item active')
  const guidance = screen.getByLabelText('Session suggestions')
  expect(guidance).toHaveTextContent('Review 1 item that needs you')
  expect(guidance).toHaveTextContent('/orchestrate is already working')
  expect(within(guidance).getByText('/orchestrate', { selector: 'code' })).toBeInTheDocument()
  expect(within(guidance).getByRole('button', { name: 'Copy command /orchestrate' })).toBeInTheDocument()
  expect(guidance).not.toHaveTextContent('Start /orchestrate')
  expect(table.compareDocumentPosition(guidance) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.queryByText('Reviewed', { exact: true })).not.toBeInTheDocument()
})

it('shows unadmitted Design work on the board and opens its verified sources', async () => {
  currentPortfolio = {
    ...portfolio(),
    operating: {
      ...portfolio().operating,
      draft_design_change_ids: ['design-draft'],
      guidance: [{ kind: 'resume-design', change_ids: ['design-draft'], work_count: 1 }],
    },
  }
  renderPage('/delivery/design-draft/design')

  const designWork = await screen.findByTestId('design-work-section')
  expect(designWork).toHaveTextContent('Design Draft')
  expect(designWork).toHaveTextContent('Not admitted to Delivery')
  expect(designWork).toHaveTextContent('/design design-draft')
  expect(within(designWork).getByRole('button', { name: 'Copy command /design design-draft' })).toBeInTheDocument()
  expect(within(designWork).getAllByRole('term').map((term) => term.textContent)).toEqual(['Work', 'Progress', 'Status'])
  expect(within(designWork).getAllByRole('definition')).toHaveLength(3)
  const status = screen.getByLabelText('Delivery portfolio status')
  expect(status).toHaveTextContent('2current Changes')
  expect(status).toHaveTextContent('1in Design')
  expect(status).toHaveTextContent('1in Delivery')

  const detailView = await screen.findByTestId('design-work-detail')
  expect(detailView).toHaveTextContent('Shape a coherent operator workflow.')
  expect(detailView).toHaveTextContent('Continue with/design design-draft')
  expect(within(detailView).getByRole('button', { name: 'Copy command /design design-draft' })).toBeInTheDocument()
  fireEvent.click(screen.getByText('Design', { selector: 'summary' }))
  expect(detailView).toHaveTextContent('Keep authority explicit.')
  expect(requests.some(({ url }) => url === '/api/design-work/design-draft')).toBe(true)
  const guidance = screen.getByLabelText('Session suggestions')
  expect(guidance).toHaveTextContent('Continue Design with')
  expect(within(guidance).getByText('/design design-draft', { selector: 'code' })).toBeInTheDocument()
  expect(within(guidance).getByRole('button', { name: 'Copy command /design design-draft' })).toBeInTheDocument()
})

it('filters grouped rows by Change and Needs without conflating Activity', async () => {
  const secondGroup = group({
    change_id: 'change-beta',
    title: 'Runtime hardening',
    snapshot_version: 'b'.repeat(64),
    outcome_total: 1,
    items: [card({
      change_id: 'change-beta',
      needs: 'dependency',
      needs_headline: 'Waiting on OUT-009',
      next_actor: 'dependency',
      next_step: 'Waiting on OUT-009',
    })],
  })
  const basePortfolio = portfolio([group(), secondGroup])
  currentPortfolio = {
    ...basePortfolio,
    operating: { ...basePortfolio.operating, draft_design_change_ids: ['design-draft'] },
  }
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-table')

  fireEvent.click(screen.getByTestId('work-filters-toggle'))
  const selects = container.querySelectorAll('p-select')
  selectValue(selects[0], 'change-alpha')
  selectValue(selects[1], 'you')

  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('1 of 4')
  expect(screen.getByTestId('work-portfolio-table')).toHaveTextContent('User controls')
  expect(screen.getByTestId('work-portfolio-table')).not.toHaveTextContent('Delivery foundation')
  expect(screen.getByTestId('work-portfolio-table')).not.toHaveTextContent('Runtime hardening')

  selectValue(selects[0], '')
  expect(await screen.findByTestId('design-work-section')).toHaveTextContent('Design Draft')
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('2 of 4')

  selectValue(selects[1], 'dependency')
  await waitFor(() => expect(screen.queryByTestId('design-work-section')).not.toBeInTheDocument())
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('1 of 4')

  selectValue(selects[1], 'you')
  selectValue(selects[0], 'change-beta')
  expect(await screen.findByText('No portfolio entries match the current filters.')).toBeInTheDocument()
  expect(screen.queryByText('No current Delivery work.')).not.toBeInTheDocument()
})

it('opens routed semantic detail with acceptance and bounded task evidence', async () => {
  renderPage()
  const table = await screen.findByTestId('work-portfolio-table')
  fireEvent.click(within(table).getAllByRole('link', { name: /Delivery foundation/ })[0])

  const inspector = await screen.findByTestId('work-item-detail')
  expect(screen.getByLabelText('Session suggestions')).toBeInTheDocument()
  expect(screen.getByTestId('work-portfolio-table')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Current delivery' })).not.toBeInTheDocument()
  expect(inspector).toHaveTextContent('Portfolio redesign / OUT-001')
  expect(within(inspector).getByText('OUT-001', { selector: 'code' })).toBeInTheDocument()
  expect(inspector).toHaveTextContent('Make Delivery supervision coherent.')
  expect(inspector).toHaveTextContent('The current state is unambiguous.')
  expect(inspector).toHaveTextContent('Build the projection')
  expect(inspector).toHaveTextContent('A reviewed grouped snapshot.')
  expect(screen.getByText('Acceptance (1)').closest('details')).not.toHaveAttribute('open')
  expect(screen.getByText('Delivery task evidence (1)').closest('details')).not.toHaveAttribute('open')
  expect(requests.some(({ url }) => url === '/api/changes/change-alpha/work-items/outcome%3AOUT-001')).toBe(true)
})

it('answers a decision request and refetches its resolved state', async () => {
  currentDetail = detail({
    requests: [{
      request_id: 'REQ-001',
      kind: 'decision',
      outcome_id: 'OUT-001',
      summary: 'Choose the retained contract',
      options: [{ option_id: 'keep', label: 'Keep it' }],
      resolution: null,
    }],
  })
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByText('Choose the retained contract')

  const submit = screen.getByText('Submit answer') as HTMLElement & { disabled: boolean }
  await waitFor(() => {
    selectValue(container.querySelector('p-select[name="request-REQ-001-option"]')!, 'keep')
    expect(submit.disabled).toBe(false)
  })
  fireEvent.click(submit)

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/requests/REQ-001/answer',
    method: 'POST',
    body: { selected_option_id: 'keep', response_text: null },
  }))
  expect(await screen.findByText('Keep it')).toBeInTheDocument()
})

it('requires evidence before clearing a requestless block', async () => {
  currentDetail = detail({
    block: {
      block_id: 'BLOCK-001',
      reason: 'Proof is missing',
      unblock_condition: 'Verify external evidence',
      expected_evidence: ['Evidence locator'],
      locators: ['request:REQ-001'],
      request_id: null,
      resolution_note: null,
      resolution_locators: [],
      resume_commit: null,
    },
  })
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  const clear = await screen.findByText('Clear block') as HTMLElement & { disabled: boolean }
  expect(clear.disabled).toBe(true)

  await waitFor(() => {
    inputValue(container.querySelector('p-input-text[name="block-note"]')!, 'Verified externally')
    inputValue(container.querySelector('p-input-text[name="block-locator"]')!, 'request:REQ-001')
    expect(clear.disabled).toBe(false)
  })
  fireEvent.click(clear)

  await waitFor(() => expect(requests.some(({ url, method }) => method === 'POST' && url.includes('/blocks/BLOCK-001/clear'))).toBe(true))
  expect(await screen.findByText('Block cleared.')).toBeInTheDocument()
})

it('keeps claim recovery and backward movement explicit and confirmable', async () => {
  currentDetail = detail({
    card: card({ stage: 'implementation' }),
    active_claim: {
      attempt_id: 'attempt-one',
      claim_id: 'claim-one',
      started_at: '2026-08-08T10:00:00Z',
      worker_role: 'builder',
      task_id: 'TASK-001',
    },
  })
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByText('Recover confirmed-lost claim')
  fireEvent.click(screen.getByText('Recover confirmed-lost claim'))
  fireEvent.click(screen.getByText('Confirm lost and recover'))
  await waitFor(() => expect(requests.some(({ url, method }) => method === 'POST' && url.endsWith('/claims/recover'))).toBe(true))

  fireEvent.click(screen.getByText('Administrative actions'))
  selectValue(container.querySelector('p-select[name="backward-stage"]')!, 'planning')
  inputValue(container.querySelector('p-input-text[name="backward-reason"]')!, 'Authority changed')
  fireEvent.click(screen.getByText('Review backward move'))
  const previewMessage = await screen.findByText('The following Outcomes will be reset:')
  const previewModal = previewMessage.closest('p-modal')!
  expect(within(previewModal).getByText('OUT-002')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Confirm backward move'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/outcomes/OUT-001/move-backward',
    method: 'POST',
    body: { target: 'planning', reason: 'Authority changed', snapshot_version: 'a'.repeat(64) },
  }))
  expect(await screen.findByText('Moved backward. Reset: OUT-002.')).toBeInTheDocument()
})

it('routes Integration repair through Orchestration while keeping raw diagnostics collapsed', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    needs: 'repair',
    needs_headline: 'Merge conflict',
    next_actor: 'repair',
    next_step: 'Run a reviewed Integration repair',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Integration repair required', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: 'merge-conflict',
      disposition: 'repair-required',
      headline: 'Merge conflict',
      explanation: 'One conflicting file requires a reviewed repair.',
      conflicted_paths: ['serve/delivery/work_items.py'],
      diagnostics: ['CONFLICT (content): Merge conflict in serve/delivery/work_items.py'],
      retry_condition: 'Admit a reviewed repair.',
      superseded: false,
      repair_active: false,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'integration', outcome_completed: 2, items: [integrationCard] })])
  renderPage('/delivery/change-alpha/integration')

  const inspector = await screen.findByTestId('work-item-detail')
  const integrationRow = screen.getByLabelText('Change Integration for Portfolio redesign')
  expect(within(integrationRow).getAllByRole('term').map((term) => term.textContent)).toEqual(['Work', 'Progress', 'Status'])
  expect(within(integrationRow).getAllByRole('definition')).toHaveLength(3)
  expect(inspector).toHaveTextContent('Merge conflict')
  expect(inspector).toHaveTextContent('Conflicting files')
  expect(inspector).toHaveTextContent('serve/delivery/work_items.py')
  expect(screen.getByLabelText('Delivery portfolio status')).toHaveTextContent('1work item queued')
  expect(inspector).not.toHaveTextContent('/integration-repair')
  expect(screen.getByText('Technical evidence').closest('details')).not.toHaveAttribute('open')
  expect(screen.queryByText('Retry Integration')).not.toBeInTheDocument()
  expect(inspector).not.toHaveTextContent('Complete')
})

it('separates current Integration retry guidance from stale attempt evidence', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    needs: 'none',
    needs_headline: 'Integration target moved',
    next_actor: 'agent',
    next_step: 'Retry against the current target',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Awaiting retry against current target', done: null, total: null },
    action: { kind: 'retry-integration', label: 'Retry Integration', command: null },
  })
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: 'merge-conflict',
      disposition: 'repair-required',
      headline: 'Integration target moved',
      explanation: 'The Integration target moved since this attempt; retry against the current target.',
      conflicted_paths: ['serve/delivery/work_items.py'],
      diagnostics: ['CONFLICT (content): Merge conflict in serve/delivery/work_items.py'],
      retry_condition: 'Retry Integration against the current target head; the previous verdict is stale.',
      superseded: true,
      repair_active: false,
    },
  })
  renderPage('/delivery/change-alpha/integration')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('The Integration target moved since this attempt; retry against the current target.')
  expect(inspector).toHaveTextContent('Waiting for Orchestration. Orchestration will retry against the current target.')
  const retryControl = within(inspector).getByText('Retry now').closest('p-button-pure') as HTMLElement & { color: string; size: string }
  expect(retryControl.color).toBe('contrast-medium')
  expect(retryControl.size).toBe('xs')
  expect(inspector).toHaveTextContent('ProgressAwaiting retry against current target')
  const staleEvidence = screen.getByText('Previous attempt (stale)').closest('details')
  expect(staleEvidence).not.toHaveAttribute('open')
  expect(staleEvidence).toHaveTextContent('serve/delivery/work_items.py')
  expect(screen.getByTestId('integration-diagnostics-scroll')).toHaveClass('min-w-0', 'max-w-full', 'overflow-x-auto')
  expect(inspector).not.toHaveTextContent('Next: Retry Integration')
})

it('states operator-required Integration status once', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    needs: 'you',
    needs_headline: 'Revision pending',
    next_actor: 'you',
    next_step: 'Revision pending',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Attempt failed', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: 'revision-pending',
      disposition: 'operator-required',
      headline: 'Revision pending',
      explanation: 'Integration retained evidence that requires your review.',
      conflicted_paths: [],
      diagnostics: [],
      retry_condition: 'Publish a corrected revision.',
      superseded: false,
      repair_active: false,
    },
  })
  renderPage('/delivery/change-alpha/integration')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).getAllByText('Revision pending')).toHaveLength(1)
  expect(within(inspector).getByRole('region', { name: 'Integration requires your attention' })).toBeInTheDocument()
})

it('uses the Done status tag without leaking the internal Stage field', async () => {
  currentDetail = detail({
    card: card({
      stage: 'completed',
      next_actor: 'none',
      next_step: 'Complete — no action needed',
      activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
      progress: { kind: 'tasks', label: '1 of 1 Delivery tasks reviewed', done: 1, total: 1 },
    }),
  })
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Done')
  expect(inspector).not.toHaveTextContent('Completed')
  expect(inspector).not.toHaveTextContent('Stage')
  expect(inspector).toHaveTextContent('Progress1 of 1 Delivery tasks reviewed')
  expect(inspector).not.toHaveTextContent('Complete — no action needed')
})

it('presents Integration retry as an optional alternative to Orchestration', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    next_actor: 'agent',
    next_step: 'Retry against the current target',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Awaiting retry against current target', done: null, total: null },
    action: { kind: 'retry-integration', label: 'Retry Integration', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'integration', outcome_completed: 2, items: [integrationCard] })])
  renderPage()

  const table = await screen.findByTestId('work-portfolio-table')
  expect(table).toHaveTextContent('Change: Portfolio redesign')
  expect(table).toHaveTextContent('Waiting for Orchestration')
  expect(table).toHaveTextContent('Optional now: Retry Integration')
  const retryLink = within(table).getByText('Retry Integration').closest('p-link-pure') as HTMLElement & { href: string; color: string; size: string }
  expect(retryLink.href).toBe('/delivery/change-alpha/integration')
  expect(retryLink.color).toBe('contrast-medium')
  expect(retryLink.size).toBe('xs')
  expect(screen.getByLabelText('Delivery portfolio status')).not.toHaveTextContent('need you')
})

it('keeps cached routed detail visible when a background refresh fails', async () => {
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  const detailView = await screen.findByTestId('work-item-detail')
  portfolioFailure = true

  const alert = await screen.findByRole('alert', {}, { timeout: 4_000 })
  expect(alert).toHaveTextContent('Showing the last successful refresh — live updates paused.')
  expect(alert).toHaveTextContent('Temporary polling failure')
  expect(alert).not.toHaveTextContent('Work portfolio is unavailable')
  expect(detailView).toBeInTheDocument()
  expect(screen.getByTestId('work-item-detail')).toBeInTheDocument()
}, 6_000)

it('keeps backend detail collapsed when a selected Work Item is unavailable', async () => {
  detailFailure = true
  renderPage('/delivery/change-alpha/outcome%3AOUT-999')

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('This Work Item is unavailable.')
  expect(alert).toHaveTextContent('Technical evidence')
  const evidence = screen.getByText('Technical evidence').closest('details')
  expect(evidence).not.toHaveAttribute('open')
})

it('explains returned Design progress and labels evidence without raw enum text', async () => {
  currentDetail = detail({
    card: card({
      stage: 'design',
      activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
      progress: { kind: 'design-return', label: 'Returned to Design', done: null, total: null },
    }),
    return_context: {
      target: 'design',
      reason: 'The admitted authority changed.',
      locators: ['request:REQ-001'],
      source_boundary: 'commit:abc123',
      preserved_commit: null,
    },
  })
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Returned to Design')
  expect(inspector).toHaveTextContent('Next: Resume /design change-alpha.')
  expect(inspector).toHaveTextContent('Evidence: request:REQ-001')
  expect(inspector).toHaveTextContent('Source boundary: commit:abc123')
  expect(inspector).not.toHaveTextContent('Next: request:REQ-001')
})

it('does not prescribe Design for a return to Planning', async () => {
  currentDetail = detail({
    card: card({ stage: 'planning' }),
    return_context: {
      target: 'planning',
      reason: 'The implementation plan needs revision.',
      locators: ['finding:F-001'],
      source_boundary: null,
      preserved_commit: null,
    },
  })
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Returned to Planning')
  expect(inspector).toHaveTextContent('The implementation plan needs revision.')
  expect(inspector).not.toHaveTextContent('/design')
})

it('shows active Integration repair state without instructing a duplicate repair', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Integration repair in progress',
    activity: { state: 'repairing', worker_role: 'integration-repairer', started_at: '2026-08-08T10:00:00Z', task_id: null },
    progress: { kind: 'integration', label: 'Repair in progress', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: 'merge-conflict',
      disposition: 'repair-required',
      headline: 'Merge conflict',
      explanation: 'One conflicting file requires a reviewed repair.',
      conflicted_paths: ['serve/delivery/work_items.py'],
      diagnostics: [],
      retry_condition: 'Admit a reviewed repair.',
      superseded: false,
      repair_active: true,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'integration', outcome_completed: 2, items: [integrationCard] })])
  renderPage('/delivery/change-alpha/integration')

  expect(await screen.findByLabelText('Delivery portfolio status')).toHaveTextContent('1work item active')
  const detailView = await screen.findByTestId('work-item-detail')
  expect(detailView).toHaveTextContent('Repair in progress')
  expect(detailView).toHaveTextContent('A reviewed Integration repair is currently in progress.')
  expect(detailView).not.toHaveTextContent('Repair required')
  expect(detailView).not.toHaveTextContent('Admit a reviewed repair.')
})

it('moves a completed selected Change into completed history instead of leaving a dead route', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Not attempted', done: null, total: null },
    action: { kind: 'integrate-change', label: 'Integrate Change', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'integration', outcome_completed: 2, items: [integrationCard] })])
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: null,
      disposition: null,
      headline: 'Ready to integrate',
      explanation: 'Every Outcome is complete.',
      conflicted_paths: [],
      diagnostics: [],
      retry_condition: null,
      superseded: false,
      repair_active: false,
    },
  })
  portfolioAfterIntegration = portfolio([])
  renderPage('/delivery/change-alpha/integration')
  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Integrate now'))

  expect(await screen.findByTestId('completed-history-workspace')).toHaveTextContent('Completed changes')
  expect(await screen.findByText('Portfolio redesign')).toBeInTheDocument()
})

it('keeps current delivery open when only the selected Integration card disappears', async () => {
  const integrationCard = card({
    item_key: 'integration',
    work_item_id: 'change-alpha',
    scope: 'change-integration',
    title: 'Integration',
    stage: null,
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'integration', label: 'Not attempted', done: null, total: null },
    action: { kind: 'integrate-change', label: 'Integrate Change', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'integration', outcome_completed: 2, items: [integrationCard] })])
  currentDetail = detail({
    card: integrationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    integration: {
      code: null,
      disposition: null,
      headline: 'Ready to integrate',
      explanation: 'Every Outcome is complete.',
      conflicted_paths: [],
      diagnostics: [],
      retry_condition: null,
      superseded: false,
      repair_active: false,
    },
  })
  portfolioAfterIntegration = portfolio([group({ items: [card({ title: 'Returned outcome' })] })])
  renderPage('/delivery/change-alpha/integration')
  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Integrate now'))

  expect(await screen.findByTestId('work-portfolio-table')).toHaveTextContent('Returned outcome')
  expect(screen.queryByTestId('completed-history-workspace')).not.toBeInTheDocument()
})
