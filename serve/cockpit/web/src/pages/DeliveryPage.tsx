import { useState } from 'react'
import { PButton, PHeading, PIcon, PTextarea } from '@porsche-design-system/components-react'
import { useSearchParams } from 'react-router'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'
import { useNativeJob, useNativeJobs, useNativeRequest } from '../hooks/useNativeResources'
import DeliveryJobBoard from '../components/DeliveryJobBoard'
import { NativeApiError, resolveNativeRequest, type NativeStoredRequest } from '../api/native'

type TextValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function textValue(event: TextValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function LinkedRequestResolver({
  changeId,
  stored,
  retryData,
}: {
  changeId: string
  stored: NativeStoredRequest
  retryData: () => void
}) {
  const request = stored.request
  const [response, setResponse] = useState('')
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null)
  const [resolutionDigest, setResolutionDigest] = useState(request.delivery_digest)
  const [conflict, setConflict] = useState<NativeApiError | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const resolve = async () => {
    setSubmitting(true)
    setConflict(null)
    try {
      await resolveNativeRequest(changeId, request.request_id, {
        delivery_digest: resolutionDigest,
        disposition: 'local',
        resolved_at: new Date().toISOString(),
        resolved_by: 'cockpit-user',
        selected_option_id: selectedOptionId,
        response: response.trim() || null,
        rationale: 'Resolved from Delivery.',
      })
      retryData()
    } catch (caught) {
      const nextConflict = caught instanceof NativeApiError
        ? caught
        : new NativeApiError(0, { code: 'ERR_NATIVE_REQUEST', detail: 'Resolution failed' })
      setConflict(nextConflict)
      if (nextConflict.currentDeliveryDigest) {
        setResolutionDigest(nextConflict.currentDeliveryDigest)
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (stored.resolution) {
    return <p className="mt-static-xs text-xs">Resolved</p>
  }

  return (
    <div className="mt-static-md border-t border-contrast-low pt-static-md" data-testid="linked-request-resolver">
      {request.kind === 'decision' ? (
        <div className="flex flex-wrap gap-static-xs">
          {(request.options ?? []).map((option) => (
            <PButton
              key={option.option_id}
              type="button"
              compact
              variant={selectedOptionId === option.option_id ? 'primary' : 'secondary'}
              onClick={() => setSelectedOptionId(option.option_id)}
            >{option.label}</PButton>
          ))}
        </div>
      ) : (
        <PTextarea
          name={`request-response-${request.request_id}`}
          label="Response"
          value={response}
          onChange={(event) => setResponse(textValue(event as TextValueEvent))}
        />
      )}
      <PButton
        type="button"
        className="mt-static-sm"
        disabled={submitting || (request.kind === 'decision' ? selectedOptionId === null : response.trim() === '')}
        onClick={() => void resolve()}
      >Complete request</PButton>
      {conflict ? (
        <div className="mt-static-sm border-l-4 border-warning pl-static-sm text-xs" role="alert">
          <strong>{conflict.code}</strong> {conflict.detail}
          <p className="break-all">Current digest: {conflict.currentDeliveryDigest ?? 'unavailable'}</p>
          <p>Submitted: {selectedOptionId ?? response}</p>
          <PButton type="button" compact variant="secondary" onClick={() => void resolve()}>Retry resolution</PButton>
        </div>
      ) : null}
    </div>
  )
}

export default function DeliveryPage() {
  const { selectedChangeId, selectedSummary } = useNativeChangeSelection()
  const [searchParams] = useSearchParams()
  const selectedJobId = searchParams.get('job')
  const selectedRequestId = searchParams.get('request')
  const jobs = useNativeJobs(selectedSummary?.state === 'loaded' ? selectedSummary.change_id : null)
  const jobDetail = useNativeJob(
    selectedSummary?.state === 'loaded' ? selectedSummary.change_id : '',
    selectedJobId && Number.isInteger(Number(selectedJobId)) ? Number(selectedJobId) : null,
  )
  const requestDetail = useNativeRequest(
    selectedSummary?.state === 'loaded' ? selectedSummary.change_id : '',
    selectedRequestId,
  )

  return (
    <main className="h-full min-h-0 overflow-y-auto bg-canvas" data-testid="delivery-page">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-static-lg px-static-md py-static-lg md:px-static-xl">
        <header className="border-b border-contrast-low pb-static-lg">
          <p className="mb-static-xs text-sm font-semibold text-contrast-medium">Current change execution</p>
          <PHeading tag="h1" size="xl">Delivery</PHeading>
        </header>
        <section tabIndex={0} aria-labelledby="delivery-change-heading">
          <PHeading id="delivery-change-heading" tag="h2" size="lg">{selectedChangeId ?? 'No change selected'}</PHeading>
          <p className="mt-static-sm max-w-[60rem] text-sm leading-relaxed text-contrast-medium">
            {selectedSummary?.state === 'invalid'
              ? 'Delivery is unavailable until the selected specification is valid.'
              : 'Plans, jobs, requests, and evidence for this change appear here.'}
          </p>
          {selectedSummary?.state === 'invalid' ? (
            <div className="mt-static-md flex items-center gap-static-sm border-l-4 border-warning bg-surface p-static-md" role="status">
              <PIcon name="warning" aria-hidden="true" />
              <span>Invalid authority prevents delivery.</span>
            </div>
          ) : null}
          {selectedJobId && jobDetail.data ? (
            <article className="mt-static-md border-l-4 border-primary pl-static-md" data-testid="selected-job-detail">
              <strong>Job #{jobDetail.data.job.job_id}: {jobDetail.data.title}</strong>
              <p className="mt-static-xs text-sm">{jobDetail.data.outcome}</p>
              <p className="mt-static-xs break-all text-xs">Token: {jobDetail.data.token}</p>
              <p className="mt-static-xs text-xs">{jobDetail.data.job.kind} · {jobDetail.data.job.disposition} · {jobDetail.data.proof}</p>
            </article>
          ) : null}
          {selectedJobId && jobDetail.error ? (
            <div className="mt-static-md flex items-center gap-static-sm" role="alert">
              <span>Job detail is unavailable. {jobDetail.error.message}</span>
              <button type="button" onClick={jobDetail.retry}>Retry job</button>
            </div>
          ) : null}
          {selectedRequestId && requestDetail.data ? (
            <article className="mt-static-md border-l-4 border-info pl-static-md" data-testid="selected-request-detail">
              <strong>{requestDetail.data.request.title}</strong>
              <p className="mt-static-xs text-sm">{requestDetail.data.request.summary}</p>
              <p className="mt-static-xs whitespace-pre-wrap text-sm">{requestDetail.data.request.body}</p>
              <p className="mt-static-xs text-xs">{requestDetail.data.resolution ? 'Resolved' : 'Pending resolution'}</p>
              <LinkedRequestResolver
                changeId={requestDetail.data.request.change_id}
                stored={requestDetail.data}
                retryData={() => {
                  requestDetail.retry()
                  jobs.retry()
                }}
              />
            </article>
          ) : null}
          {selectedRequestId && requestDetail.error ? (
            <div className="mt-static-md flex items-center gap-static-sm" role="alert">
              <span>Request detail is unavailable. {requestDetail.error.message}</span>
              <button type="button" onClick={requestDetail.retry}>Retry request</button>
            </div>
          ) : null}
        </section>
        {selectedSummary?.state === 'loaded' ? (
          <DeliveryJobBoard
            changeId={selectedSummary.change_id}
            jobs={jobs.items}
            isLoading={jobs.isLoading}
            error={jobs.error}
            retry={jobs.retry}
          />
        ) : null}
      </div>
    </main>
  )
}
