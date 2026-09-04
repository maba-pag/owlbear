import { type ReactNode, useEffect, useState } from 'react'
import {
  PButton,
  PHeading,
  PIcon,
  PInputText,
  PModal,
  PSelect,
  PSelectOption,
  PTag,
} from '@porsche-design-system/components-react'
import {
  WorkItemApiError,
  type BackwardMovePreview,
  type DeliveryRequest,
  type DeliveryRequestResolution,
  type WorkItemDetailResponse,
  type PublicationCheckBlockingState,
  type PublicationChecksObservationResponse,
  type WorkItemPublicationPhase,
  type WorkItemStage,
  type DeliveryWorkerRole,
} from '../api/workItems'
import {
  PROGRESS_STAGE_LABELS,
  workItemStatus,
  workItemStatusLabel,
} from './workItemPresentation'
import CopyCommand from './CopyCommand'
import { SectionCard, StatusChip } from './DeliveryPrimitives'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function ConfirmationContent({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div
      className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary"
      onKeyDownCapture={(event) => {
        if (event.key !== 'Escape') return
        event.preventDefault()
        onClose()
      }}
    >
      {children}
    </div>
  )
}

interface WorkItemDetailProps {
  detail: WorkItemDetailResponse
  pendingAction: string | null
  actionError: Error | null
  actionResult: string | null
  onAnswerRequest: (requestId: string, resolution: DeliveryRequestResolution) => Promise<Error | null>
  onClearBlock: (blockId: string, note: string, locators: string[]) => Promise<Error | null>
  onRecoverClaim: (attemptId: string, claimId: string) => Promise<Error | null>
  onPreviewBackward: (target: WorkItemStage) => Promise<BackwardMovePreview | null>
  onMoveBackward: (target: WorkItemStage, reason: string, snapshotVersion: string) => Promise<Error | null>
  onReconcilePublication: () => Promise<Error | null>
  onMarkPublicationReady: () => Promise<Error | null>
  publicationChecks: PublicationChecksObservationResponse | null
  publicationChecksError: Error | null
  publicationChecksStale: boolean
  isObservingPublicationChecks: boolean
  onObservePublicationChecks: () => Promise<Error | null>
  onObserveAcceptance: () => Promise<Error | null>
  onAdoptExternalHeadAfterAcceptanceAttention: (
    expectedDispositionId: string,
    expectedHead: string,
    adoptedHead: string,
  ) => Promise<Error | null>
  onResolveAttention: (expectedDispositionId: string) => Promise<Error | null>
  onSupersedePublication: () => Promise<Error | null>
  onSyncTarget: () => Promise<Error | null>
  onAbortTargetSync: (expectedDispositionId: string, targetHead: string, operationId: string) => Promise<Error | null>
  onResolveTargetSync: (expectedDispositionId: string, targetHead: string, operationId: string) => Promise<Error | null>
  onDeferChange: (reason: string) => Promise<Error | null>
  onResumeChange: () => Promise<Error | null>
  onAbandonChange: (reason: string) => Promise<Error | null>
  onCleanupAbandonedChange: () => Promise<Error | null>
  onDiscardAbandonedTargetSync: () => Promise<Error | null>
  onCleanupCompletedChange: (completionId: string) => Promise<Error | null>
  onRecoverChangeWorktree: (recoveryReviewedHead: string) => Promise<Error | null>
}

const WORKER_ROLE_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: 'Planner',
  builder: 'Builder',
}

const REQUEST_KIND_LABELS: Record<DeliveryRequest['kind'], string> = {
  decision: 'Decision',
  action: 'Action',
}

const TASK_STATUS_LABELS: Record<WorkItemDetailResponse['item']['tasks'][number]['status'], string> = {
  pending: 'Pending',
  active: 'Active',
  reviewed: 'Reviewed',
}

