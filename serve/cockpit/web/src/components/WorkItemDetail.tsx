import { useState } from 'react'
import { PButton, PHeading, PIcon, PInputText, PTag } from '@porsche-design-system/components-react'
import type { WorkItemDetailResponse, WorkItemRequestsResponse, WorkItemTraceResponse } from '../api/workItems'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function recordLabel(value: Record<string, unknown>, fallback: string): string {
  for (const key of ['summary', 'title', 'kind', 'request_id', 'identity']) {
    if (typeof value[key] === 'string') return value[key]
  }
  return fallback
}

interface WorkItemDetailProps {
  detail: WorkItemDetailResponse
  requests: WorkItemRequestsResponse | null
  trace: WorkItemTraceResponse | null
  traceOpen: boolean
  traceLoading: boolean
  onOpenTrace: () => void
  onCloseTrace: () => void
  onClose: () => void
  onCreateRequest: (summary: string) => Promise<void>
}

function DetailHeader({ detail, onClose }: { detail: WorkItemDetailResponse; onClose: () => void }) {
  return (
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
      <div className="min-w-0">
        <span className="text-xs font-semibold text-contrast-medium">{detail.card.change_id}</span>
        <PHeading id="work-detail-heading" tag="h2" size="lg">{detail.card.title}</PHeading>
      </div>
      <div className="flex flex-wrap gap-static-xs">
        <PTag compact>{detail.card.stage}</PTag>
        <PTag compact>{detail.card.attention}</PTag>
        <span className="lg:hidden">
          <PButton type="button" compact variant="secondary" onClick={onClose}>Close detail</PButton>
        </span>
      </div>
    </div>
  )
}

function SpecificationSection({ detail }: { detail: WorkItemDetailResponse }) {
  return (
    <section className="mt-static-lg border-t border-contrast-low pt-static-md" aria-labelledby="work-specification-heading">
      <PHeading id="work-specification-heading" tag="h3" size="md">Specification</PHeading>
      <h4 className="mt-static-md text-sm font-semibold">Commitments</h4>
      <ul className="mt-static-xs space-y-static-xs text-sm">
        {detail.commitments.map((commitment) => (
          <li key={commitment.commitment_id} className="border-l-2 border-contrast-low pl-static-sm">
            <strong>{commitment.commitment_id}</strong>: {commitment.statement}
          </li>
        ))}
      </ul>
      <h4 className="mt-static-md text-sm font-semibold">Acceptance</h4>
      <ul className="mt-static-xs list-disc space-y-static-xs pl-static-lg text-sm">
        {detail.acceptance.map((criterion) => <li key={criterion}>{criterion}</li>)}
      </ul>
    </section>
  )
}

