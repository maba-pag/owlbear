import { useState, useEffect, type CSSProperties } from 'react'
import { type Session } from './HistorySubtab'

export interface ActivityTabProps {
  onSelectTask?: (taskId: number, subtab?: string) => void
}

type FilterType = 'all' | 'active' | 'blocked' | 'stuck' | 'released'

function rowStyleForState(state: string): CSSProperties {
  if (state === 'blocked' || state === 'rejected') {
    return {
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-error)',
      backgroundColor: 'var(--pds-theme-light-notification-error-soft)',
    }
  }

  if (state === 'stuck') {
    return {
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-warning)',
      backgroundColor: 'var(--pds-theme-light-notification-warning-soft)',
    }
  }

  return {
    cursor: 'pointer',
    borderLeft: '4px solid var(--pds-theme-light-contrast-low)',
  }
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

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch('/api/sessions?filter=all', { method: 'GET' })
        if (res.ok) {
          const data = (await res.json()) as { sessions: Session[] }
          setSessions(data.sessions)
        }
      } catch {
        // ignore
      }
    })()
  }, [])

  const displayed = applyFilter(sessions, filter)

  return (
    <div>
      <div>
        <button data-testid="filter-active" onClick={() => setFilter('active')}>
          Active
        </button>
        <button data-testid="filter-all" onClick={() => setFilter('all')}>
          All
        </button>
        <button data-testid="filter-blocked" onClick={() => setFilter('blocked')}>
          Blocked
        </button>
        <button data-testid="filter-stuck" onClick={() => setFilter('stuck')}>
          Stuck
        </button>
        <button data-testid="filter-released" onClick={() => setFilter('released')}>
          Released
        </button>
      </div>
      <div>
        {displayed.map((s, i) => (
          <div
            key={i}
            data-testid="session-row"
            data-state={s.state}
            onClick={() => onSelectTask?.(s.task_id, 'history')}
            style={rowStyleForState(s.state)}
          >
            <span data-testid="session-agent">{s.agent}</span>
            <span data-testid="session-task">{s.task_id}</span>
            <span data-testid="session-state">{s.state}</span>
            <span data-testid="session-duration">{s.duration ?? '\u2014'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
