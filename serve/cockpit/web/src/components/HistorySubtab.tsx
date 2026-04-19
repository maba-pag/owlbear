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
}

export default function HistorySubtab({ sessions }: HistorySubtabProps) {
  return (
    <div data-testid="history-view">
      {sessions.map((s, i) => (
        <div key={i} data-testid="history-session-row">
          <span data-testid="session-agent">{s.agent}</span>
          <span data-testid="session-duration">{s.duration ?? '\u2014'}</span>
          <span data-testid="session-outcome">{s.outcome}</span>
        </div>
      ))}
    </div>
  )
}
