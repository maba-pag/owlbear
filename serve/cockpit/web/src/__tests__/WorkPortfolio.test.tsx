import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { PorscheDesignSystemProvider, PToast } from '@porsche-design-system/components-react'
import { MemoryRouter, useLocation } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import type {
  AbandonedChangeRecord,
  ChangeGroupView,
  CompletedChangeRecord,
  DeliveryHealthResponse,
  DesignWorkDetailResponse,
  PortfolioChangeLifecycleStatus,
  PortfolioOperatingView,
  WorkItemCardView,
  WorkItemDetailResponse,
  WorkItemPortfolioResponse,
  WorkItemPublicationReconciliationResponse,
  PublicationChecksObservationResponse,
} from '../api/workItems'
import { completedChangeRecordId } from '../api/workItems'
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

function changeStatus(changeId: string, overrides: Partial<PortfolioChangeLifecycleStatus> = {}): PortfolioChangeLifecycleStatus {
  return {
    change_id: changeId,
    admission: 'admitted',
    stage: 'building',
    actionable_runtime: true,
    diagnostic_code: null,
    diagnostic_detail: null,
    ...overrides,
  }
}

function portfolio(
  groups: ChangeGroupView[] = [group()],
  health: DeliveryHealthResponse = { status: 'healthy', diagnostics: [] },
): WorkItemPortfolioResponse {
  const items = groups.flatMap((item) => item.items)
  const reference = (item: WorkItemCardView) => ({
    change_id: item.change_id,
    item_key: item.item_key,
    scope: item.scope === 'change-publication' ? 'publication' as const : 'outcome' as const,
  })
  const claimed = items.filter((item) => item.activity.state === 'working').map(reference)
  const queued = items.filter((item) => item.activity.state === 'ready').map(reference)
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
        none: items.filter((item) => item.needs === 'none').length,
      },
      activity: {
        idle: items.filter((item) => item.activity.state === 'idle').length,
        ready: items.filter((item) => item.activity.state === 'ready').length,
        working: items.filter((item) => item.activity.state === 'working').length,
      },
    },
    operating: {
      unfinished_change_count: groups.length,
      completed_change_count: 0,
      statuses: groups.map((item) => changeStatus(item.change_id)),
      draft_design_change_ids: [],
      design_required_change_ids: [],
      claimed,
      queued_for_orchestration: queued,
      interventions,
      dependency_waits: dependencyWaits,
      guidance,
    },
    health,
  }
}

function withUnadmittedDesign(data: WorkItemPortfolioResponse, changeId = 'design-draft'): WorkItemPortfolioResponse {
  return {
    ...data,
    operating: {
      ...data.operating,
      statuses: [
        ...data.operating.statuses,
        changeStatus(changeId, { admission: 'unadmitted', stage: 'design', actionable_runtime: false }),
      ],
      draft_design_change_ids: [changeId],
    },
  }
}

function detail(overrides: Partial<WorkItemDetailResponse['item']> = {}): WorkItemDetailResponse {
  const publication = overrides.publication && {
    publication_generations: [],
    ...overrides.publication,
  }
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
      ...overrides,
      publication: publication || null,
    },
  }
}

type PublicationView = NonNullable<WorkItemDetailResponse['item']['publication']>

function publicationForChecks(
  phase: 'pull-request-draft' | 'awaiting-merge' | 'ready-for-finalization',
  publishedHead = '1'.repeat(40),
): PublicationView {
  return {
    phase,
    finalization_id: 'f'.repeat(64),
    finalized_head: publishedHead,
    published_head: publishedHead,
    pending_checkpoint_head: null,
    pending_checkpoint_triggers: [],
    invalidated_expected_head: null,
    invalidated_observed_head: null,
    repository: null,
    pull_request_number: null,
    pull_request_head: null,
    accepted_merge_commit: null,
    merged_at: null,
    publication_generations: [{
      repository: 'owlbear/example',
      number: 42,
      node_id: 'PR_example_42',
      head_sha: publishedHead,
    }],
  }
}

function publicationCardForChecks(overrides: Partial<WorkItemCardView> = {}): WorkItemCardView {
  return card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Review publication checks',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Pull request is draft', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
    ...overrides,
  })
}

const completed: CompletedChangeRecord = {
  schema_version: 2,
  record_kind: 'legacy-package',
  change_id: 'change-alpha',
  completion_id: 'b'.repeat(64),
  completion_path: '.owlbear/legacy/completed/change-alpha',
  historical_completion_locator: '.owlbear/completed/change-alpha',
  package_id: 'c'.repeat(64),
  introducing_target_commit: 'd'.repeat(40),
  source_target_commit: 'e'.repeat(40),
  title: 'Portfolio redesign',
  semantic_summary: 'Shipped the grouped Delivery workspace.',
  outcome_titles: ['Ship the grouped Delivery workspace'],
  outcome_promises: ['Give operators a clear view of grouped Delivery work.'],
}

const receiptCompleted: CompletedChangeRecord = {
  schema_version: 2,
  record_kind: 'completion-receipt',
  change_id: 'change-receipt',
  completion_id: '1'.repeat(64),
  title: 'Receipt-backed delivery',
  semantic_summary: 'Accepted through a merged pull request.',
  outcome_titles: ['Accept the merged Delivery change'],
  outcome_promises: ['Record the accepted change with durable evidence.'],
  finalization_receipt_id: '2'.repeat(64),
  finalized_change_head: '3'.repeat(40),
  repository_identity: 'owlbear/example',
  pull_request_identity: { number: 42, node_id: 'PR_example_42' },
  accepted_target_ref: 'main',
  accepted_merge_commit: '4'.repeat(40),
  merged_at: '2026-08-11T12:00:00Z',
  acceptance_observation_id: '5'.repeat(64),
  check_observation_ids: ['6'.repeat(64)],
  review_receipt_ids: ['7'.repeat(64)],
  acceptance_evidence_digest: '8'.repeat(64),
  completed_at: '2026-08-11T13:00:00Z',
}

function abandonedRecord(overrides: Partial<AbandonedChangeRecord> = {}): AbandonedChangeRecord {
  return {
    schema_version: 1,
    record_kind: 'abandoned-change',
    change_id: 'change-alpha',
    abandonment_id: '9'.repeat(64),
    title: 'Abandoned portfolio change',
    semantic_summary: 'Stopped before completion with its terminal evidence retained.',
    outcome_titles: ['Preserve the abandoned Change record'],
    outcome_promises: ['Keep the abandoned Change recoverable for cleanup.'],
    prior_stage: 'building',
    reason: 'User stopped the Change',
    abandoned_at: '2026-08-11T14:00:00Z',
    cleanup_available: true,
    target_sync_conflict: false,
    ...overrides,
  }
}

let currentPortfolio: WorkItemPortfolioResponse
let currentDetail: WorkItemDetailResponse
let currentDesignWork: DesignWorkDetailResponse
let portfolioAfterPublication: WorkItemPortfolioResponse | null
let portfolioFailure: boolean
let detailFailure: boolean
let pendingDetailItemKey: string | null
let pendingDetailRelease: (() => void) | null
let pendingMutationPath: string | null
let pendingMutationRelease: (() => void) | null
let pendingPublicationChecksObservation: boolean
let pendingPublicationChecksRelease: (() => void) | null
let moveBackwardUpdatesDetailStage: WorkItemCardView['stage']
let moveBackwardFailure: boolean
let mutationFailurePath: string | null
let designFailure: boolean
let acceptanceObservationFailure: boolean
let acceptanceReconciliationProviderUnavailable: boolean
let publicationChecksFailure: boolean
let publicationChecksResponse: PublicationChecksObservationResponse
let supersedeFailuresRemaining: number
let completedRecords: CompletedChangeRecord[]
let completedDetailRecord: CompletedChangeRecord | null
let completedDetailMismatch: CompletedChangeRecord | null
let completedHistoryNextCursor: string | null
let completedHistoryPageRecords: CompletedChangeRecord[]
let completedHistoryPageFailuresRemaining: number
let completedDetailFailuresRemaining: number
let completedDetailNotFound: boolean
let completedHistoryFailuresRemaining: number
let completedHistorySearchPending: boolean
let completedHistorySearchFailuresRemaining: number
let completedHistorySearchRecords: CompletedChangeRecord[]
let completedHistorySearchNextCursor: string | null
let completedHistorySearchPageRecords: CompletedChangeRecord[]
let completedHistorySearchRelease: (() => void) | null
let publicationReconciliationResult: WorkItemPublicationReconciliationResponse
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
      if (pendingDetailItemKey !== null && url.endsWith(pendingDetailItemKey)) {
        await new Promise<void>((resolve) => { pendingDetailRelease = resolve })
      }
      return detailFailure ? response({ detail: 'Delivery runtime is absent: change-alpha' }, 409) : response(currentDetail)
    }
    if (method === 'GET' && url === '/api/design-work/design-draft') {
      return designFailure ? response({ detail: 'Design source temporarily unavailable' }, 503) : response(currentDesignWork)
    }
    if (method === 'GET' && url === '/api/work-items/completed') {
      if (completedHistoryFailuresRemaining > 0) {
        completedHistoryFailuresRemaining -= 1
        return response({ detail: 'Completed history unavailable' }, 503)
      }
      return response({
        records: completedRecords,
        total_count: completedRecords.length + completedHistoryPageRecords.length,
        next_cursor: completedHistoryNextCursor,
      })
    }
    if (method === 'GET' && url.startsWith('/api/work-items/completed?cursor=')) {
      if (completedHistoryPageFailuresRemaining > 0) {
        completedHistoryPageFailuresRemaining -= 1
        return response({ detail: 'Next completed history page unavailable' }, 503)
      }
      return response({
        records: completedHistoryPageRecords,
        total_count: completedRecords.length + completedHistoryPageRecords.length,
        next_cursor: null,
      })
    }
    if (method === 'GET' && url.startsWith('/api/work-items/completed/search?')) {
      if (completedHistorySearchPending) {
        await new Promise<void>((resolve) => { completedHistorySearchRelease = resolve })
      }
      if (completedHistorySearchFailuresRemaining > 0) {
        completedHistorySearchFailuresRemaining -= 1
        return response({ detail: 'Completed history search unavailable' }, 503)
      }
      const pageRequest = url.includes('cursor=')
      return response({
        records: pageRequest ? completedHistorySearchPageRecords : completedHistorySearchRecords,
        total_count: completedHistorySearchRecords.length + completedHistorySearchPageRecords.length,
        next_cursor: pageRequest ? null : completedHistorySearchNextCursor,
      })
    }
    if (method === 'GET' && url.startsWith('/api/work-items/completed/')) {
      const selected = completedDetailMismatch ?? (completedDetailRecord && url.includes(completedChangeRecordId(completedDetailRecord))
        ? completedDetailRecord
        : completedRecords.find((record) => url.includes(completedChangeRecordId(record))))
      if (completedDetailNotFound) return response({ detail: 'Completion detail was removed' }, 404)
      if (completedDetailFailuresRemaining > 0) {
        completedDetailFailuresRemaining -= 1
        return response({ detail: 'Completion detail temporarily unavailable' }, 503)
      }
      return selected ? response(selected) : response({ detail: 'Not found' }, 404)
    }

    if (method === 'POST' && url.endsWith('/publication/checks/observe')) {
      if (pendingPublicationChecksObservation) {
        await new Promise<void>((resolve) => { pendingPublicationChecksRelease = resolve })
      }
      if (publicationChecksFailure) {
        return response({
          detail: {
            code: 'ERR_DELIVERY_PROVIDER_UNAVAILABLE',
            detail: 'GitHub is unavailable',
            authority: 'delivery',
            retry_safe: true,
          },
        }, 502)
      }
      return response(publicationChecksResponse)
    }
    if (method === 'POST' && url === '/api/work-items/acceptance/reconcile') {
      return response({
        outcomes: [{
          change_id: 'change-alpha',
          status: acceptanceReconciliationProviderUnavailable ? 'provider-unavailable' : 'waiting',
          code: acceptanceReconciliationProviderUnavailable ? 'ERR_DELIVERY_PROVIDER_UNAVAILABLE' : null,
          detail: acceptanceReconciliationProviderUnavailable ? 'GitHub acceptance provider unavailable' : null,
          completion_id: null,
        }],
      })
    }

    if (method === 'POST' && mutationFailurePath && url.endsWith(mutationFailurePath)) {
      return response({
        detail: {
          code: 'ERR_DELIVERY_CONTROL_CONFLICT',
          detail: 'The Delivery operation was rejected while the confirmation was open.',
          authority: 'delivery',
          retry_safe: true,
        },
      }, 409)
    }

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
      if (moveBackwardFailure) {
        return response({
          detail: {
            code: 'ERR_DELIVERY_ADMINISTRATIVE_MOVE',
            detail: 'The Delivery frontier changed before the move was applied.',
            authority: 'delivery',
            retry_safe: true,
          },
        }, 409)
      }
      if (moveBackwardUpdatesDetailStage) {
        currentDetail = detail({
          ...currentDetail.item,
          card: { ...currentDetail.item.card, stage: moveBackwardUpdatesDetailStage },
        })
      }
      return response({ invalidated_outcome_ids: ['OUT-002'], move: {} })
    }
    if (method === 'POST' && (
      url.endsWith('/target/sync')
      || url.endsWith('/target/conflict/abort')
      || url.endsWith('/target/conflict/resolve')
      || url.endsWith('/publication/reconcile')
      || url.endsWith('/publication/ready')
      || url.endsWith('/publication/supersede')
      || url.endsWith('/acceptance/observe')
      || url.endsWith('/attention/resolve')
      || url.endsWith('/defer')
      || url.endsWith('/resume')
      || url.endsWith('/abandon')
      || url.endsWith('/worktree/cleanup/abandoned')
      || url.endsWith('/worktree/cleanup/abandoned/target-sync-discard')
      || url.endsWith('/worktree/cleanup/completed')
      || url.endsWith('/worktree/recover')
    )) {
      if (pendingMutationPath && url.endsWith(pendingMutationPath)) {
        await new Promise<void>((resolve) => { pendingMutationRelease = resolve })
      }
      if (url.endsWith('/publication/reconcile')) return response(publicationReconciliationResult)
      if (url.endsWith('/acceptance/observe') && acceptanceObservationFailure) {
        return response({
          detail: {
            code: 'ERR_DELIVERY_ACCEPTANCE_WAITING',
            detail: 'The pull request is still open and unmerged.',
            authority: 'delivery',
            retry_safe: true,
          },
        }, 409)
      }
      if (portfolioAfterPublication) currentPortfolio = portfolioAfterPublication
      if (url.endsWith('/publication/supersede')) {
        if (supersedeFailuresRemaining > 0) {
          supersedeFailuresRemaining -= 1
          return response({ detail: { code: 'ERR_PROVIDER_UNAVAILABLE', detail: 'Provider unavailable', authority: 'delivery', retry_safe: true } }, 409)
        }
        return response({
          schema_version: 1,
          receipt_id: 'd'.repeat(64),
          operation_id: (body as { operation_id: string }).operation_id,
          change_id: 'change-alpha',
          predecessor_publication_id: 'e'.repeat(64),
          successor_publication_id: 'f'.repeat(64),
        })
      }
      if (url.endsWith('/target/sync')) {
        return response({
          schema_version: 1,
          receipt_id: 'a'.repeat(64),
          operation_id: 'cockpit-target-sync-test',
          change_id: 'change-alpha',
          target_branch: 'main',
          expected_target: '1'.repeat(40),
          target_head: '1'.repeat(40),
          change_head_before: '2'.repeat(40),
          merged_head: '3'.repeat(40),
          merge_commit: true,
          review_required: false,
        })
      }
      if (url.endsWith('/target/conflict/abort')) {
        return response({
          schema_version: 1,
          receipt_id: 'b'.repeat(64),
          operation_id: 'cockpit-target-sync-conflict',
          change_id: 'change-alpha',
          target_head: '4'.repeat(40),
          restored_head: '5'.repeat(40),
        })
      }
      if (url.endsWith('/target/conflict/resolve')) {
        return response({
          schema_version: 1,
          receipt_id: 'c'.repeat(64),
          operation_id: 'cockpit-target-sync-conflict',
          change_id: 'change-alpha',
          target_branch: 'main',
          expected_target: '4'.repeat(40),
          target_head: '4'.repeat(40),
          change_head_before: '5'.repeat(40),
          merged_head: '6'.repeat(40),
          merge_commit: true,
          review_required: true,
        })
      }
      if (url.endsWith('/worktree/cleanup/abandoned/target-sync-discard')) {
        return response({
          cleanup_id: 'd'.repeat(64),
          change_id: 'change-alpha',
          branch: 'owlbear/change/change-alpha',
          worktree_path: '.owlbear/delivery/worktrees/change-alpha',
          branch_head: '5'.repeat(40),
        })
      }
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

function namedPdsHost(container: HTMLElement, tagName: 'p-input-text' | 'p-select', name: string): Element | null {
  return Array.from(container.querySelectorAll<HTMLElement & { name?: string }>(tagName))
    .find((element) => element.name === name || element.getAttribute('name') === name) ?? null
}

function renderPage(path = '/delivery') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[path]}><LocationProbe /><WorkPortfolioPage /></MemoryRouter>
      <PToast />
    </PorscheDesignSystemProvider>,
  )
}

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="test-location">{location.pathname}</output>
}

