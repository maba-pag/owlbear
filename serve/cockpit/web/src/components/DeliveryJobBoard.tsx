import { useEffect, useMemo, useState } from 'react'
import { PButton, PHeading, PIcon, PInputNumber, PTag } from '@porsche-design-system/components-react'
import { useNavigate, useSearchParams } from 'react-router'
import {
  NativeApiError,
  cancelNativeJob,
  releaseNativeJob,
  setNativeJobPriority,
  type NativeJobProjection,
  type StoredNativeJob,
} from '../api/native'

interface DeliveryJobBoardProps {
  changeId: string
  jobs: NativeJobProjection[]
  isLoading: boolean
  error: Error | null
  retry: () => void
}

type Intent =
  | { kind: 'priority'; value: number; timestamp: string }
  | { kind: 'cancel'; timestamp: string }
  | { kind: 'release'; timestamp: string }

const GROUPS = ['plan', 'build', 'accept', 'audit'] as const

type NumberEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function numberValue(event: NumberEvent): number | null {
  const value = event.detail?.value ?? event.target?.value
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(number) ? number : null
}

function claimAge(timestamp: string | undefined): string {
  if (!timestamp) {
    return 'Unclaimed'
  }
  const milliseconds = Date.now() - Date.parse(timestamp)
  if (!Number.isFinite(milliseconds) || milliseconds < 0) {
    return 'Claimed'
  }
  const minutes = Math.floor(milliseconds / 60_000)
  return minutes < 60 ? `${minutes}m claimed` : `${Math.floor(minutes / 60)}h claimed`
}

function storedJob(value: unknown): StoredNativeJob | null {
  if (typeof value !== 'object' || value === null) return null
  const record = value as Record<string, unknown>
  return typeof record.token === 'string' && typeof record.job === 'object' && record.job !== null
    ? (record as unknown as StoredNativeJob)
    : null
}

