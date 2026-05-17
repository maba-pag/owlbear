import './SessionRows.css'

export interface Session {
  task_id: number | null
  state: string
  agent: string | null
  started_at: string
  duration: number | null
  outcome: string | null
}

export interface HistorySubtabProps {
  sessions: Session[]
  onSelectTask?: (taskId: number, subtab?: string) => void
}

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

export default function HistorySubtab({ sessions, onSelectTask }: HistorySubtabProps) {
  function navigateToTask(taskId: number | null): void {
    if (taskId !== null) {
      onSelectTask?.(taskId, 'history')
    }
  }

  return (
    <div data-testid="history-view">
      {sessions.map((s, i) => (
        <div
          key={i}
          data-testid="history-session-row"
          data-state={s.state}
          role="button"
          tabIndex={0}
          style={{ cursor: 'pointer' }}
          onClick={() => navigateToTask(s.task_id)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              navigateToTask(s.task_id)
            }
          }}
        >
          <span data-testid="session-agent">{s.agent ?? 'unknown agent'}</span>
          <span data-testid="session-duration">{formatDuration(s.duration)}</span>
          <span data-testid="session-outcome">{s.outcome}</span>
        </div>
      ))}
    </div>
  )
}