beforeEach(() => {
  currentPortfolio = portfolio()
  currentDetail = detail()
  currentDesignWork = {
    change_id: 'design-draft',
    package_id: 'd'.repeat(64),
    intent_markdown: '# Design Draft\n\nShape a coherent operator workflow.',
    design_markdown: '# Architecture\n\nKeep authority explicit.',
  }
  portfolioAfterPublication = null
  portfolioFailure = false
  detailFailure = false
  pendingDetailItemKey = null
  pendingDetailRelease = null
  pendingMutationPath = null
  pendingMutationRelease = null
  pendingPublicationChecksObservation = false
  pendingPublicationChecksRelease = null
  moveBackwardUpdatesDetailStage = null
  moveBackwardFailure = false
  mutationFailurePath = null
  designFailure = false
  acceptanceObservationFailure = false
  acceptanceReconciliationProviderUnavailable = false
  publicationChecksFailure = false
  publicationReconciliationResult = {
    change_id: 'change-alpha',
    attempted_head: null,
    reconciled: true,
    error_code: null,
    error_detail: null,
    pending_checkpoint_attempt_count: 0,
    pending_checkpoint_last_attempted_at: null,
    pending_checkpoint_error_code: null,
    pending_checkpoint_error_detail: null,
  }
  publicationChecksResponse = {
    schema_version: 1,
    observation_id: 'a'.repeat(64),
    change_id: 'change-alpha',
    repository: 'owlbear/example',
    pull_request_number: 42,
    exact_commit: '1'.repeat(40),
    observed_at: '2026-08-11T16:00:00Z',
    rollup_state: 'failure',
    checks: [
      {
        check_id: 'required-failure',
        kind: 'check_run',
        name: 'Unit tests',
        status: 'completed',
        conclusion: 'failure',
        required: true,
        blocking_state: 'blocking',
      },
      {
        check_id: 'required-pending',
        kind: 'check_run',
        name: 'Integration tests',
        status: 'queued',
        conclusion: null,
        required: true,
        blocking_state: 'required-pending',
      },
      {
        check_id: 'optional-failure',
        kind: 'check_run',
        name: 'Optional lint',
        status: 'completed',
        conclusion: 'failure',
        required: false,
        blocking_state: 'not-blocking',
      },
    ],
    required_failure_count: 1,
    truncated_count: 0,
  }
  supersedeFailuresRemaining = 0
  completedRecords = [completed]
  completedDetailRecord = null
  completedDetailMismatch = null
  completedHistoryNextCursor = null
  completedHistoryPageRecords = []
  completedHistoryPageFailuresRemaining = 0
  completedDetailFailuresRemaining = 0
  completedDetailNotFound = false
  completedHistoryFailuresRemaining = 0
  completedHistorySearchPending = false
  completedHistorySearchFailuresRemaining = 0
  completedHistorySearchRecords = []
  completedHistorySearchNextCursor = null
  completedHistorySearchPageRecords = []
  completedHistorySearchRelease = null
  requests = []
  installFetch()
})

it('summarizes all current Change phases and nonzero operating states', () => {
  const outcome = { change_id: 'delivery-change', item_key: 'outcome:OUT-001', scope: 'outcome' as const }
  const publication = { change_id: 'publication-change', item_key: 'publication', scope: 'publication' as const }
  const operating: PortfolioOperatingView = {
    unfinished_change_count: 3,
    completed_change_count: 8,
    statuses: [
      changeStatus('draft-change', { admission: 'unadmitted', stage: 'design', actionable_runtime: false }),
      changeStatus('delivery-change'),
      changeStatus('design-reentry', { stage: 'design' }),
      changeStatus('unavailable-change', { actionable_runtime: false, diagnostic_code: 'runtime_unavailable', diagnostic_detail: 'Runtime composition is unavailable.' }),
    ],
    draft_design_change_ids: ['legacy-draft', 'legacy-draft-2'],
    design_required_change_ids: ['legacy-reentry', 'legacy-reentry-2', 'legacy-reentry-3'],
    claimed: [outcome],
    queued_for_orchestration: [publication],
    interventions: [outcome],
    dependency_waits: [publication],
    guidance: [],
  }
  const totals: WorkItemPortfolioResponse['totals'] = {
    total: 3,
    complete: 0,
    needs: { you: 1, dependency: 1, none: 1 },
    activity: { idle: 1, ready: 1, working: 1 },
  }
  const onNeedsFilter = vi.fn()

  render(<PortfolioHeaderSummary operating={operating} totals={totals} needsFilter="you" onNeedsFilter={onNeedsFilter} />)

  expect(screen.getByRole('group', { name: 'Portfolio inventory' })).toHaveTextContent('4Changes2Design·2Delivery')
  expect(screen.getByRole('group', { name: 'Attention' })).toHaveTextContent('1Needs you1Blocked')
  expect(screen.getByRole('group', { name: 'Activity' })).toHaveTextContent('1Running1Ready')

  const needsYou = screen.getByRole('button', { name: 'Filter to 1 work item: Needs you' })
  expect(needsYou).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(needsYou)
  expect(onNeedsFilter).toHaveBeenCalledWith('')
})

it('classifies Design and Delivery entries from explicit lifecycle statuses', async () => {
  const planningGroup = group({
    change_id: 'planning-change',
    title: 'Admitted planning',
    items: [card({
      change_id: 'planning-change',
      title: 'Planning without a task plan',
      progress: { kind: 'plan', label: 'Task plan not published', done: null, total: null },
    })],
  })
  const reentryGroup = group({
    change_id: 'design-reentry',
    title: 'Admitted Design re-entry',
    items: [card({
      change_id: 'design-reentry',
      title: 'Returned to Design',
      stage: 'design',
      progress: { kind: 'design-return', label: 'Returned to Design', done: null, total: null },
    })],
  })
  const basePortfolio = portfolio([planningGroup, reentryGroup])
  currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [
        changeStatus('design-draft', { admission: 'unadmitted', stage: 'design', actionable_runtime: false }),
        changeStatus('planning-change'),
        changeStatus('design-reentry', { stage: 'design' }),
        changeStatus('unavailable-change', { actionable_runtime: false, diagnostic_code: 'runtime_unavailable', diagnostic_detail: 'Persisted admission is valid, but runtime composition is unavailable.' }),
      ],
      draft_design_change_ids: ['planning-change', 'design-reentry', 'unavailable-change'],
      design_required_change_ids: [],
    },
  }

  renderPage()

  const designWork = await screen.findByTestId('design-work-section')
  expect(designWork).toHaveTextContent('Design Draft')
  expect(designWork).not.toHaveTextContent('Admitted planning')
  expect(designWork).not.toHaveTextContent('Admitted Design re-entry')
  expect(designWork).not.toHaveTextContent('unavailable-change')

  const table = screen.getByTestId('work-portfolio-table')
  expect(table).toHaveTextContent('Admitted planning')
  expect(table).toHaveTextContent('Task plan not published')
  expect(table).toHaveTextContent('Admitted Design re-entry')

  const unavailable = screen.getByTestId('delivery-issues-section')
  expect(unavailable).toHaveTextContent('unavailable-change')
  expect(unavailable).toHaveTextContent('Runtime unavailable')
  expect(unavailable).toHaveTextContent('Persisted admission is valid, but runtime composition is unavailable.')
  expect(unavailable).not.toHaveTextContent('Not admitted to Delivery')

  const summary = await screen.findByLabelText('Delivery portfolio status')
  expect(summary).toHaveTextContent('4Changes')
  expect(summary).toHaveTextContent('2Design')
  expect(summary).toHaveTextContent('2Delivery')
})

