import { useState, useEffect } from 'react'

export interface ActivityTabProps {
  onSelectTask?: (taskId: number, subtab?: string) => void
}

interface Session {
  task_id: number
  state: string
  agent: string
  started_at: string
  duration: number | null
  outcome: string | null
}

type FilterType = 'all' | 'failed' | 'released'

function applyFilter(sessions: Session[], filter: FilterType): Session[] {
  switch (filter) {
    case 'all':
      return sessions
    case 'failed':
      return sessions.filter((s) => s.outcome === 'fail' || s.outcome === 'rejected')
    case 'released':
      return sessions.filter((s) => s.state === 'released')
  }
}

export default function ActivityTab({ onSelectTask }: ActivityTabProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [filter, setFilter] = useState<FilterType>('all')

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch('/api/sessions', { method: 'GET' })
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
        <button data-testid="filter-all" onClick={() => setFilter('all')}>
          All
        </button>
        <button data-testid="filter-failed" onClick={() => setFilter('failed')}>
          Failed
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
            onClick={() => onSelectTask?.(s.task_id, 'history')}
            style={{ cursor: 'pointer' }}
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
