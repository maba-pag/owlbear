import { rowStyleForState } from '../utils/styles'

export interface Session {
  task_id: number
  state: string
  agent: string
  started_at: string
  duration: number | null
  outcome: string | null
}

export interface HistorySubtabProps {
  sessions: Session[]
  onSelectTask?: (taskId: number, subtab?: string) => void
}

export default function HistorySubtab({ sessions, onSelectTask }: HistorySubtabProps) {
  return (
    <div data-testid="history-view">
      {sessions.map((s, i) => (
        <div
          key={i}
          data-testid="history-session-row"
          data-state={s.state}
          onClick={() => onSelectTask?.(s.task_id, 'history')}
          style={rowStyleForState(s.state)}
        >
          <span data-testid="session-agent">{s.agent}</span>
          <span data-testid="session-duration">{s.duration ?? '\u2014'}</span>
          <span data-testid="session-outcome">{s.outcome}</span>
        </div>
      ))}
    </div>
  )
}