it('shows bounded Delivery health diagnostics for quarantined state', async () => {
  const basePortfolio = portfolio([], {
    status: 'attention',
    diagnostics: [{
      source: 'local-runtime',
      code: 'contract-identity-invalid',
      detail: 'Persisted Change contract identity is invalid',
      change_id: 'quarantined-change',
      path: '.owlbear/delivery/runtime/changes/quarantined-change',
      retry_safe: false,
    }],
  })
  currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      statuses: [changeStatus('quarantined-change', {
        actionable_runtime: false,
        diagnostic_code: 'runtime_unavailable',
        diagnostic_detail: 'Persisted Change contract identity is invalid',
      })],
    },
  }

  renderPage()

  const health = await screen.findByTestId('delivery-issues-section')
  expect(health).toHaveTextContent('Delivery issues')
  expect(health).toHaveTextContent('Quarantined state is hidden from dispatch.')
  expect(health).toHaveTextContent('quarantined-change')
  expect(health).toHaveTextContent('local-runtime / contract-identity-invalid')
  expect(health).toHaveTextContent('Persisted Change contract identity is invalid')
  expect(screen.queryByTestId('work-portfolio-table')).not.toBeInTheDocument()
})

it('presents Change-grouped Outcomes by work, progress, and status', async () => {
  renderPage()

  const table = await screen.findByTestId('work-portfolio-table')
  expect(table).toHaveTextContent('Portfolio redesign')
  expect(table).toHaveTextContent('Work')
  expect(table).toHaveTextContent('State')
  expect(table).toHaveTextContent('Working')
  expect(table).toHaveTextContent('Builder')
  expect(table).toHaveTextContent('Decision required')
  expect(table).toHaveTextContent('Answer request')
  expect(table).toHaveTextContent('Outcome: OUT-001')
  expect(within(table).getAllByText('OUT-001', { selector: 'code' }).length).toBeGreaterThan(0)
  expect(within(table).getAllByText('Portfolio redesign')).toHaveLength(1)
  expect(await screen.findByLabelText('Delivery portfolio status')).toHaveTextContent('1Running')
  const guidance = screen.getByLabelText('Session suggestions')
  expect(guidance).toHaveTextContent('Review 1 item that needs you')
  expect(guidance).toHaveTextContent('/orchestrate is already working')
  expect(within(guidance).getByText('/orchestrate', { selector: 'code' })).toBeInTheDocument()
  expect(within(guidance).getByRole('button', { name: 'Copy command /orchestrate' })).toBeInTheDocument()
  expect(guidance).not.toHaveTextContent('Start /orchestrate')
  expect(table.compareDocumentPosition(guidance) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(screen.queryByText('Reviewed', { exact: true })).not.toBeInTheDocument()
})

it('copies empty-portfolio session commands with the shared compact control', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  currentPortfolio = portfolio([])
  renderPage()

  const guidance = await screen.findByLabelText('Session suggestions')
  const ideateCommand = within(guidance).getByRole('button', { name: 'Copy command /ideate' })
  fireEvent.click(ideateCommand)

  await waitFor(() => expect(writeText).toHaveBeenCalledWith('/ideate'))
})

it('shows unadmitted Design work on the board and opens its verified sources', async () => {
  const basePortfolio = withUnadmittedDesign(portfolio())
  currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
      guidance: [{ kind: 'resume-design', change_ids: ['design-draft'], work_count: 1 }],
    },
  }
  renderPage('/delivery/design-draft/design')

  const designWork = await screen.findByTestId('design-work-section')
  expect(designWork).toHaveTextContent('Design Draft')
  expect(designWork).toHaveTextContent('Not admitted to Delivery')
  expect(designWork).toHaveTextContent('/design design-draft')
  expect(within(designWork).getByRole('button', { name: 'Copy command /design design-draft' })).toBeInTheDocument()
  expect(within(designWork).getAllByRole('term').map((term) => term.textContent)).toEqual(['Work', 'State'])
  expect(within(designWork).getAllByRole('definition')).toHaveLength(2)
  const status = screen.getByLabelText('Delivery portfolio status')
  expect(status).toHaveTextContent('2Changes')
  expect(status).toHaveTextContent('1Design')
  expect(status).toHaveTextContent('1Delivery')

  const detailView = await screen.findByTestId('design-work-detail')
  expect(detailView).toHaveTextContent('Shape a coherent operator workflow.')
  const flyout = document.querySelector('p-flyout') as HTMLElement & { aria?: { 'aria-label'?: string } }
  expect(flyout.aria?.['aria-label']).toBe('Design detail')
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

it('uses Design-specific unavailable detail copy and retry action', async () => {
  const basePortfolio = withUnadmittedDesign(portfolio())
  currentPortfolio = {
    ...basePortfolio,
    operating: {
      ...basePortfolio.operating,
    },
  }
  designFailure = true
  renderPage('/delivery/design-draft/design')

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('This Design work is unavailable.')
  expect(alert).toHaveTextContent('Retry Design')
  expect(alert).not.toHaveTextContent('This Work Item is unavailable.')

  designFailure = false
  fireEvent.click(within(alert).getByText('Retry Design', { exact: true }))
  expect(await screen.findByTestId('design-work-detail')).toBeInTheDocument()
})

it('refreshes open Design detail after an authored package revision', async () => {
  vi.useFakeTimers()
  try {
    currentPortfolio = withUnadmittedDesign(portfolio())
    renderPage('/delivery/design-draft/design')

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    const detailView = screen.getByTestId('design-work-detail')
    expect(detailView).toHaveTextContent('Keep authority explicit.')

    currentDesignWork = {
      ...currentDesignWork,
      package_id: 'e'.repeat(64),
      design_markdown: '# Architecture\n\nUse the revised authority.',
    }
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000)
    })

    expect(detailView).toHaveTextContent('Use the revised authority.')
  } finally {
    vi.useRealTimers()
  }
})

it('shows stale Design detail state and retries the refresh in place', async () => {
  renderPage('/delivery/design-draft/design')
  const detailView = await screen.findByTestId('design-work-detail')
  designFailure = true

  const alert = await screen.findByRole('alert', {}, { timeout: 4_000 })
  expect(alert).toHaveTextContent('Showing the last successful Design detail; live updates paused.')
  expect(alert).toHaveTextContent('Design source temporarily unavailable')
  expect(detailView).toBeInTheDocument()

  designFailure = false
  fireEvent.click(within(alert).getByText('Retry Design', { exact: true }))
  await waitFor(() => expect(screen.queryByText('Showing the last successful Design detail; live updates paused.')).not.toBeInTheDocument())
  expect(screen.getByTestId('design-work-detail')).toBeInTheDocument()
}, 6_000)

it('closes removed Design detail after a portfolio refresh', async () => {
  const initialPortfolio = portfolio()
  currentPortfolio = withUnadmittedDesign(initialPortfolio)
  renderPage('/delivery/design-draft/design')
  await screen.findByTestId('design-work-detail')

  currentPortfolio = portfolio()
  fireEvent.click(screen.getByRole('button', { name: 'Change history', exact: true }))
  await screen.findByTestId('completed-history-workspace')
  fireEvent.click(screen.getByRole('button', { name: 'Current delivery', exact: true }))

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
    expect(openFlyout).toBeUndefined()
  })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Current delivery', exact: true })).toHaveFocus())
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
    operating: withUnadmittedDesign(basePortfolio).operating,
  }
  const { container } = renderPage()
  await screen.findByTestId('work-portfolio-table')

  const needsYou = screen.getByRole('button', { name: 'Filter to 1 work item: Needs you' })
  fireEvent.click(needsYou)
  await waitFor(() => expect(needsYou).toHaveAttribute('aria-pressed', 'true'))
  expect(screen.getByTestId('work-shown-count')).toHaveTextContent('2 of 4')
  fireEvent.click(needsYou)
  await waitFor(() => expect(needsYou).toHaveAttribute('aria-pressed', 'false'))
  expect(screen.queryByTestId('work-shown-count')).not.toBeInTheDocument()

  const filterToggle = screen.getByTestId('work-filters-toggle')
  fireEvent.click(filterToggle)
  expect(filterToggle).toHaveAttribute('aria-expanded', 'true')
  expect(filterToggle).toHaveAttribute('aria-controls', 'work-filters-panel')
  expect(screen.getByTestId('work-filters-panel')).toHaveAttribute('id', 'work-filters-panel')
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
  expect(await screen.findByText('No matching delivery work')).toBeInTheDocument()
  expect(screen.queryByText('No current Delivery work.')).not.toBeInTheDocument()
})

it('keeps routed detail open when filters hide its portfolio row', async () => {
  const secondGroup = group({
    change_id: 'change-beta',
    title: 'Runtime hardening',
    snapshot_version: 'b'.repeat(64),
    items: [card({
      change_id: 'change-beta',
      title: 'Blocked runtime task',
      needs: 'dependency',
      needs_headline: 'Waiting on OUT-009',
      next_actor: 'dependency',
      next_step: 'Waiting on OUT-009',
    })],
  })
  currentPortfolio = portfolio([group(), secondGroup])
  const { container } = renderPage()
  const table = await screen.findByTestId('work-portfolio-table')
  fireEvent.click(within(table).getAllByRole('link', { name: /Delivery foundation/ })[0])

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(screen.getByTestId('work-filters-toggle'))
  const selects = container.querySelectorAll('p-select')
  selectValue(selects[1], 'dependency')

  await waitFor(() => expect(table).not.toHaveTextContent('Delivery foundation'))
  expect(inspector).toBeInTheDocument()
  expect(screen.getByTestId('work-filters-panel')).toBeInTheDocument()

  fireEvent.keyDown(inspector, { key: 'Escape' })
  await waitFor(() => expect(screen.getByTestId('work-filters-toggle')).toHaveFocus())
})

it('restores focus to the clicked work item after closing its detail', async () => {
  renderPage()
  const table = await screen.findByTestId('work-portfolio-table')
  const itemLink = within(table).getAllByRole('link', { name: /Delivery foundation/ })[0]

  fireEvent.click(itemLink)
  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.keyDown(inspector, { key: 'Escape' })

  await waitFor(() => expect(itemLink).toHaveFocus())
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
  const option = await waitFor(() => {
    const element = namedPdsHost(container, 'p-select', 'request-REQ-001-option')
    expect(element).not.toBeNull()
    return element!
  })
  selectValue(option, 'keep')
  await waitFor(() => expect(submit.disabled).toBe(false))
  fireEvent.click(submit)

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/requests/REQ-001/answer',
    method: 'POST',
    body: { selected_option_id: 'keep', response_text: null },
  }))
  expect(await screen.findByText('Keep it')).toBeInTheDocument()
})

it('clears action feedback when switching to another work item', async () => {
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
  const option = await waitFor(() => {
    const element = namedPdsHost(container, 'p-select', 'request-REQ-001-option')
    expect(element).not.toBeNull()
    return element!
  })
  selectValue(option, 'keep')
  await waitFor(() => expect(submit.disabled).toBe(false))
  fireEvent.click(submit)
  expect(await screen.findByText('Request answered.')).toBeInTheDocument()

  fireEvent.click(screen.getAllByRole('link', { name: 'User controls' })[0])
  await waitFor(() => expect(screen.queryByText('Request answered.')).not.toBeInTheDocument())
})

