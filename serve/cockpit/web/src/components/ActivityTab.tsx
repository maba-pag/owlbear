import { useState, useEffect, useRef } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import { type Session } from './HistorySubtab'
import { rowStyleForState } from '../utils/styles'
import { usePollingFetch } from '../hooks/usePollingFetch'
import { useSSEEvent } from '../hooks/EventSourceProvider'

export interface ActivityTabProps {
  onSelectTask?: (taskId: number, subtab?: string) => void
}

type FilterType = 'all' | 'active' | 'blocked' | 'stuck' | 'released'

function formatDuration(duration: number | null): string {
  if (duration === null || Number.isNaN(duration)) {
    return '\u2014'
  }
  if (!Number.isInteger(duration)) {
    return String(duration)
  }
  if (duration < 60) {
    return `${Math.max(0, Math.floor(duration))}s`
  }
  if (duration < 3600) {
    return `${Math.floor(duration / 60)}m`
  }
  const hours = Math.floor(duration / 3600)
  const minutes = Math.floor((duration % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function applyFilter(sessions: Session[], filter: FilterType): Session[] {
  switch (filter) {
    case 'all':
      return sessions
    case 'active':
      return sessions.filter((s) => s.state === 'running' || s.state === 'stuck')
    case 'blocked':
      return sessions.filter((s) => s.state === 'blocked' || s.state === 'rejected')
    case 'stuck':
      return sessions.filter((s) => s.state === 'stuck')
    case 'released':
      return sessions.filter((s) => s.state === 'released')
  }
}

export default function ActivityTab({ onSelectTask }: ActivityTabProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [filter, setFilter] = useState<FilterType>('active')
  const [error, setError] = useState<string | null>(null)
  const lastObservedMtimeRef = useRef<number | null>(null)
  const { status: sseStatus, mtime } = useSSEEvent('activity-changed')

  const { refetch } = usePollingFetch<{ sessions: Session[] }>('/api/sessions?filter=all', {
    intervalMs: 120_000,
    paused: sseStatus === 'open',
    onSuccess: (data) => {
      setError(null)
      setSessions(Array.isArray(data.sessions) ? data.sessions : [])
    },
    onError: (caught) => {
      setSessions([])
      setError(caught.message)
    },
  })

  const refetchRef = useRef(refetch)
  useEffect(() => {
    refetchRef.current = refetch
  }, [refetch])

  useEffect(() => {
    if (sseStatus === 'open' && mtime !== null && lastObservedMtimeRef.current !== mtime) {
      refetchRef.current()
    }
    lastObservedMtimeRef.current = mtime
  }, [mtime, sseStatus])

  const displayed = applyFilter(sessions, filter)

  function isFilterActive(name: FilterType): boolean {
    return filter === name
  }

  function navigateToTask(taskId: number | null): void {
    if (taskId !== null) {
      onSelectTask?.(taskId, 'history')
    }
  }

  return (
    <div>
      <div>
        <PButton
          data-testid="filter-active"
          variant="secondary"
          aria-pressed={isFilterActive('active') ? 'true' : 'false'}
          onClick={() => setFilter('active')}
        >
          Active
        </PButton>
        <PButton
          data-testid="filter-all"
          variant="secondary"
          aria-pressed={isFilterActive('all') ? 'true' : 'false'}
          onClick={() => setFilter('all')}
        >
          All
        </PButton>
        <PButton
          data-testid="filter-blocked"
          variant="secondary"
          aria-pressed={isFilterActive('blocked') ? 'true' : 'false'}
          onClick={() => setFilter('blocked')}
        >
          Blocked
        </PButton>
        <PButton
          data-testid="filter-stuck"
          variant="secondary"
          aria-pressed={isFilterActive('stuck') ? 'true' : 'false'}
          onClick={() => setFilter('stuck')}
        >
          Stuck
        </PButton>
        <PButton
          data-testid="filter-released"
          variant="secondary"
          aria-pressed={isFilterActive('released') ? 'true' : 'false'}
          onClick={() => setFilter('released')}
        >
          Released
        </PButton>
      </div>
      <div>
        {error !== null ? <div data-testid="activity-error">{error}</div> : null}
        {error === null && displayed.length === 0 ? (
          <div data-testid="activity-empty">No sessions for this filter.</div>
        ) : null}
        {displayed.map((s, i) => (
          <div
            key={i}
            data-testid="session-row"
            data-state={s.state}
            role="button"
            tabIndex={0}
            onClick={() => navigateToTask(s.task_id)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                navigateToTask(s.task_id)
              }
            }}
            style={rowStyleForState(s.state)}
          >
            <span data-testid="session-agent">{s.agent ?? 'unknown agent'}</span>
            <span data-testid="session-task">{s.task_id ?? 'unassigned'}</span>
            <span data-testid="session-state">{s.state}</span>
            <span data-testid="session-duration">{formatDuration(s.duration)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