function JobCard({ changeId, job, onRefresh }: { changeId: string; job: NativeJobProjection; onRefresh: () => void }) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [priority, setPriority] = useState(job.priority)
  const [intent, setIntent] = useState<Intent | null>(null)
  const [conflict, setConflict] = useState<NativeApiError | null>(null)
  const [currentAuthority, setCurrentAuthority] = useState<StoredNativeJob | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isPending = job.disposition === 'pending'
  const isClaimed = job.claim_id !== null
  const activeAttempt = isClaimed && job.attempt?.kind === 'started' && job.attempt.claim_id === job.claim_id
    ? job.attempt
    : null
  const unresolvedRequests = job.requests.filter((request) => request.resolution === null)
  const hasRequests = unresolvedRequests.length > 0
  const digestCurrent = job.validity === null || job.validity.code === 'CURRENT'
  const releaseAuthorityChanged =
    intent?.kind === 'release' &&
    (conflict?.code === 'ERR_RELEASE_NON_OWNER' ||
      (currentAuthority !== null &&
        (currentAuthority.job.claim_id !== activeAttempt?.claim_id ||
          currentAuthority.job.attempt_id !== activeAttempt?.attempt_id)))

  useEffect(() => setPriority(job.priority), [job.priority])

  const submit = async (nextIntent: Intent) => {
    setIntent(nextIntent)
    setConflict(null)
    setIsSubmitting(true)
    try {
      if (nextIntent.kind === 'priority') {
        await setNativeJobPriority(changeId, {
          job_id: job.job_id,
          delivery_digest: currentAuthority?.job.delivery_digest ?? job.delivery_digest,
          expected_token: currentAuthority?.token ?? job.token,
          priority: nextIntent.value,
          updated_at: nextIntent.timestamp,
        })
      } else if (nextIntent.kind === 'cancel') {
        await cancelNativeJob(changeId, {
          job_id: job.job_id,
          delivery_digest: currentAuthority?.job.delivery_digest ?? job.delivery_digest,
          expected_token: currentAuthority?.token ?? job.token,
          cancelled_at: nextIntent.timestamp,
        })
      } else if (activeAttempt) {
        const currentJob = currentAuthority?.job
        await releaseNativeJob(changeId, {
          job_id: job.job_id,
          delivery_digest: currentJob?.delivery_digest ?? job.delivery_digest,
          attempt_id: currentJob?.attempt_id ?? activeAttempt.attempt_id,
          claim_id: currentJob?.claim_id ?? activeAttempt.claim_id,
          actor_id: activeAttempt.actor_id,
          process_id: activeAttempt.process_id,
          released_at: nextIntent.timestamp,
        })
      }
      onRefresh()
      setCurrentAuthority(null)
    } catch (caught) {
      const nextConflict = caught instanceof NativeApiError
        ? caught
        : new NativeApiError(0, { code: 'ERR_NATIVE_REQUEST', detail: 'Request failed' })
      setConflict(nextConflict)
      setCurrentAuthority(storedJob(nextConflict.current))
    } finally {
      setIsSubmitting(false)
    }
  }

  const inspect = () => {
    const next = new URLSearchParams(searchParams)
    next.set('job', String(job.job_id))
    setSearchParams(next)
  }

  return (
    <article className="min-w-0 border-l-4 border-contrast-low bg-surface p-static-md" data-job-id={job.job_id}>
      <div className="flex min-w-0 items-start justify-between gap-static-sm">
        <div className="min-w-0">
          <span className="text-xs font-semibold uppercase text-contrast-medium">#{job.job_id} · {job.target_node_id}</span>
          <h3 className="truncate font-semibold">{job.title}</h3>
        </div>
        <PTag compact>{job.priority}</PTag>
      </div>
      <p className="mt-static-xs line-clamp-2 text-xs text-contrast-medium">{job.outcome}</p>
      <dl className="mt-static-sm grid gap-1 text-xs">
        <div className="flex justify-between gap-static-sm"><dt>Change</dt><dd className="truncate">{job.change_id}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Status</dt><dd className="inline-flex items-center gap-1"><PIcon name={job.disposition === 'pending' ? 'clock' : 'check'} size="xs" aria-hidden="true" />{job.disposition}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Readiness</dt><dd>{job.dependency_ready ? 'Ready' : 'Waiting'}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Claim</dt><dd>{claimAge(activeAttempt?.timestamp)}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Requests</dt><dd>{unresolvedRequests.length || 'None'}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Block</dt><dd>{job.block_id ?? 'None'}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Digest</dt><dd>{digestCurrent ? 'Current' : job.validity?.code}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Attempt</dt><dd className="truncate">{job.attempt ? `${job.attempt.kind} ${job.attempt.attempt_id}` : 'None'}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Finding</dt><dd className="truncate">{job.finding?.finding_id ?? 'None'}</dd></div>
        <div className="flex justify-between gap-static-sm"><dt>Receipt</dt><dd>{job.receipt?.receipt_id ?? 'None'}</dd></div>
      </dl>

      <div className="mt-static-md flex flex-wrap items-end gap-static-xs" aria-label={`Commands for job ${job.job_id}`}>
        <label className="w-24 text-xs font-semibold">
          Priority
          <PInputNumber
            name={`priority-${job.job_id}`}
            value={priority}
            min={0}
            disabled={!isPending || isClaimed}
            onChange={(event) => {
              const next = numberValue(event as NumberEvent)
              if (next !== null) setPriority(next)
            }}
          />
        </label>
        <PButton
          type="button"
          compact
          disabled={!isPending || isClaimed || isSubmitting}
          onClick={() => void submit({ kind: 'priority', value: priority, timestamp: new Date().toISOString() })}
        >Prioritize</PButton>
        <PButton
          type="button"
          compact
          variant="secondary"
          disabled={!isPending || isClaimed || isSubmitting}
          onClick={() => void submit({ kind: 'cancel', timestamp: new Date().toISOString() })}
        >Cancel</PButton>
        <PButton
          type="button"
          compact
          variant="secondary"
          disabled={!activeAttempt || isSubmitting || releaseAuthorityChanged}
          onClick={() => void submit({ kind: 'release', timestamp: new Date().toISOString() })}
        >Release claim</PButton>
        <PButton type="button" compact variant="secondary" onClick={inspect}>Inspect</PButton>
        {hasRequests ? (
          <PButton
            type="button"
            compact
            variant="secondary"
            onClick={() => navigate(`/delivery?change=${encodeURIComponent(changeId)}&request=${encodeURIComponent(unresolvedRequests[0].request.request_id)}`)}
          >Resolve request</PButton>
        ) : null}
      </div>

      {conflict ? (
        <div className="mt-static-md border-l-4 border-warning bg-canvas p-static-sm text-xs" role="alert" data-testid={`job-conflict-${job.job_id}`}>
          <div className="flex items-center gap-static-xs font-semibold"><PIcon name="warning" aria-hidden="true" />{conflict.code}</div>
          <p className="mt-1">{conflict.detail}</p>
          <p className="mt-1 break-all">Current token: {conflict.token ?? 'unavailable'}</p>
          <p className="mt-1 break-all">Current digest: {conflict.currentDeliveryDigest ?? 'unavailable'}</p>
          {currentAuthority ? (
            <p className="mt-1">Current job: priority {currentAuthority.job.priority}, {currentAuthority.job.disposition}, {currentAuthority.job.claim_id ? 'claimed' : 'unclaimed'}</p>
          ) : null}
          {intent ? <p className="mt-1">Submitted: {intent.kind}{intent.kind === 'priority' ? ` ${intent.value}` : ''}</p> : null}
          {releaseAuthorityChanged ? (
            <PButton type="button" compact variant="secondary" onClick={onRefresh}>Refresh authority</PButton>
          ) : (
            <PButton
              type="button"
              compact
              variant="secondary"
              onClick={() => intent && void submit({ ...intent, timestamp: new Date().toISOString() })}
            >Retry</PButton>
          )}
        </div>
      ) : null}
    </article>
  )
}

