import { useState, useEffect } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import { type Session } from './HistorySubtab'
import { rowStyleForState } from '../utils/styles'

export interface ActivityTabProps {
  onSelectTask?: (taskId: number, subtab?: string) => void
}

type FilterType = 'all' | 'active' | 'blocked' | 'stuck' | 'released'

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
        <PButton data-testid="filter-active" variant="tertiary" onClick={() => setFilter('active')}>
          Active
        </PButton>
        <PButton data-testid="filter-all" variant="tertiary" onClick={() => setFilter('all')}>
          All
        </PButton>
        <PButton data-testid="filter-blocked" variant="tertiary" onClick={() => setFilter('blocked')}>
          Blocked
        </PButton>
        <PButton data-testid="filter-stuck" variant="tertiary" onClick={() => setFilter('stuck')}>
          Stuck
        </PButton>
        <PButton data-testid="filter-released" variant="tertiary" onClick={() => setFilter('released')}>
          Released
        </PButton>
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
