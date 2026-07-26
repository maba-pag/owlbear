import { useMemo, useState } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'
import { useNativeActivity } from '../hooks/useNativeResources'
import type { NativeActivityEntry } from '../api/native'

function jobId(entry: NativeActivityEntry): number | null {
  return typeof entry.job_id === 'number' ? entry.job_id : null
}

function currentEntries(entries: NativeActivityEntry[]): NativeActivityEntry[] {
  const latestByJob = new Map<number, NativeActivityEntry>()
  const changeLevel: NativeActivityEntry[] = []
  for (const entry of entries) {
    const id = jobId(entry)
    if (id === null) changeLevel.push(entry)
    else latestByJob.set(id, entry)
  }
  return [...changeLevel, ...latestByJob.values()].sort((left, right) => left.timestamp.localeCompare(right.timestamp))
}

function summary(entry: NativeActivityEntry): string {
  if (entry.attempt) return `${entry.attempt.actor_id} · ${entry.attempt.process_id}`
  if (entry.finding) return entry.finding.finding_id
  if (entry.receipt) return entry.receipt.receipt_id
  if (entry.request) return entry.request.request.title
  return entry.identity
}

export default function ActivityPage() {
  const { selectedSummary } = useNativeChangeSelection()
  const changeId = selectedSummary?.state === 'loaded' ? selectedSummary.change_id : null
  const activity = useNativeActivity(changeId)
  const [mode, setMode] = useState<'current' | 'full'>('current')
  const visible = useMemo(
    () => mode === 'current' ? currentEntries(activity.items) : activity.items,
    [activity.items, mode],
  )

  return (
    <main className="min-w-0 flex-1 overflow-x-hidden" data-testid="activity-page">
      <div className="mx-auto w-full max-w-[1440px] px-static-md py-static-lg md:px-static-xl">
        <header className="flex flex-wrap items-end justify-between gap-static-md border-b border-contrast-low pb-static-md">
          <div>
            <p className="text-xs font-semibold uppercase text-contrast-medium">Immutable runtime history</p>
            <h1 className="mt-static-xs text-3xl font-semibold">Activity</h1>
          </div>
          <div aria-label="Activity history mode" className="flex gap-static-xs">
            <PButton type="button" compact variant={mode === 'current' ? 'primary' : 'secondary'} onClick={() => setMode('current')}>Current</PButton>
            <PButton type="button" compact variant={mode === 'full' ? 'primary' : 'secondary'} onClick={() => setMode('full')}>Full history</PButton>
          </div>
        </header>

        {!changeId ? <p className="mt-static-lg text-sm">Select a valid change to inspect native activity.</p> : null}
        {activity.error ? (
          <div className="mt-static-lg flex items-center gap-static-sm" role="alert">
            <span>Activity is unavailable. {activity.error.message}</span>
            <PButton type="button" compact variant="secondary" onClick={activity.retry}>Retry</PButton>
          </div>
        ) : null}
        <ol className="mt-static-lg divide-y divide-contrast-low" aria-label="Native activity">
          {visible.map((entry) => (
            <li key={entry.identity} className="grid min-w-0 gap-static-xs py-static-md sm:grid-cols-[10rem_8rem_minmax(0,1fr)]" data-activity-id={entry.identity}>
              <time className="text-xs text-contrast-medium">{entry.timestamp}</time>
              <div className="text-sm font-semibold">{entry.kind}</div>
              <div className="min-w-0 break-words text-sm">
                {jobId(entry) === null ? 'Change' : `Job #${jobId(entry)}`} · {summary(entry)}
              </div>
            </li>
          ))}
        </ol>
        {!activity.isLoading && visible.length === 0 && changeId ? <p className="mt-static-lg text-sm">No native activity.</p> : null}
        {mode === 'full' && activity.nextCursor ? (
          <PButton type="button" variant="secondary" loading={activity.isLoadingMore} onClick={activity.loadMore}>Load more history</PButton>
        ) : null}
      </div>
    </main>
  )
}