it('shows a loading state instead of stale detail while switching work items', async () => {
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')
  pendingDetailItemKey = 'outcome%3AOUT-002'

  try {
    fireEvent.click(screen.getAllByRole('link', { name: 'User controls' })[0])
    await screen.findByText('Loading Work Item details...')
  } finally {
    pendingDetailRelease?.()
    pendingDetailItemKey = null
    pendingDetailRelease = null
  }
})

it('clears earlier action feedback before previewing a backward move', async () => {
  currentDetail = detail({
    card: card({ stage: 'planning' }),
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
  const option = await waitFor(() => {
    const element = namedPdsHost(container, 'p-select', 'request-REQ-001-option')
    expect(element).not.toBeNull()
    return element!
  })
  selectValue(option, 'keep')
  await waitFor(() => expect(submit.disabled).toBe(false))
  fireEvent.click(submit)
  expect(await screen.findByText('Request answered.')).toBeInTheDocument()

  fireEvent.click(screen.getByText('Administrative actions'))
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-select', 'backward-stage'),
      namedPdsHost(container, 'p-input-text', 'backward-reason'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  selectValue(stage, 'design')
  inputValue(reason, 'Authority changed')
  fireEvent.click(screen.getByText('Review backward move'))

  await screen.findByText('The following Outcomes will be reset:')
  expect(screen.queryByText('Request answered.')).not.toBeInTheDocument()
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

  const [note, locator] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-input-text', 'block-note'),
      namedPdsHost(container, 'p-input-text', 'block-locator'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  inputValue(note, 'Verified externally')
  inputValue(locator, 'request:REQ-001')
  await waitFor(() => expect(clear.disabled).toBe(false))
  fireEvent.click(clear)

  await waitFor(() => expect(requests.some(({ url, method }) => method === 'POST' && url.includes('/blocks/BLOCK-001/clear'))).toBe(true))
  expect(await screen.findByText('Block cleared.')).toBeInTheDocument()
})

it('keeps block evidence available when clearing the block fails', async () => {
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
  mutationFailurePath = '/clear'
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  const clear = await screen.findByText('Clear block') as HTMLElement & { disabled: boolean }
  const [note, locator] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-input-text', 'block-note'),
      namedPdsHost(container, 'p-input-text', 'block-locator'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  inputValue(note, 'Verified externally')
  inputValue(locator, 'request:REQ-001')
  await waitFor(() => expect(clear.disabled).toBe(false))
  fireEvent.click(clear)

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('The Delivery operation was rejected while the confirmation was open.')
  expect((note as HTMLElement & { value: string }).value).toBe('Verified externally')
  expect((locator as HTMLElement & { value: string }).value).toBe('request:REQ-001')
  await waitFor(() => expect(clear.disabled).toBe(false))
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
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-select', 'backward-stage'),
      namedPdsHost(container, 'p-input-text', 'backward-reason'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  selectValue(stage, 'planning')
  inputValue(reason, 'Authority changed')
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

it('keeps claim recovery confirmation open when recovery fails', async () => {
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
  mutationFailurePath = '/claims/recover'
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByText('Recover confirmed-lost claim')
  fireEvent.click(screen.getByText('Recover confirmed-lost claim'))
  fireEvent.click(screen.getByText('Confirm lost and recover'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/outcomes/OUT-001/claims/recover',
    method: 'POST',
    body: { attempt_id: 'attempt-one', claim_id: 'claim-one', confirmed_lost: true },
  }))
  const dialog = screen.getByRole('alertdialog')
  expect(within(dialog).getByRole('alert')).toHaveTextContent('The Delivery operation was rejected while the confirmation was open.')
  expect(within(dialog).getByText('Confirm lost claim')).toBeInTheDocument()
})

it('clears a backward target that becomes invalid after a successful move', async () => {
  currentDetail = detail({ card: card({ stage: 'implementation' }) })
  moveBackwardUpdatesDetailStage = 'planning'
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')

  fireEvent.click(screen.getByText('Administrative actions'))
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-select', 'backward-stage'),
      namedPdsHost(container, 'p-input-text', 'backward-reason'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  selectValue(stage, 'planning')
  inputValue(reason, 'Authority changed')
  fireEvent.click(screen.getByText('Review backward move'))
  await screen.findByText('The following Outcomes will be reset:')
  fireEvent.click(screen.getByText('Confirm backward move'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/outcomes/OUT-001/move-backward',
    method: 'POST',
    body: { target: 'planning', reason: 'Authority changed', snapshot_version: 'a'.repeat(64) },
  }))
  await waitFor(() => expect((stage as HTMLElement & { value: string }).value).toBe(''))
  expect((screen.getByText('Review backward move') as HTMLElement & { disabled: boolean }).disabled).toBe(true)
})

it('expires a backward preview when polling detects a newer snapshot', async () => {
  vi.useFakeTimers()
  try {
    currentDetail = detail({ card: card({ stage: 'implementation' }) })
    renderPage('/delivery/change-alpha/outcome%3AOUT-001')
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    fireEvent.click(screen.getByText('Administrative actions'))
    const stage = namedPdsHost(document.body, 'p-select', 'backward-stage')
    const reason = namedPdsHost(document.body, 'p-input-text', 'backward-reason')
    expect(stage).not.toBeNull()
    expect(reason).not.toBeNull()
    selectValue(stage!, 'planning')
    inputValue(reason!, 'Authority changed')
    fireEvent.click(screen.getByText('Review backward move'))
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(screen.getByText('The following Outcomes will be reset:')).toBeInTheDocument()

    currentDetail = detail({
      ...currentDetail.item,
      snapshot_version: 'b'.repeat(64),
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000)
    })

    expect(screen.queryByText('The following Outcomes will be reset:')).not.toBeInTheDocument()
    expect(screen.getByText('The backward-move preview expired because Delivery changed. Review the move again.')).toBeInTheDocument()
    expect(requests.some(({ url, method }) => method === 'POST' && url.endsWith('/move-backward'))).toBe(false)
  } finally {
    vi.useRealTimers()
  }
})

it('keeps backward confirmation open when the move fails', async () => {
  currentDetail = detail({ card: card({ stage: 'implementation' }) })
  moveBackwardFailure = true
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')

  fireEvent.click(screen.getByText('Administrative actions'))
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-select', 'backward-stage'),
      namedPdsHost(container, 'p-input-text', 'backward-reason'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  selectValue(stage, 'planning')
  inputValue(reason, 'Authority changed')
  fireEvent.click(screen.getByText('Review backward move'))
  await screen.findByText('The following Outcomes will be reset:')
  fireEvent.click(screen.getByText('Confirm backward move'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/outcomes/OUT-001/move-backward',
    method: 'POST',
    body: { target: 'planning', reason: 'Authority changed', snapshot_version: 'a'.repeat(64) },
  }))
  expect(await screen.findByRole('alert')).toHaveTextContent('The Delivery frontier changed before the move was applied.')
  expect(screen.getByText('The following Outcomes will be reset:')).toBeInTheDocument()
  expect(screen.getByRole('alertdialog')).toBeInTheDocument()
})

it('closes confirmation modals with Escape without performing the action', async () => {
  const { container } = renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')

  fireEvent.click(screen.getByText('Administrative actions'))
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, 'p-select', 'backward-stage'),
      namedPdsHost(container, 'p-input-text', 'backward-reason'),
    ]
    expect(elements.every(Boolean)).toBe(true)
    return elements as [Element, Element]
  })
  selectValue(stage, 'planning')
  inputValue(reason, 'Authority changed')
  fireEvent.click(screen.getByText('Review backward move'))
  await screen.findByText('The following Outcomes will be reset:')

  fireEvent.keyDown(screen.getByText('Confirm backward move'), { key: 'Escape' })

  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
  expect(requests.some(({ url, method }) => method === 'POST' && url.endsWith('/move-backward'))).toBe(false)
})

it('closes the primary work-item flyout with Escape', async () => {
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  const detailView = await screen.findByTestId('work-item-detail')

  fireEvent.keyDown(detailView, { key: 'Escape' })

  await waitFor(() => expect(screen.queryByTestId('work-item-detail')).not.toBeInTheDocument())
})

it('reconciles a pending publication checkpoint from the Change publication view', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Reconcile the final checkpoint',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    publication_phase: 'checkpoint-pending',
    progress: { kind: 'publication', label: 'Checkpoint pending', done: null, total: null },
    action: { kind: 'reconcile-checkpoint', label: 'Publish checkpoint', command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'checkpoint-pending',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: null,
      pending_checkpoint_head: '1'.repeat(40),
      pending_checkpoint_triggers: ['finalization'],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  const publicationRow = screen.getByLabelText('Change publication for Portfolio redesign')
  expect(within(publicationRow).getAllByRole('term').map((term) => term.textContent)).toEqual(['Work', 'State'])
  expect(within(publicationRow).getAllByRole('definition')).toHaveLength(2)
  expect(inspector).toHaveTextContent('Checkpoint pending')
  expect(inspector).toHaveTextContent('Finalized head')
  expect(inspector).toHaveTextContent('1'.repeat(40))
  expect(inspector).toHaveTextContent('Checkpoint triggers: finalization')
  expect(screen.getByLabelText('Delivery portfolio status')).toHaveTextContent('1Ready')
  expect(publicationRow).toHaveTextContent('Checkpoint pending')
  expect(within(publicationRow).getByText('Checkpoint pending', { selector: '[data-status-tone]' })).toHaveAttribute('data-status-tone', 'active')
  fireEvent.click(within(inspector).getByText('Publish checkpoint'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/publication/reconcile',
    method: 'POST',
    body: null,
  }))
  expect(await screen.findByText('Publication checkpoint reconciled.')).toBeInTheDocument()
})

it('shows persisted checkpoint retry diagnostics and structured reconciliation errors', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    next_actor: 'agent',
    next_step: 'Reconcile the final checkpoint',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Checkpoint pending', done: null, total: null },
    action: { kind: 'reconcile-checkpoint', label: 'Publish checkpoint', command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'checkpoint-pending',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: ['verified-outcome'],
      pending_checkpoint_attempt_count: 2,
      pending_checkpoint_last_attempted_at: '2026-08-11T17:00:00+00:00',
      pending_checkpoint_error_code: 'ERR_DELIVERY_CHECKPOINT_HEAD_MISSING',
      pending_checkpoint_error_detail: 'Checkpoint publication is waiting for a reviewed Change head.',
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 1, items: [publicationCard] })])
  publicationReconciliationResult = {
    change_id: 'change-alpha',
    attempted_head: null,
    reconciled: false,
    error_code: 'ERR_DELIVERY_CHECKPOINT_HEAD_MISSING',
    error_detail: 'Checkpoint publication is waiting for a reviewed Change head.',
    pending_checkpoint_attempt_count: 2,
    pending_checkpoint_last_attempted_at: '2026-08-11T17:00:00+00:00',
    pending_checkpoint_error_code: 'ERR_DELIVERY_CHECKPOINT_HEAD_MISSING',
    pending_checkpoint_error_detail: 'Checkpoint publication is waiting for a reviewed Change head.',
  }
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  const diagnostics = within(inspector).getByTestId('checkpoint-diagnostics')
  expect(diagnostics).toHaveTextContent('Checkpoint attempts: 2')
  expect(diagnostics).toHaveTextContent('Last attempt: 2026-08-11T17:00:00+00:00')
  expect(diagnostics).toHaveTextContent('ERR_DELIVERY_CHECKPOINT_HEAD_MISSING')
  fireEvent.click(within(inspector).getByText('Publish checkpoint'))

  await waitFor(() => expect(screen.getByText(
    'ERR_DELIVERY_CHECKPOINT_HEAD_MISSING: Checkpoint publication is waiting for a reviewed Change head.',
  )).toBeInTheDocument())
})