function DetailHeader({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const { card } = detail.item
  return (
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
      <div className="min-w-0">
        <span className="text-xs text-contrast-medium">
          <strong className="text-primary">{detail.item.change_title}</strong>
          {' / '}
          {card.scope === 'outcome' ? <code>{card.work_item_id}</code> : 'Change publication'}
        </span>
        <PHeading id="work-detail-heading" tag="h2" size="lg">{card.scope === 'outcome' ? card.title : 'Publication'}</PHeading>
      </div>
      <div className="flex flex-wrap gap-static-xs">
        <StatusChip label={workItemStatusLabel(card)} tone={workItemStatus(card).tone} />
      </div>
    </div>
  )
}

function RequestControl({ request, pending, onAnswer }: {
  request: DeliveryRequest
  pending: boolean
  onAnswer: WorkItemDetailProps['onAnswerRequest']
}) {
  const [selectedOptionId, setSelectedOptionId] = useState('')
  const [responseText, setResponseText] = useState('')
  const canSubmit = Boolean(selectedOptionId || responseText.trim()) && !pending
  const answer = () => onAnswer(request.request_id, {
    selected_option_id: selectedOptionId || null,
    response_text: responseText.trim() || null,
  })
  if (request.resolution) {
    const answerText = request.resolution.response_text
      || request.options.find((option) => option.option_id === request.resolution?.selected_option_id)?.label
      || 'Answered'
    return <p className="mt-static-xs text-sm text-success">{answerText}</p>
  }
  return (
    <div className="mt-static-sm grid gap-static-sm">
      {request.kind === 'decision' ? (
        <PSelect
          compact
          label="Decision"
          name={`request-${request.request_id}-option`}
          value={selectedOptionId}
          disabled={pending}
          onChange={(event) => setSelectedOptionId(fieldValue(event as FieldValueEvent))}
        >
          <PSelectOption value="">Select an option</PSelectOption>
          {request.options.map((option) => (
            <PSelectOption key={option.option_id} value={option.option_id}>{option.label}</PSelectOption>
          ))}
        </PSelect>
      ) : null}
      <PInputText
        compact
        name={`request-${request.request_id}-answer`}
        label={request.kind === 'decision' ? 'Additional response' : 'Action response'}
        value={responseText}
        disabled={pending}
        onChange={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
        onInput={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
      />
      <PButton className="w-fit" type="button" compact disabled={!canSubmit} onClick={() => void answer()}>
        {pending ? 'Submitting...' : 'Submit answer'}
      </PButton>
    </div>
  )
}

function RequestsSection({ detail, pendingAction, onAnswerRequest }: WorkItemDetailProps) {
  if (detail.item.card.scope !== 'outcome') return null
  const requests = detail.item.requests
  if (requests.length === 0) return null
  return (
    <section aria-labelledby="work-requests-heading">
      <PHeading id="work-requests-heading" tag="h3" size="md">Requests</PHeading>
      <div className="mt-static-sm grid gap-static-md">
        {requests.map((request) => (
          <article key={request.request_id} className="border-l-2 border-info pl-static-sm">
            <div className="flex flex-wrap items-center justify-between gap-static-xs">
              <strong className="text-sm">{request.summary}</strong>
              <PTag compact>{REQUEST_KIND_LABELS[request.kind]}</PTag>
            </div>
            <RequestControl request={request} pending={pendingAction !== null} onAnswer={onAnswerRequest} />
          </article>
        ))}
      </div>
    </section>
  )
}

function ChangeDispositionSection(props: WorkItemDetailProps) {
  const [reason, setReason] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (props.detail.item.card.scope !== 'change-publication') return null
  const phase = props.detail.item.publication?.phase
  if (phase === 'abandoned') return null
  const canSubmit = reason.trim().length > 0 && props.pendingAction === null
  const abandon = async () => {
    const error = await props.onAbandonChange(reason.trim())
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <details className="border-t border-contrast-low pt-static-sm" aria-labelledby="change-disposition-heading">
      <summary id="change-disposition-heading" className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">Change lifecycle</summary>
      <div className="mt-static-md grid gap-static-sm">
        <p className="text-sm text-contrast-medium">Use only when the Change should leave its current delivery path. Abandonment is permanent.</p>
        {phase === 'deferred' ? <p className="text-sm">This Change is deferred and retains its worktree.</p> : null}
        <PInputText
          compact
          name="change-disposition-reason"
          label="Reason"
          value={reason}
          disabled={props.pendingAction !== null}
          onChange={(event) => setReason(fieldValue(event as FieldValueEvent))}
          onInput={(event) => setReason(fieldValue(event as FieldValueEvent))}
        />
        <div className="flex flex-wrap gap-static-sm">
          {phase !== 'deferred' ? (
            <PButton type="button" compact variant="secondary" disabled={!canSubmit} onClick={() => void props.onDeferChange(reason.trim())}>
              {props.pendingAction === 'change-defer' ? 'Deferring...' : 'Defer Change'}
            </PButton>
          ) : null}
          <PButton type="button" compact variant="secondary" disabled={!canSubmit} onClick={() => { setActionFailed(false); setConfirmOpen(true) }}>
            {props.pendingAction === 'change-abandon' ? 'Abandoning...' : 'Abandon Change'}
          </PButton>
        </div>
      </div>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm Change abandonment' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Confirm Change abandonment</PHeading>
            <p className="text-sm">Abandonment is permanent. The Change will be retained in Change history as an abandoned record.</p>
            <p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void abandon()}>{props.pendingAction === 'change-abandon' ? 'Abandoning...' : 'Confirm abandon Change'}</PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </details>
  )
}

function BlockSection({ detail, pendingAction, onClearBlock }: WorkItemDetailProps) {
  const block = detail.item.block
  const [note, setNote] = useState('')
  const [locator, setLocator] = useState('')
  if (!block) return null
  const requestless = block.request_id === null
  const canClear = requestless && note.trim().length > 0 && locator.trim().length > 0 && pendingAction === null
  return (
    <section className="border-l-4 border-warning bg-surface p-static-md" aria-labelledby="work-block-heading">
      <PHeading id="work-block-heading" tag="h3" size="md">Blocked</PHeading>
      <p className="mt-static-xs text-sm">{block.reason}</p>
      <p className="mt-static-xs text-sm text-contrast-medium">Clear when: {block.unblock_condition}</p>
      {requestless && !block.resolution_note ? (
        <div className="mt-static-md grid gap-static-sm">
          <PInputText compact name="block-note" label="Operator note" value={note} disabled={pendingAction !== null} onChange={(event) => setNote(fieldValue(event as FieldValueEvent))} onInput={(event) => setNote(fieldValue(event as FieldValueEvent))} />
          <PInputText compact name="block-locator" label="Evidence locator" value={locator} disabled={pendingAction !== null} onChange={(event) => setLocator(fieldValue(event as FieldValueEvent))} onInput={(event) => setLocator(fieldValue(event as FieldValueEvent))} />
          <PButton className="w-fit" type="button" compact disabled={!canClear} onClick={() => void onClearBlock(block.block_id, note.trim(), [locator.trim()])}>
            {pendingAction === 'clear' ? 'Clearing...' : 'Clear block'}
          </PButton>
        </div>
      ) : null}
    </section>
  )
}

function elapsedAge(startedAt: string): string {
  const elapsed = Math.max(Date.now() - new Date(startedAt).getTime(), 0)
  const hours = Math.floor(elapsed / 3_600_000)
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`
  if (hours > 0) return `${hours}h`
  return `${Math.max(Math.floor(elapsed / 60_000), 0)}m`
}

function ClaimSection({ detail, pendingAction, actionError, onRecoverClaim }: WorkItemDetailProps) {
  const claim = detail.item.active_claim
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (!claim) return null
  const recover = async () => {
    const error = await onRecoverClaim(claim.attempt_id, claim.claim_id)
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section aria-labelledby="work-claim-heading">
      <PHeading id="work-claim-heading" tag="h3" size="md">Active claim</PHeading>
      <dl className="mt-static-sm grid gap-static-xs text-sm">
        <div className="flex justify-between gap-static-sm"><dt>Role</dt><dd>{WORKER_ROLE_LABELS[claim.worker_role]}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Started</dt><dd>{elapsedAge(claim.started_at)} ago</dd></div>
        {claim.task_id ? <div className="flex justify-between gap-static-sm"><dt>Task</dt><dd>{claim.task_id}</dd></div> : null}
      </dl>
      <PButton className="mt-static-md" type="button" compact variant="secondary" disabled={pendingAction !== null} onClick={() => { setActionFailed(false); setConfirmOpen(true) }}>
        Recover confirmed-lost claim
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm lost claim' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Confirm lost claim</PHeading>
            <p className="text-sm">Confirm the worker has stopped and this exact claim is lost. No process-status inference is used.</p>
            <dl className="grid gap-static-xs break-all text-sm"><dt>Attempt</dt><dd>{claim.attempt_id}</dd><dt>Claim</dt><dd>{claim.claim_id}</dd></dl>
            {actionFailed && actionError ? <ActionFeedback error={actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={pendingAction !== null} onClick={() => void recover()}>{pendingAction === 'recover' ? 'Recovering...' : 'Confirm lost and recover'}</PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function ExceptionalStateSection({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const { return_context: returned, recovery_attention: recovery } = detail.item
  if (!returned && !recovery) return null
  return (
    <section aria-labelledby="work-attention-heading">
      <PHeading id="work-attention-heading" tag="h3" size="md">Current exception</PHeading>
      <div className="mt-static-sm grid gap-static-md text-sm">
        {returned ? (
          <AttentionItem
            label={`Returned to ${PROGRESS_STAGE_LABELS[returned.target]}`}
            reason={returned.reason}
              retry={returned.target === 'design' ? `Resume /design ${detail.item.card.change_id}.` : undefined}
            evidence={returned.locators.join(', ')}
            sourceBoundary={returned.source_boundary}
          />
        ) : null}
        {recovery ? <AttentionItem label="Recovery attention" reason={recovery.reason} retry={recovery.retry_condition} /> : null}
      </div>
    </section>
  )
}

function CourseChangesSection({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const moves = detail.item.operator_moves
  if (moves.length === 0) return null
  return (
    <section aria-labelledby="work-course-changes-heading">
      <h3 id="work-course-changes-heading" className="text-xs font-semibold uppercase text-contrast-medium">Recorded Change course changes</h3>
      <ol className="mt-static-sm grid list-decimal gap-static-md pl-static-lg text-sm">
        {moves.map((move) => (
          <li key={move.move_id}>
            <strong>{move.outcome_id} moved back to {PROGRESS_STAGE_LABELS[move.destination]}</strong>
            <p className="mt-static-xs">{move.reason}</p>
            <p className="mt-static-xs text-contrast-medium">Reset: {move.invalidated_outcome_ids.join(', ')}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}

function AttentionItem({ label, reason, retry, evidence, sourceBoundary }: {
  label: string
  reason: string
  retry?: string
  evidence?: string
  sourceBoundary?: string | null
}) {
  return <div><strong>{label}</strong><p>{reason}</p>{retry ? <p className="text-contrast-medium">Next: {retry}</p> : null}{evidence ? <p className="text-contrast-medium">Evidence: {evidence}</p> : null}{sourceBoundary ? <p className="text-contrast-medium">Source boundary: {sourceBoundary}</p> : null}</div>
}

const STAGES: WorkItemStage[] = ['design', 'planning', 'implementation', 'completed']

function BackwardMoveSection({ detail, pendingAction, onPreviewBackward, onMoveBackward }: WorkItemDetailProps) {
  const currentStage = detail.item.card.stage
  const available = currentStage ? STAGES.slice(0, STAGES.indexOf(currentStage)) : []
  const [target, setTarget] = useState<WorkItemStage | ''>('')
  const [reason, setReason] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [preview, setPreview] = useState<BackwardMovePreview | null>(null)
  const [previewStale, setPreviewStale] = useState(false)
  const targetIsAvailable = target !== '' && available.includes(target)
  const canMove = targetIsAvailable && Boolean(reason.trim()) && pendingAction === null
  useEffect(() => {
    if (!target || available.includes(target)) return
    setTarget('')
    setPreview(null)
    setConfirmOpen(false)
  }, [currentStage, target])
  useEffect(() => {
    if (!preview || preview.snapshot_version === detail.item.snapshot_version) return
    setPreview(null)
    setConfirmOpen(false)
    setPreviewStale(true)
  }, [detail.item.snapshot_version, preview])
  if (detail.item.card.scope !== 'outcome' || available.length === 0) return null
  const move = async () => {
    if (!target || !preview || preview.snapshot_version !== detail.item.snapshot_version) return
    const error = await onMoveBackward(target, reason.trim(), preview.snapshot_version)
    if (!error) setConfirmOpen(false)
  }
  const review = async () => {
    if (!targetIsAvailable) return
    setPreviewStale(false)
    const next = await onPreviewBackward(target)
    if (!next) return
    setPreview(next)
    setConfirmOpen(true)
  }
  return (
    <details>
      <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Administrative actions</summary>
      <div className="mt-static-md">
      <div className="mt-static-sm flex flex-wrap items-end gap-static-sm">
        <PSelect compact className="w-48" label="Earlier stage" name="backward-stage" value={target} disabled={pendingAction !== null} onChange={(event) => { setTarget(fieldValue(event as FieldValueEvent) as WorkItemStage | ''); setPreview(null); setPreviewStale(false) }}><PSelectOption value="">Select a stage</PSelectOption>{available.map((stage) => <PSelectOption key={stage} value={stage}>{PROGRESS_STAGE_LABELS[stage]}</PSelectOption>)}</PSelect>
        <PInputText compact className="min-w-48 flex-1" name="backward-reason" label="Reason" value={reason} disabled={pendingAction !== null} onChange={(event) => setReason(fieldValue(event as FieldValueEvent))} onInput={(event) => setReason(fieldValue(event as FieldValueEvent))} />
        <PButton className="w-fit" type="button" compact variant="secondary" disabled={!canMove} onClick={() => void review()}>{pendingAction === 'preview' ? 'Preparing preview...' : 'Review backward move'}</PButton>
      </div>
      {previewStale ? <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">The backward-move preview expired because Delivery changed. Review the move again.</p> : null}
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm backward move' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}><PHeading tag="h2" size="lg">Move to {target ? PROGRESS_STAGE_LABELS[target] : ''}</PHeading><p className="text-sm">The following Outcomes will be reset:</p><ul className="grid list-disc gap-static-xs pl-static-lg text-sm">{preview?.invalidated_outcome_ids.map((outcomeId) => <li key={outcomeId}>{outcomeId}</li>)}</ul><p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p><div className="flex flex-wrap justify-end gap-static-xs"><PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton><PButton type="button" disabled={pendingAction !== null} onClick={() => void move()}>{pendingAction === 'move' ? 'Moving...' : 'Confirm backward move'}</PButton></div></ConfirmationContent>
        </PModal>
      ) : null}
      </div>
    </details>
  )
}

function SemanticDetail({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const item = detail.item
  if (item.card.scope !== 'outcome') return null
  return (
    <>
      {item.acceptance.length > 0 ? (
        <details>
          <summary id="work-acceptance-heading" className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Acceptance ({item.acceptance.length})</summary>
          <ol className="mt-static-sm grid list-decimal gap-static-sm pl-static-lg text-sm text-primary">
            {item.acceptance.map((observation) => <li key={observation}>{observation}</li>)}
          </ol>
        </details>
      ) : null}
      {item.tasks.length > 0 ? (
        <details>
          <summary id="work-evidence-heading" className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Delivery task evidence ({item.tasks.length})</summary>
          <div className="mt-static-sm grid gap-static-md">
            {item.tasks.map((task) => (
              <article key={task.task_id} className="border-l-2 border-contrast-low pl-static-sm text-sm text-primary">
                <div className="flex flex-wrap items-start justify-between gap-static-xs"><strong>{task.title}</strong><PTag compact>{TASK_STATUS_LABELS[task.status]}</PTag></div>
                <p className="mt-static-xs">{task.result}</p>
                {task.completed_commit ? <code className="mt-static-xs inline-block bg-canvas px-static-xs py-1 text-xs text-contrast-medium" title={task.completed_commit}>{task.completed_commit.slice(0, 12)}</code> : null}
              </article>
            ))}
          </div>
        </details>
      ) : null}
      {item.dependencies.length > 0 || item.commitments.length > 0 ? (
        <details>
          <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">References</summary>
          <ol className="mt-static-sm grid list-decimal gap-static-md pl-static-lg text-sm text-primary">
            {item.dependencies.map((dependency) => <li key={dependency.outcome_id}><strong className="block text-xs">{dependency.outcome_id}</strong>{dependency.title} · {PROGRESS_STAGE_LABELS[dependency.stage]}</li>)}
            {item.commitments.map((commitment) => <li key={commitment.commitment_id}><strong className="block text-xs">{commitment.commitment_id}</strong>{commitment.statement}</li>)}
          </ol>
        </details>
      ) : null}
      <details>
        <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Technical identity</summary>
        <code className="mt-static-sm block break-all text-xs text-contrast-medium">{item.card.change_id} / {item.card.item_key}</code>
      </details>
    </>
  )
}

const PUBLICATION_PHASE_LABELS: Record<WorkItemPublicationPhase, string> = {
  'finalization-invalidated': 'Finalization invalidated',
  'review-repair': 'Review feedback repair',
  'ready-for-finalization': 'Ready for finalization',
  'checkpoint-pending': 'Checkpoint pending',
  'pull-request-draft': 'Delivery ready state not recorded',
  'awaiting-merge': 'Awaiting merge in GitHub',
  'acceptance-observed': 'Acceptance observed',
  deferred: 'Change deferred',
  abandoned: 'Change abandoned',
}

function IdentityRow({ label, value }: { label: string; value: string | number | null }) {
  if (value === null) return null
  return <><dt className="text-contrast-medium">{label}</dt><dd className="min-w-0 break-all font-mono text-xs">{value}</dd></>
}

function pullRequestUrl(repository: string, number: number): string {
  const repositoryUrl = repository.startsWith('http')
    ? repository.replace(/\/$/, '')
    : `https://github.com/${repository}`
  return `${repositoryUrl}/pull/${number}`
}

function ExternalHeadAdoptionSection(props: WorkItemDetailProps) {
  const action = props.detail.item.card.action
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (
    action.kind !== 'adopt-external-head'
    || !action.attention_id
    || !action.expected_head
    || !action.adopted_head
  ) return null
  const run = async () => {
    const error = await props.onAdoptExternalHeadAfterAcceptanceAttention(
      action.attention_id as string,
      action.expected_head as string,
      action.adopted_head as string,
    )
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="mt-static-md border-l-4 border-warning bg-surface p-static-md" aria-labelledby="external-head-adoption-heading">
      <PHeading id="external-head-adoption-heading" tag="h4" size="sm">Pull request head changed</PHeading>
      <p className="mt-static-xs text-sm">Adopt the exact open pull-request head before re-running finalization and review.</p>
      <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs break-all text-xs">
        <IdentityRow label="Finalized head" value={action.expected_head} />
        <IdentityRow label="Pull request head" value={action.adopted_head} />
      </dl>
      <PButton
        className="mt-static-md"
        type="button"
        compact
        variant="secondary"
        data-testid="acceptance-head-adopt"
        disabled={props.pendingAction !== null}
        onClick={() => { setActionFailed(false); setConfirmOpen(true) }}
      >
        {props.pendingAction === 'acceptance-head-adopt' ? 'Adopting...' : 'Adopt changed PR head'}
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm changed pull-request head adoption' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Confirm changed PR head</PHeading>
            <p className="text-sm">The exact open pull-request head will become the new Change head. Finalization and pull-request readiness will be cleared; run `/finalize-change` again afterward.</p>
            <dl className="grid gap-static-xs break-all text-sm">
              <dt className="font-semibold">Finalized head</dt>
              <dd>{action.expected_head}</dd>
              <dt className="font-semibold">Pull request head</dt>
              <dd>{action.adopted_head}</dd>
            </dl>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === 'acceptance-head-adopt' ? 'Adopting...' : 'Confirm adoption'}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function WorktreeRecoverySection(props: WorkItemDetailProps) {
  const recovery = props.detail.item.publication?.worktree_recovery
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (!recovery) return null
  if (!recovery.eligible || !recovery.recovery_reviewed_head) {
    return recovery.blocked_reason ? (
      <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
        Worktree recovery unavailable: {recovery.blocked_reason.replace(/-/g, ' ')}.
      </p>
    ) : null
  }
  const pendingAction = 'change-worktree-recover'
  const run = async () => {
    const error = await props.onRecoverChangeWorktree(recovery.recovery_reviewed_head as string)
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="mt-static-md border-l-4 border-warning bg-surface p-static-md" aria-labelledby="worktree-recovery-heading">
      <PHeading id="worktree-recovery-heading" tag="h4" size="sm">Missing worktree</PHeading>
      <p className="mt-static-xs text-sm">Delivery can recreate the missing worktree from the exact reviewed Change head.</p>
      <code className="mt-static-sm block break-all text-xs text-contrast-medium">Reviewed head: {recovery.recovery_reviewed_head}</code>
      <PButton className="mt-static-md" type="button" compact variant="secondary" disabled={props.pendingAction !== null} onClick={() => { setActionFailed(false); setConfirmOpen(true) }}>
        {props.pendingAction === pendingAction ? 'Recovering...' : 'Recover missing worktree'}
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm worktree recovery' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Recover missing worktree</PHeading>
            <p className="text-sm">The managed worktree will be recreated at its canonical path. The Change branch and reviewed head will remain unchanged.</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === pendingAction ? 'Recovering...' : 'Confirm worktree recovery'}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function WorktreeCleanupSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  const cleanup = publication?.worktree_cleanup
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (!publication || !cleanup) return null
  const terminal = publication.phase === 'abandoned' || publication.phase === 'acceptance-observed'
  if (!terminal) return null
  const abandonedConflict = publication.phase === 'abandoned' && Boolean(publication.target_sync_conflict)
  if (abandonedConflict) {
    return <AbandonedTargetSyncCleanupSection {...props} />
  }
  if (!cleanup.eligible) {
    return cleanup.blocked_reason ? (
      <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
        Worktree cleanup unavailable: {cleanup.blocked_reason.replace(/-/g, ' ')}.
      </p>
    ) : null
  }
  const completed = publication.phase === 'acceptance-observed'
  const action = completed
    ? cleanup.completion_id ? () => props.onCleanupCompletedChange(cleanup.completion_id as string) : null
    : props.onCleanupAbandonedChange
  if (!action) return null
  const actionName = completed ? 'Clean completed worktree' : 'Clean abandoned worktree'
  const pendingAction = completed ? 'change-cleanup-completed' : 'change-cleanup-abandoned'
  const run = async () => {
    const error = await action()
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="mt-static-md border-l-4 border-warning bg-surface p-static-md" aria-labelledby="worktree-cleanup-heading">
      <PHeading id="worktree-cleanup-heading" tag="h4" size="sm">Retained worktree</PHeading>
      <p className="mt-static-xs text-sm">The terminal Change worktree is clean and ready for removal. Its branch is preserved.</p>
      <PButton className="mt-static-md" type="button" compact variant="secondary" disabled={props.pendingAction !== null} onClick={() => { setActionFailed(false); setConfirmOpen(true) }}>
        {props.pendingAction === pendingAction ? 'Cleaning...' : actionName}
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': `Confirm ${actionName.toLowerCase()}` }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">{actionName}</PHeading>
            <p className="text-sm">The worktree directory will be removed. The Change branch and cleanup receipt will remain.</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === pendingAction ? 'Cleaning...' : `Confirm ${actionName.toLowerCase()}`}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function AbandonedTargetSyncCleanupSection(props: WorkItemDetailProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  const run = async () => {
    const error = await props.onDiscardAbandonedTargetSync()
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="mt-static-md border-l-4 border-danger bg-surface p-static-md" aria-labelledby="abandoned-target-sync-cleanup-heading">
      <PHeading id="abandoned-target-sync-cleanup-heading" tag="h4" size="sm">Abandoned target sync</PHeading>
      <p className="mt-static-xs text-sm">The abandoned Change still contains a preserved target merge. Discard that merge before removing the worktree.</p>
      <PButton className="mt-static-md" type="button" compact variant="secondary" disabled={props.pendingAction !== null} onClick={() => { setActionFailed(false); setConfirmOpen(true) }}>
        {props.pendingAction === 'change-cleanup-abandoned-target-sync' ? 'Discarding and cleaning...' : 'Discard merge and clean worktree'}
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm target merge discard and worktree cleanup' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Discard target merge and clean worktree</PHeading>
            <p className="text-sm">The preserved target merge will be aborted and its worktree directory removed. The abandoned Change branch and receipts will remain.</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === 'change-cleanup-abandoned-target-sync' ? 'Discarding and cleaning...' : 'Confirm discard and cleanup'}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function TargetSyncConflictSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  const conflict = publication?.target_sync_conflict
  const attention = publication?.attention
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (!publication || !conflict) return null
  const canExit = attention?.kind === 'publication-attention'
  const abort = async () => {
    if (!attention) return
    const error = await props.onAbortTargetSync(attention.disposition_id, conflict.target_head, conflict.operation_id)
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="border-l-4 border-danger bg-surface p-static-md" aria-labelledby="target-sync-conflict-heading">
      <PHeading id="target-sync-conflict-heading" tag="h4" size="sm">Target sync conflict</PHeading>
      <p className="mt-static-xs text-sm">The merge is preserved in the Change worktree. Choose an explicit exit after reviewing the conflict.</p>
      {props.detail.item.card.action.command ? (
        <div className="mt-static-md">
          <p className="text-sm">Run the target conflict workflow before submitting the resolved merge.</p>
          <CopyCommand className="mt-static-xs" command={props.detail.item.card.action.command} />
        </div>
      ) : null}
      <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs break-all text-xs">
        <IdentityRow label="Operation" value={conflict.operation_id} />
        <IdentityRow label="Target head" value={conflict.target_head} />
        <IdentityRow label="Reviewed head" value={conflict.change_head_before} />
      </dl>
      {conflict.conflict_paths.length > 0 ? (
        <ul className="mt-static-md list-disc break-all pl-static-md text-sm">
          {conflict.conflict_paths.map((path) => <li key={path}>{path}</li>)}
        </ul>
      ) : <p className="mt-static-md text-sm text-contrast-medium">Git did not report individual conflict paths.</p>}
      {canExit && attention ? (
        <div className="mt-static-md flex flex-wrap gap-static-sm">
          <PButton
            type="button"
            compact
            variant="secondary"
            data-testid="target-sync-conflict-abort"
            disabled={props.pendingAction !== null}
            onClick={() => { setActionFailed(false); setConfirmOpen(true) }}
          >
            {props.pendingAction === 'target-sync-abort' ? 'Aborting...' : 'Abort target sync'}
          </PButton>
          <PButton
            type="button"
            compact
            variant="secondary"
            data-testid="target-sync-conflict-resolve"
            disabled={props.pendingAction !== null}
            onClick={() => void props.onResolveTargetSync(attention.disposition_id, conflict.target_head, conflict.operation_id)}
          >
            {props.pendingAction === 'target-sync-resolve' ? 'Submitting...' : 'Submit resolved merge'}
          </PButton>
        </div>
      ) : <p className="mt-static-md text-sm text-contrast-medium">Waiting for the matching Change attention record.</p>}
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm target sync abort' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Abort target sync</PHeading>
            <p className="text-sm">The preserved target merge will be aborted and the Change will return to its reviewed head. Any target-sync merge state will be discarded.</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void abort()}>
                {props.pendingAction === 'target-sync-abort' ? 'Aborting...' : 'Confirm abort'}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

function TargetSyncSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [actionFailed, setActionFailed] = useState(false)
  if (!publication || publication.attention || ['deferred', 'abandoned', 'acceptance-observed'].includes(publication.phase)) return null
  const run = async () => {
    const error = await props.onSyncTarget()
    setActionFailed(error !== null)
    if (!error) setConfirmOpen(false)
  }
  return (
    <section className="border-t border-contrast-low pt-static-sm" aria-labelledby="target-sync-heading">
      <h4 id="target-sync-heading" className="text-xs font-semibold uppercase text-contrast-medium">Change maintenance</h4>
      <p className="mt-static-xs text-sm text-contrast-medium">Bring the latest integration target into the Change before continuing delivery.</p>
      <PButton
        className="mt-static-sm"
        type="button"
        compact
        variant="secondary"
        disabled={props.pendingAction !== null || props.isObservingPublicationChecks}
        onClick={() => { setActionFailed(false); setConfirmOpen(true) }}
      >
        {props.pendingAction === 'target-sync' ? 'Updating Change...' : 'Merge latest target into Change'}
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm target synchronization' }}>
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Merge latest target into Change</PHeading>
            <p className="text-sm">Delivery will merge the current integration target into the managed Change. This can create a merge commit or conflicts, invalidate finalization, and require a new review.</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === 'target-sync' ? 'Updating Change...' : 'Confirm target update'}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  )
}

const PUBLICATION_CHECK_STATE_LABELS: Record<PublicationCheckBlockingState, string> = {
  blocking: 'Blocking',
  'required-pending': 'Required pending',
  'not-blocking': 'Not blocking',
}

function PublicationCheckItem({ check }: { check: PublicationChecksObservationResponse['checks'][number] }) {
  return (
    <li className="border-l-2 border-contrast-low pl-static-sm" data-testid="publication-check">
      <div className="flex flex-wrap items-start justify-between gap-static-xs">
        <strong className="text-sm">{check.name}</strong>
        <PTag compact>{PUBLICATION_CHECK_STATE_LABELS[check.blocking_state]}</PTag>
      </div>
      <p className="mt-static-xs text-xs text-contrast-medium">
        {check.required ? 'Required' : 'Optional'} · {check.status}
        {check.conclusion ? ` · ${check.conclusion}` : ''}
      </p>
    </li>
  )
}

function PublicationChecksSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  const observable = Boolean(publication
    && (publication.phase === 'pull-request-draft' || publication.phase === 'awaiting-merge')
    && publication.published_head !== null
    && publication.publication_generations.length > 0)
  const draftPublication = observable && publication?.phase === 'pull-request-draft'
  const observation = props.publicationChecks
  const retainsEvidence = observation !== null || props.publicationChecksStale
  if (!observable && !retainsEvidence) return null
  const errorCode = props.publicationChecksError instanceof WorkItemApiError
    ? props.publicationChecksError.code
    : 'ERR_WORK_ITEM_PUBLICATION_CHECKS_OBSERVE'
  const status = props.isObservingPublicationChecks
    ? 'Observing publication checks...'
    : props.publicationChecksStale
      ? 'Previous check results were cleared because the published head changed. Observe again for the current head.'
      : observation
        ? `Checks observed for ${observation.exact_commit}.`
        : draftPublication
          ? null
          : 'No checks observed for this head yet.'
  return (
    <section className="border-l border-contrast-low bg-surface p-static-md" aria-labelledby="publication-checks-heading">
      <div className="flex flex-wrap items-start justify-between gap-static-sm">
          <PHeading id="publication-checks-heading" tag="h4" size="sm">PR CI checks</PHeading>
        {observable ? (
          <PButton
            type="button"
            compact
            variant="secondary"
            data-testid="publication-checks-observe"
            aria-describedby={draftPublication ? 'publication-checks-draft-guidance' : undefined}
            disabled={draftPublication || props.isObservingPublicationChecks || props.pendingAction !== null}
            onClick={draftPublication ? undefined : () => void props.onObservePublicationChecks()}
          >
            {props.isObservingPublicationChecks ? 'Checking CI...' : 'Observe current checks'}
          </PButton>
        ) : null}
      </div>
      {draftPublication ? (
        <p id="publication-checks-draft-guidance" className="mt-static-sm text-sm" role="status" data-testid="publication-checks-draft-guidance">
          You can observe check results here once this pull request is ready for review.
        </p>
      ) : null}
      {status ? <p className="mt-static-sm text-sm" aria-live="polite" role="status" data-testid="publication-checks-status">{status}</p> : null}
      {props.publicationChecksError ? (
        <p className="mt-static-sm flex items-center gap-static-xs border-l-4 border-danger bg-surface p-static-sm text-sm" role="alert">
          <PIcon name="error" size="sm" aria-hidden="true" />
          <strong>{errorCode}</strong>: {props.publicationChecksError.message}
        </p>
      ) : null}
      {observation ? (
        <>
          <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm">
            <dt className="text-contrast-medium">Observed commit</dt>
            <dd className="min-w-0 break-all font-mono text-xs">{observation.exact_commit}</dd>
            <dt className="text-contrast-medium">Evidence recorded</dt>
            <dd className="min-w-0 break-all font-mono text-xs"><time dateTime={observation.observed_at}>{observation.observed_at}</time></dd>
            <dt className="text-contrast-medium">Required blocking checks</dt>
            <dd>{observation.required_failure_count}</dd>
            {observation.rollup_state ? <><dt className="text-contrast-medium">Provider rollup</dt><dd>{observation.rollup_state}</dd></> : null}
          </dl>
          {observation.truncated_count > 0 ? (
            <p className="mt-static-sm border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
              {observation.truncated_count} additional check{observation.truncated_count === 1 ? '' : 's'} not shown.
            </p>
          ) : null}
          <ul className="mt-static-md grid gap-static-sm" aria-label="Publication check results">
            {observation.checks.map((check) => <PublicationCheckItem key={check.check_id} check={check} />)}
          </ul>
        </>
      ) : null}
    </section>
  )
}

function PublicationSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  const [readyConflictConfirmOpen, setReadyConflictConfirmOpen] = useState(false)
  if (!publication) return null
  const finalizationPhase = publication.phase === 'ready-for-finalization' || publication.phase === 'finalization-invalidated'
  const finalizationBlocked = finalizationPhase && publication.ready_for_finalization === false
  const action = props.detail.item.card.action
  const targetSyncAttention = Boolean(
    publication.target_sync_conflict && publication.attention?.kind === 'publication-attention',
  )
  const publicationGenerations = publication.publication_generations ?? []
  const canSupersede = publication.attention?.kind === 'publication-attention'
    && publicationGenerations.length > 0
    && !targetSyncAttention
  const control = action.kind === 'reconcile-checkpoint'
    ? props.onReconcilePublication
    : action.kind === 'mark-ready'
      ? props.onMarkPublicationReady
      : action.kind === 'observe-acceptance'
        ? props.onObserveAcceptance
        : action.kind === 'resolve-attention' && action.attention_id && !targetSyncAttention
          ? () => props.onResolveAttention(action.attention_id as string)
        : action.kind === 'resume-change'
          ? props.onResumeChange
        : null
  const pending = action.kind === 'reconcile-checkpoint'
    ? props.pendingAction === 'publication-reconcile'
    : action.kind === 'mark-ready'
      ? props.pendingAction === 'publication-ready'
      : action.kind === 'observe-acceptance'
        ? props.pendingAction === 'acceptance-observe'
        : action.kind === 'resolve-attention'
          ? props.pendingAction === 'attention-resolve'
          : props.pendingAction === 'change-resume'
  const statusTone = workItemStatus({ ...props.detail.item.card, publication_phase: publication.phase }).tone
  const situationTone = statusTone === 'attention' || statusTone === 'blocked'
    ? 'warning'
    : statusTone === 'active'
      ? 'info'
    : statusTone === 'complete'
      ? 'success'
      : 'neutral'
  const invalidationReason = publication.invalidated_expected_head && publication.invalidated_observed_head
    ? `The Change head moved from ${publication.invalidated_expected_head.slice(0, 12)} to ${publication.invalidated_observed_head.slice(0, 12)}, so the previous finalization no longer matches.`
    : null
  const runControl = () => {
    if (!control) return
    if (action.kind === 'mark-ready' && publication.mergeable === false) {
      setReadyConflictConfirmOpen(true)
      return
    }
    void control()
  }
  const confirmReadyDespiteConflict = () => {
    setReadyConflictConfirmOpen(false)
    if (control) void control()
  }
  return (
    <section className="min-w-0" aria-labelledby="work-publication-heading">
      <SectionCard tone={situationTone} className="border-l-4 p-static-md">
        <PHeading id="work-publication-heading" tag="h3" size="md">{PUBLICATION_PHASE_LABELS[publication.phase]}</PHeading>
        <p className="mt-static-xs text-sm leading-relaxed">{invalidationReason ?? props.detail.item.card.next_step}</p>
        {invalidationReason ? <div className="mt-static-sm grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-sm gap-y-static-xs text-xs"><span className="text-contrast-medium">Expected</span><code>{publication.invalidated_expected_head}</code><span className="text-contrast-medium">Observed</span><code>{publication.invalidated_observed_head}</code></div> : null}
        {invalidationReason ? <p className="mt-static-sm text-sm text-contrast-medium">Next: {props.detail.item.card.next_step}</p> : null}
        {action.command && !finalizationBlocked && !targetSyncAttention ? <CopyCommand command={action.command} className="mt-static-md" /> : null}
        {control && action.label && (!action.command || action.kind === 'mark-ready') ? <PButton className="mt-static-md" type="button" compact disabled={props.pendingAction !== null || props.isObservingPublicationChecks} onClick={runControl}>{pending ? 'Working...' : action.label}</PButton> : null}
      </SectionCard>
      {readyConflictConfirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setReadyConflictConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm making conflicted pull request ready' }}>
          <ConfirmationContent onClose={() => setReadyConflictConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">Make conflicted PR ready?</PHeading>
            <p className="text-sm">GitHub reports conflicts with the integration target. Making the pull request ready will not resolve them, and reviewers will still be unable to merge it.</p>
            {action.command ? <p className="text-sm">Recommended next step: <CopyCommand command={action.command} /></p> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setReadyConflictConfirmOpen(false)}>Keep PR in draft</PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={confirmReadyDespiteConflict}>Make PR ready anyway</PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
      {finalizationBlocked ? (
        <section className="mt-static-md border-l-4 border-warning bg-surface p-static-sm" role="status" data-testid="finalization-readiness">
          <PHeading tag="h4" size="sm">Finalization unavailable</PHeading>
          <p className="mt-static-xs text-sm">Delivery cannot finalize the current Change yet.</p>
          {(publication.readiness_diagnostics ?? []).length > 0 ? (
            <ul className="mt-static-xs list-disc pl-static-md text-sm">
              {(publication.readiness_diagnostics ?? []).map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)}
            </ul>
          ) : null}
          <p className="mt-static-xs text-sm text-contrast-medium">Resolve the condition, then run `/finalize-change` again.</p>
        </section>
      ) : null}
      <TargetSyncConflictSection {...props} />
      {publication.attention ? (
        <div className="mt-static-md border-l-4 border-warning bg-surface p-static-sm" role="alert">
          <PHeading tag="h4" size="sm">Change attention</PHeading>
          <p className="mt-static-xs text-sm">{publication.attention.kind === 'publication-attention' ? 'Publication evidence needs reconciliation.' : 'Acceptance evidence needs reconciliation.'}</p>
          <ul className="mt-static-xs list-disc pl-static-md text-sm">
            {publication.attention.diagnostics.map((diagnostic) => <li key={diagnostic}>{diagnostic}</li>)}
          </ul>
          <p className="mt-static-xs break-all font-mono text-xs">Disposition: {publication.attention.disposition_id}</p>
        </div>
      ) : null}
      <ExternalHeadAdoptionSection {...props} />
      <details className="mt-static-md border-t border-contrast-low pt-static-sm">
        <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus">Publication evidence</summary>
        <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm">
        <IdentityRow label="Repository" value={publication.repository} />
        {publication.repository && publication.pull_request_number ? (
          <>
            <dt className="text-contrast-medium">Pull request</dt>
            <dd className="min-w-0 break-all text-xs">
              <a className="font-medium text-primary underline decoration-contrast-low underline-offset-2 hover:decoration-primary" href={pullRequestUrl(publication.repository, publication.pull_request_number)} target="_blank" rel="noreferrer">
                {publication.repository} #{publication.pull_request_number}
              </a>
            </dd>
          </>
        ) : <IdentityRow label="Pull request" value={publication.pull_request_number} />}
        <IdentityRow label="Finalized head" value={publication.finalized_head} />
        <IdentityRow label="Published head" value={publication.published_head} />
        <IdentityRow label="Pull request head" value={publication.pull_request_head} />
        <IdentityRow label="Accepted merge commit" value={publication.accepted_merge_commit} />
        <IdentityRow label="Expected head" value={publication.invalidated_expected_head} />
        <IdentityRow label="Observed head" value={publication.invalidated_observed_head} />
        <IdentityRow label="Merged at" value={publication.merged_at} />
        <IdentityRow label="Target head" value={publication.target_sync?.target_head ?? null} />
        <IdentityRow label="Target-sync merge result" value={publication.target_sync?.merged_head ?? null} />
      </dl>
      {publication.target_sync ? (
        <p className="mt-static-sm text-xs text-contrast-medium">
          Last target sync: {publication.target_sync.target_branch}
          {publication.target_sync.merge_commit ? ' (merge commit)' : ' (fast-forward)'}
        </p>
      ) : null}
      {publicationGenerations.length > 0 ? (
        <div className="mt-static-md" data-testid="publication-history">
          <PHeading tag="h4" size="sm">Publication history</PHeading>
          <ol className="mt-static-xs grid gap-static-xs text-xs">
            {publicationGenerations.map((generation, index) => (
              <li key={`${generation.node_id}-${generation.head_sha}`} className="break-all">
                Generation {index + 1}: {generation.repository} #{generation.number} / {generation.head_sha}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {publication.phase === 'checkpoint-pending' && ((publication.pending_checkpoint_attempt_count ?? 0) > 0
        || publication.pending_checkpoint_error_code
        || publication.pending_checkpoint_head
        || publication.pending_checkpoint_triggers.length > 0) ? (
        <div className={`mt-static-sm border-l-2 p-static-sm text-sm ${publication.pending_checkpoint_error_code || (publication.pending_checkpoint_attempt_count ?? 0) > 0 ? 'border-warning bg-surface' : 'border-info bg-info-low'}`} data-testid="checkpoint-diagnostics" role={publication.pending_checkpoint_error_code ? 'alert' : 'status'}>
          <p><strong>Checkpoint recovery</strong></p>
          {(publication.pending_checkpoint_attempt_count ?? 0) > 0 ? <p className="mt-static-xs">{publication.pending_checkpoint_attempt_count} attempt{publication.pending_checkpoint_attempt_count === 1 ? '' : 's'} recorded</p> : null}
          {publication.pending_checkpoint_head ? <p className="mt-static-xs break-all text-xs text-contrast-medium">Pending head: <code>{publication.pending_checkpoint_head}</code></p> : null}
          {publication.pending_checkpoint_triggers.length > 0 ? <p className="mt-static-xs break-words text-xs text-contrast-medium">Triggered by: {Array.from(new Set(publication.pending_checkpoint_triggers)).join(', ')}</p> : null}
          {publication.pending_checkpoint_last_attempted_at ? <p className="mt-static-xs text-xs text-contrast-medium">Last attempt: <time dateTime={publication.pending_checkpoint_last_attempted_at}>{publication.pending_checkpoint_last_attempted_at}</time></p> : null}
          {publication.pending_checkpoint_error_code ? <p className="mt-static-xs break-words"><strong>{publication.pending_checkpoint_error_code}</strong>{publication.pending_checkpoint_error_detail ? `: ${publication.pending_checkpoint_error_detail}` : ''}</p> : null}
        </div>
      ) : null}
      </details>
      <PublicationChecksSection {...props} />
      {canSupersede ? (
        <PButton
          className="mt-static-md"
          type="button"
          compact
          variant="secondary"
          data-testid="publication-supersede"
          disabled={props.pendingAction !== null || props.isObservingPublicationChecks}
          onClick={() => void props.onSupersedePublication()}
        >
          {props.pendingAction === 'publication-supersede' ? 'Superseding...' : 'Supersede publication'}
        </PButton>
      ) : null}
      <TargetSyncSection {...props} />
      <WorktreeRecoverySection {...props} />
      <WorktreeCleanupSection {...props} />
    </section>
  )
}

function ActionFeedback({ error, result }: { error: Error | null; result: string | null }) {
  if (error) {
    const code = error instanceof WorkItemApiError ? error.code : 'ERR_DELIVERY_CONTROL'
    const waiting = code === 'ERR_DELIVERY_ACCEPTANCE_WAITING'
    return <p className={`flex items-center gap-static-xs border-l-4 ${waiting ? 'border-warning' : 'border-danger'} bg-surface p-static-sm text-sm`} role={waiting ? 'status' : 'alert'}><PIcon name={waiting ? 'warning' : 'error'} size="sm" aria-hidden="true" /><strong>{code}</strong>: {error.message}</p>
  }
  return result ? <p className="border-l-4 border-success bg-surface p-static-sm text-sm" role="status">{result}</p> : null
}

export default function WorkItemDetail(props: WorkItemDetailProps) {
  const { card } = props.detail.item
  return (
    <div className="min-w-0" aria-labelledby="work-detail-heading" data-testid="work-item-detail">
      <div className="grid gap-static-lg">
        <div>
          <DetailHeader detail={props.detail} />
          <p className="mt-static-md max-w-[72ch] text-base leading-relaxed">{props.detail.item.promise}</p>
          <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md py-static-xs text-sm">
            <dt className="text-contrast-medium">Progress</dt><dd>{card.progress.label}</dd>
          </dl>
        </div>
        <ActionFeedback error={props.actionError} result={props.actionResult} />
        <BlockSection {...props} />
        <RequestsSection {...props} />
        <PublicationSection {...props} />
        <CourseChangesSection detail={props.detail} />
        <SemanticDetail detail={props.detail} />
        <ClaimSection {...props} />
        <ExceptionalStateSection detail={props.detail} />
        <BackwardMoveSection {...props} />
        <ChangeDispositionSection {...props} />
      </div>
    </div>
  )
}
