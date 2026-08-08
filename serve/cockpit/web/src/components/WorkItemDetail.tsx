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
  type WorkItemStage,
} from '../api/workItems'

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
  onRetryIntegration: () => Promise<void>
}

const STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  assembly: 'Assembly',
  completed: 'Complete',
}

function DetailHeader({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const { card } = detail.item
  return (
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
      <div className="min-w-0">
        <span className="text-xs font-semibold text-contrast-medium">{card.change_id} · {card.scope === 'outcome' ? card.work_item_id : 'Change Integration'}</span>
        <PHeading id="work-detail-heading" tag="h2" size="lg">{card.title}</PHeading>
      </div>
      <div className="flex flex-wrap gap-static-xs">
        <PTag compact>{STAGE_LABELS[card.stage]}</PTag>
        {card.needs !== 'none' ? <PTag compact>{card.needs === 'you' ? 'Needs you' : card.needs === 'dependency' ? 'Waiting on dependency' : 'Repair required'}</PTag> : null}
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
        <label className="grid gap-static-xs text-sm font-semibold">
          Decision
          <PSelect
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
        </label>
      ) : null}
      <PInputText
        name={`request-${request.request_id}-answer`}
        label={request.kind === 'decision' ? 'Additional response' : 'Action response'}
        value={responseText}
        disabled={pending}
        onChange={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
        onInput={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
      />
      <PButton type="button" compact disabled={!canSubmit} onClick={() => void answer()}>
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
    <section className="border-t border-contrast-low pt-static-md" aria-labelledby="work-requests-heading">
      <PHeading id="work-requests-heading" tag="h3" size="md">Requests</PHeading>
      <div className="mt-static-sm grid gap-static-md">
        {requests.map((request) => (
          <article key={request.request_id} className="border-l-2 border-info pl-static-sm">
            <div className="flex flex-wrap items-center justify-between gap-static-xs">
              <strong className="text-sm">{request.summary}</strong>
              <PTag compact>{request.kind}</PTag>
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
          <PInputText name="block-note" label="Operator note" value={note} disabled={pendingAction !== null} onChange={(event) => setNote(fieldValue(event as FieldValueEvent))} onInput={(event) => setNote(fieldValue(event as FieldValueEvent))} />
          <PInputText name="block-locator" label="Evidence locator" value={locator} disabled={pendingAction !== null} onChange={(event) => setLocator(fieldValue(event as FieldValueEvent))} onInput={(event) => setLocator(fieldValue(event as FieldValueEvent))} />
          <PButton type="button" compact disabled={!canClear} onClick={() => void onClearBlock(block.block_id, note.trim(), [locator.trim()])}>
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
    <section className="border-t border-contrast-low pt-static-md" aria-labelledby="work-claim-heading">
      <PHeading id="work-claim-heading" tag="h3" size="md">Active claim</PHeading>
      <dl className="mt-static-sm grid gap-static-xs text-sm">
        <div className="flex justify-between gap-static-sm"><dt>Role</dt><dd>{claim.worker_role}</dd></div>
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
    <section className="border-t border-contrast-low pt-static-md" aria-labelledby="work-attention-heading">
      <PHeading id="work-attention-heading" tag="h3" size="md">Current exception</PHeading>
      <div className="mt-static-sm grid gap-static-md text-sm">
        {returned ? <AttentionItem label={`Returned to ${returned.target}`} reason={returned.reason} retry={returned.locators.join(', ')} /> : null}
        {recovery ? <AttentionItem label="Recovery attention" reason={recovery.reason} retry={recovery.retry_condition} /> : null}
      </div>
    </section>
  )
}

function AttentionItem({ label, reason, retry }: { label: string; reason: string; retry: string }) {
  return <div><strong>{label}</strong><p>{reason}</p><p className="text-contrast-medium">Next: {retry}</p></div>
}

const STAGES: WorkItemStage[] = ['design', 'planning', 'implementation', 'assembly', 'completed']

function BackwardMoveSection({ detail, pendingAction, onPreviewBackward, onMoveBackward }: WorkItemDetailProps) {
  const available = STAGES.slice(0, STAGES.indexOf(detail.item.card.stage))
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
    <details className="border-t border-contrast-low pt-static-md">
      <summary className="cursor-pointer text-sm font-semibold">Administrative actions</summary>
      <section className="mt-static-md" aria-labelledby="work-move-heading">
      <PHeading id="work-move-heading" tag="h3" size="md">Move backward</PHeading>
      <div className="mt-static-sm grid gap-static-sm">
        <label className="grid gap-static-xs text-sm font-semibold">Earlier stage<PSelect name="backward-stage" value={target} disabled={pendingAction !== null} onChange={(event) => { setTarget(fieldValue(event as FieldValueEvent) as WorkItemStage | ''); setPreview(null) }}><PSelectOption value="">Select a stage</PSelectOption>{available.map((stage) => <PSelectOption key={stage} value={stage}>{stage}</PSelectOption>)}</PSelect></label>
        <PInputText name="backward-reason" label="Reason" value={reason} disabled={pendingAction !== null} onChange={(event) => setReason(fieldValue(event as FieldValueEvent))} onInput={(event) => setReason(fieldValue(event as FieldValueEvent))} />
        <PButton type="button" compact variant="secondary" disabled={!canMove} onClick={() => void review()}>{pendingAction === 'preview' ? 'Preparing preview...' : 'Review backward move'}</PButton>
      </div>
      {confirmOpen ? (
        <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm backward move' }}>
          <div className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary"><PHeading tag="h2" size="lg">Move to {target}</PHeading><p className="text-sm">The following Outcomes will be reset:</p><ul className="grid list-disc gap-static-xs pl-static-lg text-sm">{preview?.invalidated_outcome_ids.map((outcomeId) => <li key={outcomeId}>{outcomeId}</li>)}</ul><p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p><div className="flex flex-wrap justify-end gap-static-xs"><PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton><PButton type="button" disabled={pendingAction !== null} onClick={() => void move()}>{pendingAction === 'move' ? 'Moving...' : 'Confirm backward move'}</PButton></div></div>
        </PModal>
      ) : null}
      </section>
    </details>
  )
}

function SemanticDetail({ detail }: Pick<WorkItemDetailProps, 'detail'>) {
  const item = detail.item
  if (item.card.scope !== 'outcome') return null
  return (
    <>
      {item.acceptance.length > 0 ? (
        <section aria-labelledby="work-acceptance-heading">
          <PHeading id="work-acceptance-heading" tag="h3" size="md">Acceptance</PHeading>
          <ul className="mt-static-sm grid list-disc gap-static-xs pl-static-lg text-sm">
            {item.acceptance.map((observation) => <li key={observation}>{observation}</li>)}
          </ul>
        </section>
      ) : null}
      {item.tasks.length > 0 ? (
        <section className="border-t border-contrast-low pt-static-md" aria-labelledby="work-evidence-heading">
          <PHeading id="work-evidence-heading" tag="h3" size="md">Task evidence</PHeading>
          <div className="mt-static-sm grid gap-static-md">
            {item.tasks.map((task) => (
              <article key={task.task_id} className="border-l-2 border-contrast-low pl-static-sm text-sm">
                <div className="flex flex-wrap items-start justify-between gap-static-xs"><strong>{task.title}</strong><PTag compact>{task.status}</PTag></div>
                <p className="mt-static-xs text-contrast-medium">{task.result}</p>
                {task.completed_commit ? <p className="mt-static-xs break-all font-mono text-xs text-contrast-medium">{task.completed_commit}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {item.dependencies.length > 0 || item.commitments.length > 0 ? (
        <details className="border-t border-contrast-low pt-static-md">
          <summary className="cursor-pointer text-sm font-semibold">References</summary>
          <div className="mt-static-sm grid gap-static-md text-sm">
            {item.dependencies.map((dependency) => <p key={dependency.outcome_id}><strong>{dependency.outcome_id}</strong> · {dependency.title} · {STAGE_LABELS[dependency.stage]}</p>)}
            {item.commitments.map((commitment) => <p key={commitment.commitment_id}><strong>{commitment.commitment_id}</strong> · {commitment.statement}</p>)}
          </div>
        </details>
      ) : null}
    </>
  )
}

function IntegrationSection({ detail, pendingAction, onRetryIntegration }: WorkItemDetailProps) {
  const integration = detail.item.integration
  if (!integration) return null
  const action = detail.item.card.action
  const canIntegrate = action.kind === 'integrate-change' || action.kind === 'retry-integration'
  return (
    <section className="border-l-4 border-warning bg-surface p-static-md" aria-labelledby="work-integration-heading">
      <PHeading id="work-integration-heading" tag="h3" size="md">{integration.headline}</PHeading>
      <p className="mt-static-xs text-sm leading-relaxed">{integration.explanation}</p>
      {integration.conflicted_paths.length > 0 ? (
        <ul className="mt-static-sm grid list-disc gap-static-xs pl-static-lg font-mono text-xs">
          {integration.conflicted_paths.map((path) => <li key={path}>{path}</li>)}
        </ul>
      ) : null}
      {action.command ? <code className="mt-static-sm block break-all bg-canvas p-static-sm text-xs">{action.command}</code> : null}
      {canIntegrate ? (
        <PButton className="mt-static-md" type="button" compact disabled={pendingAction !== null} onClick={() => void onRetryIntegration()}>
          {pendingAction === 'integration' ? 'Working...' : action.label}
        </PButton>
      ) : null}
      {integration.retry_condition ? <p className="mt-static-sm text-xs text-contrast-medium">Next: {integration.retry_condition}</p> : null}
      {integration.diagnostics.length > 0 ? (
        <details className="mt-static-md border-t border-contrast-low pt-static-sm">
          <summary className="cursor-pointer text-xs font-semibold">Technical evidence</summary>
          <pre className="mt-static-sm max-h-48 overflow-auto whitespace-pre-wrap break-all text-xs text-contrast-medium">{integration.diagnostics.join('\n')}</pre>
        </details>
      ) : null}
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
  return (
    <aside className="min-w-0" aria-labelledby="work-detail-heading" data-testid="work-item-detail">
      <div className="grid gap-static-lg">
        <div><DetailHeader detail={props.detail} /><p className="mt-static-sm text-sm leading-relaxed text-contrast-medium"><strong className="text-primary">Promise:</strong> {props.detail.item.promise}</p></div>
        <ActionFeedback error={props.actionError} result={props.actionResult} />
        <IntegrationSection {...props} />
        <SemanticDetail detail={props.detail} />
        <BlockSection {...props} />
        <RequestsSection {...props} />
        <ClaimSection {...props} />
        <ExceptionalStateSection detail={props.detail} />
        <BackwardMoveSection {...props} />
      </div>
    </aside>
  )
}