it('does not claim publication success when reconciliation remains incomplete', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Reconcile the final checkpoint',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Checkpoint pending', done: null, total: null },
    action: { kind: 'reconcile-checkpoint', label: 'Publish checkpoint', command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'checkpoint-pending',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: null,
      pending_checkpoint_head: '1'.repeat(40),
      pending_checkpoint_triggers: ['finalization'],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  publicationReconciliationResult = {
    change_id: 'change-alpha',
    attempted_head: null,
    reconciled: false,
    error_code: null,
    error_detail: null,
    pending_checkpoint_attempt_count: 0,
    pending_checkpoint_last_attempted_at: null,
    pending_checkpoint_error_code: null,
    pending_checkpoint_error_detail: null,
  }
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Publish checkpoint'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/publication/reconcile',
    method: 'POST',
    body: null,
  }))
  await waitFor(() => expect(screen.queryByText('Publication checkpoint reconciled.')).not.toBeInTheDocument())
})

it('syncs the Change with the target and shows the latest sync receipt', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Finalize the reviewed Change',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Ready for finalization', done: null, total: null },
    action: { kind: 'finalize', label: 'Finalize Change', command: '/finalize-change change-alpha' },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'ready-for-finalization',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      target_sync: {
        receipt_id: 'a'.repeat(64),
        operation_id: 'sync-portfolio-change',
        target_branch: 'main',
        expected_target: '1'.repeat(40),
        target_head: '1'.repeat(40),
        change_head_before: '2'.repeat(40),
        merged_head: '3'.repeat(40),
        merge_commit: true,
        review_required: false,
      },
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'finalization', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent(`Target head${'1'.repeat(40)}`)
  expect(inspector).toHaveTextContent(`Target-sync merge result${'3'.repeat(40)}`)
  expect(inspector).toHaveTextContent('Last target sync: main (merge commit)')
  fireEvent.click(within(inspector).getByText('Merge latest target into Change'))
  fireEvent.click(screen.getByText('Confirm target update'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/target/sync',
    method: 'POST',
    body: { operation_id: expect.stringMatching(/^cockpit-target-sync-/) },
  }))
  expect(await screen.findByText('Target synchronized with the integration target.')).toBeInTheDocument()
})

it('shows publication history and keeps ordinary attention remedies available', async () => {
  const attentionId = 'a'.repeat(64)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Change attention requires resolution',
    next_actor: 'you',
    next_step: 'Resolve publication attention',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Resolve publication attention', done: null, total: null },
    action: { kind: 'resolve-attention', label: 'Resolve publication attention', command: null, attention_id: attentionId },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Resolve the provider evidence before continuing.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'awaiting-merge',
      finalization_id: 'b'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: attentionId,
        kind: 'publication-attention',
        change_id: 'change-alpha',
        entered_from: 'awaiting-merge',
        recorded_at: '2026-08-11T16:00:00Z',
        diagnostics: ['Provider publication needs reconciliation.'],
      },
      publication_generations: [
        { repository: 'owlbear/example', number: 41, node_id: 'PR_example_41', head_sha: '2'.repeat(40) },
        { repository: 'owlbear/example', number: 42, node_id: 'PR_example_42', head_sha: '1'.repeat(40) },
      ],
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Publication history')
  expect(inspector).toHaveTextContent(`Generation 1: owlbear/example #41 / ${'2'.repeat(40)}`)
  expect(inspector).toHaveTextContent(`Generation 2: owlbear/example #42 / ${'1'.repeat(40)}`)
  expect(within(inspector).getAllByText('Resolve publication attention')).not.toHaveLength(0)
  expect(within(inspector).getByTestId('publication-supersede')).toBeInTheDocument()

  fireEvent.click(within(inspector).getByTestId('publication-supersede'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/publication/supersede',
    method: 'POST',
    body: { operation_id: expect.stringMatching(/^cockpit-publication-supersede-/) },
  }))
  expect(await screen.findByText('Publication superseded.')).toBeInTheDocument()
})

it('reuses a supersession operation identity after a retry-safe failure', async () => {
  const attentionId = 'a'.repeat(64)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Change attention requires resolution',
    next_actor: 'you',
    next_step: 'Resolve publication attention',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Resolve publication attention', done: null, total: null },
    action: { kind: 'resolve-attention', label: 'Resolve publication attention', command: null, attention_id: attentionId },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: 'awaiting-merge',
      finalization_id: 'b'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: attentionId,
        kind: 'publication-attention',
        change_id: 'change-alpha',
        entered_from: 'awaiting-merge',
        recorded_at: '2026-08-11T16:00:00Z',
        diagnostics: ['Provider publication needs reconciliation.'],
      },
      publication_generations: [
        { repository: 'owlbear/example', number: 42, node_id: 'PR_example_42', head_sha: '1'.repeat(40) },
      ],
    },
  })
  supersedeFailuresRemaining = 1
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const supersede = await screen.findByTestId('publication-supersede')
  fireEvent.click(supersede)
  await waitFor(() => expect(screen.getByText('ERR_PROVIDER_UNAVAILABLE')).toBeInTheDocument())
  fireEvent.click(supersede)
  await waitFor(() => expect(requests.filter(({ url, method }) => method === 'POST' && url.endsWith('/publication/supersede'))).toHaveLength(2))

  const supersessionRequests = requests.filter(({ url, method }) => method === 'POST' && url.endsWith('/publication/supersede'))
  expect(supersessionRequests[0].body).toEqual({ operation_id: expect.stringMatching(/^cockpit-publication-supersede-/) })
  expect(supersessionRequests[1].body).toEqual(supersessionRequests[0].body)
})

it('offers explicit exits for a preserved target-sync conflict', async () => {
  const dispositionId = 'd'.repeat(64)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Target sync conflict',
    next_actor: 'you',
    next_step: 'Choose an explicit target-sync conflict exit',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Finalization invalidated', done: null, total: null },
    action: { kind: 'resolve-attention', label: 'Resolve attention', command: null, attention_id: dispositionId },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'finalization-invalidated',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: '5'.repeat(40),
      invalidated_observed_head: '4'.repeat(40),
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: dispositionId,
        kind: 'publication-attention',
        change_id: 'change-alpha',
        entered_from: 'finalization',
        recorded_at: '2026-08-12T12:00:00Z',
        diagnostics: ['target-sync-operation:cockpit-target-sync-conflict'],
      },
      target_sync_conflict: {
        conflict_id: 'e'.repeat(64),
        operation_id: 'cockpit-target-sync-conflict',
        target_head: '4'.repeat(40),
        change_head_before: '5'.repeat(40),
        conflict_paths: ['src/app.py', 'tests/test_app.py'],
      },
      publication_generations: [
        { repository: 'owlbear/example', number: 42, node_id: 'PR_example_42', head_sha: '1'.repeat(40) },
      ],
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Target sync conflict')
  expect(inspector).toHaveTextContent('src/app.py')
  expect(within(inspector).queryByText('Resolve attention')).toBeNull()
  expect(within(inspector).queryByTestId('publication-supersede')).toBeNull()

  fireEvent.click(screen.getByTestId('target-sync-conflict-abort'))
  fireEvent.click(screen.getByText('Confirm abort'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/target/conflict/abort',
    method: 'POST',
    body: {
      expected_disposition_id: dispositionId,
      target_head: '4'.repeat(40),
      operation_id: 'cockpit-target-sync-conflict',
    },
  }))
  expect(await screen.findByText('Target sync conflict aborted.')).toBeInTheDocument()

  fireEvent.click(screen.getByTestId('target-sync-conflict-resolve'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/target/conflict/resolve',
    method: 'POST',
    body: {
      expected_disposition_id: dispositionId,
      target_head: '4'.repeat(40),
      operation_id: 'cockpit-target-sync-conflict',
    },
  }))
})

it('offers the finalization command from the Change publication row and detail view', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Finalize the reviewed Change',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Ready for finalization', done: null, total: null },
    action: { kind: 'finalize', label: 'Finalize Change', command: '/finalize-change change-alpha' },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'ready-for-finalization',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'finalization', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).getByLabelText('Copy command /finalize-change change-alpha')).toBeInTheDocument()
  expect(screen.getAllByLabelText('Copy command /finalize-change change-alpha')).toHaveLength(3)
  expect(within(screen.getByTestId('portfolio-commands')).getByLabelText('Copy command /finalize-change change-alpha')).toBeInTheDocument()
})

it('keeps invalidated finalization heads distinct and offers re-finalization', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: 'Finalization invalidated',
    next_actor: 'agent',
    next_step: 'Re-finalize the current Change head',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Head drift observed', done: null, total: null },
    action: { kind: 'finalize', label: 'Re-finalize Change', command: '/finalize-change change-alpha' },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'finalization-invalidated',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: '1'.repeat(40),
      invalidated_observed_head: '2'.repeat(40),
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).getByRole('region', { name: 'Finalization invalidated' })).toBeInTheDocument()
  expect(inspector).toHaveTextContent(`Expected head${'1'.repeat(40)}`)
  expect(inspector).toHaveTextContent(`Observed head${'2'.repeat(40)}`)
  expect(inspector).toHaveTextContent('Re-finalize the current Change head')
  expect(within(inspector).getByLabelText('Copy command /finalize-change change-alpha')).toBeInTheDocument()
})

it('shows GitHub merge as user-owned work with observation as the only Cockpit control', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Merge pull request in GitHub',
    next_actor: 'you',
    next_step: 'Merge pull request in GitHub',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Awaiting merge in GitHub', done: null, total: null },
    action: { kind: 'observe-acceptance', label: 'Check merge status', command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'awaiting-merge',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).getByRole('region', { name: 'Awaiting merge in GitHub' })).toBeInTheDocument()
  expect(inspector).toHaveTextContent('owlbear/example')
  expect(inspector).toHaveTextContent('42')
  expect(within(inspector).queryByText(/merge now/i)).not.toBeInTheDocument()
  fireEvent.click(within(inspector).getByText('Check merge status'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/acceptance/observe',
    method: 'POST',
    body: null,
  }))

  acceptanceObservationFailure = true
  fireEvent.click(within(inspector).getByText('Check merge status'))
  const waiting = await within(inspector).findByRole('status')
  expect(waiting).toHaveTextContent('ERR_DELIVERY_ACCEPTANCE_WAITING')
  expect(within(inspector).queryByRole('alert')).not.toBeInTheDocument()
})

it('surfaces acceptance-reconciliation provider failure with an immediate retry', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Merge pull request in GitHub',
    next_actor: 'you',
    next_step: 'Merge pull request in GitHub',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Awaiting merge in GitHub', done: null, total: null },
    action: { kind: 'observe-acceptance', label: 'Check merge status', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', items: [publicationCard] })])
  acceptanceReconciliationProviderUnavailable = true
  renderPage()

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('GitHub acceptance checks are unavailable for change-alpha.')
  expect(alert).toHaveTextContent('GitHub acceptance provider unavailable')

  acceptanceReconciliationProviderUnavailable = false
  fireEvent.click(within(alert).getByText('Retry acceptance check'))
  await waitFor(() => expect(screen.queryByText('GitHub acceptance checks are unavailable for change-alpha.')).not.toBeInTheDocument())
  expect(requests.filter((request) => request.url === '/api/work-items/acceptance/reconcile')).toHaveLength(2)
})

it('shows Change attention diagnostics and resolves the selected disposition', async () => {
  const attentionId = 'a'.repeat(64)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Change attention requires resolution',
    next_actor: 'you',
    next_step: 'Resolve acceptance attention',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Resolve acceptance attention', done: null, total: null },
    action: { kind: 'resolve-attention', label: 'Resolve acceptance attention', command: null, attention_id: attentionId },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Resolve the provider evidence before continuing.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'awaiting-merge',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: attentionId,
        kind: 'acceptance-attention',
        change_id: 'change-alpha',
        entered_from: 'awaiting-merge',
        recorded_at: '2026-08-11T16:00:00Z',
        diagnostics: ['Pull request was closed without a merge commit.'],
      },
      publication_generations: [
        { repository: 'owlbear/example', number: 42, node_id: 'PR_example_42', head_sha: '1'.repeat(40) },
      ],
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'acceptance', outcome_completed: 0, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(inspector).toHaveTextContent('Change attention')
  expect(inspector).toHaveTextContent('Pull request was closed without a merge commit.')
  expect(inspector).toHaveTextContent(`Disposition: ${attentionId}`)
  expect(within(inspector).queryByTestId('publication-supersede')).toBeNull()
  fireEvent.click(within(inspector).getAllByText('Resolve acceptance attention').at(-1)!)
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/attention/resolve',
    method: 'POST',
    body: { expected_disposition_id: attentionId },
  }))
  expect(await screen.findByText('Change attention resolved.')).toBeInTheDocument()
})

