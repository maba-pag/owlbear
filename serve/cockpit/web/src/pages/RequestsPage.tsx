import { useEffect, useMemo, useRef, useState } from 'react'
import { PButton, PHeading, PIcon, PTag } from '@porsche-design-system/components-react'
import { useNavigate, useSearchParams } from 'react-router'
import NativeRequestResolver from '../components/NativeRequestResolver'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'
import { useNativeRequest, useNativeRequests } from '../hooks/useNativeResources'
import type { NativeStoredRequest } from '../api/native'

type RequestFilter = 'pending' | 'resolved' | 'all'

function RequestCard({
  stored,
  active,
  onSelect,
}: {
  stored: NativeStoredRequest
  active: boolean
  onSelect: () => void
}) {
  const request = stored.request
  return (
    <button
      type="button"
      data-request-id={request.request_id}
      className={[
        'w-full min-w-0 border-l-4 p-static-md text-left',
        active ? 'border-primary bg-surface' : 'border-contrast-low bg-canvas hover:bg-surface',
      ].join(' ')}
      onClick={onSelect}
    >
      <span className="flex min-w-0 items-center justify-between gap-static-sm">
        <strong className="truncate">{request.title}</strong>
        <PTag compact>{stored.resolution ? 'Resolved' : 'Pending'}</PTag>
      </span>
      <span className="mt-static-xs block text-xs text-contrast-medium">{request.kind} · {request.target_node_id ?? 'change-level'}</span>
      <span className="mt-static-xs line-clamp-2 block text-sm">{request.summary}</span>
    </button>
  )
}

