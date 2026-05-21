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
    <div data-testid="history-view" className="grid gap-static-xs">
      {sessions.length === 0 ? (
        <p data-testid="history-empty-state" className="m-0 rounded-lg border border-contrast-low bg-surface p-static-sm text-sm text-primary">
          No history yet
        </p>
      ) : null}
      {sessions.map((s, i) => (
        <div
          key={i}
          data-testid="history-session-row"
          data-state={s.state}
          role="button"
          aria-disabled={s.task_id === null ? 'true' : undefined}
          aria-label={s.task_id !== null ? `Open task #${s.task_id} history` : 'Session without linked task'}
          tabIndex={0}
          className="history-session-row grid min-h-12 gap-1 rounded-md border border-contrast-low bg-surface p-static-xs text-sm text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"
          onClick={() => navigateToTask(s.task_id)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              navigateToTask(s.task_id)
            }
          }}
        >
          <span data-testid="session-agent" className="min-w-0 truncate font-semibold">{s.agent ?? 'unknown agent'}</span>
          <span data-testid="session-duration" className="rounded-full bg-canvas px-static-xs py-1 text-xs font-semibold">{formatDuration(s.duration)}</span>
          <span data-testid="session-outcome" className="text-xs font-semibold text-primary">{s.outcome ?? s.state}</span>
        </div>
      ))}
    </div>
  )
}