it('posts reasoned Change dispositions and resumes a deferred Change', async () => {
  const activeCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Finalize the reviewed Change',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Ready for finalization', done: null, total: null },
    action: { kind: 'finalize', label: 'Finalize Change', command: '/finalize-change change-alpha' },
  })
  currentDetail = detail({
    card: activeCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'ready-for-finalization',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'finalization', outcome_completed: 2, items: [activeCard] })])
  const initialRender = renderPage('/delivery/change-alpha/publication')
  const inspector = await screen.findByTestId('work-item-detail')
  const reason = await waitFor(() => {
    const element = namedPdsHost(inspector, 'p-input-text', 'change-disposition-reason')
    expect(element).not.toBeNull()
    return element!
  })
  inputValue(reason, 'Wait for user review')
  fireEvent.change(reason, new CustomEvent('change', { detail: { value: 'Wait for user review' }, bubbles: true }))
  const defer = within(inspector).getByText('Defer Change') as HTMLElement & { disabled: boolean }
  await waitFor(() => expect(defer.disabled).toBe(false))
  fireEvent.click(defer)
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/defer',
    method: 'POST',
    body: { reason: 'Wait for user review' },
  }))

  inputValue(reason, 'User stopped the Change')
  fireEvent.change(reason, new CustomEvent('change', { detail: { value: 'User stopped the Change' }, bubbles: true }))
  fireEvent.click(within(inspector).getByText('Abandon Change'))
  fireEvent.click(await screen.findByText('Confirm abandon Change'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/abandon',
    method: 'POST',
    body: { confirmed_abandonment: true, reason: 'User stopped the Change' },
  }))

  initialRender.unmount()
  const deferredCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'you',
    needs_headline: 'Change is deferred',
    next_actor: 'you',
    next_step: 'Resume the deferred Change',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Change deferred', done: null, total: null },
    action: { kind: 'resume-change', label: 'Resume Change', command: null },
  })
  currentDetail = detail({
    card: deferredCard,
    publication: {
      phase: 'deferred',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'deferred', items: [deferredCard] })])
  renderPage('/delivery/change-alpha/publication')
  const deferredInspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(deferredInspector).getByText('Resume Change'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/resume',
    method: 'POST',
    body: null,
  }))
})

it('keeps Change abandonment confirmation open when abandonment fails', async () => {
  const publicationCard = publicationCardForChecks({
    next_step: 'Finalize the reviewed Change',
    progress: { kind: 'publication', label: 'Ready for finalization', done: null, total: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('ready-for-finalization'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'finalization', items: [publicationCard] })])
  mutationFailurePath = '/abandon'
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  const reason = await waitFor(() => {
    const element = namedPdsHost(inspector, 'p-input-text', 'change-disposition-reason')
    expect(element).not.toBeNull()
    return element!
  })
  inputValue(reason, 'User stopped the Change')
  fireEvent.change(reason, new CustomEvent('change', { detail: { value: 'User stopped the Change' }, bubbles: true }))
  fireEvent.click(within(inspector).getByText('Abandon Change'))
  fireEvent.click(await screen.findByText('Confirm abandon Change'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/abandon',
    method: 'POST',
    body: { confirmed_abandonment: true, reason: 'User stopped the Change' },
  }))
  const dialog = screen.getByRole('alertdialog')
  expect(within(dialog).getByRole('alert')).toHaveTextContent('The Delivery operation was rejected while the confirmation was open.')
  expect(within(dialog).getByText('Confirm Change abandonment')).toBeInTheDocument()
})

it('does not show Change disposition controls on an Outcome detail', async () => {
  currentDetail = detail()
  currentPortfolio = portfolio()
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).queryByText('Defer Change')).not.toBeInTheDocument()
  expect(within(inspector).queryByText('Abandon Change')).not.toBeInTheDocument()
})

it('does not show Change disposition controls for an abandoned Change', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'none',
    next_step: 'Change abandoned',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Change abandoned', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: 'abandoned',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'abandoned', items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).queryByText('Defer Change')).not.toBeInTheDocument()
  expect(within(inspector).queryByText('Abandon Change')).not.toBeInTheDocument()
})

it('confirms and cleans an eligible abandoned Change from Change history', async () => {
  const abandoned = abandonedRecord()
  completedRecords = [abandoned]
  renderPage()

  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  fireEvent.click(within(record).getByRole('button', { name: `Inspect ${abandoned.title}` }))
  const detailView = await screen.findByTestId('completed-change-detail')
  fireEvent.click(within(detailView).getByText('Clean abandoned worktree'))
  fireEvent.click(await screen.findByText('Confirm cleanup'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/cleanup/abandoned',
    method: 'POST',
    body: null,
  }))
  expect(await screen.findByText('Abandoned Change worktree cleaned up.')).toBeInTheDocument()
})

it('keeps abandoned history cleanup confirmation open when cleanup fails', async () => {
  const abandoned = abandonedRecord()
  completedRecords = [abandoned]
  mutationFailurePath = '/worktree/cleanup/abandoned'
  renderPage()

  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  fireEvent.click(within(record).getByRole('button', { name: `Inspect ${abandoned.title}` }))
  const detailView = await screen.findByTestId('completed-change-detail')
  fireEvent.click(within(detailView).getByText('Clean abandoned worktree'))
  fireEvent.click(await screen.findByText('Confirm cleanup'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/cleanup/abandoned',
    method: 'POST',
    body: null,
  }))
  const dialog = screen.getByRole('alertdialog')
  expect(within(dialog).getByRole('alert')).toHaveTextContent('The Delivery operation was rejected while the confirmation was open.')
  expect(within(dialog).getByText('Clean abandoned worktree')).toBeInTheDocument()
})

it('confirms discard and cleanup for an abandoned target-sync conflict from Change history', async () => {
  const abandoned = abandonedRecord({
    target_sync_conflict: true,
    cleanup_available: true,
  })
  completedRecords = [abandoned]
  renderPage()

  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  fireEvent.click(within(record).getByRole('button', { name: `Inspect ${abandoned.title}` }))
  const detailView = await screen.findByTestId('completed-change-detail')
  fireEvent.click(within(detailView).getByText('Discard conflict and clean worktree'))
  fireEvent.click(await screen.findByText('Confirm cleanup'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/cleanup/abandoned/target-sync-discard',
    method: 'POST',
    body: { confirmed_discard: true },
  }))
  expect(await screen.findByText('Target merge discarded and abandoned Change worktree cleaned up.')).toBeInTheDocument()
})

it('cleans an eligible completed Change worktree with its exact completion identity', async () => {
  const completionId = 'e'.repeat(64)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'none',
    next_step: 'Acceptance observed',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Acceptance observed', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: 'acceptance-observed',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: '2'.repeat(40),
      merged_at: '2026-08-11T13:00:00Z',
      worktree_cleanup: { eligible: true, blocked_reason: null, completion_id: completionId },
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'acceptance', items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Clean completed worktree'))
  fireEvent.click(await screen.findByText('Confirm clean completed worktree'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/cleanup/completed',
    method: 'POST',
    body: { completion_id: completionId },
  }))
  expect(await screen.findByText('Completed Change worktree cleaned up.')).toBeInTheDocument()
})

it('confirms and recovers a missing Change worktree from its exact reviewed head', async () => {
  const reviewedHead = '9'.repeat(40)
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'none',
    next_step: 'Change abandoned',
    activity: { state: 'idle', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Change abandoned', done: null, total: null },
    action: { kind: 'none', label: null, command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: 'abandoned',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      worktree_recovery: { eligible: true, blocked_reason: null, recovery_reviewed_head: reviewedHead },
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'abandoned', items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).getByText(`Reviewed head: ${reviewedHead}`)).toBeInTheDocument()
  fireEvent.click(within(inspector).getByText('Recover missing worktree'))
  fireEvent.click(await screen.findByText('Confirm worktree recovery'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/recover',
    method: 'POST',
    body: { confirmed_recovery: true, recovery_reviewed_head: reviewedHead },
  }))
  expect(await screen.findByText('Missing Change worktree recovered.')).toBeInTheDocument()
})

it('keeps missing worktree recovery confirmation open when recovery fails', async () => {
  const reviewedHead = '1'.repeat(40)
  const publicationCard = publicationCardForChecks({
    next_step: 'Change abandoned',
    progress: { kind: 'publication', label: 'Change abandoned', done: null, total: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: 'abandoned',
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      worktree_recovery: { eligible: true, blocked_reason: null, recovery_reviewed_head: reviewedHead },
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'abandoned', items: [publicationCard] })])
  mutationFailurePath = '/worktree/recover'
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Recover missing worktree'))
  fireEvent.click(await screen.findByText('Confirm worktree recovery'))
  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/worktree/recover',
    method: 'POST',
    body: { confirmed_recovery: true, recovery_reviewed_head: reviewedHead },
  }))
  const dialog = screen.getByRole('alertdialog')
  expect(within(dialog).getByRole('alert')).toHaveTextContent('The Delivery operation was rejected while the confirmation was open.')
  expect(within(dialog).getByText('Recover missing worktree')).toBeInTheDocument()
})

it('uses the Complete status tag without leaking the internal Stage field', async () => {
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
  expect(inspector).toHaveTextContent('Complete')
  expect(inspector).not.toHaveTextContent('Completed')
  expect(inspector).not.toHaveTextContent('Stage')
  expect(inspector).toHaveTextContent('Progress1 of 1 Delivery tasks reviewed')
  expect(inspector).not.toHaveTextContent('Complete — no action needed')
})

it('presents a draft pull request as publication work', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    next_actor: 'agent',
    next_step: 'Mark the pull request ready through Delivery',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    publication_phase: 'pull-request-draft',
    progress: { kind: 'publication', label: 'Delivery ready state not recorded', done: null, total: null },
    action: { kind: 'mark-ready', label: 'Make PR ready for review', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  renderPage()

  const table = await screen.findByTestId('work-portfolio-table')
  expect(table).toHaveTextContent('Change: Portfolio redesign')
  expect(table).toHaveTextContent('Delivery ready state not recorded')
  expect(table).toHaveTextContent('Make PR ready for review')
  const publicationRow = screen.getByLabelText('Change publication for Portfolio redesign')
  expect(publicationRow.querySelector('[data-status-tone]')).toHaveTextContent('Delivery ready state not recorded')
  const readyLink = within(table).getByText('Make PR ready for review').closest('p-link-pure') as HTMLElement & { href: string }
  expect(readyLink.href).toBe('/delivery/change-alpha/publication')
  expect(screen.getByLabelText('Delivery portfolio status')).not.toHaveTextContent('need you')
})

it('observes checks from a draft even when repository and pull request fields are null', async () => {
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('pull-request-draft'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'publication', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  const portfolioReadsBefore = requests.filter(({ url, method }) => url === '/api/work-items' && method === 'GET').length
  expect(within(inspector).getByTestId('publication-checks-observe')).toBeInTheDocument()
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))

  await waitFor(() => expect(requests).toContainEqual({
    url: '/api/changes/change-alpha/publication/checks/observe',
    method: 'POST',
    body: null,
  }))
  expect(await within(inspector).findByText('Unit tests')).toBeInTheDocument()
  expect(within(inspector).getByText('Blocking', { exact: true })).toBeInTheDocument()
  expect(within(inspector).getByText('Required pending', { exact: true })).toBeInTheDocument()
  expect(within(inspector).getByText('Not blocking', { exact: true })).toBeInTheDocument()
  expect(within(inspector).getByText('Observed commit').nextElementSibling).toHaveTextContent('1'.repeat(40))
  expect(within(inspector).getByText('Evidence recorded').nextElementSibling).toHaveTextContent('2026-08-11T16:00:00Z')
  expect(Array.from(within(inspector).getAllByTestId('publication-check')).map((item) => item.textContent)).toEqual([
    expect.stringContaining('Unit tests'),
    expect.stringContaining('Integration tests'),
    expect.stringContaining('Optional lint'),
  ])
  const portfolioReadsAfter = requests.filter(({ url, method }) => url === '/api/work-items' && method === 'GET').length
  expect(portfolioReadsAfter).toBe(portfolioReadsBefore)
})