export default function DeliveryJobBoard({ changeId, jobs, isLoading, error, retry }: DeliveryJobBoardProps) {
  const grouped = useMemo(
    () => Object.fromEntries(GROUPS.map((kind) => [kind, jobs.filter((job) => job.kind === kind)])) as Record<(typeof GROUPS)[number], NativeJobProjection[]>,
    [jobs],
  )

  return (
    <section aria-labelledby="job-board-heading" className="border-t border-contrast-low pt-static-lg" data-testid="delivery-job-board">
      <div className="flex items-center justify-between gap-static-sm">
        <PHeading id="job-board-heading" tag="h2" size="lg">Jobs</PHeading>
        {isLoading ? <span role="status" className="text-sm">Refreshing jobs...</span> : null}
      </div>
      {error ? (
        <div className="mt-static-md flex items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">Jobs are unavailable. {error.message}</span>
          <PButton type="button" variant="secondary" onClick={retry}>Retry jobs</PButton>
        </div>
      ) : null}
      <div className="mt-static-md grid min-w-0 gap-static-md lg:grid-cols-4">
        {GROUPS.map((kind) => (
          <section key={kind} aria-labelledby={`job-group-${kind}`} className="min-w-0">
            <div className="mb-static-sm flex items-center justify-between border-b border-contrast-low pb-static-xs">
              <h3 id={`job-group-${kind}`} className="font-semibold capitalize">{kind}</h3>
              <span className="text-xs text-contrast-medium">{grouped[kind].length}</span>
            </div>
            <div className="flex flex-col gap-static-sm">
              {grouped[kind].map((job) => <JobCard key={job.job_id} changeId={changeId} job={job} onRefresh={retry} />)}
              {grouped[kind].length === 0 ? <p className="text-xs text-contrast-medium">No {kind} jobs.</p> : null}
            </div>
          </section>
        ))}
      </div>
    </section>
  )
}
