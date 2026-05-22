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
  taskId?: number | null
  createdAt?: string | null
  onSelectTask?: (taskId: number, subtab?: string) => void
}

type HistoryRow = Session & { kind: 'created' | 'session' }

function formatDuration(duration: number | null): string {
  if (duration === null || !Number.isFinite(duration)) {
    return '\u2014'
  }
  const seconds = Math.max(0, Math.floor(duration))
  if (seconds < 60) {
    return `${seconds}s`
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m`
  }
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

function formatTimestamp(value: string): string {
  const parsed = Date.parse(value)
  if (!Number.isFinite(parsed)) {
    return value || 'Time unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(parsed))
}

function buildCreationEvent(taskId: number | null | undefined, createdAt: string | null | undefined): HistoryRow[] {
  if (!createdAt) {
    return []
  }

  return [{
    kind: 'created',
    task_id: taskId ?? null,
    state: 'created',
    agent: 'Task created',
    started_at: createdAt,
    duration: null,
    outcome: 'Created',
  }]
}

export default function HistorySubtab({ sessions, taskId, createdAt, onSelectTask }: HistorySubtabProps) {
  const historyRows: HistoryRow[] = [
    ...buildCreationEvent(taskId, createdAt),
    ...sessions.map((session) => ({ ...session, kind: 'session' as const })),
  ]

  function navigateToTask(taskId: number | null): void {
    if (taskId !== null) {
      onSelectTask?.(taskId, 'history')
    }
  }

  return (
    <div data-testid="history-view" className="grid gap-static-xs">
      {historyRows.length === 0 ? (
        <p data-testid="history-empty-state" className="m-0 rounded-lg border border-contrast-low bg-surface p-static-sm text-sm text-primary">
          No history yet
        </p>
      ) : null}
      {historyRows.map((session, index) => (
        <div
          key={`${session.state}:${session.started_at}:${index}`}
          data-testid={session.kind === 'created' ? 'history-created-row' : 'history-session-row'}
          data-state={session.state}
          role="button"
          aria-disabled={session.task_id === null ? 'true' : undefined}
          aria-label={session.task_id !== null ? `Open task #${session.task_id} history` : 'Session without linked task'}
          tabIndex={0}
          className="history-session-row grid min-h-12 gap-1 rounded-md border border-contrast-low bg-surface p-static-xs text-sm text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] sm:grid-cols-[minmax(0,1fr)_auto_auto_auto] sm:items-center"
          onClick={() => navigateToTask(session.task_id)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              navigateToTask(session.task_id)
            }
          }}
        >
          <span data-testid="session-agent" className="min-w-0 truncate font-semibold">{session.agent ?? 'unknown agent'}</span>
          <span data-testid="session-started-at" data-timestamp={session.started_at} className="text-xs font-semibold text-contrast-high">{formatTimestamp(session.started_at)}</span>
          <span data-testid="session-duration" className="rounded-full bg-canvas px-static-xs py-1 text-xs font-semibold">{formatDuration(session.duration)}</span>
          <span data-testid="session-outcome" className="text-xs font-semibold text-primary">{session.outcome ?? session.state}</span>
        </div>
      ))}
    </div>
  )
}