it('does not offer publication-check observation outside draft and awaiting-merge phases', async () => {
  const publicationCard = publicationCardForChecks({
    progress: { kind: 'publication', label: 'Ready for finalization', done: null, total: null },
  })
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('ready-for-finalization'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'finalization', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  expect(within(inspector).queryByTestId('publication-checks-observe')).not.toBeInTheDocument()
})

it('clears publication-check results when the polled published head changes', async () => {
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))
  await within(inspector).findByText('Unit tests')

  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge', '2'.repeat(40)),
  })
  await waitFor(
    () => expect(within(inspector).getByTestId('publication-checks-status')).toHaveTextContent('Previous check results were cleared'),
    { timeout: 6_000 },
  )
  expect(within(inspector).queryByText('Unit tests')).not.toBeInTheDocument()
})

it('keeps observed publication checks visible across a phase change with the same head', async () => {
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))
  await within(inspector).findByText('Unit tests')

  currentDetail = detail({
    card: publicationCard,
    publication: {
      ...publicationForChecks('awaiting-merge'),
      phase: 'checkpoint-pending',
      pending_checkpoint_head: '1'.repeat(40),
      pending_checkpoint_triggers: ['finalization'],
    },
  })
  await waitFor(() => {
    expect(within(inspector).getByText('Checkpoint pending')).toBeInTheDocument()
    expect(within(inspector).queryByTestId('publication-checks-observe')).not.toBeInTheDocument()
  }, { timeout: 6_000 })
  expect(within(inspector).getByText('Unit tests')).toBeInTheDocument()
})

it('disables publication-check observation while another publication action is pending', async () => {
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  pendingMutationPath = '/target/sync'
  const inspector = (renderPage('/delivery/change-alpha/publication'), await screen.findByTestId('work-item-detail'))

  try {
    fireEvent.click(within(inspector).getByText('Merge latest target into Change'))
    fireEvent.click(screen.getByText('Confirm target update'))
    const observe = within(inspector).getByTestId('publication-checks-observe') as HTMLElement & { disabled: boolean }
    await waitFor(() => expect(observe.disabled).toBe(true))
  } finally {
    pendingMutationRelease?.()
    pendingMutationPath = null
    pendingMutationRelease = null
  }
})

it('disables publication actions while publication-check observation is pending', async () => {
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  pendingPublicationChecksObservation = true
  renderPage('/delivery/change-alpha/publication')
  const inspector = await screen.findByTestId('work-item-detail')

  try {
    fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))
    const sync = within(inspector).getByText('Merge latest target into Change') as HTMLElement & { disabled: boolean }
    await waitFor(() => expect(sync.disabled).toBe(true))
    expect(requests.filter(({ url, method }) => method === 'POST' && url.endsWith('/target/sync'))).toHaveLength(0)
  } finally {
    pendingPublicationChecksRelease?.()
    pendingPublicationChecksObservation = false
    pendingPublicationChecksRelease = null
  }
})

it('rejects an observation returned for a different exact head', async () => {
  publicationChecksResponse = { ...publicationChecksResponse, exact_commit: '2'.repeat(40) }
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))

  const error = await within(inspector).findByRole('alert')
  expect(error).toHaveTextContent('ERR_WORK_ITEM_PUBLICATION_CHECKS_OBSERVE')
  expect(error).toHaveTextContent('do not match the current Change published head')
  expect(within(inspector).queryByText('Unit tests')).not.toBeInTheDocument()
})

it('discloses provider checks omitted by the bounded response', async () => {
  publicationChecksResponse = { ...publicationChecksResponse, truncated_count: 1 }
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))

  expect(await within(inspector).findByText('1 additional check not shown.')).toBeInTheDocument()
})

it('shows typed provider failure for publication-check observation', async () => {
  publicationChecksFailure = true
  const publicationCard = publicationCardForChecks()
  currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks('awaiting-merge'),
  })
  currentPortfolio = portfolio([group({ lifecycle: 'awaiting-merge', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByTestId('publication-checks-observe'))
  const error = await within(inspector).findByRole('alert')
  expect(error).toHaveTextContent('ERR_DELIVERY_PROVIDER_UNAVAILABLE')
  expect(error).toHaveTextContent('GitHub is unavailable')
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

it('shows stale Work Item detail state and retries the refresh in place', async () => {
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')
  detailFailure = true

  const alert = await screen.findByRole('alert', {}, { timeout: 4_000 })
  expect(alert).toHaveTextContent('Showing the last successful Work Item detail; live updates paused.')
  expect(alert).toHaveTextContent('Delivery runtime is absent: change-alpha')
  expect(screen.getByTestId('work-item-detail')).toBeInTheDocument()

  detailFailure = false
  fireEvent.click(within(alert).getByText('Retry Work Item', { exact: true }))
  await waitFor(() => expect(screen.queryByText('Showing the last successful Work Item detail; live updates paused.')).not.toBeInTheDocument())
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

it('shows finalized and accepted merge heads as distinct identities', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    needs: 'none',
    needs_headline: null,
    next_actor: 'agent',
    next_step: 'Record accepted completion',
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Merge observed', done: null, total: null },
    action: { kind: 'observe-acceptance', label: 'Complete accepted Change', command: null },
  })
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'acceptance-observed',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: '2'.repeat(40),
      merged_at: '2026-08-11T12:00:00Z',
    },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'acceptance', outcome_completed: 2, items: [publicationCard] })])
  renderPage('/delivery/change-alpha/publication')

  const detailView = await screen.findByTestId('work-item-detail')
  expect(detailView).toHaveTextContent(`Finalized head${'1'.repeat(40)}`)
  expect(detailView).toHaveTextContent(`Accepted merge commit${'2'.repeat(40)}`)
  expect(detailView).not.toHaveTextContent(/ancestor|descendant|merge method/i)
})

it('moves a completed selected Change into completed history instead of leaving a dead route', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Merge observed', done: null, total: null },
    action: { kind: 'observe-acceptance', label: 'Complete accepted Change', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'acceptance', outcome_completed: 2, items: [publicationCard] })])
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'acceptance-observed',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: '2'.repeat(40),
      merged_at: '2026-08-11T12:00:00Z',
    },
  })
  portfolioAfterPublication = portfolio([])
  renderPage('/delivery/change-alpha/publication')
  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Complete accepted Change'))

  expect(await screen.findByTestId('completed-history-workspace')).toHaveTextContent('Change history')
  await waitFor(() => expect(screen.getByTestId('test-location')).toHaveTextContent('/delivery/history'))
  expect(await screen.findByText('Portfolio redesign')).toBeInTheDocument()
})

it('closes live detail before entering completed history', async () => {
  renderPage('/delivery/change-alpha/outcome%3AOUT-001')
  await screen.findByTestId('work-item-detail')

  fireEvent.click(screen.getByRole('button', { name: 'Change history', exact: true }))

  await screen.findByTestId('completed-history-workspace')
  expect(screen.queryByTestId('work-item-detail')).not.toBeInTheDocument()
  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
    expect(openFlyout).toBeUndefined()
  })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Change history', exact: true })).toHaveFocus())
})

it('presents legacy completion package provenance explicitly', async () => {
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  fireEvent.click(within(record).getByRole('button', { name: 'Inspect Portfolio redesign' }))

  const detailView = await screen.findByTestId('completed-change-detail')
  const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
  expect(openFlyout).toBeInTheDocument()
  expect(detailView).toHaveTextContent('Purpose')
  expect(detailView).toHaveTextContent('Give operators a clear view of grouped Delivery work.')
  expect(detailView).toHaveTextContent('Delivered outcomes')
  expect(detailView).toHaveTextContent('Ship the grouped Delivery workspace')
  expect(detailView).toHaveTextContent('Historical delivery')
  expect(detailView).toHaveTextContent('Legacy package')
  expect(detailView).toHaveTextContent('.owlbear/legacy/completed/change-alpha')
  expect(detailView).toHaveTextContent('.owlbear/completed/change-alpha')
})

it('refreshes current delivery immediately after returning from completed history', async () => {
  currentPortfolio = portfolio([group({ title: 'Initial delivery' })])
  renderPage()
  await screen.findByRole('heading', { name: 'Initial delivery', exact: true })

  fireEvent.click(screen.getByRole('button', { name: 'Change history', exact: true }))
  await screen.findByTestId('completed-history-workspace')
  currentPortfolio = portfolio([group({ title: 'Refreshed delivery' })])
  const requestsBeforeReturn = requests.filter(({ method, url }) => method === 'GET' && url === '/api/work-items').length

  fireEvent.click(screen.getByRole('button', { name: 'Current delivery', exact: true }))
  await screen.findByRole('heading', { name: 'Refreshed delivery', exact: true })

  const requestsAfterReturn = requests.filter(({ method, url }) => method === 'GET' && url === '/api/work-items').length
  expect(requestsAfterReturn).toBeGreaterThan(requestsBeforeReturn)
})

it('explains when completed history is empty', async () => {
  completedRecords = []
  renderPage()
  fireEvent.click(screen.getByText('Change history'))

  const emptyState = await screen.findByTestId('completed-history-empty-state')
  expect(emptyState).toHaveTextContent('No changes in history yet')
  expect(emptyState).toHaveTextContent('Completed and abandoned Changes will appear here with their retained evidence.')
})

it('distinguishes no matching completed history and clears the search', async () => {
  completedRecords = [completed]
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await screen.findByTestId('completed-change-record')

  const search = container.querySelector('p-input-search')
  expect(search).not.toBeNull()
  inputValue(search as Element, 'unmatched history')

  const emptyState = await screen.findByTestId('completed-history-empty-state')
  expect(emptyState).toHaveTextContent('No changes match "unmatched history"')
  expect(emptyState).toHaveTextContent('Try a different search or clear the current search.')
  fireEvent.click(within(emptyState).getByText('Clear search', { exact: true }))

  await waitFor(() => expect(screen.getByTestId('completed-change-record')).toBeInTheDocument())
})

it('marks previous completed history results while a search is pending', async () => {
  completedRecords = [completed, receiptCompleted]
  completedHistorySearchPending = true
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2))

  try {
    const search = container.querySelector('p-input-search')
    expect(search).not.toBeNull()
    inputValue(search as Element, 'unmatched history')

    const staleStatus = await screen.findByTestId('completed-history-stale-status')
    expect(staleStatus).toHaveTextContent('Previous results are shown until the search finishes.')
    expect(screen.getByTestId('completed-history-results')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2)
    expect(screen.getAllByTestId('completed-change-record')[0]).toHaveAttribute('data-stale', 'true')
  } finally {
    completedHistorySearchRelease?.()
    completedHistorySearchPending = false
    completedHistorySearchRelease = null
  }

  await screen.findByTestId('completed-history-empty-state')
})

it('retains previous completed history when a search fails', async () => {
  completedRecords = [completed, receiptCompleted]
  completedHistoryNextCursor = 'page-2'
  completedHistorySearchFailuresRemaining = 1
  completedHistorySearchRecords = [receiptCompleted]
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2))

  const search = container.querySelector('p-input-search')
  expect(search).not.toBeNull()
  inputValue(search as Element, 'Beta')

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Change history is unavailable.')
  expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2)
  expect(screen.getByTestId('completed-history-stale-status')).toHaveTextContent('Previous results are shown while this search is retried.')
  const loadMore = screen.getByText('Load more', { exact: true }).closest('p-button') as HTMLElement & { disabled?: boolean }
  expect(loadMore.disabled).toBe(true)

  fireEvent.click(within(alert).getByText('Retry history', { exact: true }))
  await screen.findByText('Receipt-backed delivery', { exact: true })
  expect(screen.getAllByTestId('completed-change-record')).toHaveLength(1)
  expect(screen.queryByTestId('completed-history-stale-status')).not.toBeInTheDocument()
})