function RequestComposer({ onCreateRequest }: Pick<WorkItemDetailProps, 'onCreateRequest'>) {
  const [requestSummary, setRequestSummary] = useState('')
  const [requestError, setRequestError] = useState<Error | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const submitRequest = async () => {
    const summary = requestSummary.trim()
    if (!summary) return
    setIsSubmitting(true)
    setRequestError(null)
    try {
      await onCreateRequest(summary)
      setRequestSummary('')
    } catch (caught) {
      setRequestError(caught instanceof Error ? caught : new Error('Request could not be created'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <div className="mt-static-md grid gap-static-sm">
        <PInputText
          name="work-request-summary"
          label="Request summary"
          value={requestSummary}
          compact
          onChange={(event) => setRequestSummary(fieldValue(event as FieldValueEvent))}
        />
        <PButton type="button" compact disabled={!requestSummary.trim() || isSubmitting} onClick={() => void submitRequest()}>
          Create request
        </PButton>
      </div>
      {requestError ? (
        <p className="mt-static-sm flex items-center gap-static-xs text-sm" role="alert">
          <PIcon name="error" size="sm" aria-hidden="true" />{requestError.message}
        </p>
      ) : null}
    </>
  )
}

function RequestsSection({ requests, onCreateRequest }: Pick<WorkItemDetailProps, 'requests' | 'onCreateRequest'>) {
  return (
    <section className="mt-static-lg border-t border-contrast-low pt-static-md" aria-labelledby="work-requests-heading">
      <div className="flex items-center justify-between gap-static-sm">
        <PHeading id="work-requests-heading" tag="h3" size="md">Requests</PHeading>
        <span className="text-xs text-contrast-medium">{requests?.requests.length ?? 0}</span>
      </div>
      <div className="mt-static-sm space-y-static-xs text-sm">
        {requests?.requests.map((request, index) => (
          <p key={String(request.request_id ?? index)} className="border-l-2 border-info pl-static-sm">
            {recordLabel(request, `Request ${index + 1}`)}
          </p>
        ))}
        {requests?.requests.length === 0 ? <p className="text-contrast-medium">No open requests.</p> : null}
      </div>
      <RequestComposer onCreateRequest={onCreateRequest} />
    </section>
  )
}

function ProgressSection({ detail }: { detail: WorkItemDetailResponse }) {
  return (
    <section className="mt-static-lg border-t border-contrast-low pt-static-md" aria-labelledby="work-progress-heading">
      <PHeading id="work-progress-heading" tag="h3" size="md">Progress</PHeading>
      <dl className="mt-static-sm grid gap-static-xs text-sm">
        <div className="flex justify-between gap-static-sm"><dt>Tasks</dt><dd>{detail.card.reviewed_task_count} / {detail.card.task_count} reviewed</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Next</dt><dd className="text-right">{detail.card.next_action}</dd></div>
      </dl>
    </section>
  )
}

function TraceSection(props: Pick<WorkItemDetailProps, 'trace' | 'traceOpen' | 'traceLoading' | 'onOpenTrace' | 'onCloseTrace'>) {
  const { trace, traceOpen, traceLoading, onOpenTrace, onCloseTrace } = props
  return (
    <section className="mt-static-lg border-t border-contrast-low pt-static-md" aria-labelledby="technical-trace-heading">
      <div className="flex flex-wrap items-center justify-between gap-static-sm">
        <PHeading id="technical-trace-heading" tag="h3" size="md">Technical trace</PHeading>
        <PButton type="button" compact variant="secondary" onClick={traceOpen ? onCloseTrace : onOpenTrace}>
          {traceOpen ? 'Hide trace' : 'Show technical trace'}
        </PButton>
      </div>
      {traceLoading ? <p className="mt-static-sm text-sm" role="status">Loading technical trace...</p> : null}
      {traceOpen && trace ? <TraceColumns trace={trace} /> : null}
    </section>
  )
}

function TraceColumns({ trace }: { trace: WorkItemTraceResponse }) {
  return (
    <div className="mt-static-md grid gap-static-md sm:grid-cols-2" data-testid="work-technical-trace">
      {([['Activity', trace.activity], ['Evidence', trace.evidence]] as const).map(([label, entries]) => (
        <section key={label} aria-labelledby={`work-${label.toLowerCase()}-heading`}>
          <h4 id={`work-${label.toLowerCase()}-heading`} className="font-semibold">{label}</h4>
          <ul className="mt-static-xs space-y-static-xs text-sm">
            {entries.map((entry, index) => <li key={index}>{recordLabel(entry, `${label} ${index + 1}`)}</li>)}
          </ul>
        </section>
      ))}
    </div>
  )
}

export default function WorkItemDetail(props: WorkItemDetailProps) {
  const { detail, requests, onClose, onCreateRequest } = props
  return (
    <aside
      className="fixed inset-x-0 bottom-0 z-30 max-h-[82dvh] min-w-0 overflow-y-auto border-t border-contrast-low bg-canvas p-static-md shadow-lg lg:static lg:z-auto lg:max-h-none lg:overflow-visible lg:border-l lg:border-t-0 lg:p-0 lg:pl-static-lg lg:shadow-none"
      aria-labelledby="work-detail-heading"
      data-testid="work-item-detail"
    >
      <DetailHeader detail={detail} onClose={onClose} />
      <p className="mt-static-sm text-sm leading-relaxed text-contrast-medium">{detail.card.promise}</p>
      <SpecificationSection detail={detail} />
      <RequestsSection requests={requests} onCreateRequest={onCreateRequest} />
      <ProgressSection detail={detail} />
      {detail.semantic_updates.length > 0 ? (
        <section className="mt-static-lg border-t border-contrast-low pt-static-md">
          <PHeading tag="h3" size="md">Updates</PHeading>
          {detail.semantic_updates.map((update) => <p key={update.update_id} className="mt-static-sm text-sm">{update.rationale}</p>)}
        </section>
      ) : null}
      <TraceSection {...props} />
    </aside>
  )
}
