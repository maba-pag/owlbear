import { useState } from 'react'
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
  type WorkItemPublicationPhase,
  type WorkItemStage,
  type DeliveryWorkerRole,
} from '../api/workItems'
import {
  PROGRESS_STAGE_LABELS,
  workItemStatusLabel,
} from './workItemPresentation'
import CopyCommand from './CopyCommand'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

interface WorkItemDetailProps {
  detail: WorkItemDetailResponse
  pendingAction: string | null
  actionError: Error | null
  actionResult: string | null
  onAnswerRequest: (requestId: string, resolution: DeliveryRequestResolution) => Promise<void>
  onClearBlock: (blockId: string, note: string, locators: string[]) => Promise<void>
  onRecoverClaim: (attemptId: string, claimId: string) => Promise<void>
  onPreviewBackward: (target: WorkItemStage) => Promise<BackwardMovePreview | null>
  onMoveBackward: (target: WorkItemStage, reason: string, snapshotVersion: string) => Promise<void>
  onReconcilePublication: () => Promise<void>
  onMarkPublicationReady: () => Promise<void>
  onObserveAcceptance: () => Promise<void>
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
        <PTag compact>{workItemStatusLabel(card)}</PTag>
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

function ClaimSection({ detail, pendingAction, onRecoverClaim }: WorkItemDetailProps) {
  const claim = detail.item.active_claim
  const [confirmOpen, setConfirmOpen] = useState(false)
  if (!claim) return null
  const recover = async () => {
    await onRecoverClaim(claim.attempt_id, claim.claim_id)
    setConfirmOpen(false)
  }
  return (
    <section aria-labelledby="work-claim-heading">
      <PHeading id="work-claim-heading" tag="h3" size="md">Active claim</PHeading>
      <dl className="mt-static-sm grid gap-static-xs text-sm">
        <div className="flex justify-between gap-static-sm"><dt>Role</dt><dd>{WORKER_ROLE_LABELS[claim.worker_role]}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Started</dt><dd>{elapsedAge(claim.started_at)} ago</dd></div>
        {claim.task_id ? <div className="flex justify-between gap-static-sm"><dt>Task</dt><dd>{claim.task_id}</dd></div> : null}
      </dl>
      <PButton className="mt-static-md" type="button" compact variant="secondary" disabled={pendingAction !== null} onClick={() => setConfirmOpen(true)}>
        Recover confirmed-lost claim
      </PButton>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm lost claim' }}>
          <div className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary">
            <PHeading tag="h2" size="lg">Confirm lost claim</PHeading>
            <p className="text-sm">Confirm the worker has stopped and this exact claim is lost. No process-status inference is used.</p>
            <dl className="grid gap-static-xs break-all text-sm"><dt>Attempt</dt><dd>{claim.attempt_id}</dd><dt>Claim</dt><dd>{claim.claim_id}</dd></dl>
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
              <PButton type="button" disabled={pendingAction !== null} onClick={() => void recover()}>{pendingAction === 'recover' ? 'Recovering...' : 'Confirm lost and recover'}</PButton>
            </div>
          </div>
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
  const canMove = Boolean(target && reason.trim()) && pendingAction === null
  if (detail.item.card.scope !== 'outcome' || available.length === 0) return null
  const move = async () => {
    if (!target || !preview) return
    await onMoveBackward(target, reason.trim(), preview.snapshot_version)
    setConfirmOpen(false)
  }
  const review = async () => {
    if (!target) return
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
        <PSelect compact className="w-48" label="Earlier stage" name="backward-stage" value={target} disabled={pendingAction !== null} onChange={(event) => { setTarget(fieldValue(event as FieldValueEvent) as WorkItemStage | ''); setPreview(null) }}><PSelectOption value="">Select a stage</PSelectOption>{available.map((stage) => <PSelectOption key={stage} value={stage}>{PROGRESS_STAGE_LABELS[stage]}</PSelectOption>)}</PSelect>
        <PInputText compact className="min-w-48 flex-1" name="backward-reason" label="Reason" value={reason} disabled={pendingAction !== null} onChange={(event) => setReason(fieldValue(event as FieldValueEvent))} onInput={(event) => setReason(fieldValue(event as FieldValueEvent))} />
        <PButton className="w-fit" type="button" compact variant="secondary" disabled={!canMove} onClick={() => void review()}>{pendingAction === 'preview' ? 'Preparing preview...' : 'Review backward move'}</PButton>
      </div>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm backward move' }}>
          <div className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary"><PHeading tag="h2" size="lg">Move to {target ? PROGRESS_STAGE_LABELS[target] : ''}</PHeading><p className="text-sm">The following Outcomes will be reset:</p><ul className="grid list-disc gap-static-xs pl-static-lg text-sm">{preview?.invalidated_outcome_ids.map((outcomeId) => <li key={outcomeId}>{outcomeId}</li>)}</ul><p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p><div className="flex flex-wrap justify-end gap-static-xs"><PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton><PButton type="button" disabled={pendingAction !== null} onClick={() => void move()}>{pendingAction === 'move' ? 'Moving...' : 'Confirm backward move'}</PButton></div></div>
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
  'ready-for-finalization': 'Ready for finalization',
  'checkpoint-pending': 'Checkpoint pending',
  'pull-request-draft': 'Pull request draft',
  'awaiting-merge': 'Awaiting merge in GitHub',
  'acceptance-observed': 'Acceptance observed',
}

function IdentityRow({ label, value }: { label: string; value: string | number | null }) {
  if (value === null) return null
  return <><dt className="text-contrast-medium">{label}</dt><dd className="min-w-0 break-all font-mono text-xs">{value}</dd></>
}

function PublicationSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication
  if (!publication) return null
  const action = props.detail.item.card.action
  const control = action.kind === 'reconcile-checkpoint'
    ? props.onReconcilePublication
    : action.kind === 'mark-ready'
      ? props.onMarkPublicationReady
      : action.kind === 'observe-acceptance'
        ? props.onObserveAcceptance
        : null
  const pending = action.kind === 'reconcile-checkpoint'
    ? props.pendingAction === 'publication-reconcile'
    : action.kind === 'mark-ready'
      ? props.pendingAction === 'publication-ready'
      : props.pendingAction === 'acceptance-observe'
  return (
    <section className="min-w-0 border-l border-contrast-low bg-surface p-static-md" aria-labelledby="work-publication-heading">
      <PHeading id="work-publication-heading" tag="h3" size="md">{PUBLICATION_PHASE_LABELS[publication.phase]}</PHeading>
      <p className="mt-static-xs text-sm leading-relaxed">{props.detail.item.card.next_step}</p>
      <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm">
        <IdentityRow label="Repository" value={publication.repository} />
        <IdentityRow label="Pull request" value={publication.pull_request_number} />
        <IdentityRow label="Finalized head" value={publication.finalized_head} />
        <IdentityRow label="Published head" value={publication.published_head} />
        <IdentityRow label="Pull request head" value={publication.pull_request_head} />
        <IdentityRow label="Accepted merge commit" value={publication.accepted_merge_commit} />
        <IdentityRow label="Expected head" value={publication.invalidated_expected_head} />
        <IdentityRow label="Observed head" value={publication.invalidated_observed_head} />
        <IdentityRow label="Merged at" value={publication.merged_at} />
      </dl>
      {publication.pending_checkpoint_triggers.length > 0 ? <p className="mt-static-sm text-xs text-contrast-medium">Checkpoint triggers: {publication.pending_checkpoint_triggers.join(', ')}</p> : null}
      {action.command ? <CopyCommand command={action.command} className="mt-static-md" /> : null}
      {!action.command && control && action.label ? <PButton className="mt-static-md" type="button" compact disabled={props.pendingAction !== null} onClick={() => void control()}>{pending ? 'Working...' : action.label}</PButton> : null}
    </section>
  )
}

function ActionFeedback({ error, result }: { error: Error | null; result: string | null }) {
  if (error) {
    const code = error instanceof WorkItemApiError ? error.code : 'ERR_DELIVERY_CONTROL'
    return <p className="flex items-center gap-static-xs border-l-4 border-danger bg-surface p-static-sm text-sm" role="alert"><PIcon name="error" size="sm" aria-hidden="true" /><strong>{code}</strong>: {error.message}</p>
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
      </div>
    </div>
  )
}