it('disables load more while a completed history search is pending', async () => {
  completedRecords = [completed, receiptCompleted]
  completedHistoryNextCursor = 'page-2'
  completedHistorySearchPending = true
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2))

  try {
    const search = container.querySelector('p-input-search')
    expect(search).not.toBeNull()
    inputValue(search as Element, 'Beta')
    await screen.findByTestId('completed-history-stale-status')

    const loadMore = screen.getByTestId('completed-history-load-more').closest('p-button') as HTMLElement & { disabled?: boolean }
    expect(loadMore.disabled).toBe(true)
  } finally {
    completedHistorySearchRelease?.()
    completedHistorySearchPending = false
    completedHistorySearchRelease = null
  }
})

it('appends paginated results for a completed history search', async () => {
  completedHistorySearchRecords = [completed]
  completedHistorySearchNextCursor = 'search-page-2'
  completedHistorySearchPageRecords = [receiptCompleted]
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(1))

  const search = container.querySelector('p-input-search')
  expect(search).not.toBeNull()
  inputValue(search as Element, 'Beta')
  await screen.findByTestId('completed-history-load-more')

  fireEvent.click(screen.getByTestId('completed-history-load-more'))
  await screen.findByText('Receipt-backed delivery', { exact: true })
  expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2)
  expect(requests.filter(({ url, method }) => method === 'GET'
    && url === '/api/work-items/completed/search?query=Beta&cursor=search-page-2')).toHaveLength(1)
  await waitFor(() => expect(screen.getByTestId('completed-history-workspace')).toHaveFocus())
})

it('closes completed history detail when a settled search removes the selected record', async () => {
  completedRecords = [completed, receiptCompleted]
  completedHistorySearchPending = true
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2))

  try {
    const search = container.querySelector('p-input-search')
    expect(search).not.toBeNull()
    inputValue(search as Element, 'unmatched history')
    await screen.findByTestId('completed-history-stale-status')

    const record = screen.getAllByTestId('completed-change-record').find((candidate) => candidate.textContent?.includes('Portfolio redesign'))
    expect(record).toBeDefined()
    fireEvent.click(within(record!).getByRole('button', { name: 'Inspect Portfolio redesign' }))
    await screen.findByTestId('completed-change-detail')

    completedHistorySearchRelease?.()
    completedHistorySearchPending = false
    await screen.findByTestId('completed-history-empty-state')
    await waitFor(() => {
      const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
      expect(openFlyout).toBeUndefined()
    })
  } finally {
    completedHistorySearchRelease?.()
    completedHistorySearchPending = false
    completedHistorySearchRelease = null
  }
})

it('debounces completed history search requests while typing', async () => {
  completedRecords = [completed, receiptCompleted]
  const { container } = renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await waitFor(() => expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2))

  const search = container.querySelector('p-input-search')
  expect(search).not.toBeNull()
  for (const value of ['a', 'al', 'alp', 'alph', 'alpha']) inputValue(search as Element, value)

  const searchRequests = () => requests.filter(({ url, method }) => method === 'GET' && url.startsWith('/api/work-items/completed/search?'))
  await waitFor(() => expect(searchRequests()).toHaveLength(1), { timeout: 2_000 })
  expect(searchRequests()[0].url).toContain('query=alpha')
})

it('retries failed completed history detail in place', async () => {
  completedRecords = [completed]
  completedDetailFailuresRemaining = 1
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  fireEvent.click(within(record).getByRole('button', { name: 'Inspect Portfolio redesign' }))

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Completion detail is unavailable.')
  fireEvent.click(within(alert).getByText('Retry completion detail', { exact: true }))

  await screen.findByTestId('completed-change-detail')
  expect(screen.getByTestId('completed-change-detail')).toHaveTextContent('Historical delivery')
  expect(requests.filter(({ url, method }) => method === 'GET' && url.includes('/api/work-items/completed/change-alpha?')).length).toBe(2)
})

it('closes a listed completion when its detail is confirmed missing', async () => {
  completedRecords = [completed]
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  const trigger = within(record).getByRole('button', { name: 'Inspect Portfolio redesign' })
  completedDetailNotFound = true
  fireEvent.click(trigger)

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
    expect(openFlyout).toBeUndefined()
  })
  await waitFor(() => expect(trigger).toHaveFocus())
})

it('closes a missing completion despite a failed history page load', async () => {
  completedRecords = [completed]
  completedHistoryNextCursor = 'page-2'
  completedHistoryPageFailuresRemaining = 1
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  const trigger = within(record).getByRole('button', { name: 'Inspect Portfolio redesign' })

  fireEvent.click(screen.getByText('Load more', { exact: true }))
  await screen.findByText('Retry loading more', { exact: true })
  completedDetailNotFound = true
  fireEvent.click(trigger)

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll('p-flyout')).find((element) => (element as HTMLElement & { open: boolean }).open)
    expect(openFlyout).toBeUndefined()
  })
  await waitFor(() => expect(trigger).toHaveFocus())
})

it('returns focus to history after appending the final page', async () => {
  const nextRecord: CompletedChangeRecord = {
    ...completed,
    change_id: 'change-beta',
    completion_id: 'f'.repeat(64),
    title: 'Second historical change',
  }
  completedRecords = [completed]
  completedHistoryNextCursor = 'page-2'
  completedHistoryPageRecords = [nextRecord]
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await screen.findByTestId('completed-history-load-more')

  fireEvent.click(screen.getByTestId('completed-history-load-more'))
  await screen.findByText('Second historical change', { exact: true })
  await waitFor(() => expect(screen.getByTestId('completed-history-workspace')).toHaveFocus())
})

it('keeps a valid later-page completion deep link open', async () => {
  completedRecords = [completed]
  completedDetailRecord = receiptCompleted
  completedHistoryNextCursor = 'page-2'
  renderPage(`/delivery/history/${receiptCompleted.change_id}/${receiptCompleted.completion_id}`)

  const detailView = await screen.findByTestId('completed-change-detail')
  expect(detailView).toHaveTextContent('Receipt-backed delivery')
  expect(screen.getByTestId('completed-history-workspace')).toBeInTheDocument()
})

it('keeps a deep-linked completion open while the initial history list fails', async () => {
  completedHistoryFailuresRemaining = 1
  renderPage(`/delivery/history/${completed.change_id}/${completed.completion_id}`)

  const detailView = await screen.findByTestId('completed-change-detail')
  expect(detailView).toHaveTextContent('Historical delivery')
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Change history is unavailable.')

  fireEvent.click(within(alert).getByText('Retry history', { exact: true }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  expect(screen.getByTestId('completed-change-detail')).toBe(detailView)

  fireEvent.click(within(detailView).getByText('Close', { exact: true }))
  await waitFor(() => expect(screen.getByTestId('completed-history-workspace')).toHaveFocus())
})

it('rejects a completion detail response with the wrong identity', async () => {
  completedDetailMismatch = receiptCompleted
  renderPage(`/delivery/history/${completed.change_id}/${completed.completion_id}`)

  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Completion detail is unavailable.')
  expect(alert).toHaveTextContent('did not match the requested identity')
  expect(screen.queryByText('Receipt-backed delivery')).not.toBeInTheDocument()

  completedDetailMismatch = null
  fireEvent.click(within(alert).getByText('Retry completion detail', { exact: true }))
  const detailView = await screen.findByTestId('completed-change-detail')
  expect(detailView).toHaveTextContent('Historical delivery')
})

it('retries a failed completed history page without resetting loaded records', async () => {
  const nextRecord: CompletedChangeRecord = {
    ...completed,
    change_id: 'change-beta',
    completion_id: 'f'.repeat(64),
    title: 'Second historical change',
  }
  completedRecords = [completed]
  completedHistoryNextCursor = 'page-2'
  completedHistoryPageRecords = [nextRecord]
  completedHistoryPageFailuresRemaining = 1
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  await screen.findByTestId('completed-change-record')
  expect(screen.getByTestId('completed-history-count')).toHaveTextContent('2')

  fireEvent.click(screen.getByText('Load more', { exact: true }))
  const alert = await screen.findByRole('alert')
  expect(alert).toHaveTextContent('Could not load more Change history.')
  expect(within(alert).getByText('Retry loading more', { exact: true })).toBeInTheDocument()
  expect(screen.getAllByTestId('completed-change-record')).toHaveLength(1)

  fireEvent.click(within(alert).getByText('Retry loading more', { exact: true }))
  await screen.findByText('Second historical change', { exact: true })
  expect(screen.getAllByTestId('completed-change-record')).toHaveLength(2)
  expect(requests.filter(({ url, method }) => method === 'GET' && url === '/api/work-items/completed?cursor=page-2')).toHaveLength(2)
})

it('presents receipt completion identities without graph claims', async () => {
  completedRecords = [receiptCompleted]
  renderPage()
  fireEvent.click(screen.getByText('Change history'))
  const record = await screen.findByTestId('completed-change-record')
  const pullRequest = within(record).getByRole('link', { name: 'PR #42' })
  expect(pullRequest).toHaveAttribute('href', 'https://github.com/owlbear/example/pull/42')
  expect(within(record).getByText(/Aug 11, 2026/)).toBeInTheDocument()
  const writeText = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  fireEvent.click(within(record).getByRole('button', { name: 'Copy accepted merge commit' }))
  await waitFor(() => expect(writeText).toHaveBeenCalledWith('4'.repeat(40)))
  fireEvent.click(within(record).getByRole('button', { name: 'Inspect Receipt-backed delivery' }))

  const detailView = await screen.findByTestId('completed-change-detail')
  expect(detailView).toHaveTextContent('Purpose')
  expect(detailView).toHaveTextContent('Record the accepted change with durable evidence.')
  expect(detailView).toHaveTextContent('Delivered outcomes')
  expect(detailView).toHaveTextContent('Accept the merged Delivery change')
  expect(detailView).toHaveTextContent('Accepted delivery')
  expect(detailView).toHaveTextContent('Completion receipt')
  expect(detailView).toHaveTextContent('owlbear/example')
  expect(detailView).toHaveTextContent('#42')
  expect(detailView).toHaveTextContent('main')
  expect(detailView).toHaveTextContent('Finalized Change head')
  expect(detailView).toHaveTextContent('3'.repeat(40))
  expect(detailView).toHaveTextContent('Accepted merge commit')
  expect(detailView).toHaveTextContent('4'.repeat(40))
  expect(within(detailView).getByRole('button', { name: 'Copy completion ID' })).toBeInTheDocument()
  expect(within(detailView).getByRole('button', { name: 'Copy finalized Change head' })).toBeInTheDocument()
  expect(detailView).not.toHaveTextContent(/ancestor|descendant|merged into|merge method/i)
})

it('keeps current delivery open when only the selected publication card disappears', async () => {
  const publicationCard = card({
    item_key: 'publication',
    work_item_id: 'change-alpha',
    scope: 'change-publication',
    title: 'Change publication',
    stage: null,
    activity: { state: 'ready', worker_role: null, started_at: null, task_id: null },
    progress: { kind: 'publication', label: 'Merge observed', done: null, total: null },
    action: { kind: 'observe-acceptance', label: 'Complete accepted Change', command: null },
  })
  currentPortfolio = portfolio([group({ lifecycle: 'acceptance', outcome_completed: 2, items: [publicationCard] })])
  currentDetail = detail({
    card: publicationCard,
    promise: 'Publish the reviewed Change.',
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: 'acceptance-observed',
      finalization_id: 'f'.repeat(64),
      finalized_head: '1'.repeat(40),
      published_head: '1'.repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: 'owlbear/example',
      pull_request_number: 42,
      pull_request_head: '1'.repeat(40),
      accepted_merge_commit: '2'.repeat(40),
      merged_at: '2026-08-11T12:00:00Z',
    },
  })
  portfolioAfterPublication = portfolio([group({ items: [card({ title: 'Returned outcome' })] })])
  renderPage('/delivery/change-alpha/publication')
  const inspector = await screen.findByTestId('work-item-detail')
  fireEvent.click(within(inspector).getByText('Complete accepted Change'))

  expect(await screen.findByTestId('work-portfolio-table')).toHaveTextContent('Returned outcome')
  expect(screen.queryByTestId('completed-history-workspace')).not.toBeInTheDocument()
})