export default function RequestsPage() {
  const { selectedSummary } = useNativeChangeSelection()
  const changeId = selectedSummary?.state === 'loaded' ? selectedSummary.change_id : null
  const requests = useNativeRequests(changeId)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<RequestFilter>('pending')
  const selectedRequestId = searchParams.get('request')
  const selectedRequest = useNativeRequest(changeId ?? '', selectedRequestId)
  const returnRequestIdRef = useRef<string | null>(null)

  const visible = useMemo(
    () => requests.items.filter((stored) => {
      if (filter === 'all') return true
      return filter === 'resolved' ? stored.resolution !== null : stored.resolution === null
    }),
    [filter, requests.items],
  )

  useEffect(() => {
    const requestId = returnRequestIdRef.current
    if (!requestId || selectedRequestId !== null) return
    returnRequestIdRef.current = null
    requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(`[data-request-id="${requestId}"]`)?.focus()
    })
  }, [selectedRequestId])

  const selectRequest = (requestId: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('request', requestId)
    setSearchParams(next)
  }
  const returnToList = () => {
    if (selectedRequestId) returnRequestIdRef.current = selectedRequestId
    const next = new URLSearchParams(searchParams)
    next.delete('request')
    setSearchParams(next)
  }

  return (
    <main className="h-full min-h-0 overflow-y-auto bg-canvas" data-testid="requests-page">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-static-lg px-static-md py-static-lg md:px-static-xl">
        <header className="flex flex-wrap items-end justify-between gap-static-md border-b border-contrast-low pb-static-lg">
          <div>
            <p className="mb-static-xs text-sm font-semibold text-contrast-medium">Change and job coordination</p>
            <PHeading tag="h1" size="xl">Requests</PHeading>
          </div>
          <div className="flex flex-wrap gap-static-xs" aria-label="Request status filter">
            {(['pending', 'resolved', 'all'] as const).map((item) => (
              <PButton
                key={item}
                type="button"
                compact
                variant={filter === item ? 'primary' : 'secondary'}
                onClick={() => setFilter(item)}
              >{item[0].toUpperCase() + item.slice(1)}</PButton>
            ))}
          </div>
        </header>

        {!changeId ? (
          <div className="flex items-center gap-static-sm" role="status"><PIcon name="warning" aria-hidden="true" />Select a valid change to inspect requests.</div>
        ) : null}
        {requests.isLoading && requests.items.length === 0 ? <p role="status">Loading requests...</p> : null}
        {requests.error ? (
          <div className="flex items-center gap-static-sm border-l-4 border-danger p-static-md" role="alert">
            <span className="min-w-0 flex-1">Requests are unavailable. {requests.error.message}</span>
            <PButton type="button" variant="secondary" onClick={requests.retry}>Retry requests</PButton>
          </div>
        ) : null}

        <div className="grid min-h-0 gap-static-lg lg:grid-cols-[minmax(18rem,0.8fr)_minmax(0,1.2fr)]">
          <section aria-label="Request list" className="flex min-w-0 flex-col gap-static-sm">
            {visible.map((stored) => (
              <RequestCard
                key={stored.request.request_id}
                stored={stored}
                active={selectedRequestId === stored.request.request_id}
                onSelect={() => selectRequest(stored.request.request_id)}
              />
            ))}
            {visible.length === 0 && !requests.isLoading ? <p className="text-sm text-contrast-medium">No {filter} requests.</p> : null}
            {requests.nextCursor ? <PButton type="button" variant="secondary" onClick={requests.loadMore}>Load more</PButton> : null}
          </section>

          <section aria-label="Request detail" className="min-w-0 border-l-4 border-info pl-static-md" data-testid="request-detail">
            {selectedRequest.isLoading ? <p role="status">Loading request detail...</p> : null}
            {selectedRequest.error ? (
              <div role="alert">
                Request detail is unavailable. {selectedRequest.error.message}
                <PButton type="button" variant="secondary" onClick={selectedRequest.retry}>Retry request</PButton>
              </div>
            ) : null}
            {selectedRequest.data ? (
              <article>
                <div className="flex flex-wrap items-start justify-between gap-static-sm">
                  <div>
                    <span className="text-xs font-semibold uppercase text-contrast-medium">{selectedRequest.data.request.request_id}</span>
                    <PHeading tag="h2" size="lg">{selectedRequest.data.request.title}</PHeading>
                  </div>
                  <PTag compact>{selectedRequest.data.resolution ? 'Resolved' : 'Pending'}</PTag>
                </div>
                <p className="mt-static-sm text-sm">{selectedRequest.data.request.summary}</p>
                <div className="mt-static-sm whitespace-pre-wrap text-sm">{selectedRequest.data.request.body}</div>
                <dl className="mt-static-md grid gap-static-xs text-xs sm:grid-cols-2">
                  <div><dt className="font-semibold">Change</dt><dd>{selectedRequest.data.request.change_id}</dd></div>
                  <div><dt className="font-semibold">Node</dt><dd>{selectedRequest.data.request.target_node_id ?? 'Change-level'}</dd></div>
                  <div><dt className="font-semibold">Jobs</dt><dd>{selectedRequest.data.request.job_ids.map((id) => `#${id}`).join(', ') || 'None'}</dd></div>
                  <div><dt className="font-semibold">Agent</dt><dd>{selectedRequest.data.request.agent}</dd></div>
                </dl>
                <div className="mt-static-md flex flex-wrap gap-static-xs">
                  {selectedRequest.data.request.target_node_id ? (
                    <PButton
                      type="button"
                      compact
                      variant="secondary"
                      onClick={() => navigate(`/?change=${encodeURIComponent(selectedRequest.data!.request.change_id)}&node=${encodeURIComponent(selectedRequest.data!.request.target_node_id!)}`)}
                    >Open node</PButton>
                  ) : null}
                  {selectedRequest.data.request.job_ids.map((jobId) => (
                    <PButton
                      key={jobId}
                      type="button"
                      compact
                      variant="secondary"
                      onClick={() => navigate(`/delivery?change=${encodeURIComponent(selectedRequest.data!.request.change_id)}&job=${jobId}`)}
                    >Open job #{jobId}</PButton>
                  ))}
                </div>
                <NativeRequestResolver
                  key={selectedRequest.data.request.request_id}
                  stored={selectedRequest.data}
                  onResolved={() => {
                    selectedRequest.retry()
                    requests.retry()
                  }}
                  onReturn={returnToList}
                />
              </article>
            ) : selectedRequestId ? null : <p className="text-sm text-contrast-medium">Choose a request to inspect its complete context.</p>}
          </section>
        </div>
      </div>
    </main>
  )
}
